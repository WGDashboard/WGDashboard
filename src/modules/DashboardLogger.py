"""
Dashboard Logger Class
"""
import uuid
import sqlalchemy as db
from flask import current_app
from .ConnectionString import ConnectionString, DEFAULT_DB, DEFAULT_LOG_DB


class DashboardLogger:
    def __init__(self):
        self.engine = db.create_engine(ConnectionString(DEFAULT_LOG_DB))
        self.metadata = db.MetaData()
        self.dashboardLoggerTable = db.Table('DashboardLog', self.metadata,
                                             
                                             db.Column('LogID', db.String(255), nullable=False, primary_key=True),
                                             db.Column('LogDate',
                                                       (db.DATETIME if 'sqlite:///' in ConnectionString(DEFAULT_DB) else db.TIMESTAMP),
                                                       server_default=db.func.now()),
                                             db.Column('URL', db.String(255)),
                                             db.Column('IP', db.String(255)),
                                             
                                             db.Column('Status', db.String(255), nullable=False),
                                             db.Column('Message', db.Text), extend_existing=True,
                                             )
        self.metadata.create_all(self.engine)
        self.log(Message="WGDashboard started")

    def log(self, URL: str = "", IP: str = "", Status: str = "true", Message: str = "") -> bool:
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.dashboardLoggerTable.insert().values(
                        LogID=str(uuid.uuid4()),
                        URL=URL,
                        IP=IP,
                        Status=Status,
                        Message=Message
                    )
                )
            return True
        except Exception as e:
            current_app.logger.error(f"Access Log Error", e)
            return False