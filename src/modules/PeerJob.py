"""
Peer Job
"""
from datetime import datetime
class PeerJob:
    def __init__(self, JobID: str, Configuration: str, Peer: str,
                 Field: str, Operator: str, Value: str, CreationDate: datetime, ExpireDate: datetime, Action: str):
        self.Action = Action
        self.ExpireDate = ExpireDate
        self.CreationDate = CreationDate
        self.Value = Value
        self.Operator = Operator
        self.Field = Field
        self.Configuration = Configuration
        self.Peer = Peer
        self.JobID = JobID

    def toJson(self):
        return {
            "JobID": self.JobID,
            "Configuration": self.Configuration,
            "Peer": self.Peer,
            "Field": self.Field,
            "Operator": self.Operator,
            "Value": self.Value,
            "CreationDate": self.CreationDate.strftime("%Y-%m-%d %H:%M:%S"),
            "ExpireDate": (self.ExpireDate.strftime("%Y-%m-%d %H:%M:%S") if self.ExpireDate is not None else None),
            "Action": self.Action
        }

    def __dict__(self):
        return self.toJson()