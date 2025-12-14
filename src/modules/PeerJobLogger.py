"""
Peer Job Logger
"""
import uuid
from typing import Sequence

import sqlalchemy as db
from flask import current_app
from sqlalchemy import RowMapping

from .ConnectionString import ConnectionString
from .Log import Log

class PeerJobLogger:
    def __init__(self, AllPeerJobs, DashboardConfig):
        self.engine = db.create_engine(ConnectionString("wgdashboard_log"))                
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
    
    def getFailingJobs(self) -> Sequence[RowMapping]:
        with self.engine.connect() as conn:
            table = conn.execute(
                db.select(
                    self.jobLogTable.c.JobID
                ).where(
                    (db.or_(
                        self.jobLogTable.c.Status == 'false',
                        self.jobLogTable.c.Status == 0
                    ) if conn.dialect.name == 'sqlite' else self.jobLogTable.c.Status == 'false')
                ).group_by(
                    self.jobLogTable.c.JobID
                ).having(
                    db.func.count(
                        self.jobLogTable.c.JobID
                    ) > 10
                )
            ).mappings().fetchall()
            return table
    
    def deleteLogs(self, LogID = None, JobID = None):
        with self.engine.begin() as conn:
            print(f"[WGDashboard] Deleted stale logs of JobID: {JobID}")
            conn.execute(
                self.jobLogTable.delete().where(
                    db.and_(
                        (self.jobLogTable.c.LogID == LogID if LogID is not None else True),
                        (self.jobLogTable.c.JobID == JobID if JobID is not None else True),
                    )
                )
            )
    
    def vacuum(self):
        with self.engine.begin() as conn:
            if conn.dialect.name == 'sqlite':
                print("[WGDashboard] SQLite Vacuuming PeerJobLogs Database")
                conn.execute(db.text('VACUUM;'))