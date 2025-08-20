"""
AmneziaWG Configuration
"""
import random, sqlalchemy, os, subprocess, re, uuid

from .PeerJobs import PeerJobs
from .AmneziaWGPeer import AmneziaWGPeer
from .PeerShareLinks import PeerShareLinks
from .Utilities import RegexMatch
from .WireguardConfiguration import WireguardConfiguration


class AmneziaWireguardConfiguration(WireguardConfiguration):
    def __init__(self, DashboardConfig,
                 AllPeerJobs: PeerJobs,
                 AllPeerShareLinks: PeerShareLinks,
                 name: str = None, data: dict = None, backup: dict = None, startup: bool = False):
        self.Jc = 0
        self.Jmin = 0
        self.Jmax = 0
        self.S1 = 0
        self.S2 = 0
        self.H1 = 1
        self.H2 = 2
        self.H3 = 3
        self.H4 = 4

        super().__init__(DashboardConfig, AllPeerJobs, AllPeerShareLinks, name, data, backup, startup, wg=False)

    def toJson(self):
        self.Status = self.getStatus()
        return {
            "Status": self.Status,
            "Name": self.Name,
            "PrivateKey": self.PrivateKey,
            "PublicKey": self.PublicKey,
            "Address": self.Address,
            "ListenPort": self.ListenPort,
            "PreUp": self.PreUp,
            "PreDown": self.PreDown,
            "PostUp": self.PostUp,
            "PostDown": self.PostDown,
            "SaveConfig": self.SaveConfig,
            "Info": self.configurationInfo.model_dump(),
            "DataUsage": {
                "Total": sum(list(map(lambda x: x.cumu_data + x.total_data, self.Peers))),
                "Sent": sum(list(map(lambda x: x.cumu_sent + x.total_sent, self.Peers))),
                "Receive": sum(list(map(lambda x: x.cumu_receive + x.total_receive, self.Peers)))
            },
            "ConnectedPeers": len(list(filter(lambda x: x.status == "running", self.Peers))),
            "TotalPeers": len(self.Peers),
            "Protocol": self.Protocol,
            "Jc": self.Jc,
            "Jmin": self.Jmin,
            "Jmax": self.Jmax,
            "S1": self.S1,
            "S2": self.S2,
            "H1": self.H1,
            "H2": self.H2,
            "H3": self.H3,
            "H4": self.H4
        }

    def createDatabase(self, dbName = None):
        if dbName is None:
            dbName = self.Name


        self.peersTable = sqlalchemy.Table(
            dbName, self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False, primary_key=True),
            sqlalchemy.Column('private_key', sqlalchemy.String(255)),
            sqlalchemy.Column('DNS', sqlalchemy.Text),
            sqlalchemy.Column('advanced_security', sqlalchemy.String(255)),
            sqlalchemy.Column('endpoint_allowed_ip', sqlalchemy.Text),
            sqlalchemy.Column('name', sqlalchemy.Text),
            sqlalchemy.Column('total_receive', sqlalchemy.Float),
            sqlalchemy.Column('total_sent', sqlalchemy.Float),
            sqlalchemy.Column('total_data', sqlalchemy.Float),
            sqlalchemy.Column('endpoint', sqlalchemy.String(255)),
            sqlalchemy.Column('status', sqlalchemy.String(255)),
            sqlalchemy.Column('latest_handshake', sqlalchemy.String(255)),
            sqlalchemy.Column('allowed_ip', sqlalchemy.String(255)),
            sqlalchemy.Column('cumu_receive', sqlalchemy.Float),
            sqlalchemy.Column('cumu_sent', sqlalchemy.Float),
            sqlalchemy.Column('cumu_data', sqlalchemy.Float),
            sqlalchemy.Column('mtu', sqlalchemy.Integer),
            sqlalchemy.Column('keepalive', sqlalchemy.Integer),
            sqlalchemy.Column('remote_endpoint', sqlalchemy.String(255)),
            sqlalchemy.Column('preshared_key', sqlalchemy.String(255)),
            extend_existing=True
        )
        self.peersRestrictedTable = sqlalchemy.Table(
            f'{dbName}_restrict_access', self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False, primary_key=True),
            sqlalchemy.Column('private_key', sqlalchemy.String(255)),
            sqlalchemy.Column('DNS', sqlalchemy.Text),
            sqlalchemy.Column('advanced_security', sqlalchemy.String(255)),
            sqlalchemy.Column('endpoint_allowed_ip', sqlalchemy.Text),
            sqlalchemy.Column('name', sqlalchemy.Text),
            sqlalchemy.Column('total_receive', sqlalchemy.Float),
            sqlalchemy.Column('total_sent', sqlalchemy.Float),
            sqlalchemy.Column('total_data', sqlalchemy.Float),
            sqlalchemy.Column('endpoint', sqlalchemy.String(255)),
            sqlalchemy.Column('status', sqlalchemy.String(255)),
            sqlalchemy.Column('latest_handshake', sqlalchemy.String(255)),
            sqlalchemy.Column('allowed_ip', sqlalchemy.String(255)),
            sqlalchemy.Column('cumu_receive', sqlalchemy.Float),
            sqlalchemy.Column('cumu_sent', sqlalchemy.Float),
            sqlalchemy.Column('cumu_data', sqlalchemy.Float),
            sqlalchemy.Column('mtu', sqlalchemy.Integer),
            sqlalchemy.Column('keepalive', sqlalchemy.Integer),
            sqlalchemy.Column('remote_endpoint', sqlalchemy.String(255)),
            sqlalchemy.Column('preshared_key', sqlalchemy.String(255)),
            extend_existing=True
        )
        self.peersTransferTable = sqlalchemy.Table(
            f'{dbName}_transfer', self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False),
            sqlalchemy.Column('total_receive', sqlalchemy.Float),
            sqlalchemy.Column('total_sent', sqlalchemy.Float),
            sqlalchemy.Column('total_data', sqlalchemy.Float),
            sqlalchemy.Column('cumu_receive', sqlalchemy.Float),
            sqlalchemy.Column('cumu_sent', sqlalchemy.Float),
            sqlalchemy.Column('cumu_data', sqlalchemy.Float),
            sqlalchemy.Column('time', (sqlalchemy.DATETIME if self.DashboardConfig.GetConfig("Database", "type")[1] == 'sqlite' else sqlalchemy.TIMESTAMP),
                              server_default=sqlalchemy.func.now()),
            extend_existing=True
        )
        self.peersDeletedTable = sqlalchemy.Table(
            f'{dbName}_deleted', self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False),
            sqlalchemy.Column('private_key', sqlalchemy.String(255)),
            sqlalchemy.Column('DNS', sqlalchemy.Text),
            sqlalchemy.Column('advanced_security', sqlalchemy.String(255)),
            sqlalchemy.Column('endpoint_allowed_ip', sqlalchemy.Text),
            sqlalchemy.Column('name', sqlalchemy.Text),
            sqlalchemy.Column('total_receive', sqlalchemy.Float),
            sqlalchemy.Column('total_sent', sqlalchemy.Float),
            sqlalchemy.Column('total_data', sqlalchemy.Float),
            sqlalchemy.Column('endpoint', sqlalchemy.String(255)),
            sqlalchemy.Column('status', sqlalchemy.String(255)),
            sqlalchemy.Column('latest_handshake', sqlalchemy.String(255)),
            sqlalchemy.Column('allowed_ip', sqlalchemy.String(255)),
            sqlalchemy.Column('cumu_receive', sqlalchemy.Float),
            sqlalchemy.Column('cumu_sent', sqlalchemy.Float),
            sqlalchemy.Column('cumu_data', sqlalchemy.Float),
            sqlalchemy.Column('mtu', sqlalchemy.Integer),
            sqlalchemy.Column('keepalive', sqlalchemy.Integer),
            sqlalchemy.Column('remote_endpoint', sqlalchemy.String(255)),
            sqlalchemy.Column('preshared_key', sqlalchemy.String(255)),
            extend_existing=True
        )
        self.infoTable = sqlalchemy.Table(
            'ConfigurationsInfo', self.metadata,
            sqlalchemy.Column('ID', sqlalchemy.String(255), primary_key=True),
            sqlalchemy.Column('Info', sqlalchemy.Text),
            extend_existing=True
        )

        self.metadata.create_all(self.engine)

    def getPeers(self):
        self.Peers.clear()
        if self.configurationFileChanged():
            with open(self.configPath, 'r') as configFile:
                p = []
                pCounter = -1
                content = configFile.read().split('\n')
                try:
                    peerStarts = content.index("[Peer]")
                    content = content[peerStarts:]
                    for i in content:
                        if not RegexMatch("#(.*)", i) and not RegexMatch(";(.*)", i):
                            if i == "[Peer]":
                                pCounter += 1
                                p.append({})
                                p[pCounter]["name"] = ""
                            else:
                                if len(i) > 0:
                                    split = re.split(r'\s*=\s*', i, 1)
                                    if len(split) == 2:
                                        p[pCounter][split[0]] = split[1]

                        if RegexMatch("#Name# = (.*)", i):
                            split = re.split(r'\s*=\s*', i, 1)
                            if len(split) == 2:
                                p[pCounter]["name"] = split[1]
                    with self.engine.begin() as conn:
                        for i in p:
                            if "PublicKey" in i.keys():
                                tempPeer = conn.execute(self.peersTable.select().where(
                                    self.peersTable.columns.id == i['PublicKey']
                                )).mappings().fetchone()
                                if tempPeer is None:
                                    tempPeer = {
                                        "id": i['PublicKey'],
                                        "advanced_security": i.get('AdvancedSecurity', 'off'),
                                        "private_key": "",
                                        "DNS": self.DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1],
                                        "endpoint_allowed_ip": self.DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[
                                            1],
                                        "name": i.get("name"),
                                        "total_receive": 0,
                                        "total_sent": 0,
                                        "total_data": 0,
                                        "endpoint": "N/A",
                                        "status": "stopped",
                                        "latest_handshake": "N/A",
                                        "allowed_ip": i.get("AllowedIPs", "N/A"),
                                        "cumu_receive": 0,
                                        "cumu_sent": 0,
                                        "cumu_data": 0,
                                        "mtu": self.DashboardConfig.GetConfig("Peers", "peer_mtu")[1],
                                        "keepalive": self.DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1],
                                        "remote_endpoint": self.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1],
                                        "preshared_key": i["PresharedKey"] if "PresharedKey" in i.keys() else ""
                                    }
                                    # sqlUpdate(
                                    #     """
                                    #     INSERT INTO '%s'
                                    #         VALUES (:id, :private_key, :DNS, :advanced_security, :endpoint_allowed_ip, :name, :total_receive, :total_sent, 
                                    #         :total_data, :endpoint, :status, :latest_handshake, :allowed_ip, :cumu_receive, :cumu_sent, 
                                    #         :cumu_data, :mtu, :keepalive, :remote_endpoint, :preshared_key);
                                    #     """ % self.Name
                                    #     , newPeer)
                                    conn.execute(
                                        self.peersTable.insert().values(tempPeer)
                                    )
                                else:
                                    # sqlUpdate("UPDATE '%s' SET allowed_ip = ? WHERE id = ?" % self.Name,
                                    #           (i.get("AllowedIPs", "N/A"), i['PublicKey'],))
                                    conn.execute(
                                        self.peersTable.update().values({
                                            "allowed_ip": i.get("AllowedIPs", "N/A")
                                        }).where(
                                            self.peersTable.columns.id == i['PublicKey']
                                        )
                                    )
                                self.Peers.append(AmneziaWGPeer(tempPeer, self))
                except Exception as e:
                    if __name__ == '__main__':
                        print(f"[WGDashboard] {self.Name} getPeers() Error: {str(e)}")
        else:
            # checkIfExist = sqlSelect("SELECT * FROM '%s'" % self.Name).fetchall()
            with self.engine.connect() as conn:
                existingPeers = conn.execute(self.peersTable.select()).mappings().fetchall()
                for i in existingPeers:
                    self.Peers.append(AmneziaWGPeer(i, self))

    def addPeers(self, peers: list) -> tuple[bool, dict]:
        result = {
            "message": None,
            "peers": []
        }
        try:
            with self.engine.begin() as conn:
                for i in peers:
                    newPeer = {
                        "id": i['id'],
                        "private_key": i['private_key'],
                        "DNS": i['DNS'],
                        "endpoint_allowed_ip": i['endpoint_allowed_ip'],
                        "name": i['name'],
                        "total_receive": 0,
                        "total_sent": 0,
                        "total_data": 0,
                        "endpoint": "N/A",
                        "status": "stopped",
                        "latest_handshake": "N/A",
                        "allowed_ip": i.get("allowed_ip", "N/A"),
                        "cumu_receive": 0,
                        "cumu_sent": 0,
                        "cumu_data": 0,
                        "mtu": i['mtu'],
                        "keepalive": i['keepalive'],
                        "remote_endpoint": self.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1],
                        "preshared_key": i["preshared_key"],
                        "advanced_security": i['advanced_security']
                    }
                    conn.execute(
                        self.peersTable.insert().values(newPeer)
                    )
            for p in peers:
                presharedKeyExist = len(p['preshared_key']) > 0
                rd = random.Random()
                uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))
                if presharedKeyExist:
                    with open(uid, "w+") as f:
                        f.write(p['preshared_key'])

                subprocess.check_output(
                    f"{self.Protocol} set {self.Name} peer {p['id']} allowed-ips {p['allowed_ip'].replace(' ', '')}{f' preshared-key {uid}' if presharedKeyExist else ''}",
                    shell=True, stderr=subprocess.STDOUT)
                if presharedKeyExist:
                    os.remove(uid)
            subprocess.check_output(
                f"{self.Protocol}-quick save {self.Name}", shell=True, stderr=subprocess.STDOUT)
            self.getPeers()
            for p in peers:
                p = self.searchPeer(p['id'])
                if p[0]:
                    result['peers'].append(p[1])
            return True, result
        except Exception as e:
            result['message'] = str(e)
            return False, result

    def getRestrictedPeers(self):
        self.RestrictedPeers = []
        with self.engine.connect() as conn:
            restricted = conn.execute(self.peersRestrictedTable.select()).mappings().fetchall()
            for i in restricted:
                self.RestrictedPeers.append(AmneziaWGPeer(i, self))