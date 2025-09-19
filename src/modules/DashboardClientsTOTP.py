import datetime
import hashlib
import uuid

import sqlalchemy as db
from .ConnectionString import ConnectionString, DEFAULT_DB


class DashboardClientsTOTP:
    def __init__(self):
        self.engine = db.create_engine(ConnectionString(DEFAULT_DB))
        self.metadata = db.MetaData()
        self.dashboardClientsTOTPTable = db.Table(
            'DashboardClientsTOTPTokens', self.metadata,
            db.Column("Token", db.String(500), primary_key=True, index=True),
                db.Column("ClientID", db.String(500), index=True),
                db.Column(
                    "ExpireTime", (db.DATETIME if 'sqlite:///' in ConnectionString(DEFAULT_DB) else db.TIMESTAMP)
                )
        )
        self.metadata.create_all(self.engine)
        self.metadata.reflect(self.engine)
        self.dashboardClientsTable = self.metadata.tables['DashboardClients']
        
    def GenerateToken(self, ClientID) -> str:
        token = hashlib.sha512(f"{ClientID}_{datetime.datetime.now()}_{uuid.uuid4()}".encode()).hexdigest()
        with self.engine.begin() as conn:
            conn.execute(
                self.dashboardClientsTOTPTable.update().values({
                    "ExpireTime": datetime.datetime.now()
                }).where(
                   db.and_(self.dashboardClientsTOTPTable.c.ClientID == ClientID,  self.dashboardClientsTOTPTable.c.ExpireTime > datetime.datetime.now())
                )
            )
            conn.execute(
                self.dashboardClientsTOTPTable.insert().values({
                    "Token": token,
                    "ClientID": ClientID,
                    "ExpireTime": datetime.datetime.now() + datetime.timedelta(minutes=10)
                })
            )
        return token
    
    def RevokeToken(self, Token) -> bool:
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.dashboardClientsTOTPTable.update().values({
                        "ExpireTime": datetime.datetime.now()
                    }).where(
                        self.dashboardClientsTOTPTable.c.Token == Token
                    )
                )
        except Exception as e:
            return False
        return True
    
    def GetTotp(self, token: str) -> tuple[bool, dict] or tuple[bool, None]:
        with self.engine.connect() as conn:
            totp = conn.execute(
                db.select(
                    self.dashboardClientsTable.c.ClientID,
                    self.dashboardClientsTable.c.Email,
                    self.dashboardClientsTable.c.TotpKey,
                    self.dashboardClientsTable.c.TotpKeyVerified,
                ).select_from(
                    self.dashboardClientsTOTPTable
                ).where(
                    db.and_(
                        self.dashboardClientsTOTPTable.c.Token == token,
                        self.dashboardClientsTOTPTable.c.ExpireTime > datetime.datetime.now()
                    )
                ).join(
                    self.dashboardClientsTable,
                    self.dashboardClientsTOTPTable.c.ClientID == self.dashboardClientsTable.c.ClientID
                )            
            ).mappings().fetchone()
            if totp:
                return True, dict(totp)
        return False, None

        