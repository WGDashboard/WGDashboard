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
        publicKey = subprocess.check_output(f"wg pubkey", input=privateKey.encode(), shell=True,
                                            stderr=subprocess.STDOUT)
        return True, publicKey.decode().strip('\n')
    except subprocess.CalledProcessError:
        return False, None
    
def GenerateWireguardPrivateKey() -> tuple[bool, str] | tuple[bool, None]:
    try:
        publicKey = subprocess.check_output(f"wg genkey", shell=True,
                                            stderr=subprocess.STDOUT)
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