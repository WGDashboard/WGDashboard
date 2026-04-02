import json
import threading
import time
import urllib.parse
import uuid
from datetime import datetime, timedelta

import requests
from pydantic import BaseModel, field_serializer
import sqlalchemy as db
from .ConnectionString import ConnectionString
from flask import current_app

WebHookActions = ['peer_created', 'peer_deleted', 'peer_updated']
class WebHook(BaseModel):
    WebHookID: str = ''
    PayloadURL: str = ''
    ContentType: str = 'application/json'
    Headers: dict[str, dict[str, str]] = {}
    VerifySSL: bool = True
    SubscribedActions: list[str] = WebHookActions
    IsActive: bool = True
    CreationDate: datetime = ''
    Notes: str = ''

class WebHookSessionLog(BaseModel):
    LogTime: datetime
    Status: int
    Message: str = ''
    
    @field_serializer('LogTime')
    def logTimeSerializer(self, LogTime: datetime):
        return LogTime.strftime("%Y-%m-%d %H:%M:%S")

class WebHookSessionLogs(BaseModel):
    Logs: list[WebHookSessionLog] = []
    
    def addLog(self, status: int, message: str):
        self.Logs.append(WebHookSessionLog(LogTime=datetime.now(), Status=status, Message=message))

class DashboardWebHooks:
    def __init__(self, DashboardConfig):
        self.engine = db.create_engine(ConnectionString("wgdashboard"))
        self.metadata = db.MetaData()
        self.webHooksTable = db.Table(
            'DashboardWebHooks', self.metadata,
            db.Column('WebHookID', db.String(255), nullable=False, primary_key=True),
            db.Column('PayloadURL', db.Text, nullable=False),
            db.Column('ContentType', db.String(255), nullable=False),
            db.Column('Headers', db.JSON),
            db.Column('VerifySSL', db.Boolean, nullable=False),
            db.Column('SubscribedActions', db.JSON),
            db.Column('IsActive', db.Boolean, nullable=False),
            db.Column('CreationDate',
                      (db.DATETIME if DashboardConfig.GetConfig("Database", "type")[1] == 'sqlite' else db.TIMESTAMP),
                      server_default=db.func.now(),
                      nullable=False),
            db.Column('Notes', db.Text),
            extend_existing=True
        )
        self.webHookSessionsTable = db.Table(
            'DashboardWebHookSessions', self.metadata,
            db.Column('WebHookSessionID', db.String(255), nullable=False, primary_key=True),
            db.Column('WebHookID', db.String(255), nullable=False),
            db.Column('StartDate', 
                      (db.DATETIME if DashboardConfig.GetConfig("Database", "type")[1] == 'sqlite' else db.TIMESTAMP),
                      server_default=db.func.now(),
                      nullable=False
            ),
            db.Column('EndDate',
                      (db.DATETIME if DashboardConfig.GetConfig("Database", "type")[1] == 'sqlite' else db.TIMESTAMP),
            ),
            db.Column('Data', db.JSON),
            db.Column('Status', db.INTEGER),
            db.Column('Logs', db.JSON)
        )
        
        self.metadata.create_all(self.engine)
        self.WebHooks: list[WebHook] = []
        
        with self.engine.begin() as conn:
           conn.execute(
               self.webHookSessionsTable.update().values({
                   "EndDate": datetime.now(),
                   "Status": 2
               }).where(
                   self.webHookSessionsTable.c.Status == -1
               )
           )
        
        self.__getWebHooks()
        
    def __getWebHooks(self):
        with self.engine.connect() as conn:
            webhooks = conn.execute(
                self.webHooksTable.select().order_by(
                    self.webHooksTable.c.CreationDate
                )
            ).mappings().fetchall()
            self.WebHooks.clear()
            self.WebHooks = [WebHook(**webhook) for webhook in webhooks]
            
    def GetWebHooks(self):
        self.__getWebHooks()
        return list(map(lambda x : x.model_dump(), self.WebHooks))
    
    def GetWebHookSessions(self, webHook: WebHook):
        with self.engine.connect() as conn:
            sessions = conn.execute(
                self.webHookSessionsTable.select().where(
                    self.webHookSessionsTable.c.WebHookID == webHook.WebHookID
                ).order_by(
                    db.desc(self.webHookSessionsTable.c.StartDate)
                )
            ).mappings().fetchall()
        return sessions
    
    def CreateWebHook(self) -> WebHook:
        return WebHook(WebHookID=str(uuid.uuid4()))
    
    def SearchWebHook(self, webHook: WebHook) -> WebHook | None:
        try:
            first = next(filter(lambda x : x.WebHookID == webHook.WebHookID, self.WebHooks))
        except StopIteration:
            return None
        return first
    
    def SearchWebHookByID(self, webHookID: str) -> WebHook | None:
        try:
            first = next(filter(lambda x : x.WebHookID == webHookID, self.WebHooks))
        except StopIteration:
            return None
        return first
    
    def UpdateWebHook(self, webHook: dict[str, str]) -> tuple[bool, str] | tuple[bool, None]:
        try:
            webHook = WebHook(**webHook)
            
            if len(webHook.PayloadURL) == 0:
                return False, "Payload URL cannot be empty"
            
            if len(webHook.ContentType) == 0 or webHook.ContentType not in [
                'application/json', 'application/x-www-form-urlencoded'
            ]:
                return False, "Content Type is invalid"
            
            
            with self.engine.begin() as conn:
                if self.SearchWebHook(webHook):
                    conn.execute(
                        self.webHooksTable.update().values(
                            webHook.model_dump(exclude={'WebHookID'})
                        ).where(
                            self.webHooksTable.c.WebHookID == webHook.WebHookID
                        )
                    )
                else:
                    webHook.CreationDate = datetime.now()
                    conn.execute(
                        self.webHooksTable.insert().values(
                            webHook.model_dump()
                        )
                    )
            self.__getWebHooks()
        except Exception as e:
            return False, str(e)
        return True, None
    
    def DeleteWebHook(self, webHook) -> tuple[bool, str] | tuple[bool, None]:
        try:
            webHook = WebHook(**webHook)
            with self.engine.begin() as conn:
                conn.execute(
                    self.webHooksTable.delete().where(
                        self.webHooksTable.c.WebHookID == webHook.WebHookID
                    )
                )
            self.__getWebHooks()
        except Exception as e:
            return False, str(e)
        return True, None
    
    def RunWebHook(self, action: str, data):
        try:
            if action not in WebHookActions:
                return False
            self.__getWebHooks()
            subscribedWebHooks = filter(lambda webhook: action in webhook.SubscribedActions and webhook.IsActive, 
                                        self.WebHooks)
            data['action'] = action
            for i in subscribedWebHooks:
                try:
                    ws = WebHookSession(i, data)
                    t = threading.Thread(target=ws.Execute, daemon=True)
                    t.start()
                    current_app.logger.info(f"Requesting {i.PayloadURL}")
                except Exception as e:
                    current_app.logger.error(f"Requesting {i.PayloadURL} error", e)
        except Exception as e:
            current_app.logger.error("Error when running WebHook")

class WebHookSession:
    def __init__(self, webHook: WebHook, data: dict[str, str]):
        self.engine = db.create_engine(ConnectionString("wgdashboard"))
        self.metadata = db.MetaData()
        self.webHookSessionsTable = db.Table('DashboardWebHookSessions', self.metadata, autoload_with=self.engine)
        self.webHook = webHook
        self.sessionID = str(uuid.uuid4())
        self.webHookSessionLogs: WebHookSessionLogs = WebHookSessionLogs()
        self.time = datetime.now()
        data['time'] = self.time.strftime("%Y-%m-%d %H:%M:%S")
        data['webhook_id'] = webHook.WebHookID
        data['webhook_session'] = self.sessionID
        self.data = data
        self.Prepare()
        
    def Prepare(self):
        with self.engine.begin() as conn:
            conn.execute(
                self.webHookSessionsTable.insert().values({
                    "WebHookSessionID": self.sessionID,
                    "WebHookID": self.webHook.WebHookID,
                    "Data": self.data,
                    "StartDate": self.time,
                    "Status": -1,
                    "Logs": self.webHookSessionLogs.model_dump()
                })
            )
        self.UpdateSessionLog(-1, "Preparing webhook session")
            
    def UpdateSessionLog(self, status, message):
        self.webHookSessionLogs.addLog(status, message)
        with self.engine.begin() as conn:
            conn.execute(
                self.webHookSessionsTable.update().values({
                    "Logs": self.webHookSessionLogs.model_dump()
                }).where(
                    self.webHookSessionsTable.c.WebHookSessionID == self.sessionID
                )
            )
    
    def UpdateStatus(self, status: int):
        with self.engine.begin() as conn:
            conn.execute(
                self.webHookSessionsTable.update().values({
                    "Status": status,
                    "EndDate": datetime.now()
                }).where(
                    self.webHookSessionsTable.c.WebHookSessionID == self.sessionID
                )
            )
    
    def Execute(self):
        success = False
        
        for i in range(5):
            headerDictionary = {
                'Content-Type': self.webHook.ContentType
            }
            for header in self.webHook.Headers.values():
                if header['key'] not in ['Content-Type']:
                    headerDictionary[header['key']] = header['value']
                
            if self.webHook.ContentType == "application/json":
                reqData = json.dumps(self.data)
            else:
                for (key, val) in self.data.items():
                    if type(self.data[key]) not in [str, int]:
                        self.data[key] = json.dumps(self.data[key])
                reqData = urllib.parse.urlencode(self.data)
            try:
                req = requests.post(
                    self.webHook.PayloadURL, headers=headerDictionary, timeout=10, data=reqData, verify=self.webHook.VerifySSL
                )
                req.raise_for_status()
                success = True
                self.UpdateSessionLog(0, "Webhook request finished")
                self.UpdateSessionLog(0, json.dumps({"returned_data": req.text}))
                self.UpdateStatus(0)
                break
            except requests.exceptions.RequestException as e:
                self.UpdateSessionLog(1, f"Attempt #{i + 1}/5. Request errored. Reason: " + str(e))
            time.sleep(10)
        
        if not success:
            self.UpdateSessionLog(1, "Webhook request failed & terminated.")
            self.UpdateStatus(1)