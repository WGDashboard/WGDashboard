import os
import random
import re
import subprocess
import uuid

from .Peer import Peer
from .Utilities import ValidateIPAddressesWithRange, ValidateDNSAddress, GenerateWireguardPublicKey


class AmneziaWGPeer(Peer):
    def __init__(self, tableData, configuration):
        self.advanced_security = tableData["advanced_security"]
        super().__init__(tableData, configuration)

    def downloadPeer(self) -> dict[str, str]:
        filename = self.name
        if len(filename) == 0:
            filename = "UntitledPeer"
        filename = "".join(filename.split(' '))
        filename = f"{filename}_{self.configuration.Name}"
        illegal_filename = [".", ",", "/", "?", "<", ">", "\\", ":", "*", '|' '\"', "com1", "com2", "com3",
                            "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
                            "lpt5", "lpt6", "lpt7", "lpt8", "lpt9", "con", "nul", "prn"]
        for i in illegal_filename:
            filename = filename.replace(i, "")

        finalFilename = ""
        for i in filename:
            if re.match("^[a-zA-Z0-9_=+.-]$", i):
                finalFilename += i

        interfaceSection = {
            "PrivateKey": self.private_key,
            "Address": self.allowed_ip,
            "MTU": self.mtu,
            "DNS": self.DNS,
            "Jc": self.configuration.Jc,
            "Jmin": self.configuration.Jmin,
            "Jmax": self.configuration.Jmax,
            "S1": self.configuration.S1,
            "S2": self.configuration.S2,
            "H1": self.configuration.H1,
            "H2": self.configuration.H2,
            "H3": self.configuration.H3,
            "H4": self.configuration.H4 
        }
        peerSection = {
            "PublicKey": self.configuration.PublicKey,
            "AllowedIPs": self.endpoint_allowed_ip,
            "Endpoint": f'{self.configuration.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1]}:{self.configuration.ListenPort}',
            "PersistentKeepalive": self.keepalive,
            "PresharedKey": self.preshared_key
        }
        combine = [interfaceSection.items(), peerSection.items()]
        peerConfiguration = ""
        for s in range(len(combine)):
            if s == 0:
                peerConfiguration += "[Interface]\n"
            else:
                peerConfiguration += "\n[Peer]\n"
            for (key, val) in combine[s]:
                if val is not None and ((type(val) is str and len(val) > 0) or (type(val) is int and val > 0)):
                    peerConfiguration += f"{key} = {val}\n"

#         peerConfiguration = f'''[Interface]
# PrivateKey = {self.private_key}
# Address = {self.allowed_ip}
# MTU = {str(self.mtu)}
# Jc = {self.configuration.Jc}
# Jmin = {self.configuration.Jmin}
# Jmax = {self.configuration.Jmax}
# S1 = {self.configuration.S1}
# S2 = {self.configuration.S2}
# H1 = {self.configuration.H1}
# H2 = {self.configuration.H2}
# H3 = {self.configuration.H3}
# H4 = {self.configuration.H4}
# '''
#         if len(self.DNS) > 0:
#             peerConfiguration += f"DNS = {self.DNS}\n"
#         peerConfiguration += f'''
# [Peer]
# PublicKey = {self.configuration.PublicKey}
# AllowedIPs = {self.endpoint_allowed_ip}
# Endpoint = {self.configuration.DashboardConfig.GetConfig("Peers", "remote_endpoint")[1]}:{self.configuration.ListenPort}
# PersistentKeepalive = {str(self.keepalive)}
# '''
#         if len(self.preshared_key) > 0:
#             peerConfiguration += f"PresharedKey = {self.preshared_key}\n"
        return {
            "fileName": finalFilename,
            "file": peerConfiguration
        }

    def updatePeer(self, name: str, private_key: str,
                   preshared_key: str,
                   dns_addresses: str, allowed_ip: str, endpoint_allowed_ip: str, mtu: int,
                   keepalive: int, advanced_security: str) -> tuple[bool, str] or tuple[bool, None]:
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

        if type(mtu) is str:
            mtu = 0

        if type(keepalive) is str:
            keepalive = 0
        
        if mtu < 0 or mtu > 1460:
            return False, "MTU format is not correct"
        if keepalive < 0:
            return False, "Persistent Keepalive format is not correct"
        if advanced_security != "on" and advanced_security != "off":
            return False, "Advanced Security can only be on or off"
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
            # sqlUpdate(
            #     '''UPDATE '%s' SET name = ?, private_key = ?, DNS = ?, endpoint_allowed_ip = ?, mtu = ?, 
            #     keepalive = ?, preshared_key = ?, advanced_security = ?  WHERE id = ?''' % self.configuration.Name,
            #     (name, private_key, dns_addresses, endpoint_allowed_ip, mtu,
            #      keepalive, preshared_key, advanced_security, self.id,)
            # )

            with self.configuration.engine.begin() as conn:
                conn.execute(
                    self.configuration.peersTable.update().values({
                        "name": name,
                        "private_key": private_key,
                        "DNS": dns_addresses,
                        "endpoint_allowed_ip": endpoint_allowed_ip,
                        "mtu": mtu,
                        "keepalive": keepalive,
                        "preshared_key": preshared_key,
                        "advanced_security": advanced_security
                    }).where(
                        self.configuration.peersTable.c.id == self.id
                    )
                )

            return True, None
        except subprocess.CalledProcessError as exc:
            return False, exc.output.decode("UTF-8").strip()