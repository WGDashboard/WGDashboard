from pydantic import BaseModel

class OverridePeerSettingsClass(BaseModel):
    DNS: str = ''
    EndpointAllowedIPs: str = ''
    MTU: str | int = ''
    PersistentKeepalive: int | str = ''
    PeerRemoteEndpoint: str = ''
    ListenPort: int | str = ''
    
class PeerGroupsClass(BaseModel):
    GroupName: str = ''
    Description: str = ''
    BackgroundColor: str = ''
    Icon: str = ''
    Peers: list[str] = []

class WireguardConfigurationInfo(BaseModel):
    Description: str = ''
    OverridePeerSettings: OverridePeerSettingsClass = OverridePeerSettingsClass(**{})
    PeerGroups: dict[str, PeerGroupsClass] = {}