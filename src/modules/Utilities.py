import re, ipaddress, os, shutil
import subprocess


def RegexMatch(regex, text) -> bool:
    """
    Regex Match
    @param regex: Regex patter
    @param text: Text to match
    @return: Boolean indicate if the text match the regex pattern
    """
    pattern = re.compile(regex)
    return pattern.search(text) is not None

def GetRemoteEndpoint() -> str:
    """
    Using socket to determine default interface IP address. Thanks, @NOXICS
    @return: 
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("1.1.1.1", 80))  # Connecting to a public IP
        wgd_remote_endpoint = s.getsockname()[0]
        return str(wgd_remote_endpoint)


def StringToBoolean(value: str):
    """
    Convert string boolean to boolean
    @param value: Boolean value in string came from Configuration file
    @return: Boolean value
    """
    return (value.strip().replace(" ", "").lower() in 
            ("yes", "true", "t", "1", 1))

def ValidateIPAddressesWithRange(ips: str) -> bool:
    s = ips.replace(" ", "").split(",")
    for ip in s:
        try:
            ipaddress.ip_network(ip)
        except ValueError as e:
            return False
    return True

def ValidateIPAddresses(ips) -> bool:
    s = ips.replace(" ", "").split(",")
    for ip in s:
        try:
            ipaddress.ip_address(ip)
        except ValueError as e:
            return False
    return True

def ValidateDNSAddress(addresses) -> tuple[bool, str]:
    s = addresses.replace(" ", "").split(",")
    for address in s:
        if not ValidateIPAddresses(address) and not RegexMatch(
                r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z]{0,61}[a-z]", address):
            return False, f"{address} does not appear to be an valid DNS address"
    return True, ""

def ValidateEndpointAllowedIPs(IPs) -> tuple[bool, str] | tuple[bool, None]:
    ips = IPs.replace(" ", "").split(",")
    for ip in ips:
        try:
            ipaddress.ip_network(ip, strict=False)
        except ValueError as e:
            return False, str(e)
    return True, None

_ALLOWED_PROTOCOLS = {
    "wg": {
        "exe": ("/usr/sbin/wg", "/usr/bin/wg"),
        "quick": ("/usr/sbin/wg-quick", "/usr/bin/wg-quick"),
    },
    "awg": {
        "exe": ("/usr/sbin/awg", "/usr/bin/awg"),
        "quick": ("/usr/sbin/awg-quick", "/usr/bin/awg-quick"),
    },
}
_ALLOWED_SUDO = ("/usr/sbin/sudo", "/usr/bin/sudo")
_IFACE_RE = re.compile(r"^[A-Za-z0-9_.-]{1,15}$")
_PEER_RE = re.compile(r"^[A-Za-z0-9+/=]{32,64}$")


def _resolve_executable(protocol: str, quick: bool) -> str:
    if protocol not in _ALLOWED_PROTOCOLS:
        raise ValueError(f"Unsupported protocol: {protocol}")
    key = "quick" if quick else "exe"
    candidates = _ALLOWED_PROTOCOLS[protocol][key]
    for path in candidates:
        if os.path.exists(path):
            return path
    fallback = shutil.which(f"{protocol}-quick" if quick else protocol)
    if fallback:
        fallback = os.path.realpath(fallback)
        if fallback in candidates:
            return fallback
    raise FileNotFoundError(f"{protocol} binary not found in allowed paths")


def _resolve_sudo() -> str:
    for path in _ALLOWED_SUDO:
        if os.path.exists(path):
            return path
    fallback = shutil.which("sudo")
    if fallback:
        fallback = os.path.realpath(fallback)
        if fallback in _ALLOWED_SUDO:
            return fallback
    raise FileNotFoundError("sudo not found in allowed paths")


def _validate_interface(name: str) -> str:
    if not name or not _IFACE_RE.fullmatch(name):
        raise ValueError(f"Invalid interface name: {name}")
    return name


def _validate_peer_id(peer_id: str) -> str:
    if not peer_id or not _PEER_RE.fullmatch(peer_id):
        raise ValueError("Invalid peer public key")
    return peer_id


def _normalize_allowed_ips(allowed_ips: str) -> str:
    if allowed_ips is None:
        raise ValueError("AllowedIPs is required")
    cleaned = str(allowed_ips).replace(" ", "")
    ok, err = ValidateEndpointAllowedIPs(cleaned)
    if not ok:
        raise ValueError(err or "Invalid AllowedIPs")
    return cleaned


def _apply_sudo(cmd: list[str], require_root: bool) -> list[str]:
    if require_root and os.geteuid() != 0:
        sudo_path = _resolve_sudo()
        return [sudo_path, "--non-interactive"] + cmd
    return cmd


def WgShow(protocol: str, interface: str, field: str) -> bytes:
    if field not in ("transfer", "endpoints", "latest-handshakes"):
        raise ValueError(f"Unsupported show field: {field}")
    exe = _resolve_executable(protocol, quick=False)
    iface = _validate_interface(interface)
    cmd = _apply_sudo([exe, "show", iface, field], require_root=True)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def WgQuick(protocol: str, action: str, interface: str) -> bytes:
    if action not in ("up", "down", "save"):
        raise ValueError(f"Unsupported wg-quick action: {action}")
    exe = _resolve_executable(protocol, quick=True)
    iface = _validate_interface(interface)
    cmd = _apply_sudo([exe, action, iface], require_root=True)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def WgSetPeerAllowedIps(protocol: str, interface: str, peer_id: str,
                        allowed_ips: str, preshared_key_path: str | None = None) -> bytes:
    exe = _resolve_executable(protocol, quick=False)
    iface = _validate_interface(interface)
    peer = _validate_peer_id(peer_id)
    allowed = _normalize_allowed_ips(allowed_ips)
    cmd = [exe, "set", iface, "peer", peer, "allowed-ips", allowed]
    if preshared_key_path:
        cmd += ["preshared-key", preshared_key_path]
    cmd = _apply_sudo(cmd, require_root=True)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def WgPeerRemove(protocol: str, interface: str, peer_id: str) -> bytes:
    exe = _resolve_executable(protocol, quick=False)
    iface = _validate_interface(interface)
    peer = _validate_peer_id(peer_id)
    cmd = _apply_sudo([exe, "set", iface, "peer", peer, "remove"], require_root=True)
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)


def WgPubkey(private_key: bytes) -> bytes:
    exe = _resolve_executable("wg", quick=False)
    cmd = [exe, "pubkey"]
    return subprocess.check_output(cmd, input=private_key, stderr=subprocess.STDOUT)


def WgGenkey() -> bytes:
    exe = _resolve_executable("wg", quick=False)
    cmd = [exe, "genkey"]
    return subprocess.check_output(cmd, stderr=subprocess.STDOUT)

def GenerateWireguardPublicKey(privateKey: str) -> tuple[bool, str] | tuple[bool, None]:
    try:
        publicKey = WgPubkey(privateKey.encode())
        return True, publicKey.decode().strip('\n')
    except subprocess.CalledProcessError:
        return False, None
    
def GenerateWireguardPrivateKey() -> tuple[bool, str] | tuple[bool, None]:
    try:
        publicKey = WgGenkey()
        return True, publicKey.decode().strip('\n')
    except subprocess.CalledProcessError:
        return False, None
    
def ValidatePasswordStrength(password: str) -> tuple[bool, str] | tuple[bool, None]:
    # Rules:
    #     - Must be over 8 characters & numbers
    #     - Must contain at least 1 Uppercase & Lowercase letters
    #     - Must contain at least 1 Numbers (0-9)
    #     - Must contain at least 1 special characters from $&+,:;=?@#|'<>.-^*()%!~_-
    if len(password) < 8:
        return False, "Password must be 8 characters or more"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least 1 lowercase character"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least 1 uppercase character"
    if not re.search(r'\d', password):
        return False, "Password must contain at least 1 number"
    if not re.search(r'[$&+,:;=?@#|\'<>.\-^*()%!~_-]', password):
        return False, "Password must contain at least 1 special character from $&+,:;=?@#|'<>.-^*()%!~_-"
    
    return True, None
