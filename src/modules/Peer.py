"""
Peer
"""
import base64
import datetime
import json
import os, subprocess, uuid, random, re
from datetime import timedelta

import jinja2
import sqlalchemy as db
from .PeerJob import PeerJob
from .PeerShareLink import PeerShareLink
from .Utilities import GenerateWireguardPublicKey, ValidateIPAddressesWithRange, ValidateDNSAddress


class Peer:
    def __init__(self, tableData, configuration):
        self.configuration = configuration
        self.id = tableData["id"]
        self.private_key = tableData["private_key"]
        self.DNS = tableData["DNS"]
        self.endpoint_allowed_ip = tableData["endpoint_allowed_ip"]
        self.name = tableData["name"]
        self.total_receive = tableData["total_receive"]
        self.total_sent = tableData["total_sent"]
        self.total_data = tableData["total_data"]
        self.endpoint = tableData["endpoint"]
        self.status = tableData["status"]
        self.latest_handshake = tableData["latest_handshake"]
        self.allowed_ip = tableData["allowed_ip"]
        self.cumu_receive = tableData["cumu_receive"]
        self.cumu_sent = tableData["cumu_sent"]
        self.cumu_data = tableData["cumu_data"]
        self.mtu = tableData["mtu"]
        self.keepalive = tableData["keepalive"]
        self.remote_endpoint = tableData["remote_endpoint"]
        self.preshared_key = tableData["preshared_key"]
        self.jobs: list[PeerJob] = []
        self.ShareLink: list[PeerShareLink] = []
        self.getJobs()
        self.getShareLink()

    def toJson(self):
        # self.getJobs()
        # self.getShareLink()
        return self.__dict__

    def __repr__(self):
        return str(self.toJson())

    def updatePeer(self, name: str, private_key: str,
                   preshared_key: str,
                   dns_addresses: str, allowed_ip: str, endpoint_allowed_ip: str, mtu: int,
                   keepalive: int) -> tuple[bool, str] or tuple[bool, None]:
        if not self.configuration.getStatus():
            self.configuration.toggleConfiguration()

        existingAllowedIps = [item for row in list(
            map(lambda x: [q.strip() for q in x.split(',')],
                map(lambda y: y.allowed_ip,
                    list(filter(lambda k: k.id != self.id, self.configuration.getPeersList()))))) for item in row]

        if allowed_ip in existingAllowedIps:
            return False, "Allowed IP already taken by another peer"
        
        if not ValidateIPAddressesWithRange(endpoint_allowed_ip):
            return False, f"Endpoint Allowed IPs format is incorrect"
        
        if len(dns_addresses) > 0 and not ValidateDNSAddress(dns_addresses):
            return False, f"DNS format is incorrect"
        
        if type(mtu) is str or mtu is None:
            mtu = 0
        
        if mtu < 0 or mtu > 1460:
            return False, "MTU format is not correct"
        
        if type(keepalive) is str or keepalive is None:
            keepalive = 0
        
        if keepalive < 0:
            return False, "Persistent Keepalive format is not correct"
        if len(private_key) > 0:
            pubKey = GenerateWireguardPublicKey(private_key)
            if not pubKey[0] or pubKey[1] != self.id:
                return False, "Private key does not match with the public key"
        try:
            rd = random.Random()
            uid = str(uuid.UUID(int=rd.getrandbits(128), version=4))
            pskExist = len(preshared_key) > 0

            if pskExist:
                with open(uid, "w+") as f:
                    f.write(preshared_key)
            newAllowedIPs = allowed_ip.replace(" ", "")
            updateAllowedIp = subprocess.check_output(
                f"{self.configuration.Protocol} set {self.configuration.Name} peer {self.id} allowed-ips {newAllowedIPs} {f'preshared-key {uid}' if pskExist else 'preshared-key /dev/null'}",
                shell=True, stderr=subprocess.STDOUT)

            if pskExist: os.remove(uid)
            if len(updateAllowedIp.decode().strip("\n")) != 0:
                return False, "Update peer failed when updating Allowed IPs"
            saveConfig = subprocess.check_output(f"{self.configuration.Protocol}-quick save {self.configuration.Name}",
                                                 shell=True, stderr=subprocess.STDOUT)
            if f"wg showconf {self.configuration.Name}" not in saveConfig.decode().strip('\n'):
                return False, "Update peer failed when saving the configuration"
            with self.configuration.engine.begin() as conn:
                conn.execute(
                    self.configuration.peersTable.update().values({
                        "name": name,
                        "private_key": private_key,
                        "DNS": dns_addresses,
                        "endpoint_allowed_ip": endpoint_allowed_ip,
                        "mtu": mtu,
                        "keepalive": keepalive,
                        "preshared_key": preshared_key
                    }).where(
                        self.configuration.peersTable.c.id == self.id
                    )
                )
            return True, None
        except subprocess.CalledProcessError as exc:
            return False, exc.output.decode("UTF-8").strip()

    def downloadPeer(self) -> dict[str, str]:
        final = {
            "fileName": "",
            "file": ""
        }
        filename = self.name
        if len(filename) == 0:
            filename = "UntitledPeer"
        filename = "".join(filename.split(' '))
        filename = f"{filename}"
        illegal_filename = [".", ",", "/", "?", "<", ">", "\\", ":", "*", '|' '\"', "com1", "com2", "com3",
                            "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
                            "lpt5", "lpt6", "lpt7", "lpt8", "lpt9", "con", "nul", "prn"]
        for i in illegal_filename:
            filename = filename.replace(i, "")

        for i in filename:
            if re.match("^[a-zA-Z0-9_=+.-]$", i):
                final["fileName"] += i
                
        interfaceSection = {
            "PrivateKey": self.private_key,
            "Address": self.allowed_ip,
            "MTU": (
                self.configuration.configurationInfo.OverridePeerSettings.MTU
                    if self.configuration.configurationInfo.OverridePeerSettings.MTU else self.mtu
            ),
            "DNS": (
                self.configuration.configurationInfo.OverridePeerSettings.DNS 
                    if self.configuration.configurationInfo.OverridePeerSettings.DNS else self.DNS
            )
        }
        
        if self.configuration.Protocol == "awg":
            interfaceSection.update({
                "Jc": self.configuration.Jc,
                "Jmin": self.configuration.Jmin,
                "Jmax": self.configuration.Jmax,
                "S1": self.configuration.S1,
                "S2": self.configuration.S2,
                "H1": self.configuration.H1,
                "H2": self.configuration.H2,
                "H3": self.configuration.H3,
                "H4": self.configuration.H4
            })
            
        peerSection = {
            "PublicKey": self.configuration.PublicKey,
            "AllowedIPs": (
                self.configuration.configurationInfo.OverridePeerSettings.EndpointAllowedIPs
                    if self.configuration.configurationInfo.OverridePeerSettings.EndpointAllowedIPs else self.endpoint_allowed_ip
            ),
            "Endpoint": f'{(self.configuration.configurationInfo.OverridePeerSettings.PeerRemoteEndpoint if self.configuration.configurationInfo.OverridePeerSettings.PeerRemoteEndpoint else self.configuration.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1])}:{(self.configuration.configurationInfo.OverridePeerSettings.ListenPort if self.configuration.configurationInfo.OverridePeerSettings.ListenPort else self.configuration.ListenPort)}',
            "PersistentKeepalive": (
                self.configuration.configurationInfo.OverridePeerSettings.PersistentKeepalive 
                if self.configuration.configurationInfo.OverridePeerSettings.PersistentKeepalive
                else self.keepalive
            ),
            "PresharedKey": self.preshared_key
        }
        combine = [interfaceSection.items(), peerSection.items()]
        for s in range(len(combine)):
            if s == 0:
                final["file"] += "[Interface]\n"
            else:
                final["file"] += "\n[Peer]\n"
            for (key, val) in combine[s]:
                if val is not None and ((type(val) is str and len(val) > 0) or (type(val) is int and val > 0)):
                    final["file"] += f"{key} = {val}\n"
        
        final["file"] = jinja2.Template(final["file"]).render(configuration=self.configuration)


        if self.configuration.Protocol == "awg":
            final["amneziaVPN"] = json.dumps({
                "containers": [{
                    "awg": {
                        "isThirdPartyConfig": True,
                        "last_config": final['file'],
                        "port": self.configuration.ListenPort,
                        "transport_proto": "udp"
                    },
                    "container": "amnezia-awg"
                }],
                "defaultContainer": "amnezia-awg",
                "description": self.name,
                "hostName": (
                    self.configuration.configurationInfo.OverridePeerSettings.PeerRemoteEndpoint 
                        if self.configuration.configurationInfo.OverridePeerSettings.PeerRemoteEndpoint 
                        else self.configuration.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1])
            })
        return final

    def getJobs(self):
        self.jobs = self.configuration.AllPeerJobs.searchJob(self.configuration.Name, self.id)

    def getShareLink(self):
        self.ShareLink = self.configuration.AllPeerShareLinks.getLink(self.configuration.Name, self.id)

    def resetDataUsage(self, mode: str):
        try:
            with self.configuration.engine.begin() as conn:
                if mode == "total":
                    conn.execute(
                        self.configuration.peersTable.update().values({
                            "total_data": 0,
                            "cumu_data": 0,
                            "total_receive": 0,
                            "cumu_receive": 0,
                            "total_sent": 0,
                            "cumu_sent": 0
                        }).where(
                            self.configuration.peersTable.c.id == self.id
                        )
                    )
                    self.total_data = 0
                    self.total_receive = 0
                    self.total_sent = 0
                    self.cumu_data = 0
                    self.cumu_sent = 0
                    self.cumu_receive = 0
                elif mode == "receive":
                    conn.execute(
                        self.configuration.peersTable.update().values({
                            "total_receive": 0,
                            "cumu_receive": 0,
                        }).where(
                            self.configuration.peersTable.c.id == self.id
                        )
                    )
                    self.cumu_receive = 0
                    self.total_receive = 0
                elif mode == "sent":
                    conn.execute(
                        self.configuration.peersTable.update().values({
                            "total_sent": 0,
                            "cumu_sent": 0
                        }).where(
                            self.configuration.peersTable.c.id == self.id
                        )
                    )
                    self.cumu_sent = 0
                    self.total_sent = 0
                else:
                    return False
        except Exception as e:
            print(e)
            return False
        return True
    
    def getEndpoints(self):
        result = []
        with self.configuration.engine.connect() as conn:
            result = conn.execute(
                db.select(
                    self.configuration.peersHistoryEndpointTable.c.endpoint
                ).group_by(
                    self.configuration.peersHistoryEndpointTable.c.endpoint
                ).where(
                    self.configuration.peersHistoryEndpointTable.c.id == self.id
                )
            ).mappings().fetchall()
        return list(result)
    
    def getTraffics(self, interval: int = 30, startDate: datetime.datetime = None, endDate: datetime.datetime = None):
        if startDate is None and endDate is None:
            endDate = datetime.datetime.now()
            startDate = endDate - timedelta(minutes=interval)
        else:
            endDate = endDate.replace(hour=23, minute=59, second=59, microsecond=999999)
            startDate = startDate.replace(hour=0, minute=0, second=0, microsecond=0)

        with self.configuration.engine.connect() as conn:
            result = conn.execute(
                db.select(
                    self.configuration.peersTransferTable.c.cumu_data,
                    self.configuration.peersTransferTable.c.total_data,
                    self.configuration.peersTransferTable.c.cumu_receive,
                    self.configuration.peersTransferTable.c.total_receive,
                    self.configuration.peersTransferTable.c.cumu_sent,
                    self.configuration.peersTransferTable.c.total_sent,
                    self.configuration.peersTransferTable.c.time
                ).where(
                    db.and_(
                        self.configuration.peersTransferTable.c.id == self.id,
                        self.configuration.peersTransferTable.c.time <= endDate,
                        self.configuration.peersTransferTable.c.time >= startDate,
                        )
                ).order_by(
                    self.configuration.peersTransferTable.c.time
                )
            ).mappings().fetchall()
        return list(result)
            
    
    def getSessions(self, startDate: datetime.datetime = None, endDate: datetime.datetime = None):
        if endDate is None:
            endDate = datetime.datetime.now()
        
        if startDate is None:
            startDate = endDate

        endDate = endDate.replace(hour=23, minute=59, second=59, microsecond=999999)
        startDate = startDate.replace(hour=0, minute=0, second=0, microsecond=0)
            

        with self.configuration.engine.connect() as conn:
            result = conn.execute(
                db.select(
                    self.configuration.peersTransferTable.c.time
                ).where(
                    db.and_(
                        self.configuration.peersTransferTable.c.id == self.id,
                        self.configuration.peersTransferTable.c.time <= endDate,
                        self.configuration.peersTransferTable.c.time >= startDate,
                    )
                ).order_by(
                    self.configuration.peersTransferTable.c.time
                )
            ).fetchall()
        time = list(map(lambda x : x[0], result))
        return time
    
    def __duration(self, t1: datetime.datetime, t2: datetime.datetime):
        delta = t1 - t2
        
        hours, remainder = divmod(delta.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"