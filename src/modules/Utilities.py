import re, ipaddress
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

def GenerateWireguardPublicKey(privateKey: str) -> tuple[bool, str] | tuple[bool, None]:
    try:
        result = subprocess.run(['wg', 'pubkey'], input=privateKey.encode(),
                               capture_output=True, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            return False, None
        return True, result.stdout.decode().strip('\n')
    except subprocess.CalledProcessError:
        return False, None
    
def GenerateWireguardPrivateKey() -> tuple[bool, str] | tuple[bool, None]:
    try:
        result = subprocess.run(['wg', 'genkey'], capture_output=True,
                               stderr=subprocess.STDOUT)
        if result.returncode != 0:
            return False, None
        return True, result.stdout.decode().strip('\n')
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

def ValidateWireguardIdentifier(identifier: str) -> bool:
    """
    Validate WireGuard configuration name or peer ID to prevent command injection.
    Only allows alphanumeric characters, underscores, and hyphens.
    
    Security notes:
    - No dots (.) to prevent path traversal (e.g., ../etc/passwd)
    - No shell metacharacters
    - Length limited to prevent buffer issues
    """
    if not identifier or len(identifier) == 0:
        return False
    if len(identifier) > 64:  # WireGuard interface names typically limited
        return False
    # Allow only alphanumeric, underscore, and hyphen (NO dots to prevent path traversal)
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', identifier))

def ValidateUUIDFilename(filename: str) -> bool:
    """
    Validate UUID-based temporary filenames used for preshared keys.
    UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """
    if not filename or len(filename) == 0:
        return False
    # UUID v4 format with hyphens
    return bool(re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', filename))

def ValidateWireguardPublicKey(public_key: str) -> bool:
    """
    Validate WireGuard public key format.
    WireGuard public keys are base64 encoded and typically 44 characters long.
    """
    if not public_key or len(public_key) == 0:
        return False
    # Base64 characters only
    return bool(re.match(r'^[A-Za-z0-9+/=]+$', public_key))

def ValidateWireguardPrivateKey(private_key: str) -> bool:
    """
    Validate WireGuard private key format.
    WireGuard private keys are base64 encoded and typically 44 characters long.
    """
    if not private_key or len(private_key) == 0:
        return False
    # Base64 characters only
    return bool(re.match(r'^[A-Za-z0-9+/=]+$', private_key))

def ValidateWireguardAllowedIPs(allowed_ips: str) -> bool:
    """
    Validate WireGuard allowed IPs format.
    Should be comma-separated list of IP addresses or CIDR ranges.
    """
    if not allowed_ips or len(allowed_ips) == 0:
        return False
    # Remove spaces and split by comma
    ips = allowed_ips.replace(" ", "").split(",")
    for ip in ips:
        try:
            ipaddress.ip_network(ip, strict=False)
        except ValueError:
            return False
    return True

def ExecuteWireguardCommand(protocol: str, command: str, args: list) -> tuple[bool, str]:
    """
    Execute WireGuard commands safely without shell=True.
    
    Args:
        protocol: WireGuard protocol ('wg' or 'awg')
        command: WireGuard command (e.g., 'set', 'show', 'quick')
        args: List of command arguments
    
    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        # Validate protocol
        if protocol not in ['wg', 'awg']:
            return False, f"Invalid protocol: {protocol}"
        
        # Build command list
        cmd = []
        
        # Handle different command types
        if command == 'set':
            # Format: wg set <interface> peer <peer_id> allowed-ips <ips> [preshared-key <file>]
            if len(args) < 4:
                return False, "Insufficient arguments for 'set' command"
            
            interface = args[0]
            if not ValidateWireguardIdentifier(interface):
                return False, f"Invalid interface name: {interface}"
            
            cmd = [f"{protocol}", "set", interface]
            
            # Parse peer-specific arguments
            i = 1
            while i < len(args):
                if args[i] == 'peer':
                    if i + 1 >= len(args):
                        return False, "Missing peer ID"
                    peer_id = args[i + 1]
                    if not ValidateWireguardIdentifier(peer_id):
                        return False, f"Invalid peer ID: {peer_id}"
                    cmd.extend(['peer', peer_id])
                    i += 2
                elif args[i] == 'allowed-ips':
                    if i + 1 >= len(args):
                        return False, "Missing allowed IPs"
                    allowed_ips = args[i + 1]
                    if not ValidateWireguardAllowedIPs(allowed_ips):
                        return False, f"Invalid allowed IPs: {allowed_ips}"
                    cmd.extend(['allowed-ips', allowed_ips])
                    i += 2
                elif args[i] == 'preshared-key':
                    if i + 1 >= len(args):
                        return False, "Missing preshared key file"
                    psk_file = args[i + 1]
                    # Validate file path is safe
                    # Allow /dev/null and UUID-based temp files
                    if psk_file == '/dev/null':
                        cmd.extend(['preshared-key', psk_file])
                    elif ValidateWireguardIdentifier(psk_file) or ValidateUUIDFilename(psk_file):
                        cmd.extend(['preshared-key', psk_file])
                    else:
                        return False, f"Invalid preshared key file: {psk_file}"
                    i += 2
                elif args[i] == 'remove':
                    cmd.append('remove')
                    i += 1
                else:
                    i += 1
        
        elif command == 'show':
            # Format: wg show <interface> <attribute>
            if len(args) < 1:
                return False, "Insufficient arguments for 'show' command"
            
            interface = args[0]
            if not ValidateWireguardIdentifier(interface):
                return False, f"Invalid interface name: {interface}"
            
            cmd = [f"{protocol}", "show", interface]
            if len(args) > 1:
                cmd.extend(args[1:])
        
        elif command == 'quick':
            # Format: wg-quick save <interface> or wg-quick up <interface>
            if len(args) < 2:
                return False, "Insufficient arguments for 'quick' command"
            
            action = args[0]
            if action not in ['save', 'up', 'down']:
                return False, f"Invalid quick action: {action}"
            
            interface = args[1]
            if not ValidateWireguardIdentifier(interface):
                return False, f"Invalid interface name: {interface}"
            
            cmd = [f"{protocol}-quick", action, interface]
        
        else:
            return False, f"Unknown command: {command}"
        
        # Execute command without shell=True
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True, result.decode('utf-8').strip()
    
    except subprocess.CalledProcessError as e:
        return False, e.output.decode('utf-8').strip()
    except Exception as e:
        return False, str(e)