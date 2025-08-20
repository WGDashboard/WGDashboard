"""
WireGuard Configuration
"""
from typing import Any

import jinja2
import sqlalchemy, random, shutil, configparser, ipaddress, os, subprocess, time, re, uuid, psutil, traceback
from zipfile import ZipFile
from datetime import datetime, timedelta
from itertools import islice

from .ConnectionString import ConnectionString
from .DashboardConfig import DashboardConfig
from .Peer import Peer
from .PeerJobs import PeerJobs
from .PeerShareLinks import PeerShareLinks
from .Utilities import StringToBoolean, GenerateWireguardPublicKey, RegexMatch, ValidateDNSAddress, \
    ValidateEndpointAllowedIPs
from .WireguardConfigurationInfo import WireguardConfigurationInfo, PeerGroupsClass


class WireguardConfiguration:
    class InvalidConfigurationFileException(Exception):
        def __init__(self, m):
            self.message = m

        def __str__(self):
            return self.message

    def __init__(self, DashboardConfig: DashboardConfig, 
                 AllPeerJobs: PeerJobs,
                 AllPeerShareLinks: PeerShareLinks,
                 name: str = None,
                 data: dict = None,
                 backup: dict = None,
                 startup: bool = False,
                 wg: bool = True
                 ):
        self.Peers = []
        self.__parser: configparser.ConfigParser = configparser.RawConfigParser(strict=False)
        self.__parser.optionxform = str
        self.__configFileModifiedTime = None

        self.Status: bool = False
        self.Name: str = ""
        self.PrivateKey: str = ""
        self.PublicKey: str = ""

        self.ListenPort: str = ""
        self.Address: str = ""
        self.DNS: str = ""
        self.Table: str = ""
        self.MTU: str = ""
        self.PreUp: str = ""
        self.PostUp: str = ""
        self.PreDown: str = ""
        self.PostDown: str = ""
        self.SaveConfig: bool = True
        self.Name = name
        self.Protocol = "wg" if wg else "awg"
        self.AllPeerJobs = AllPeerJobs
        self.DashboardConfig = DashboardConfig
        self.AllPeerShareLinks = AllPeerShareLinks
        self.configPath = os.path.join(self.__getProtocolPath(), f'{self.Name}.conf')
        self.engine: sqlalchemy.engine = sqlalchemy.create_engine(ConnectionString("wgdashboard"))
        self.metadata: sqlalchemy.MetaData = sqlalchemy.MetaData()
        self.dbType = self.DashboardConfig.GetConfig("Database", "type")[1]
        
        if name is not None:
            if data is not None and "Backup" in data.keys():
                db = self.__importDatabase(
                    os.path.join(
                        self.__getProtocolPath(),
                        'WGDashboard_Backup',
                        data["Backup"].replace(".conf", ".sql")), True)
            else:
                self.createDatabase()

            self.__parseConfigurationFile()
            self.__initPeersList()
        else:
            self.Name = data["ConfigurationName"]
            self.configPath = os.path.join(self.__getProtocolPath(), f'{self.Name}.conf')

            for i in dir(self):
                if str(i) in data.keys():
                    if isinstance(getattr(self, i), bool):
                        setattr(self, i, StringToBoolean(data[i]))
                    else:
                        setattr(self, i, str(data[i]))

            self.__parser["Interface"] = {
                "PrivateKey": self.PrivateKey,
                "Address": self.Address,
                "ListenPort": self.ListenPort,
                "PreUp": f"{self.PreUp}",
                "PreDown": f"{self.PreDown}",
                "PostUp": f"{self.PostUp}",
                "PostDown": f"{self.PostDown}",
                "SaveConfig": "true"
            }

            if self.Protocol == 'awg':
                self.__parser["Interface"]["Jc"] = self.Jc
                self.__parser["Interface"]["Jc"] = self.Jc
                self.__parser["Interface"]["Jmin"] = self.Jmin
                self.__parser["Interface"]["Jmax"] = self.Jmax
                self.__parser["Interface"]["S1"] = self.S1
                self.__parser["Interface"]["S2"] = self.S2
                self.__parser["Interface"]["H1"] = self.H1
                self.__parser["Interface"]["H2"] = self.H2
                self.__parser["Interface"]["H3"] = self.H3
                self.__parser["Interface"]["H4"] = self.H4

            if "Backup" not in data.keys():
                self.createDatabase()
                with open(self.configPath, "w+") as configFile:
                    self.__parser.write(configFile)
                    print(f"[WGDashboard] Configuration file {self.configPath} created")
                self.__initPeersList()

        if not os.path.exists(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup')):
            os.mkdir(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup'))

        print(f"[WGDashboard] Initialized Configuration: {name}")
        self.__dumpDatabase()
        if self.getAutostartStatus() and not self.getStatus() and startup:
            self.toggleConfiguration()
            print(f"[WGDashboard] Autostart Configuration: {name}")
            
        self.configurationInfo: WireguardConfigurationInfo | None = None
        configurationInfoJson = self.readConfigurationInfo()
        if not configurationInfoJson:
            self.configurationInfo = WireguardConfigurationInfo(**{})
            self.initConfigurationInfo()
        else:
            self.configurationInfo = WireguardConfigurationInfo.model_validate_json(configurationInfoJson.get("Info"))
        

    def __getProtocolPath(self):
        return self.DashboardConfig.GetConfig("Server", "wg_conf_path")[1] if self.Protocol == "wg" \
            else self.DashboardConfig.GetConfig("Server", "awg_conf_path")[1]

    def __initPeersList(self):
        self.Peers: list[Peer] = []
        self.getPeers()
        self.getRestrictedPeersList()

    def getRawConfigurationFile(self):
        return open(self.configPath, 'r').read()

    def updateRawConfigurationFile(self, newRawConfiguration):
        backupStatus, backup = self.backupConfigurationFile()
        if not backupStatus:
            return False, "Cannot create backup"

        if self.Status:
            self.toggleConfiguration()

        with open(self.configPath, 'w') as f:
            f.write(newRawConfiguration)

        status, err = self.toggleConfiguration()
        if not status:
            restoreStatus = self.restoreBackup(backup['filename'])
            print(f"Restore status: {restoreStatus}")
            self.toggleConfiguration()
            return False, err
        return True, None

    def __parseConfigurationFile(self):
        with open(self.configPath, 'r') as f:
            original = [l.rstrip("\n") for l in f.readlines()]
            try:
                start = original.index("[Interface]")

                # Clean
                for i in range(start, len(original)):
                    if original[i] == "[Peer]":
                        break
                    split = re.split(r'\s*=\s*', original[i], 1)
                    if len(split) == 2:
                        key = split[0]
                        if key in dir(self):
                            if isinstance(getattr(self, key), bool):
                                setattr(self, key, False)
                            else:
                                setattr(self, key, "")

                # Set
                for i in range(start, len(original)):
                    if original[i] == "[Peer]":
                        break
                    split = re.split(r'\s*=\s*', original[i], 1)
                    if len(split) == 2:
                        key = split[0]
                        value = split[1]
                        if key in dir(self):
                            if isinstance(getattr(self, key), bool):
                                setattr(self, key, StringToBoolean(value))
                            else:
                                if len(getattr(self, key)) > 0:
                                    setattr(self, key, f"{getattr(self, key)}, {value}")
                                else:
                                    setattr(self, key, value)
            except ValueError as e:
                raise self.InvalidConfigurationFileException(
                    "[Interface] section not found in " + self.configPath)
            if self.PrivateKey:
                self.PublicKey = self.__getPublicKey()
            self.Status = self.getStatus()

    def __dropDatabase(self):
        existingTables = [self.Name, f'{self.Name}_restrict_access', f'{self.Name}_transfer', f'{self.Name}_deleted']
        try:
            with self.engine.begin() as conn:
                for t in existingTables:
                    conn.execute(
                        sqlalchemy.text(
                            f'DROP TABLE "{t}"'
                        )
                    )
        except Exception as e:
            print("[WGDashboard] Error: Drop table failed - " + str(e))
            return False
        return True

    def createDatabase(self, dbName = None):
        if dbName is None:
            dbName = self.Name
        self.peersTable = sqlalchemy.Table(
            dbName, self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False, primary_key=True),
            sqlalchemy.Column('private_key', sqlalchemy.String(255)),
            sqlalchemy.Column('DNS', sqlalchemy.Text),
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
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False, primary_key=True),
            sqlalchemy.Column('private_key', sqlalchemy.String(255)),
            sqlalchemy.Column('DNS', sqlalchemy.Text),
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

    def __dumpDatabase(self):
        with self.engine.connect() as conn:
            tables = [self.peersTable, self.peersRestrictedTable, self.peersTransferTable, self.peersDeletedTable]
            for i in tables:
                rows = conn.execute(i.select()).mappings().fetchall()
                for row in rows:
                    insert_stmt = i.insert().values(dict(row))
                    yield str(insert_stmt.compile(compile_kwargs={"literal_binds": True}))

    def __importDatabase(self, sqlFilePath, restore = False) -> bool:
        if not restore:
            self.__dropDatabase()
        self.createDatabase()
        if not os.path.exists(sqlFilePath):
            return False
        with self.engine.begin() as conn:
            with open(sqlFilePath, 'r') as f:
                for l in f.readlines():
                    l = l.rstrip("\n")
                    if len(l) > 0:
                        conn.execute(sqlalchemy.text(l))
        return True

    def __getPublicKey(self) -> str:
        return GenerateWireguardPublicKey(self.PrivateKey)[1]

    def getStatus(self) -> bool:
        self.Status = self.Name in psutil.net_if_addrs().keys()
        return self.Status

    def getAutostartStatus(self):
        s, d = self.DashboardConfig.GetConfig("WireGuardConfiguration", "autostart")
        return self.Name in d

    def getRestrictedPeers(self):
        self.RestrictedPeers = []
        with self.engine.connect() as conn:
            restricted = conn.execute(self.peersRestrictedTable.select()).mappings().fetchall()
            for i in restricted:
                self.RestrictedPeers.append(Peer(i, self))

    def configurationFileChanged(self) :
        mt = os.path.getmtime(self.configPath)
        changed = self.__configFileModifiedTime is None or self.__configFileModifiedTime != mt
        self.__configFileModifiedTime = mt
        return changed

    def getPeers(self):
        tmpList = []
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
                                    conn.execute(
                                        self.peersTable.insert().values(tempPeer)
                                    )
                                else:
                                    conn.execute(
                                        self.peersTable.update().values({
                                            "allowed_ip": i.get("AllowedIPs", "N/A")
                                        }).where(
                                            self.peersTable.columns.id == i['PublicKey']
                                        )
                                    )
                                tmpList.append(Peer(tempPeer, self))
                except Exception as e:
                    if __name__ == '__main__':
                        print(f"[WGDashboard] {self.Name} getPeers() Error: {str(e)}")
        else:
            with self.engine.connect() as conn:
                existingPeers = conn.execute(self.peersTable.select()).mappings().fetchall()
                for i in existingPeers:
                    tmpList.append(Peer(i, self))
        self.Peers = []
        self.Peers = tmpList

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
                        "preshared_key": i["preshared_key"]
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

                subprocess.check_output(f"{self.Protocol} set {self.Name} peer {p['id']} allowed-ips {p['allowed_ip'].replace(' ', '')}{f' preshared-key {uid}' if presharedKeyExist else ''}",
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

    def searchPeer(self, publicKey):
        for i in self.Peers:
            if i.id == publicKey:
                return True, i
        return False, None

    def allowAccessPeers(self, listOfPublicKeys) -> tuple[bool, str]:
        if not self.getStatus():
            self.toggleConfiguration()
        with self.engine.begin() as conn:
            for i in listOfPublicKeys:
                stmt = self.peersRestrictedTable.select().where(
                    self.peersRestrictedTable.columns.id == i
                )
                restrictedPeer = conn.execute(stmt).mappings().fetchone()
                if restrictedPeer is not None:
                    conn.execute(
                        self.peersTable.insert().from_select(
                            [c.name for c in self.peersTable.columns],
                            stmt
                        )
                    )
                    conn.execute(
                        self.peersRestrictedTable.delete().where(
                            self.peersRestrictedTable.columns.id == i
                        )
                    )

                    presharedKeyExist = len(restrictedPeer['preshared_key']) > 0
                    rd = random.Random()
                    uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))
                    if presharedKeyExist:
                        with open(uid, "w+") as f:
                            f.write(restrictedPeer['preshared_key'])

                    subprocess.check_output(f"{self.Protocol} set {self.Name} peer {restrictedPeer['id']} allowed-ips {restrictedPeer['allowed_ip'].replace(' ', '')}{f' preshared-key {uid}' if presharedKeyExist else ''}",
                                            shell=True, stderr=subprocess.STDOUT)
                    if presharedKeyExist: os.remove(uid)
                else:
                    return False, "Failed to allow access of peer " + i
        if not self.__wgSave():
            return False, "Failed to save configuration through WireGuard"
        self.getPeers()
        return True, "Allow access successfully"

    def restrictPeers(self, listOfPublicKeys) -> tuple[bool, str]:
        numOfRestrictedPeers = 0
        numOfFailedToRestrictPeers = 0
        if not self.getStatus():
            self.toggleConfiguration()

        with self.engine.begin() as conn:
            for p in listOfPublicKeys:
                found, pf = self.searchPeer(p)
                if found:
                    try:
                        subprocess.check_output(f"{self.Protocol} set {self.Name} peer {pf.id} remove",
                                                shell=True, stderr=subprocess.STDOUT)
                        conn.execute(
                            self.peersRestrictedTable.insert().from_select(
                                [c.name for c in self.peersTable.columns],
                                self.peersTable.select().where(
                                    self.peersTable.columns.id == pf.id
                                )
                            )
                        )
                        conn.execute(
                            self.peersRestrictedTable.update().values({
                                "status": "stopped"
                            }).where(
                                self.peersRestrictedTable.columns.id == pf.id
                            )
                        )
                        conn.execute(
                            self.peersTable.delete().where(
                                self.peersTable.columns.id == pf.id
                            )
                        )
                        numOfRestrictedPeers += 1
                    except Exception as e:
                        traceback.print_stack()
                        numOfFailedToRestrictPeers += 1

        if not self.__wgSave():
            return False, "Failed to save configuration through WireGuard"

        self.getPeers()

        if numOfRestrictedPeers == len(listOfPublicKeys):
            return True, f"Restricted {numOfRestrictedPeers} peer(s)"
        return False, f"Restricted {numOfRestrictedPeers} peer(s) successfully. Failed to restrict {numOfFailedToRestrictPeers} peer(s)"


    def deletePeers(self, listOfPublicKeys, AllPeerJobs: PeerJobs, AllPeerShareLinks: PeerShareLinks) -> tuple[bool, str]:
        numOfDeletedPeers = 0
        numOfFailedToDeletePeers = 0
        if not self.getStatus():
            self.toggleConfiguration()
        with self.engine.begin() as conn:
            for p in listOfPublicKeys:
                found, pf = self.searchPeer(p)
                for job in pf.jobs:
                    AllPeerJobs.deleteJob(job)
                for shareLink in pf.ShareLink:
                    AllPeerShareLinks.updateLinkExpireDate(shareLink.ShareID, datetime.now())
                if found:
                    try:
                        subprocess.check_output(f"{self.Protocol} set {self.Name} peer {pf.id} remove",
                                                shell=True, stderr=subprocess.STDOUT)
                        conn.execute(
                            self.peersTable.delete().where(
                                self.peersTable.columns.id == pf.id
                            )
                        )
                        numOfDeletedPeers += 1
                    except Exception as e:
                        numOfFailedToDeletePeers += 1

        if not self.__wgSave():
            return False, "Failed to save configuration through WireGuard"

        self.getPeers()

        if numOfDeletedPeers == 0 and numOfFailedToDeletePeers == 0:
            return False, "No peer(s) to delete found"

        if numOfDeletedPeers == len(listOfPublicKeys):
            return True, f"Deleted {numOfDeletedPeers} peer(s)"
        return False, f"Deleted {numOfDeletedPeers} peer(s) successfully. Failed to delete {numOfFailedToDeletePeers} peer(s)"

    def __wgSave(self) -> tuple[bool, str] | tuple[bool, None]:
        try:
            subprocess.check_output(f"{self.Protocol}-quick save {self.Name}", shell=True, stderr=subprocess.STDOUT)
            return True, None
        except subprocess.CalledProcessError as e:
            return False, str(e)

    def getPeersLatestHandshake(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            latestHandshake = subprocess.check_output(f"{self.Protocol} show {self.Name} latest-handshakes",
                                                      shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return "stopped"
        latestHandshake = latestHandshake.decode("UTF-8").split()
        count = 0
        now = datetime.now()
        time_delta = timedelta(minutes=3)

        with self.engine.begin() as conn:
            for _ in range(int(len(latestHandshake) / 2)):
                minus = now - datetime.fromtimestamp(int(latestHandshake[count + 1]))
                if minus < time_delta:
                    status = "running"
                else:
                    status = "stopped"
                if int(latestHandshake[count + 1]) > 0:
                    conn.execute(
                        self.peersTable.update().values({
                            "latest_handshake": str(minus).split(".", maxsplit=1)[0],
                            "status": status
                        }).where(
                            self.peersTable.columns.id == latestHandshake[count]
                        )
                    )
                else:
                    conn.execute(
                        self.peersTable.update().values({
                            "latest_handshake": "No Handshake",
                            "status": status
                        }).where(
                            self.peersTable.columns.id == latestHandshake[count]
                        )
                    )
                count += 2

    def getPeersTransfer(self):
        if not self.getStatus():
            self.toggleConfiguration()
        # try:
        data_usage = subprocess.check_output(f"{self.Protocol} show {self.Name} transfer",
                                             shell=True, stderr=subprocess.STDOUT)
        data_usage = data_usage.decode("UTF-8").split("\n")
        
        data_usage = [p.split("\t") for p in data_usage]
        cur_i = None
        with self.engine.begin() as conn:
            for i in range(len(data_usage)):
                if len(data_usage[i]) == 3:
                    cur_i = conn.execute(
                        self.peersTable.select().where(
                            self.peersTable.c.id == data_usage[i][0]
                        )
                    ).mappings().fetchone()
                    if cur_i is not None:
                        # print(cur_i is None)
                        total_sent = cur_i['total_sent']
                        # print(cur_i is None)
                        total_receive = cur_i['total_receive']
                        cur_total_sent = float(data_usage[i][2]) / (1024 ** 3)
                        cur_total_receive = float(data_usage[i][1]) / (1024 ** 3)
                        cumulative_receive = cur_i['cumu_receive'] + total_receive
                        cumulative_sent = cur_i['cumu_sent'] + total_sent
                        if total_sent <= cur_total_sent and total_receive <= cur_total_receive:
                            total_sent = cur_total_sent
                            total_receive = cur_total_receive
                        else:
                            conn.execute(
                                self.peersTable.update().values({
                                    "cumu_receive": cumulative_receive,
                                    "cumu_sent": cumulative_sent,
                                    "cumu_data": cumulative_sent + cumulative_receive
                                }).where(
                                    self.peersTable.c.id == data_usage[i][0]
                                )
                            )

                            total_sent = 0
                            total_receive = 0
                        status, p = self.searchPeer(data_usage[i][0])
                        if status:
                            if p.total_receive != total_receive or p.total_sent != total_sent:
                                conn.execute(
                                    self.peersTable.update().values({
                                        "total_receive": total_receive,
                                        "total_sent": total_sent,
                                        "total_data": total_receive + total_sent
                                    }).where(
                                        self.peersTable.c.id == data_usage[i][0]
                                    )
                                )

        # except Exception as e:
        #     print(cur_i, cur_i['total_receive'])
        #     print(f"[WGDashboard] {self.Name} getPeersTransfer() Error: {str(e)} {str(e.__traceback__)}")
            

    def getPeersEndpoint(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            data_usage = subprocess.check_output(f"{self.Protocol} show {self.Name} endpoints",
                                                 shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return "stopped"
        data_usage = data_usage.decode("UTF-8").split()
        count = 0
        with self.engine.begin() as conn:
            for _ in range(int(len(data_usage) / 2)):
                conn.execute(
                    self.peersTable.update().values({
                        "endpoint": data_usage[count + 1]
                    }).where(
                        self.peersTable.c.id == data_usage[count]
                    )
                )
                count += 2

    def toggleConfiguration(self) -> [bool, str]:
        self.getStatus()
        if self.Status:
            try:
                check = subprocess.check_output(f"{self.Protocol}-quick down {self.Name}",
                                                shell=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as exc:
                return False, str(exc.output.strip().decode("utf-8"))
        else:
            try:
                check = subprocess.check_output(f"{self.Protocol}-quick up {self.Name}", shell=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as exc:
                return False, str(exc.output.strip().decode("utf-8"))
        self.__parseConfigurationFile()
        self.getStatus()
        return True, None

    def getPeersList(self):
        return self.Peers

    def getRestrictedPeersList(self) -> list:
        self.getRestrictedPeers()
        return self.RestrictedPeers

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
            "DataUsage": {
                "Total": sum(list(map(lambda x: x.cumu_data + x.total_data, self.Peers))),
                "Sent": sum(list(map(lambda x: x.cumu_sent + x.total_sent, self.Peers))),
                "Receive": sum(list(map(lambda x: x.cumu_receive + x.total_receive, self.Peers)))
            },
            "ConnectedPeers": len(list(filter(lambda x: x.status == "running", self.Peers))),
            "TotalPeers": len(self.Peers),
            "Protocol": self.Protocol,
            "Table": self.Table,
            "Info": self.configurationInfo.model_dump()
        }

    def backupConfigurationFile(self) -> tuple[bool, dict[str, str]]:
        if not os.path.exists(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup')):
            os.mkdir(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup'))
        time = datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy(
            self.configPath,
            os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', f'{self.Name}_{time}.conf')
        )
        with open(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', f'{self.Name}_{time}.sql'), 'w+') as f:
            for l in self.__dumpDatabase():
                f.write(l + "\n")

        return True, {
            "filename": f'{self.Name}_{time}.conf',
            "backupDate": datetime.now().strftime("%Y%m%d%H%M%S")
        }

    def getBackups(self, databaseContent: bool = False) -> list[dict[str: str, str: str, str: str]]:
        backups = []

        directory = os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup')
        files = [(file, os.path.getctime(os.path.join(directory, file)))
                 for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]
        files.sort(key=lambda x: x[1], reverse=True)

        for f, ct in files:
            if RegexMatch(f"^({self.Name})_(.*)\\.(conf)$", f):
                s = re.search(f"^({self.Name})_(.*)\\.(conf)$", f)
                date = s.group(2)
                d = {
                    "filename": f,
                    "backupDate": date,
                    "content": open(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', f), 'r').read()
                }
                if f.replace(".conf", ".sql") in list(os.listdir(directory)):
                    d['database'] = True
                    if databaseContent:
                        d['databaseContent'] = open(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', f.replace(".conf", ".sql")), 'r').read()
                backups.append(d)

        return backups

    def restoreBackup(self, backupFileName: str) -> bool:
        backups = list(map(lambda x : x['filename'], self.getBackups()))
        if backupFileName not in backups:
            return False
        if self.Status:
            self.toggleConfiguration()
        target = os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backupFileName)
        targetSQL = os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backupFileName.replace(".conf", ".sql"))
        if not os.path.exists(target):
            return False
        targetContent = open(target, 'r').read()
        try:
            with open(self.configPath, 'w') as f:
                f.write(targetContent)
        except Exception as e:
            return False
        self.__parseConfigurationFile()
        self.__importDatabase(targetSQL)
        self.__initPeersList()
        return True

    def deleteBackup(self, backupFileName: str) -> bool:
        backups = list(map(lambda x : x['filename'], self.getBackups()))
        if backupFileName not in backups:
            return False
        try:
            os.remove(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backupFileName))
        except Exception as e:
            return False
        return True

    def downloadBackup(self, backupFileName: str) -> tuple[bool, str] | tuple[bool, None]:
        backup = list(filter(lambda x : x['filename'] == backupFileName, self.getBackups()))
        if len(backup) == 0:
            return False, None
        zip = f'{str(uuid.UUID(int=random.Random().getrandbits(128), version=4))}.zip'
        with ZipFile(os.path.join('download', zip), 'w') as zipF:
            zipF.write(
                os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backup[0]['filename']),
                os.path.basename(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backup[0]['filename']))
            )
            if backup[0]['database']:
                zipF.write(
                    os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backup[0]['filename'].replace('.conf', '.sql')),
                    os.path.basename(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup', backup[0]['filename'].replace('.conf', '.sql')))
                )

        return True, zip

    def updateConfigurationSettings(self, newData: dict) -> tuple[bool, str]:
        if self.Status:
            self.toggleConfiguration()
        original = []
        dataChanged = False
        with open(self.configPath, 'r') as f:
            original = [l.rstrip("\n") for l in f.readlines()]
            allowEdit = ["Address", "PreUp", "PostUp", "PreDown", "PostDown", "ListenPort", "Table"]
            if self.Protocol == 'awg':
                allowEdit += ["Jc", "Jmin", "Jmax", "S1", "S2", "H1", "H2", "H3", "H4"]
            start = original.index("[Interface]")
            try:
                end = original.index("[Peer]")
            except ValueError as e:
                end = len(original)
            new = ["[Interface]"]
            peerFound = False
            for line in range(start, end):
                split = re.split(r'\s*=\s*', original[line], 1)
                if len(split) == 2:
                    if split[0] not in allowEdit:
                        new.append(original[line])
            for key in allowEdit:
                new.insert(1, f"{key} = {str(newData[key]).strip()}")
            new.append("")
            for line in range(end, len(original)):
                new.append(original[line])
            self.backupConfigurationFile()
            with open(self.configPath, 'w') as f:
                f.write("\n".join(new))

        status, msg = self.toggleConfiguration()
        if not status:
            return False, msg
        for i in allowEdit:
            setattr(self, i, str(newData[i]))
                
        return True, ""

    def deleteConfiguration(self):
        if self.getStatus():
            self.toggleConfiguration()
        os.remove(self.configPath)
        self.__dropDatabase()
        return True

    def renameConfiguration(self, newConfigurationName) -> tuple[bool, str]:
        try:
            if self.getStatus():
                self.toggleConfiguration()
            self.createDatabase(newConfigurationName)
            with self.engine.begin() as conn:
                conn.execute(
                    sqlalchemy.text(
                        f'INSERT INTO "{newConfigurationName}" SELECT * FROM "{self.Name}"'
                    )
                )
                conn.execute(
                    sqlalchemy.text(
                        f'INSERT INTO "{newConfigurationName}_restrict_access" SELECT * FROM "{self.Name}_restrict_access"'
                    )
                )
                conn.execute(
                    sqlalchemy.text(
                        f'INSERT INTO "{newConfigurationName}_deleted" SELECT * FROM "{self.Name}_deleted"'
                    )
                )
                conn.execute(
                    sqlalchemy.text(
                        f'INSERT INTO "{newConfigurationName}_transfer" SELECT * FROM "{self.Name}_transfer"'
                    )
                )
            self.AllPeerJobs.updateJobConfigurationName(self.Name, newConfigurationName)
            shutil.copy(
                self.configPath,
                os.path.join(self.__getProtocolPath(), f'{newConfigurationName}.conf')
            )
            self.deleteConfiguration()
        except Exception as e:
            traceback.print_stack()
            return False, str(e)
        return True, None

    def getNumberOfAvailableIP(self):
        if len(self.Address) < 0:
            return False, None
        existedAddress = set()
        availableAddress = {}
        for p in self.Peers + self.getRestrictedPeersList():
            peerAllowedIP = p.allowed_ip.split(',')
            for pip in peerAllowedIP:
                ppip = pip.strip().split('/')
                if len(ppip) == 2:
                    try:
                        check = ipaddress.ip_network(ppip[0])
                        existedAddress.add(check)
                    except Exception as e:
                        print(f"[WGDashboard] Error: {self.Name} peer {p.id} have invalid ip")
        configurationAddresses = self.Address.split(',')
        for ca in configurationAddresses:
            ca = ca.strip()
            caSplit = ca.split('/')
            try:
                if len(caSplit) == 2:
                    network = ipaddress.ip_network(ca, False)
                    existedAddress.add(ipaddress.ip_network(caSplit[0]))
                    availableAddress[ca] = network.num_addresses
                    for p in existedAddress:
                        if p.version == network.version and p.subnet_of(network):
                            availableAddress[ca] -= 1
            except Exception as e:
                print(e)
                print(f"[WGDashboard] Error: Failed to parse IP address {ca} from {self.Name}")
        return True, availableAddress

    def getAvailableIP(self, threshold = 255):
        if len(self.Address) < 0:
            return False, None
        existedAddress = set()
        availableAddress = {}
        for p in self.Peers + self.getRestrictedPeersList():
            peerAllowedIP = p.allowed_ip.split(',')
            for pip in peerAllowedIP:
                ppip = pip.strip().split('/')
                if len(ppip) == 2:
                    try:
                        check = ipaddress.ip_network(ppip[0])
                        existedAddress.add(check.compressed)
                    except Exception as e:
                        print(f"[WGDashboard] Error: {self.Name} peer {p.id} have invalid ip")
        configurationAddresses = self.Address.split(',')
        for ca in configurationAddresses:
            ca = ca.strip()
            caSplit = ca.split('/')
            try:
                if len(caSplit) == 2:
                    network = ipaddress.ip_network(ca, False)
                    existedAddress.add(ipaddress.ip_network(caSplit[0]).compressed)
                    if threshold == -1:
                        availableAddress[ca] = filter(lambda ip : ip not in existedAddress,
                                                      map(lambda iph : ipaddress.ip_network(iph).compressed, network.hosts()))
                    else:
                        availableAddress[ca] = list(islice(filter(lambda ip : ip not in existedAddress,
                                                                  map(lambda iph : ipaddress.ip_network(iph).compressed, network.hosts())), threshold))
            except Exception as e:
                print(e)
                print(f"[WGDashboard] Error: Failed to parse IP address {ca} from {self.Name}")
        return True, availableAddress

    def getRealtimeTrafficUsage(self):
        stats = psutil.net_io_counters(pernic=True, nowrap=True)
        if self.Name in stats.keys():
            stat = stats[self.Name]
            recv1 = stat.bytes_recv
            sent1 = stat.bytes_sent
            time.sleep(1)
            stats = psutil.net_io_counters(pernic=True, nowrap=True)
            if self.Name in stats.keys():
                stat = stats[self.Name]
                recv2 = stat.bytes_recv
                sent2 = stat.bytes_sent
                net_in = round((recv2 - recv1) / 1024 / 1024, 3)
                net_out = round((sent2 - sent1) / 1024 / 1024, 3)
                return {
                    "sent": net_out,
                    "recv": net_in
                }
            else:
                return { "sent": 0, "recv": 0 }
        else:
            return { "sent": 0, "recv": 0 }
    
    '''
    Manager WireGuard Configuration Information
    '''
    
    def readConfigurationInfo(self):
        with self.engine.connect() as conn:
            result = conn.execute(
                self.infoTable.select().where(
                    self.infoTable.c.ID == self.Name
                )
            ).mappings().fetchone()
        return result
    
    def initConfigurationInfo(self):
        with self.engine.begin() as conn:
            conn.execute(
                self.infoTable.insert().values(
                    {
                        "ID": self.Name,
                        "Info": self.configurationInfo.model_dump_json()
                    }
                )
            )
    
    def storeConfigurationInfo(self):
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.infoTable.update().values(
                        {
                            "Info": self.configurationInfo.model_dump_json()
                        }
                    ).where(
                        self.infoTable.c.ID == self.Name
                    )
                )
        except Exception as e:
            return False
        
    def updateConfigurationInfo(self, key: str, value: str | dict[str, str] | dict[str, dict]) -> tuple[bool, Any, str] | tuple[
        bool, str, None] | tuple[bool, None, None]:
        if key == "Description":
            self.configurationInfo.Description = value
        elif key == "OverridePeerSettings":
            for (key, val) in value.items():
                try:
                    status, msg = self.__validateOverridePeerSettings(key, jinja2.Template(val).render(configuration=self.toJson()))
                    if not status:
                        return False, msg, key
                except Exception as e:
                    return False, str(e), None
            self.configurationInfo.OverridePeerSettings = (
                self.configurationInfo.OverridePeerSettings.model_validate(value))
        elif key == "PeerGroups":
            peerGroups = {}
            for name, data in value.items():
                peerGroups[name] = PeerGroupsClass(**data)
            self.configurationInfo.PeerGroups = peerGroups
        else: 
            return False, "Key does not exist", None
        
        self.storeConfigurationInfo()
        return True, None, None
    
    def __validateOverridePeerSettings(self, key: str, value: str | int) -> tuple[bool, None] | tuple[bool, str]:
        status = True
        msg = None
        print(value)
        if key == "DNS" and value:
            status, msg = ValidateDNSAddress(value)
        elif key == "EndpointAllowedIPs" and value:
            status, msg = ValidateEndpointAllowedIPs(value)
        elif key == "ListenPort" and value:
            if not value.isnumeric() or not (1 <= int(value) <= 65535):
                status = False
                msg = "Listen Port must be >= 1 and <= 65535"        
        return status, msg
        