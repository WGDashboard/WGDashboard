"""
Peer Job Logger
"""
import uuid
import sqlalchemy as db
from flask import current_app
from .ConnectionString import ConnectionString, DEFAULT_LOG_DB
from .Log import Log

class PeerJobLogger:
    def __init__(self, AllPeerJobs, DashboardConfig):
        self.engine = db.create_engine(ConnectionString(DEFAULT_LOG_DB))                
        self.metadata = db.MetaData()
        self.jobLogTable = db.Table('JobLog', self.metadata,
                                    db.Column('LogID', db.String(255), nullable=False, primary_key=True),
                                    db.Column('JobID', db.String(255), nullable=False),
                                    db.Column('LogDate', (db.DATETIME if DashboardConfig.GetConfig("Database", "type")[1] == 'sqlite' else db.TIMESTAMP), 
                                              server_default=db.func.now()),
                                    db.Column('Status', db.String(255), nullable=False),
                                    db.Column('Message', db.Text)
                                    )
        self.logs: list[Log] = []
        self.metadata.create_all(self.engine)
        self.AllPeerJobs = AllPeerJobs
    def log(self, JobID: str, Status: bool = True, Message: str = "") -> bool:
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.jobLogTable.insert().values(
                        {
                            "LogID": str(uuid.uuid4()), 
                            "JobID": JobID, 
                            "Status": Status, 
                            "Message": Message
                        }
                    )
                )
        except Exception as e:
            current_app.logger.error(f"Peer Job Log Error", e)
            return False
        return True

    def getLogs(self, configName = None) -> list[Log]:
        logs: list[Log] = []
        try:
            allJobs = self.AllPeerJobs.getAllJobs(configName)
            allJobsID = [x.JobID for x in allJobs]
            stmt = self.jobLogTable.select().where(self.jobLogTable.columns.JobID.in_(
                allJobsID
            ))
            with self.engine.connect() as conn:
                table = conn.execute(stmt).fetchall()
                for l in table:
                    logs.append(
                        Log(l.LogID, l.JobID, l.LogDate.strftime("%Y-%m-%d %H:%M:%S"), l.Status, l.Message))
        except Exception as e:
            current_app.logger.error(f"Getting Peer Job Log Error", e)
            return logs
        return logs