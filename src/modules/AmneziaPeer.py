import os
import random
import re
import subprocess
import uuid

from flask import current_app
from .Peer import Peer
from .Utilities import CheckAddress, ValidateDNSAddress, GenerateWireguardPublicKey


class AmneziaPeer(Peer):
    def __init__(self, tableData, configuration):
        super().__init__(tableData, configuration)


    def updatePeer(self, name: str, private_key: str,
                   preshared_key: str,
                   dns_addresses: str,
                   allowed_ip: str,
                   endpoint_allowed_ip: str,
                   mtu: int,
                   keepalive: int,
                   notes: str
                   ) -> tuple[bool, str | None]:

        if not self.configuration.getStatus():
            self.configuration.toggleConfiguration()

        # Before we do any compute, let us check if the given endpoint allowed ip is valid at all
        if not CheckAddress(endpoint_allowed_ip):
            return False, f"Endpoint Allowed IPs format is incorrect"

        peers = []
        for peer in self.configuration.getPeersList():
            # Make sure to exclude your own data when updating since its not really relevant
            if peer.id != self.id:
                continue
            peers.append(peer)

        used_allowed_ips = []
        for peer in peers:
            ips = peer.allowed_ip.split(',')
            ips = [ip.strip() for ip in ips]
            used_allowed_ips.append(ips)

        if allowed_ip in used_allowed_ips:
            return False, "Allowed IP already taken by another peer"

        if not ValidateDNSAddress(dns_addresses):
            return False, f"DNS IP-Address or FQDN is incorrect"

        if isinstance(mtu, str):
            mtu = 0

        if isinstance(keepalive, str):
            keepalive = 0
        
        if mtu not in range(0, 1461):
            return False, "MTU format is not correct"

        if keepalive < 0:
            return False, "Persistent Keepalive format is not correct"

        if len(private_key) > 0:
            pubKey = GenerateWireguardPublicKey(private_key)
            if not pubKey[0] or pubKey[1] != self.id:
                return False, "Private key does not match with the public key"
    
        try:
            rand = random.Random()
            uid = str(uuid.UUID(int=rand.getrandbits(128), version=4))
            psk_exist = len(preshared_key) > 0

            if psk_exist:
                with open(uid, "w+") as f:
                    f.write(preshared_key)

            newAllowedIPs = allowed_ip.replace(" ", "")
            updateAllowedIp = subprocess.check_output(
                f"{self.configuration.Protocol} set {self.configuration.Name} peer {self.id} allowed-ips {newAllowedIPs} {f'preshared-key {uid}' if psk_exist else 'preshared-key /dev/null'}",
                shell=True, stderr=subprocess.STDOUT)

            if psk_exist: os.remove(uid)

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
                        "notes": notes,
                        "preshared_key": preshared_key
                    }).where(
                        self.configuration.peersTable.c.id == self.id
                    )
                )
            self.configuration.getPeers()
            return True, None
        except subprocess.CalledProcessError as exc:
            return False, exc.output.decode("UTF-8").strip()