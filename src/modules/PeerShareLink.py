from datetime import datetime
"""
Peer Share Link
"""
class PeerShareLink:
    def __init__(self, ShareID:str, Configuration: str, Peer: str, ExpireDate: datetime, SharedDate: datetime):
        self.ShareID = ShareID
        self.Peer = Peer
        self.Configuration = Configuration
        self.SharedDate = SharedDate
        self.ExpireDate = ExpireDate

    def toJson(self):
        return {
            "ShareID": self.ShareID,
            "Peer": self.Peer,
            "Configuration": self.Configuration,
            "ExpireDate": self.ExpireDate.strftime("%Y-%m-%d %H:%M:%S"),
            "SharedDate": self.SharedDate.strftime("%Y-%m-%d %H:%M:%S"),
        }