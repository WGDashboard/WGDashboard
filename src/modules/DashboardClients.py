import datetime
import hashlib
import uuid

import bcrypt
import pyotp
import sqlalchemy as db
import requests

from .ConnectionString import ConnectionString
from .DashboardClientsPeerAssignment import DashboardClientsPeerAssignment
from .DashboardClientsTOTP import DashboardClientsTOTP
from .DashboardOIDC import DashboardOIDC
from .Utilities import ValidatePasswordStrength
from .DashboardLogger import DashboardLogger
from flask import session


class DashboardClients:
    def __init__(self, wireguardConfigurations):
        self.logger = DashboardLogger()
        self.engine = db.create_engine(ConnectionString("wgdashboard"))
        self.metadata = db.MetaData()
        self.OIDC = DashboardOIDC("Client")
        
        self.dashboardClientsTable = db.Table(
            'DashboardClients', self.metadata,
            db.Column('ClientID', db.String(255), nullable=False, primary_key=True),
            db.Column('Email', db.String(255), nullable=False, index=True),
            db.Column('Password', db.String(500)),
            db.Column('TotpKey', db.String(500)),
            db.Column('TotpKeyVerified', db.Integer),
            db.Column('CreatedDate', 
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP),
                      server_default=db.func.now()),
            db.Column('DeletedDate', 
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP)),
            extend_existing=True,
        )
        
        self.dashboardOIDCClientsTable = db.Table(
            'DashboardOIDCClients', self.metadata,
            db.Column('ClientID', db.String(255), nullable=False, primary_key=True),
            db.Column('Email', db.String(255), nullable=False, index=True),
            db.Column('ProviderIssuer', db.String(500), nullable=False, index=True),
            db.Column('ProviderSubject', db.String(500), nullable=False, index=True),
            db.Column('CreatedDate',
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP),
                      server_default=db.func.now()),
            db.Column('DeletedDate',
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP)),
            extend_existing=True,
        )

        self.dashboardClientsInfoTable = db.Table(
            'DashboardClientsInfo', self.metadata,
            db.Column('ClientID', db.String(255), nullable=False, primary_key=True),
            db.Column('Name', db.String(500)),
            extend_existing=True,   
        )
        
        self.dashboardClientsPasswordResetLinkTable = db.Table(
            'DashboardClientsPasswordResetLinks', self.metadata,
            db.Column('ResetToken', db.String(255), nullable=False, primary_key=True),
            db.Column('ClientID', db.String(255), nullable=False),
            db.Column('CreatedDate',
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP),
                      server_default=db.func.now()),
            db.Column('ExpiryDate',
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP)),
            extend_existing=True
        )

        self.metadata.create_all(self.engine)
        self.Clients = {}
        self.ClientsRaw = []
        self.__getClients()
        self.DashboardClientsTOTP = DashboardClientsTOTP()
        self.DashboardClientsPeerAssignment = DashboardClientsPeerAssignment(wireguardConfigurations)
        
    def __getClients(self):
        with self.engine.connect() as conn:
            localClients = db.select(
                self.dashboardClientsTable.c.ClientID,
                self.dashboardClientsTable.c.Email,
                db.literal_column("'Local'").label("ClientGroup")
            ).where(
                self.dashboardClientsTable.c.DeletedDate.is_(None)
            )
            
            oidcClients = db.select(
                self.dashboardOIDCClientsTable.c.ClientID,
                self.dashboardOIDCClientsTable.c.Email,
                self.dashboardOIDCClientsTable.c.ProviderIssuer.label("ClientGroup"),
            ).where(
                self.dashboardOIDCClientsTable.c.DeletedDate.is_(None)
            )
            
            union = db.union(localClients, oidcClients).alias("U")
            
            self.ClientsRaw = conn.execute(
                db.select(
                    union, 
                    self.dashboardClientsInfoTable.c.Name
                ).outerjoin(self.dashboardClientsInfoTable, 
                            union.c.ClientID == self.dashboardClientsInfoTable.c.ClientID)
            ).mappings().fetchall()
            
            groups = set(map(lambda c: c.get('ClientGroup'), self.ClientsRaw))
            gr = {}
            for g in groups:
                gr[(g if g == 'Local' else self.OIDC.GetProviderNameByIssuer(g))] = [
                    dict(x) for x in list(
                        filter(lambda c: c.get('ClientGroup') == g, self.ClientsRaw)
                    )
                ]
            self.Clients = gr
            
    def GetAllClients(self):
        self.__getClients()
        return self.Clients
    
    def GetAllClientsRaw(self):
        self.__getClients()
        return self.ClientsRaw
    
    def GetClient(self, ClientID) -> dict[str, str] | None:
        c = filter(lambda x: x['ClientID'] == ClientID, self.ClientsRaw)
        client = next((dict(client) for client in c), None)
        if client is not None:
            client['ClientGroup'] = self.OIDC.GetProviderNameByIssuer(client['ClientGroup'])
        return client
    
    def GetClientProfile(self, ClientID):
        with self.engine.connect() as conn:
            return dict(conn.execute(
                db.select(
                    *[c for c in self.dashboardClientsInfoTable.c if c.name != 'ClientID']
                ).where(
                    self.dashboardClientsInfoTable.c.ClientID == ClientID
                )
            ).mappings().fetchone())
    
    def SignIn_ValidatePassword(self, Email, Password) -> bool:
        if not all([Email, Password]):
            return False
        existingClient = self.SignIn_UserExistence(Email)
        if existingClient:
            return bcrypt.checkpw(Password.encode("utf-8"), existingClient.get("Password").encode("utf-8"))            
        return False
        
    def SignIn_UserExistence(self, Email):
        with self.engine.connect() as conn:
            existingClient = conn.execute(
                self.dashboardClientsTable.select().where(
                    self.dashboardClientsTable.c.Email == Email
                )
            ).mappings().fetchone()
            return existingClient
    
    def SignIn_OIDC_UserExistence(self, data: dict[str, str]):
        with self.engine.connect() as conn:
            existingClient = conn.execute(
                self.dashboardOIDCClientsTable.select().where(
                    db.and_(
                        self.dashboardOIDCClientsTable.c.ProviderIssuer == data.get('iss'),
                        self.dashboardOIDCClientsTable.c.ProviderSubject == data.get('sub'),
                    )
                )
            ).mappings().fetchone()
            return existingClient
        
    def SignUp_OIDC(self, data: dict[str, str]) -> tuple[bool, str] | tuple[bool, None]:
        if not self.SignIn_OIDC_UserExistence(data):
            with self.engine.begin() as conn:
                newClientUUID = str(uuid.uuid4())
                conn.execute(
                    self.dashboardOIDCClientsTable.insert().values({
                        "ClientID": newClientUUID,
                        "Email": data.get('email', ''),
                        "ProviderIssuer": data.get('iss', ''),
                        "ProviderSubject": data.get('sub', '')
                    })
                )
                conn.execute(
                    self.dashboardClientsInfoTable.insert().values({
                        "ClientID": newClientUUID,
                        "Name": data.get("name")
                    })
                )
                self.logger.log(Message=f"User {data.get('email', '')} from {data.get('iss', '')} signed up")
            self.__getClients()
            return True, newClientUUID
        return False, "User already signed up"
    
    def SignOut_OIDC(self):
        sessionPayload = session.get('OIDCPayload')
        status, oidc_config = self.OIDC.GetProviderConfiguration(session.get('SignInPayload').get("Provider"))        
        signOut = requests.get(
            oidc_config.get("end_session_endpoint"), 
            params={
                'id_token_hint': session.get('SignInPayload').get("Payload").get('sid')
            }
        )
        return True
        
    def SignIn_OIDC(self, **kwargs):
        status, data = self.OIDC.VerifyToken(**kwargs)
        if not status:
            return False, "Sign in failed. Reason: " + data
        existingClient = self.SignIn_OIDC_UserExistence(data)
        print(data)
        if not existingClient:
            status, newClientUUID = self.SignUp_OIDC(data)
            session['ClientID'] = newClientUUID
        else:
            session['ClientID'] = existingClient.get("ClientID")
        session['SignInMethod'] = 'OIDC'
        session['SignInPayload'] = {
            "Provider": kwargs.get('provider'),
            "Payload": data
        }
        return True, data
        
    def SignIn(self, Email, Password) -> tuple[bool, str]:
        if not all([Email, Password]):
            return False, "Please fill in all fields"
        existingClient = self.SignIn_UserExistence(Email)
        if existingClient:
            checkPwd = self.SignIn_ValidatePassword(Email, Password)
            if checkPwd:
                session['SignInMethod'] = 'local'
                session['Email'] = Email
                session['ClientID'] = existingClient.get("ClientID")
                return True, self.DashboardClientsTOTP.GenerateToken(existingClient.get("ClientID"))
        return False, "Email or Password is incorrect"
    
    def SignIn_GetTotp(self, Token: str, UserProvidedTotp: str = None) -> tuple[bool, str] or tuple[bool, None, str]:
        status, data = self.DashboardClientsTOTP.GetTotp(Token)
        
        if not status:
            return False, "TOTP Token is invalid"    
        if UserProvidedTotp is None:
            if data.get('TotpKeyVerified') is None:
                return True, pyotp.totp.TOTP(data.get('TotpKey')).provisioning_uri(name=data.get('Email'),
                                                                                   issuer_name="WGDashboard Client")
        else:
            totpMatched = pyotp.totp.TOTP(data.get('TotpKey')).verify(UserProvidedTotp)
            if not totpMatched:
                return False, "TOTP is does not match"
            else:
                self.DashboardClientsTOTP.RevokeToken(Token)
        if data.get('TotpKeyVerified') is None:
            with self.engine.begin() as conn:
                conn.execute(
                    self.dashboardClientsTable.update().values({
                        'TotpKeyVerified': 1
                    }).where(
                        self.dashboardClientsTable.c.ClientID == data.get('ClientID')
                    )
                )
              
        return True, None
        
    def SignUp(self, Email, Password, ConfirmPassword) -> tuple[bool, str] or tuple[bool, None]:
        try:
            if not all([Email, Password, ConfirmPassword]):
                return False, "Please fill in all fields"
            if Password != ConfirmPassword:
                return False, "Passwords does not match"

            existingClient = self.SignIn_UserExistence(Email)
            if existingClient:
                return False, "Email already signed up"
    
            pwStrength, msg = ValidatePasswordStrength(Password)
            if not pwStrength:
                return pwStrength, msg
    
            with self.engine.begin() as conn:
                newClientUUID = str(uuid.uuid4())
                totpKey = pyotp.random_base32()
                encodePassword = Password.encode('utf-8')
                conn.execute(
                    self.dashboardClientsTable.insert().values({
                        "ClientID": newClientUUID,
                        "Email": Email,
                        "Password": bcrypt.hashpw(encodePassword, bcrypt.gensalt()).decode("utf-8"),
                        "TotpKey": totpKey
                    })
                )
                conn.execute(
                    self.dashboardClientsInfoTable.insert().values({
                        "ClientID": newClientUUID
                    })
                )
                self.logger.log(Message=f"User {Email} signed up")
            self.__getClients()
        except Exception as e:
            self.logger.log(Status="false", Message=f"Signed up failed, reason: {str(e)}")
            return False, "Signe up failed."
            
        return True, None
    
    def GetClientAssignedPeers(self, ClientID):
        return self.DashboardClientsPeerAssignment.GetAssignedPeers(ClientID)
            
    def UpdateClientPassword(self, Email, CurrentPassword, NewPassword, ConfirmNewPassword):
        if not all([CurrentPassword, NewPassword, ConfirmNewPassword]):
            return False, "Please fill in all fields"
        
        if not self.SignIn_ValidatePassword(Email, CurrentPassword):
            return False, "Current password does not match"
        
        if NewPassword != ConfirmNewPassword:
            return False, "New passwords does not match"

        pwStrength, msg = ValidatePasswordStrength(NewPassword)
        if not pwStrength:
            return pwStrength, msg
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.dashboardClientsTable.update().values({
                        "Password": bcrypt.hashpw(NewPassword.encode('utf-8'), bcrypt.gensalt()).decode("utf-8"),
                    }).where(
                        self.dashboardClientsTable.c.Email == Email
                    )
                )
                self.logger.log(Message=f"User {Email} updated password")
        except Exception as e:
            self.logger.log(Status="false", Message=f"Signed up failed, reason: {str(e)}")
            return False, "Signed up failed."
        return True, None
    
    def UpdateClientProfile(self, ClientID, Name):
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.dashboardClientsInfoTable.update().values({
                        "Name": Name
                    }).where(
                        self.dashboardClientsInfoTable.c.ClientID == ClientID
                    )
                )
            self.logger.log(Message=f"User {ClientID} updated name to {Name}")
        except Exception as e:
            self.logger.log(Status="false", Message=f"User {ClientID} updated name to {Name} failed")
            return False
        return True
    
    def DeleteClient(self, ClientID):
        try:
            with self.engine.begin() as conn:
                client = self.GetClient(ClientID)
                if client.get("ClientGroup") == "Local":
                    conn.execute(
                        self.dashboardClientsTable.delete().where(
                            self.dashboardClientsTable.c.ClientID == ClientID
                        )
                    )
                else:
                    conn.execute(
                        self.dashboardOIDCClientsTable.delete().where(
                            self.dashboardOIDCClientsTable.c.ClientID == ClientID
                        )
                    )
                conn.execute(
                    self.dashboardClientsInfoTable.delete().where(
                        self.dashboardClientsInfoTable.c.ClientID == ClientID
                    )
                )
            self.DashboardClientsPeerAssignment.UnassignPeers(ClientID)
            self.__getClients()
        except Exception as e:
            self.logger.log(Status="false", Message=f"Failed to delete {ClientID}")
            return False
        return True
    
    '''
    For WGDashboard Admin to Manage Clients
    '''

    def GenerateClientPasswordResetLink(self, ClientID) -> bool | str:
        c = self.GetClient(ClientID)
        if c is None:
            return False
        
        newToken = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                self.dashboardClientsPasswordResetLinkTable.update().values({
                    "ExpiryDate": db.func.now()
                }).where(
                    db.and_(
                        self.dashboardClientsPasswordResetLinkTable.c.ClientID == ClientID,
                        self.dashboardClientsPasswordResetLinkTable.c.ExpiryDate > db.func.now()
                    )
                )
            )
            conn.execute(
                self.dashboardClientsPasswordResetLinkTable.insert().values({
                    "ResetToken": newToken,
                    "ClientID": ClientID,
                    "ExpiryDate": datetime.datetime.now() + datetime.timedelta(minutes=30)
                })
            )
        
        return newToken
        
        
    
    def GetAssignedPeerClients(self, ConfigurationName, PeerID):
        c = self.DashboardClientsPeerAssignment.GetAssignedClients(ConfigurationName, PeerID)
        for a in c:
            client = self.GetClient(a.ClientID)
            if client is not None:
                a.Client = self.GetClient(a.ClientID)
        return c
    
    def GetClientAssignedPeersGrouped(self, ClientID):
        client = self.GetClient(ClientID)
        if client is not None:
            p = self.DashboardClientsPeerAssignment.GetAssignedPeers(ClientID)
            configs = set(map(lambda x : x['configuration_name'], p))
            d = {}
            for i in configs:
                d[i] = list(filter(lambda x : x['configuration_name'] == i, p)) 
            return d
        return None

    def AssignClient(self, ConfigurationName, PeerID, ClientID) -> tuple[bool, dict[str, str]] | tuple[bool, None]:
        return self.DashboardClientsPeerAssignment.AssignClient(ClientID, ConfigurationName, PeerID) 
    
    def UnassignClient(self, AssignmentID):
        return self.DashboardClientsPeerAssignment.UnassignClients(AssignmentID)
        