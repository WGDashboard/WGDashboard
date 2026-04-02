import datetime
import uuid

from .ConnectionString import ConnectionString
from .DashboardLogger import DashboardLogger
import sqlalchemy as db
from .WireguardConfiguration import WireguardConfiguration

class Assignment:
    def __init__(self, **kwargs):
        self.AssignmentID: str = kwargs.get('AssignmentID')
        self.ClientID: str = kwargs.get('ClientID')
        self.ConfigurationName: str = kwargs.get('ConfigurationName')
        self.PeerID: str = kwargs.get('PeerID')
        self.AssignedDate: datetime.datetime = kwargs.get('AssignedDate')
        self.UnassignedDate: datetime.datetime = kwargs.get('UnassignedDate')
        self.Client: dict = {
            "ClientID": self.ClientID
        }
    
    def toJson(self):
        return {
            "AssignmentID": self.AssignmentID,
            "Client": self.Client,
            "ConfigurationName": self.ConfigurationName,
            "PeerID": self.PeerID,
            "AssignedDate": self.AssignedDate.strftime("%Y-%m-%d %H:%M:%S"),
            "UnassignedDate": self.UnassignedDate.strftime("%Y-%m-%d %H:%M:%S") if self.UnassignedDate is not None else self.UnassignedDate
        }
        
class DashboardClientsPeerAssignment:
    def __init__(self, wireguardConfigurations: dict[str, WireguardConfiguration]):
        self.logger = DashboardLogger()
        self.engine = db.create_engine(ConnectionString("wgdashboard"))
        self.metadata = db.MetaData()
        self.wireguardConfigurations = wireguardConfigurations
        self.dashboardClientsPeerAssignmentTable = db.Table(
            'DashboardClientsPeerAssignment', self.metadata,
            db.Column('AssignmentID', db.String(255), nullable=False, primary_key=True),
            db.Column('ClientID', db.String(255), nullable=False, index=True),
            db.Column('ConfigurationName', db.String(255)),
            db.Column('PeerID', db.String(500)),
            db.Column('AssignedDate',
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP),
                      server_default=db.func.now()),
            db.Column('UnassignedDate',
                      (db.DATETIME if 'sqlite:///' in ConnectionString("wgdashboard") else db.TIMESTAMP)),
            extend_existing=True
        )
        self.metadata.create_all(self.engine)
        self.assignments: list[Assignment] = []
        self.__getAssignments()
        
    def __getAssignments(self):
        with self.engine.connect() as conn:
            assignments = []
            get = conn.execute(
                self.dashboardClientsPeerAssignmentTable.select().where(
                    self.dashboardClientsPeerAssignmentTable.c.UnassignedDate.is_(None)
                )
            ).mappings().fetchall()
            for a in get:
                assignments.append(Assignment(**a))
            self.assignments = assignments
            
            
    def AssignClient(self, ClientID, ConfigurationName, PeerID):
        existing = list(
            filter(lambda e: 
                   e.ClientID == ClientID and 
                   e.ConfigurationName == ConfigurationName and
                   e.PeerID == PeerID, self.assignments)
        )
        if len(existing) == 0:
            if ConfigurationName in self.wireguardConfigurations.keys():
                config = self.wireguardConfigurations.get(ConfigurationName)
                peer = list(filter(lambda x : x.id == PeerID, config.Peers))
                if len(peer) == 1:
                    with self.engine.begin() as conn:
                        data = {
                            "AssignmentID": str(uuid.uuid4()),
                            "ClientID": ClientID,
                            "ConfigurationName": ConfigurationName,
                            "PeerID": PeerID
                        }
                        conn.execute(
                            self.dashboardClientsPeerAssignmentTable.insert().values(data)
                        )
                    self.__getAssignments()
                    return True, data
        return False, None
    
    def UnassignClients(self, AssignmentID):
        existing = list(
            filter(lambda e:
                   e.AssignmentID == AssignmentID, self.assignments)
        )
        if not existing:
            return False
        with self.engine.begin() as conn:
            conn.execute(
                self.dashboardClientsPeerAssignmentTable.update().values({
                    "UnassignedDate": datetime.datetime.now()
                }).where(
                    self.dashboardClientsPeerAssignmentTable.c.AssignmentID == AssignmentID
                )
            )
            self.__getAssignments()
            return True
        
    def UnassignPeers(self, ClientID):
        with self.engine.begin() as conn:
            conn.execute(
                self.dashboardClientsPeerAssignmentTable.update().values({
                    "UnassignedDate": datetime.datetime.now()
                }).where(
                    db.and_(
                        self.dashboardClientsPeerAssignmentTable.c.ClientID == ClientID,
                        self.dashboardClientsPeerAssignmentTable.c.UnassignedDate.is_(db.null())
                    )
                )
            )
            self.__getAssignments()
            return True
    
    def GetAssignedClients(self, ConfigurationName, PeerID) -> list[Assignment]:
        self.__getAssignments()
        return list(filter(
            lambda c : c.ConfigurationName == ConfigurationName and 
                       c.PeerID == PeerID, self.assignments))
    
    def GetAssignedPeers(self, ClientID):
        self.__getAssignments()
        
        peers = []
        assigned = filter(lambda e:
                          e.ClientID == ClientID, self.assignments)
        
        for a in assigned:
            peer = filter(lambda e : e.id == a.PeerID, 
                          self.wireguardConfigurations[a.ConfigurationName].Peers)
            for p in peer:
                peers.append({
                    'assignment_id': a.AssignmentID,
                    'protocol': self.wireguardConfigurations[a.ConfigurationName].Protocol,
                    'id': p.id,
                    'private_key': p.private_key,
                    'name': p.name,
                    'received_data': p.total_receive + p.cumu_receive,
                    'sent_data': p.total_sent + p.cumu_sent,
                    'data': p.total_data + p.cumu_data,
                    'status': p.status,
                    'latest_handshake': p.latest_handshake,
                    'allowed_ip': p.allowed_ip,
                    'jobs': p.jobs,
                    'configuration_name': a.ConfigurationName,
                    'peer_configuration_data': p.downloadPeer()
                })
        return peers