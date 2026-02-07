"""
Peer Health Monitor for WGDashboard
===================================
Periodically pings VPN IP addresses of peers to:
1. Trigger endpoint update on roaming (IP change)
2. Collect availability statistics for peers

Even if the peer doesn't respond to ICMP (firewall), the ping
causes the server to send a packet, and the client will respond
with a WireGuard keepalive from its new IP -> endpoint update.

Status logic:
- ONLINE: handshake < 3 min AND ping success
- UNPINGABLE: handshake < 3 min AND ping failed (connected but firewall blocks ICMP)
- RECENT: handshake 3-15 min (still ping to trigger endpoint update)
- OFFLINE: handshake > 15 min (DO NOT ping - waste of resources)
- UNKNOWN: no handshake data ever
"""

import threading
import time
import ipaddress
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from icmplib import ping as icmp_ping
import logging


class PeerStatus(Enum):
    """Peer status based on handshake time and ping result"""
    ONLINE = "online"           # handshake < 3 min AND pingable
    UNPINGABLE = "unpingable"   # handshake < 3 min BUT ping failed (firewall)
    RECENT = "recent"           # handshake 3-15 min
    OFFLINE = "offline"         # handshake > 15 min (don't ping these)
    UNKNOWN = "unknown"         # no handshake data


# Timeouts for status determination
HANDSHAKE_ONLINE_TIMEOUT = timedelta(minutes=3)
HANDSHAKE_RECENT_TIMEOUT = timedelta(minutes=15)


@dataclass
class PeerHealthInfo:
    """Health information for a single peer"""
    public_key: str
    vpn_ip: str
    interface: str
    name: str = ""              # Peer name from configuration

    # Ping statistics
    is_pingable: bool = False
    last_ping_time: Optional[datetime] = None
    last_ping_success: bool = False
    ping_rtt_ms: float = 0.0
    ping_success_count: int = 0
    ping_fail_count: int = 0

    # Handshake status (from WireGuard)
    last_handshake: Optional[datetime] = None
    status: PeerStatus = PeerStatus.UNKNOWN

    # Endpoint tracking
    last_endpoint: str = ""
    endpoint_changed: bool = False

    def to_dict(self) -> dict:
        return {
            "public_key": self.public_key,
            "vpn_ip": self.vpn_ip,
            "interface": self.interface,
            "name": self.name,
            "is_pingable": self.is_pingable,
            "last_ping_time": self.last_ping_time.isoformat() if self.last_ping_time else None,
            "last_ping_success": self.last_ping_success,
            "ping_rtt_ms": round(self.ping_rtt_ms, 2),
            "ping_success_rate": self._ping_success_rate(),
            "status": self.status.value,
            "last_handshake": self.last_handshake.isoformat() if self.last_handshake else None,
            "last_endpoint": self.last_endpoint,
            "endpoint_changed": self.endpoint_changed
        }

    def _ping_success_rate(self) -> float:
        total = self.ping_success_count + self.ping_fail_count
        if total == 0:
            return 0.0
        return round((self.ping_success_count / total) * 100, 1)


@dataclass
class InterfaceHealthConfig:
    """Configuration for health monitoring of an interface"""
    enabled: bool = True
    ping_interval: int = 30     # seconds
    set_keepalive: bool = True  # automatically set PersistentKeepalive
    keepalive_value: int = 25


class PeerHealthMonitor:
    """
    Background service for monitoring WireGuard peers.

    Functionality:
    - Periodic ping to VPN IP of all peers (except offline ones)
    - Automatic PersistentKeepalive setting on server
    - Collection of availability statistics
    - Detection of endpoint changes
    - Per-interface configuration with persistence
    
    Status determination:
    - First check handshake age (from WireGuard)
    - Then ping only if peer might be reachable (handshake < 15 min)
    - ONLINE = recent handshake + ping success
    - UNPINGABLE = recent handshake + ping failed (firewall blocking ICMP)
    - OFFLINE = old handshake (don't waste resources pinging)
    """

    def __init__(self, dashboard_config, wireguard_configurations: dict, logger=None):
        self.dashboard_config = dashboard_config
        self.wg_configs = wireguard_configurations
        self.logger = logger or logging.getLogger(__name__)

        # Health data for all peers (key = public_key)
        self._peer_health: Dict[str, PeerHealthInfo] = {}
        self._health_lock = threading.Lock()

        # Per-interface configuration
        self._interface_config: Dict[str, InterfaceHealthConfig] = {}

        # Thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Statistics
        self._stats = {
            "total_pings": 0,
            "successful_pings": 0,
            "failed_pings": 0,
            "skipped_offline": 0,
            "endpoint_updates": 0,
            "last_cycle_time": None,
            "last_cycle_duration_ms": 0
        }

        # Load saved configuration from INI file
        self._load_config_from_ini()

    def _load_config_from_ini(self):
        """Load per-interface configuration from wg-dashboard.ini"""
        try:
            # Get all sections that start with "Health:"
            config = self.dashboard_config._DashboardConfig__config
            for section in config.sections():
                if section.startswith("Health:"):
                    interface_name = section[7:]  # Remove "Health:" prefix
                    cfg = InterfaceHealthConfig()
                    
                    if config.has_option(section, "enabled"):
                        cfg.enabled = config.get(section, "enabled").lower() == "true"
                    if config.has_option(section, "ping_interval"):
                        cfg.ping_interval = max(10, min(300, int(config.get(section, "ping_interval"))))
                    if config.has_option(section, "set_keepalive"):
                        cfg.set_keepalive = config.get(section, "set_keepalive").lower() == "true"
                    if config.has_option(section, "keepalive_value"):
                        cfg.keepalive_value = max(10, min(120, int(config.get(section, "keepalive_value"))))
                    
                    self._interface_config[interface_name] = cfg
                    self.logger.info(f"Loaded health config for {interface_name}: enabled={cfg.enabled}, interval={cfg.ping_interval}")
        except Exception as e:
            self.logger.error(f"Error loading health config from INI: {e}")

    def _save_interface_config_to_ini(self, interface: str):
        """Save interface configuration to wg-dashboard.ini"""
        try:
            if interface not in self._interface_config:
                return False
            
            cfg = self._interface_config[interface]
            section = f"Health:{interface}"
            
            # Ensure section exists
            config = self.dashboard_config._DashboardConfig__config
            if not config.has_section(section):
                config.add_section(section)
            
            # Set values
            config.set(section, "enabled", "true" if cfg.enabled else "false")
            config.set(section, "ping_interval", str(cfg.ping_interval))
            config.set(section, "set_keepalive", "true" if cfg.set_keepalive else "false")
            config.set(section, "keepalive_value", str(cfg.keepalive_value))
            
            # Save to file
            return self.dashboard_config.SaveConfig()
        except Exception as e:
            self.logger.error(f"Error saving health config for {interface}: {e}")
            return False

    def start(self) -> bool:
        """Start health monitoring thread"""
        if self._running:
            self.logger.warning("PeerHealthMonitor already running")
            return False

        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="PeerHealthMonitor"
        )
        self._thread.start()
        self.logger.info(f"PeerHealthMonitor started (PID: {threading.get_native_id()})")
        return True

    def stop(self) -> bool:
        """Stop health monitoring"""
        if not self._running:
            return False

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("PeerHealthMonitor stopped")
        return True

    def is_running(self) -> bool:
        return self._running

    def get_interface_config(self, interface: str) -> InterfaceHealthConfig:
        """Return configuration for interface"""
        if interface not in self._interface_config:
            self._interface_config[interface] = InterfaceHealthConfig()
            # Save default config to INI
            self._save_interface_config_to_ini(interface)
        return self._interface_config[interface]

    def set_interface_config(self, interface: str, config: dict) -> bool:
        """Set configuration for interface and persist to INI"""
        try:
            if interface not in self._interface_config:
                self._interface_config[interface] = InterfaceHealthConfig()

            cfg = self._interface_config[interface]
            if 'enabled' in config:
                cfg.enabled = bool(config['enabled'])
            if 'ping_interval' in config:
                cfg.ping_interval = max(10, min(300, int(config['ping_interval'])))
            if 'set_keepalive' in config:
                cfg.set_keepalive = bool(config['set_keepalive'])
            if 'keepalive_value' in config:
                cfg.keepalive_value = max(10, min(120, int(config['keepalive_value'])))

            # Persist to INI file
            self._save_interface_config_to_ini(interface)
            self.logger.info(f"Updated health config for {interface}: enabled={cfg.enabled}, interval={cfg.ping_interval}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting interface config: {e}")
            return False

    def get_peer_health(self, public_key: str) -> Optional[dict]:
        """Return health information for peer"""
        with self._health_lock:
            if public_key in self._peer_health:
                return self._peer_health[public_key].to_dict()
        return None

    def get_all_health(self) -> dict:
        """Return health information for all peers, filtering disabled/inactive interfaces"""
        result = {
            "peers": {},
            "interfaces": {},
            "stats": self._stats.copy(),
            "running": self._running
        }

        # Only include peers from active interfaces
        with self._health_lock:
            for pk, health in self._peer_health.items():
                # Check if interface is active (running)
                iface_name = health.interface
                if iface_name in self.wg_configs:
                    wg_config = self.wg_configs[iface_name]
                    if wg_config.getStatus():  # Only include if interface is UP
                        result["peers"][pk] = health.to_dict()

        # Only include active interfaces in the config list
        for iface_name, wg_config in self.wg_configs.items():
            is_active = wg_config.getStatus()
            if is_active:  # Only show active interfaces in Health UI
                cfg = self.get_interface_config(iface_name)
                result["interfaces"][iface_name] = {
                    "enabled": cfg.enabled,
                    "ping_interval": cfg.ping_interval,
                    "set_keepalive": cfg.set_keepalive,
                    "keepalive_value": cfg.keepalive_value,
                    "interface_active": True
                }

        return result

    def get_stats(self) -> dict:
        """Return general statistics"""
        return self._stats.copy()

    def ping_peer_now(self, public_key: str) -> Optional[dict]:
        """Execute ping to specific peer immediately"""
        with self._health_lock:
            if public_key not in self._peer_health:
                return None
            health = self._peer_health[public_key]

        result = self._do_ping(health.vpn_ip)
        self._update_peer_after_ping(health, result)

        return health.to_dict()

    def force_cycle(self) -> dict:
        """Force one check cycle immediately"""
        return self._run_health_cycle()

    def _monitor_loop(self):
        """Main monitoring thread loop"""
        # Wait a bit on startup
        time.sleep(15)

        while self._running:
            try:
                self._run_health_cycle()
            except Exception as e:
                self.logger.error(f"Error in health monitor cycle: {e}")

            # Wait until next cycle (shortest interval from all interfaces)
            min_interval = 30
            for cfg in self._interface_config.values():
                if cfg.enabled and cfg.ping_interval < min_interval:
                    min_interval = cfg.ping_interval

            # Sleep in parts for faster shutdown
            for _ in range(min_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _run_health_cycle(self) -> dict:
        """Execute one health check cycle"""
        start_time = time.time()
        cycle_results = {
            "checked": 0,
            "online": 0,
            "unpingable": 0,
            "recent": 0,
            "offline": 0,
            "skipped": 0,
            "pingable": 0,
            "endpoint_changes": 0
        }

        # Collect all peers from all interfaces
        peers_to_check = []

        for iface_name, wg_config in self.wg_configs.items():
            # Skip interfaces that are not running (DOWN)
            if not wg_config.getStatus():
                continue

            cfg = self.get_interface_config(iface_name)
            # Skip interfaces where health monitoring is disabled
            if not cfg.enabled:
                continue

            # Set PersistentKeepalive if enabled
            if cfg.set_keepalive:
                self._ensure_keepalive(iface_name, wg_config, cfg.keepalive_value)

            # Collect peers
            for peer in wg_config.Peers:
                vpn_ip = self._extract_vpn_ip(peer.allowed_ip)
                if vpn_ip:
                    peers_to_check.append({
                        "interface": iface_name,
                        "public_key": peer.id,
                        "name": getattr(peer, 'name', '') or '',
                        "vpn_ip": vpn_ip,
                        "endpoint": getattr(peer, 'endpoint', ''),
                        "latest_handshake": getattr(peer, 'latest_handshake', None)
                    })

        # Check all peers
        for peer_info in peers_to_check:
            try:
                self._check_peer(peer_info, cycle_results)
            except Exception as e:
                self.logger.error(f"Error checking peer {peer_info['public_key']}: {e}")

        # Update statistics
        duration_ms = (time.time() - start_time) * 1000
        self._stats["last_cycle_time"] = datetime.now().isoformat()
        self._stats["last_cycle_duration_ms"] = round(duration_ms, 2)

        return cycle_results

    def _check_peer(self, peer_info: dict, results: dict):
        """Check one peer - FIRST handshake, THEN ping only if needed"""
        public_key = peer_info["public_key"]
        vpn_ip = peer_info["vpn_ip"]
        interface = peer_info["interface"]
        name = peer_info.get("name", "")

        # Get or create health record
        with self._health_lock:
            if public_key not in self._peer_health:
                self._peer_health[public_key] = PeerHealthInfo(
                    public_key=public_key,
                    vpn_ip=vpn_ip,
                    interface=interface,
                    name=name
                )
            health = self._peer_health[public_key]

        # Update VPN IP and name if changed
        health.vpn_ip = vpn_ip
        health.interface = interface
        health.name = name

        # Check for endpoint change
        current_endpoint = peer_info.get("endpoint", "")
        if health.last_endpoint and health.last_endpoint != current_endpoint and current_endpoint != "(none)":
            health.endpoint_changed = True
            results["endpoint_changes"] += 1
            self._stats["endpoint_updates"] += 1
            self.logger.info(f"Endpoint changed for {name or public_key[:8]}...: {health.last_endpoint} -> {current_endpoint}")
        else:
            health.endpoint_changed = False
        health.last_endpoint = current_endpoint

        # STEP 1: Parse handshake time and determine base status
        latest_handshake = peer_info.get("latest_handshake")
        handshake_age = self._parse_handshake_age(health, latest_handshake)

        results["checked"] += 1

        # STEP 2: Determine if we should ping based on handshake
        if handshake_age is None:
            # Never connected - unknown status, don't ping
            health.status = PeerStatus.UNKNOWN
            results["skipped"] += 1
            self._stats["skipped_offline"] += 1
            return

        if handshake_age > HANDSHAKE_RECENT_TIMEOUT:
            # Offline - don't waste resources pinging
            health.status = PeerStatus.OFFLINE
            health.is_pingable = False
            results["offline"] += 1
            results["skipped"] += 1
            self._stats["skipped_offline"] += 1
            return

        # STEP 3: Peer has recent handshake - ping to trigger endpoint update
        ping_result = self._do_ping(vpn_ip)
        self._update_peer_after_ping(health, ping_result)

        # STEP 4: Determine final status based on handshake + ping
        if handshake_age < HANDSHAKE_ONLINE_TIMEOUT:
            # Recent handshake (< 3 min)
            if ping_result["success"]:
                health.status = PeerStatus.ONLINE
                health.is_pingable = True
                results["online"] += 1
                results["pingable"] += 1
            else:
                # Connected but firewall blocks ICMP
                health.status = PeerStatus.UNPINGABLE
                health.is_pingable = False
                results["unpingable"] += 1
        else:
            # Handshake 3-15 min ago - "recent" status
            health.status = PeerStatus.RECENT
            results["recent"] += 1
            if ping_result["success"]:
                health.is_pingable = True
                results["pingable"] += 1

    def _parse_handshake_age(self, health: PeerHealthInfo, latest_handshake) -> Optional[timedelta]:
        """Parse handshake time and return age. Returns None if no valid handshake.
        
        Handles formats:
        - "0:00:54" (H:MM:SS)
        - "1 day, 20:38:48" (X day(s), H:MM:SS)
        - "No Handshake" / "N/A" -> None
        - Unix timestamp (int/float)
        - ISO format datetime string
        """
        if not latest_handshake:
            return None
        
        # Handle string formats
        if isinstance(latest_handshake, str):
            # Skip invalid values
            if latest_handshake in ("No Handshake", "N/A", "", "0"):
                return None
            
            try:
                # Try to parse timedelta string format from WGDashboard
                # Format: "H:MM:SS" or "X day(s), H:MM:SS"
                days = 0
                time_part = latest_handshake
                
                if "day" in latest_handshake:
                    # "1 day, 20:38:48" or "2 days, 1:23:45"
                    parts = latest_handshake.split(", ")
                    day_part = parts[0]
                    days = int(day_part.split()[0])
                    time_part = parts[1] if len(parts) > 1 else "0:0:0"
                
                # Parse time part "H:MM:SS" or "HH:MM:SS"
                time_parts = time_part.split(":")
                if len(time_parts) == 3:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    seconds = int(time_parts[2])
                    
                    age = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
                    health.last_handshake = datetime.now() - age
                    return age
                    
            except (ValueError, IndexError) as e:
                self.logger.debug(f"Could not parse timedelta string '{latest_handshake}': {e}")
            
            # Try ISO format
            try:
                health.last_handshake = datetime.fromisoformat(latest_handshake)
                return datetime.now() - health.last_handshake
            except ValueError:
                pass
            
            # Try as Unix timestamp string
            try:
                ts = float(latest_handshake)
                if ts > 0:
                    health.last_handshake = datetime.fromtimestamp(ts)
                    return datetime.now() - health.last_handshake
            except ValueError:
                pass
                
        # Handle numeric timestamps
        elif isinstance(latest_handshake, (int, float)):
            if latest_handshake > 0:
                health.last_handshake = datetime.fromtimestamp(latest_handshake)
                return datetime.now() - health.last_handshake
                
        # Handle datetime objects
        elif isinstance(latest_handshake, datetime):
            health.last_handshake = latest_handshake
            return datetime.now() - health.last_handshake

        return None

    def _do_ping(self, ip: str, count: int = 1, timeout: int = 2) -> dict:
        """Execute ICMP ping"""
        try:
            result = icmp_ping(ip, count=count, timeout=timeout, privileged=True)
            self._stats["total_pings"] += 1

            if result.is_alive:
                self._stats["successful_pings"] += 1
                return {
                    "success": True,
                    "rtt_ms": result.avg_rtt,
                    "packets_sent": result.packets_sent,
                    "packets_received": result.packets_received
                }
            else:
                self._stats["failed_pings"] += 1
                return {
                    "success": False,
                    "rtt_ms": 0,
                    "packets_sent": result.packets_sent,
                    "packets_received": 0
                }
        except Exception as e:
            self._stats["failed_pings"] += 1
            self.logger.debug(f"Ping failed for {ip}: {e}")
            return {
                "success": False,
                "rtt_ms": 0,
                "packets_sent": 1,
                "packets_received": 0,
                "error": str(e)
            }

    def _update_peer_after_ping(self, health: PeerHealthInfo, ping_result: dict):
        """Update health information after ping"""
        health.last_ping_time = datetime.now()
        health.last_ping_success = ping_result["success"]
        health.ping_rtt_ms = ping_result.get("rtt_ms", 0)

        if ping_result["success"]:
            health.ping_success_count += 1
        else:
            health.ping_fail_count += 1

    def _extract_vpn_ip(self, allowed_ips: str) -> Optional[str]:
        """Extract VPN IP from AllowedIPs"""
        if not allowed_ips:
            return None

        for ip_str in allowed_ips.replace(" ", "").split(","):
            try:
                network = ipaddress.ip_network(ip_str, strict=False)
                hosts = list(network.hosts())
                if len(hosts) == 1:
                    return str(hosts[0])
                elif network.prefixlen == 32:
                    return str(network.network_address)
            except ValueError:
                continue

        return None

    def _ensure_keepalive(self, interface: str, wg_config, keepalive: int):
        """Set PersistentKeepalive on server for all peers"""
        try:
            # Determine if AWG or WG
            wg_cmd = "awg" if hasattr(wg_config, 'Protocol') and wg_config.Protocol == 'awg' else "wg"

            for peer in wg_config.Peers:
                # Check current keepalive
                current_keepalive = getattr(peer, 'persistent_keepalive', 0)
                if current_keepalive != keepalive:
                    cmd = [
                        wg_cmd, "set", interface,
                        "peer", peer.id,
                        "persistent-keepalive", str(keepalive)
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=5)
                    self.logger.debug(f"Set keepalive={keepalive} for {peer.id[:8]}... on {interface}")
        except Exception as e:
            self.logger.error(f"Error setting keepalive on {interface}: {e}")

    def to_json(self) -> dict:
        """For serialization in JSON response"""
        return self.get_all_health()
