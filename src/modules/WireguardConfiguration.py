"""
WireGuard Configuration
"""
from pathlib import Path
from threading import RLock
from typing import Any

import sqlalchemy, random, shutil, configparser, ipaddress, os, subprocess, time, re, uuid, psutil, traceback
from zipfile import ZipFile
from datetime import datetime, timedelta
from itertools import islice
from flask import current_app

from .DatabaseConnection import ConnectionString
from .DashboardConfig import DashboardConfig
from .Peer import Peer
from .PeerJobs import PeerJobs
from .PeerShareLinks import PeerShareLinks
from .Utilities import StringToBoolean, \
    GenerateWireguardPublicKey, \
    RegexMatch, \
    ValidateDNSAddress, \
    ValidateEndpointAllowedIPs, \
    CheckAddress, \
    CheckPeerKey, \
    RenderSandboxedTemplate
from .WireguardConfigurationInfo import WireguardConfigurationInfo, PeerGroupsClass
from .DashboardWebHooks import DashboardWebHooks


class WireguardConfiguration:
    _ENDPOINT_HISTORY_HEADER = "-- WGDashboard backup includes endpoint history"

    class InvalidConfigurationFileException(Exception):
        def __init__(self, m):
            self.message = m

        def __str__(self):
            return self.message

    def __init__(self, DashboardConfig: DashboardConfig, 
                 AllPeerJobs: PeerJobs,
                 AllPeerShareLinks: PeerShareLinks,
                 DashboardWebHooks: DashboardWebHooks,
                 name: str = None,
                 data: dict = None,
                 backup: dict = None,
                 startup: bool = False,
                 wg: bool = True
                 ):
        self._backupLock = RLock()
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
        self.DashboardConfig.EnsureDatabaseIntegrity({self.Name: self})
        self.AllPeerShareLinks = AllPeerShareLinks
        self.DashboardWebHooks = DashboardWebHooks
        self.configPath = os.path.join(self.__getProtocolPath(), f'{self.Name}.conf')
        self.engine: sqlalchemy.Engine = sqlalchemy.create_engine(ConnectionString("wgdashboard"))
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
                values = {
                    "Jc": self.Jc,
                    "Jmin": self.Jmin,
                    "Jmax": self.Jmax,
                    "S1": self.S1,
                    "S2": self.S2,
                    "S3": self.S3,
                    "S4": self.S4,
                    "H1": self.H1,
                    "H2": self.H2,
                    "H3": self.H3,
                    "H4": self.H4,
                    "I1": self.I1,
                    "I2": self.I2,
                    "I3": self.I3,
                    "I4": self.I4,
                    "I5": self.I5,
                    "HeaderProtectionKey": self.HeaderProtectionKey,
                    "ContentPaddingAddition": self.ContentPaddingAddition,
                    "RekeyAfterTime": self.RekeyAfterTime,
                    "RekeyTimeout": self.RekeyTimeout,
                    "RejectAfterTime": self.RejectAfterTime,
                    "KeepaliveTimeout": self.KeepaliveTimeout,
                    "MaxHandshakeAttempts": self.MaxHandshakeAttempts,
                    "RandomTrailers": self.RandomTrailers,
                    "DisableCookies": self.DisableCookies,
                    "J1": self.J1,
                    "J2": self.J2,
                    "J3": self.J3,
                    "Itime": self.Itime
                }
                for key, value in values.items():
                    if value != None and str(value).strip():
                        self.__parser["Interface"][key] = str(value)

            if "Backup" not in data.keys():
                self.createDatabase()
                with open(self.configPath, "w+") as configFile:
                    self.__parser.write(configFile)
                    current_app.logger.info(f"Configuration file {self.configPath} created")
                self.__initPeersList()

        if not os.path.exists(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup')):
            os.mkdir(os.path.join(self.__getProtocolPath(), 'WGDashboard_Backup'))

        current_app.logger.info(f"Initialized Configuration: {name}")
        self.__dumpDatabase()
        if self.getAutostartStatus() and not self.getStatus() and startup:
            status, ext = self.toggleConfiguration()
            if not status:
                current_app.logger.error(f"Failed to autostart configuration: {name}. Reason: {ext}")
            else:
                current_app.logger.info(f"Autostart Configuration: {name}")
            
        self.configurationInfo: WireguardConfigurationInfo | None = None
        configurationInfoJson = self.readConfigurationInfo()
        if not configurationInfoJson:
            self.configurationInfo = WireguardConfigurationInfo(**{})
            self.initConfigurationInfo()
        else:
            self.configurationInfo = WireguardConfigurationInfo.model_validate_json(configurationInfoJson.get("Info"))
        
        if self.Status:
            self.addAutostart()

    def __getProtocolPath(self) -> str:
        _, path = self.DashboardConfig.GetConfig("Server", "wg_conf_path") if self.Protocol == "wg" \
            else self.DashboardConfig.GetConfig("Server", "awg_conf_path")
        return path

    def __initPeersList(self):
        self.Peers: list[Peer] = []
        self.getPeers()
        self.getRestrictedPeersList()

    def getRawConfigurationFile(self):
        return open(self.configPath, 'r').read()

    def updateRawConfigurationFile(self, newRawConfiguration):
        with self._backupLock:
            return self._updateRawConfigurationFile(newRawConfiguration)

    def _updateRawConfigurationFile(self, newRawConfiguration):
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
            current_app.logger.error(f"Backup restore status: {restoreStatus}")
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

    def __dropDatabase(self, *, includeEndpointHistory=True):
        existingTables = [self.Name, f'{self.Name}_restrict_access', f'{self.Name}_transfer', f'{self.Name}_deleted']
        if includeEndpointHistory:
            existingTables.append(f'{self.Name}_history_endpoint')
        try:
            with self.engine.begin() as conn:
                for name in existingTables:
                    table = sqlalchemy.Table(name, sqlalchemy.MetaData())
                    conn.execute(
                        sqlalchemy.schema.DropTable(table, if_exists=True)
                    )
        except Exception:
            current_app.logger.exception("Dropping table failed")
            return False
        return True

    def createDatabase(self, dbName = None):
        def generate_column_obj():
            return [
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
                sqlalchemy.Column('notes', sqlalchemy.Text),
                sqlalchemy.Column('remote_endpoint', sqlalchemy.String(255)),
                sqlalchemy.Column('preshared_key', sqlalchemy.String(255))
            ]

        if dbName is None:
            dbName = self.Name

        self.peersTable = sqlalchemy.Table(
            f'{dbName}', self.metadata, *generate_column_obj(), extend_existing=True
        )

        self.peersRestrictedTable = sqlalchemy.Table(
            f'{dbName}_restrict_access', self.metadata, *generate_column_obj(), extend_existing=True
        )

        self.peersDeletedTable = sqlalchemy.Table(
            f'{dbName}_deleted', self.metadata, *generate_column_obj(), extend_existing=True
        )

        if self.DashboardConfig.GetConfig("Database", "type")[1] == 'sqlite':
            time_col_type = sqlalchemy.DATETIME
        else:
            time_col_type = sqlalchemy.TIMESTAMP

        self.peersTransferTable = sqlalchemy.Table(
            f'{dbName}_transfer', self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False),
            sqlalchemy.Column('total_receive', sqlalchemy.Float),
            sqlalchemy.Column('total_sent', sqlalchemy.Float),
            sqlalchemy.Column('total_data', sqlalchemy.Float),
            sqlalchemy.Column('cumu_receive', sqlalchemy.Float),
            sqlalchemy.Column('cumu_sent', sqlalchemy.Float),
            sqlalchemy.Column('cumu_data', sqlalchemy.Float),
            sqlalchemy.Column('time', time_col_type, server_default=sqlalchemy.func.now()),
            extend_existing=True
        )
        
        self.peersHistoryEndpointTable = sqlalchemy.Table(
            f'{dbName}_history_endpoint', self.metadata,
            sqlalchemy.Column('id', sqlalchemy.String(255), nullable=False),
            sqlalchemy.Column('endpoint', sqlalchemy.String(255), nullable=False),
            sqlalchemy.Column('time', time_col_type),
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
            tables = [
                self.peersTable, self.peersRestrictedTable, self.peersTransferTable,
                self.peersDeletedTable, self.peersHistoryEndpointTable,
            ]
            for table in tables:
                rows = conn.execution_options(yield_per=1000).execute(table.select()).mappings()
                # The restore screen counts peer records by INSERT line. Batch only traffic history.
                batchSize = 500 if table in (self.peersTransferTable, self.peersHistoryEndpointTable) else 1
                for batch in rows.partitions(batchSize):
                    values = [dict(row) for row in batch]
                    statement = table.insert().values(values if batchSize > 1 else values[0])
                    yield str(
                        statement.compile(
                            dialect=self.engine.dialect,
                            compile_kwargs={"literal_binds": True},
                        )
                    )

    def __importDatabase(self, sqlFilePath, restore = False) -> bool:
        try:
            sqlFile = open(sqlFilePath, 'r')
        except FileNotFoundError:
            return False
        with sqlFile:
            hasEndpointHistory = sqlFile.readline().rstrip("\n") == self._ENDPOINT_HISTORY_HEADER
            if not hasEndpointHistory:
                sqlFile.seek(0)
            if not restore and not self.__dropDatabase(includeEndpointHistory=hasEndpointHistory):
                raise RuntimeError(f"Failed to drop tables for configuration {self.Name}")
            self.createDatabase()
            with self.engine.begin() as conn:
                for line in sqlFile:
                    if line.strip():
                        conn.exec_driver_sql(line)
        return True

    def __getPublicKey(self) -> str:
        return GenerateWireguardPublicKey(self.PrivateKey)[1]

    def getStatus(self) -> bool:
        self.Status = self.Name in psutil.net_if_addrs().keys()
        return self.Status

    def getAutostartStatus(self):
        s, d = self.DashboardConfig.GetConfig("WireGuardConfiguration", "autostart")
        return self.Name in d
    
    def addAutostart(self):
        s, d = self.DashboardConfig.GetConfig("WireGuardConfiguration", "autostart")
        if self.Name not in d:
            d.append(self.Name)
            self.DashboardConfig.SetConfig("WireGuardConfiguration", "autostart", d)
    
    def removeAutostart(self):
        s, d = self.DashboardConfig.GetConfig("WireGuardConfiguration", "autostart")
        if self.Name in d:
            d.remove(self.Name)
            self.DashboardConfig.SetConfig("WireGuardConfiguration", "autostart", d)

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
                    if "[Peer]" not in content:
                        current_app.logger.info(f"{self.Name} config has no [Peer] section")
                        self.Peers = []
                        return

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
                    
                    for i in p:
                        if "PublicKey" in i.keys():
                            with self.engine.connect() as conn:
                                tempPeer = conn.execute(
                                    self.peersTable.select().where(
                                        self.peersTable.columns.id == i['PublicKey']
                                    )
                                ).mappings().fetchone()
                            
                            if tempPeer is None:
                                tempPeer = {
                                    "id": i['PublicKey'],
                                    "private_key": "",
                                    "DNS": self.DashboardConfig.GetConfig("Peers", "peer_global_DNS")[1],
                                    "endpoint_allowed_ip": self.DashboardConfig.GetConfig("Peers", "peer_endpoint_allowed_ip")[1],
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
                                    "mtu": self.DashboardConfig.GetConfig("Peers", "peer_mtu")[1] if len(self.DashboardConfig.GetConfig("Peers", "peer_mtu")[1]) > 0 else None,
                                    "keepalive": self.DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1] if len(self.DashboardConfig.GetConfig("Peers", "peer_keep_alive")[1]) > 0 else None,
                                    "notes": "",
                                    "remote_endpoint": self.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1],
                                    "preshared_key": i["PresharedKey"] if "PresharedKey" in i.keys() else ""
                                }
                                with self.engine.begin() as conn:
                                    conn.execute(
                                        self.peersTable.insert().values(tempPeer)
                                    )                                    
                            else:
                                with self.engine.begin() as conn:
                                    conn.execute(
                                        self.peersTable.update().values({
                                            "allowed_ip": i.get("AllowedIPs", "N/A")
                                        }).where(
                                            self.peersTable.columns.id == i['PublicKey']
                                        )
                                    )
                            tmpList.append(Peer(tempPeer, self))
                except Exception as e:
                    current_app.logger.error(f"{self.Name} getPeers() Error", e)
        else:
            with self.engine.connect() as conn:
                existingPeers = conn.execute(self.peersTable.select()).mappings().fetchall()
                for i in existingPeers:
                    tmpList.append(Peer(i, self))
        self.Peers = tmpList
    
    def logPeersTraffic(self):
        with self.engine.begin() as conn:
            for tempPeer in self.Peers:
                if tempPeer.status == "running":
                    conn.execute(
                        self.peersTransferTable.insert().values({
                            "id": tempPeer.id,
                            "total_receive": tempPeer.total_receive,
                            "total_sent": tempPeer.total_sent,
                            "total_data": tempPeer.total_data,
                            "cumu_sent": tempPeer.cumu_sent,
                            "cumu_receive": tempPeer.cumu_receive,
                            "cumu_data": tempPeer.cumu_data,
                            "time": datetime.now()
                        })
                    )
    
    def logPeersHistoryEndpoint(self):
        with self.engine.begin() as conn:
            for tempPeer in self.Peers:
                if tempPeer.status == "running":
                    endpoint = tempPeer.endpoint.rsplit(":", 1)    
                    if len(endpoint) == 2 and len(endpoint[0]) > 0:
                        exist = conn.execute(
                            self.peersHistoryEndpointTable.select().where(
                                sqlalchemy.and_(
                                    self.peersHistoryEndpointTable.c.id == tempPeer.id,
                                    self.peersHistoryEndpointTable.c.endpoint == endpoint[0]
                                )
                            )
                        ).mappings().fetchone()
                        if not exist:
                            conn.execute(
                                self.peersHistoryEndpointTable.insert().values({
                                    "id": tempPeer.id,
                                    "endpoint": endpoint[0],
                                    "time": datetime.now()
                                })
                            )
                          
    def addPeers(self, peers: list) -> tuple[bool, list, str]:
        result = {
            "message": None,
            "peers": []
        }
        try:
            cleanedAllowedIPs = {}
            for p in peers:
                newAllowedIPs = p['allowed_ip'].replace(" ", "")
                if not CheckAddress(newAllowedIPs):
                    return False, [], "Allowed IPs entry format is incorrect"
                if not CheckPeerKey(p["id"]):
                    return False, [], "Peer key format is incorrect"
                cleanedAllowedIPs[p["id"]] = newAllowedIPs

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
                        "notes": i.get("notes", ""),
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

                command = [self.Protocol, "set", self.Name, "peer", p['id'], "allowed-ips", cleanedAllowedIPs[p["id"]], "preshared-key", uid if presharedKeyExist else "/dev/null"]
                subprocess.check_output(command, stderr=subprocess.STDOUT)

                if presharedKeyExist:
                    os.remove(uid)

            command = [f"{self.Protocol}-quick", "save", self.Name]
            subprocess.check_output(command, stderr=subprocess.STDOUT)

            self.getPeers()
            for p in peers:
                p = self.searchPeer(p['id'])
                if p[0]:
                    result['peers'].append(p[1])
            self.DashboardWebHooks.RunWebHook("peer_created", {
                "configuration": self.Name,
                "peers": list(map(lambda k : k['id'], peers))
            })
        except Exception as e:
            current_app.logger.error("Add peers error", e)
            return False, [], "Internal server error"
        return True, result['peers'], ""

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

                    newAllowedIPs = restrictedPeer['allowed_ip'].replace(" ", "")
                    if not CheckAddress(newAllowedIPs):
                        return False, "Allowed IPs entry format is incorrect"

                    if not CheckPeerKey(restrictedPeer["id"]):
                        return False, "Peer key format is incorrect"

                    command = [self.Protocol, "set", self.Name, "peer", restrictedPeer["id"], "allowed-ips", newAllowedIPs, "preshared-key", uid if presharedKeyExist else "/dev/null"]
                    subprocess.check_output(command, stderr=subprocess.STDOUT)

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
                        command = [self.Protocol, "set", self.Name, "peer", pf.id, "remove"]
                        subprocess.check_output(command, stderr=subprocess.STDOUT)

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
        self.getRestrictedPeers()
        self.getPeers()
        if numOfRestrictedPeers == len(listOfPublicKeys):
            return True, f"Restricted {numOfRestrictedPeers} peer(s)"
        return False, f"Restricted {numOfRestrictedPeers} peer(s) successfully. Failed to restrict {numOfFailedToRestrictPeers} peer(s)"


    def deletePeers(self, listOfPublicKeys, AllPeerJobs: PeerJobs, AllPeerShareLinks: PeerShareLinks) -> tuple[bool, str]:
        numOfDeletedPeers = 0
        numOfFailedToDeletePeers = 0
        deleted = []
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
                        deleted.append(pf.id)
                        numOfDeletedPeers += 1
                    except Exception as e:
                        numOfFailedToDeletePeers += 1

        if not self.__wgSave():
            return False, "Failed to save configuration through WireGuard"

        self.getPeers()
        
        if numOfDeletedPeers == 0 and numOfFailedToDeletePeers == 0:
            return False, "No peer(s) to delete found"
        
        if numOfDeletedPeers == len(listOfPublicKeys):
            self.DashboardWebHooks.RunWebHook("peer_deleted", {
                "configuration": self.Name,
                "peers": deleted
            })
            return True, f"Deleted {numOfDeletedPeers} peer(s)"
        
        return False, f"Deleted {numOfDeletedPeers} peer(s) successfully. Failed to delete {numOfFailedToDeletePeers} peer(s)"

    def __wgSave(self) -> tuple[bool, str] | tuple[bool, None]:
        try:
            command = [f"{self.Protocol}-quick", "save", self.Name]
            subprocess.check_output(command, stderr=subprocess.STDOUT)

            return True, None
        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"Failed to process command:\n{str(e)}")
            return False, "Internal server error"

    def getPeersLatestHandshake(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            command = [self.Protocol, "show", self.Name, "latest-handshakes"]
            latestHandshake = subprocess.check_output(command, stderr=subprocess.STDOUT)
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
        command = [self.Protocol, "show", self.Name, "transfer"]
        data_usage = subprocess.check_output(command, stderr=subprocess.STDOUT)

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
                        total_sent = cur_i['total_sent']
                        total_receive = cur_i['total_receive']
                        cur_total_sent = float(data_usage[i][2]) / (1024 ** 3)
                        cur_total_receive = float(data_usage[i][1]) / (1024 ** 3)
                        cumulative_receive = cur_i['cumu_receive'] + total_receive
                        cumulative_sent = cur_i['cumu_sent'] + total_sent
                        if (total_sent * 0.999 ) <= cur_total_sent and (total_receive * 0.999) <= cur_total_receive: # An accuracy of 1K ppm is sufficient
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

            

    def getPeersEndpoint(self):
        if not self.getStatus():
            self.toggleConfiguration()
        try:
            command = [self.Protocol, "show", self.Name, "endpoints"]
            data_usage = subprocess.check_output(command, stderr=subprocess.STDOUT)
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

    def toggleConfiguration(self) -> tuple[bool, str] | tuple[bool, None]:
        self.getStatus()
        if self.Status:
            try:
                command = [f"{self.Protocol}-quick", "down", self.Name]
                check = subprocess.check_output(command, stderr=subprocess.STDOUT)

                self.removeAutostart()
            except subprocess.CalledProcessError as exc:
                return False, str(exc.output.strip().decode("utf-8"))
        else:
            try:
                command = [f"{self.Protocol}-quick", "up", self.Name]
                check = subprocess.check_output(command, stderr=subprocess.STDOUT)

                self.addAutostart()
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

    def _backupDirectory(self):
        return Path(self.__getProtocolPath()) / "WGDashboard_Backup"

    def _backupPath(self, filename):
        if isinstance(filename, str) and re.fullmatch(rf"{re.escape(self.Name)}_\d+\.conf", filename):
            path = self._backupDirectory() / filename
            if path.is_file():
                return path
        return None

    def backupConfigurationFile(self) -> tuple[bool, dict[str, str]]:
        with self._backupLock:
            directory = self._backupDirectory()
            directory.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            while (directory / f"{self.Name}_{stamp}.conf").exists() or (directory / f"{self.Name}_{stamp}.sql").exists():
                stamp = str(int(stamp) + 1)
            conf = directory / f"{self.Name}_{stamp}.conf"
            sql = conf.with_suffix(".sql")
            tempConf = conf.with_suffix(".conf.tmp")
            tempSql = conf.with_suffix(".sql.tmp")
            try:
                shutil.copy(self.configPath, tempConf)
                with tempSql.open("w") as f:
                    f.write(self._ENDPOINT_HISTORY_HEADER + "\n")
                    for statement in self.__dumpDatabase():
                        f.write(statement + "\n")
                tempSql.replace(sql)
                try:
                    tempConf.replace(conf)
                except OSError:
                    sql.unlink(missing_ok=True)
                    raise
            finally:
                tempConf.unlink(missing_ok=True)
                tempSql.unlink(missing_ok=True)

            return True, {"filename": conf.name, "backupDate": stamp[:14]}

    def getBackups(self, databaseContent=False, *, metadataOnly=False):
        with self._backupLock:
            directory = self._backupDirectory()
            try:
                with os.scandir(directory) as entries:
                    files = {entry.name for entry in entries if entry.is_file()}
            except FileNotFoundError:
                return []

            pattern = re.compile(rf"{re.escape(self.Name)}_(\d+)\.conf")
            backups = []
            matches = [(filename, match[1]) for filename in files if (match := pattern.fullmatch(filename))]
            matches.sort(key=lambda item: item[1], reverse=True)
            for filename, stamp in matches:
                path = directory / filename
                sql = path.with_suffix(".sql")
                backup = {
                    "filename": filename,
                    "backupDate": stamp[:14],
                    "database": sql.name in files,
                }
                if not metadataOnly:
                    backup["content"] = path.read_text()
                if databaseContent and backup["database"]:
                    backup["databaseContent"] = sql.read_text()
                backups.append(backup)
            return backups

    def getBackupContent(self, filename):
        with self._backupLock:
            path = self._backupPath(filename)
            return path.read_text() if path is not None else None

    def restoreBackup(self, backupFileName: str) -> bool:
        with self._backupLock:
            target = self._backupPath(backupFileName)
            if target is None:
                return False
            if self.Status:
                self.toggleConfiguration()
            targetContent = target.read_text()
            try:
                with open(self.configPath, 'w') as f:
                    f.write(targetContent)
            except OSError:
                return False
            self.__parseConfigurationFile()
            self.__importDatabase(target.with_suffix(".sql"))
            self.__initPeersList()
            return True

    def _removeBackupFiles(self, path):
        path.unlink()
        path.with_suffix(".sql").unlink(missing_ok=True)

    def deleteBackup(self, backupFileName: str) -> bool:
        with self._backupLock:
            path = self._backupPath(backupFileName)
            if path is None:
                return False
            try:
                self._removeBackupFiles(path)
            except OSError:
                return False
            return True

    def downloadBackup(self, backupFileName: str) -> tuple[bool, str] | tuple[bool, None]:
        with self._backupLock:
            path = self._backupPath(backupFileName)
            if path is None:
                return False, None
            archive = f"{uuid.uuid4()}.zip"
            with ZipFile(os.path.join("download", archive), "w") as zipFile:
                zipFile.write(path, path.name)
                sql = path.with_suffix(".sql")
                if sql.is_file():
                    zipFile.write(sql, sql.name)
            return True, archive

    def updateConfigurationSettings(self, newData: dict) -> tuple[bool, str]:
        if self.Status:
            self.toggleConfiguration()
        original = []
        dataChanged = False
        with open(self.configPath, 'r') as f:
            original = [l.rstrip("\n") for l in f.readlines()]
            allowEdit = ["Address", "PreUp", "PostUp", "PreDown", "PostDown", "ListenPort", "Table"]
            awgKeys = []
            if self.Protocol == 'awg':
                awgKeys = ["Jc", "Jmin", "Jmax", "S1", "S2", "S3", "S4", "H1", "H2", "H3", "H4", "I1", "I2", "I3", "I4", "I5", "HeaderProtectionKey", "ContentPaddingAddition", "RekeyAfterTime", "RekeyTimeout", "RejectAfterTime", "KeepaliveTimeout", "MaxHandshakeAttempts", "RandomTrailers", "DisableCookies", "J1", "J2", "J3", "Itime"]
                allowEdit += awgKeys
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
                val = str(newData.get(key, "")).strip()
                if key in awgKeys and val == "":
                    continue
                new.insert(1, f"{key} = {val}")
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
        newConfigurationName = os.path.basename(newConfigurationName)

        if len(newConfigurationName) > 15 or not re.match(r'^[a-zA-Z0-9_=\+\.\-]{1,15}$', newConfigurationName):
            return False, "Configuration name is either too long or contains an illegal character"
        
        newConfigurationName = newConfigurationName.replace("`", "") # double check
    
        try:
            if self.getStatus():
                self.toggleConfiguration()
            self.createDatabase(newConfigurationName)
            with self.engine.begin() as conn:
                def doRenameStatement(suffix):
                    newConfig = f"{newConfigurationName}{suffix}"
                    oldConfig = f"{self.Name}{suffix}"

                    conn.execute(
                        sqlalchemy.text(
                            f'INSERT INTO `{newConfig}` SELECT * FROM `{oldConfig}`'
                        )
                    )

                doRenameStatement("")
                doRenameStatement("_restrict_access")
                doRenameStatement("_deleted")
                doRenameStatement("_transfer")
                doRenameStatement("_history_endpoint")
                conn.execute(
                    self.infoTable.update()
                    .where(self.infoTable.c.ID == self.Name)
                    .values(ID=newConfigurationName)
                )

            self.AllPeerJobs.updateJobConfigurationName(self.Name, newConfigurationName)
            shutil.copy(
                self.configPath,
                os.path.join(self.__getProtocolPath(), f'{newConfigurationName}.conf')
            )
            self.deleteConfiguration()
        except Exception as e:
            current_app.logger.error(f"Failed to rename configuration.\nNew Configuration Name: {newConfigurationName}\nError: {str(e)}")
            return False, "Internal server error"
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
                        current_app.logger.error(f"{self.Name} peer {p.id} have invalid ip", e)
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
                current_app.logger.error(f"Error: Failed to parse IP address {ca} from {self.Name}", e)
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
                        current_app.logger.error(f"{self.Name} peer {p.id} have invalid ip", e)
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
                current_app.logger.error(f"Failed to parse IP address {ca} from {self.Name}", e)
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
        
    def updateConfigurationInfo(self, key: str, value: str | dict[str, str] | dict[str, dict] | bool) -> tuple[bool, Any, str] | tuple[
        bool, str, None] | tuple[bool, None, None]:
        if key == "Description":
            self.configurationInfo.Description = value
        elif key == "OverridePeerSettings":
            for (key, val) in value.items():
                try:
                    status, msg = self.__validateOverridePeerSettings(key, RenderSandboxedTemplate(val, configuration=self.toJson()))
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
        elif key == "PeerTrafficTracking":
            self.configurationInfo.PeerTrafficTracking = value
        elif key == "PeerHistoricalEndpointTracking":
            self.configurationInfo.PeerHistoricalEndpointTracking = value
        else: 
            return False, "Key does not exist", None
        self.storeConfigurationInfo()
        return True, None, None
    
    def __validateOverridePeerSettings(self, key: str, value: str | int) -> tuple[bool, None] | tuple[bool, str]:
        status = True
        msg = None
        if key == "DNS" and value:
            status, msg = ValidateDNSAddress(value)
        elif key == "EndpointAllowedIPs" and value:
            status, msg = ValidateEndpointAllowedIPs(value)
        elif key == "ListenPort" and value:
            if not value.isnumeric() or not (1 <= int(value) <= 65535):
                status = False
                msg = "Listen Port must be >= 1 and <= 65535"        
        return status, msg
        
    def getTransferTableSize(self):
        with self.engine.connect() as db:
            row_count = db.execute(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(self.peersTransferTable)
            ).scalar()
            return int(row_count)

    def getHistoricalEndpointTableSize(self):
        with self.engine.connect() as db:
            row_count = db.execute(
                sqlalchemy.select(sqlalchemy.func.count()).select_from(self.peersHistoryEndpointTable)
            ).scalar()
            return int(row_count)
        
    def downloadTransferTable(self):
        with self.engine.connect() as db:
            data = db.execute(
                self.peersTransferTable.select()
            ).mappings().fetchall()
            return data

    def downloadHistoricalEndpointTable(self):
        with self.engine.connect() as db:
            data = db.execute(
                self.peersHistoryEndpointTable.select()
            ).mappings().fetchall()
            return data
    
    def deleteTransferTable(self):
        try:
            with self.engine.begin() as db:
                db.execute(
                    self.peersTransferTable.delete()
            )
            with self.engine.connect() as conn:
                if conn.dialect.name == 'sqlite':
                    print("[WGDashboard] SQLite Vacuuming Database")
                    conn.execute(sqlalchemy.text('VACUUM;'))
        except Exception as e:
            return False
        return True

    def deleteHistoryEndpointTable(self):
        try:
            with self.engine.begin() as db:
                db.execute(
                    self.peersHistoryEndpointTable.delete()
                )
            with self.engine.connect() as conn:
                if conn.dialect.name == 'sqlite':
                    print("[WGDashboard] SQLite Vacuuming Database")
                    conn.execute(sqlalchemy.text('VACUUM;'))
        except Exception as e:
            return False
        return True
