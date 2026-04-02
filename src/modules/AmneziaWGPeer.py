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
            self.configuration.getPeers()
            return True, None
        except subprocess.CalledProcessError as exc:
            return False, exc.output.decode("UTF-8").strip()