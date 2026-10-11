import bcrypt, pyotp
import sqlalchemy as db
from .DashboardConfig import DashboardConfig
from .DatabaseConnection import ConnectionString


class DashboardAccounts:
    def __init__(self, DashboardConfig: DashboardConfig):
        self.DashboardConfig = DashboardConfig
        self.engine = db.create_engine(ConnectionString('wgdashboard'))
        self.dbMetadata = db.MetaData()
        self.accountsTable = db.Table(
            'DashboardAccounts', self.dbMetadata,
            db.Column('Username', db.String(255), nullable=False, primary_key=True),
            db.Column('Password', db.String(255), nullable=False),
            db.Column('EnableTotp', db.Boolean, nullable=False, default=False),
            db.Column('TotpVerified', db.Boolean, nullable=False, default=False),
            db.Column('TotpKey', db.String(255), nullable=False),
            db.Column('CreatedAt',
                      (db.DATETIME if DashboardConfig.GetConfig('Database', 'type')[1] == 'sqlite' else db.TIMESTAMP),
                      server_default=db.func.now())
        )
        self.dbMetadata.create_all(self.engine)

    @staticmethod
    def __hashPassword(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def __checkPassword(password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def PrimaryUsername(self) -> str:
        return self.DashboardConfig.GetConfig("Account", "username")[1]

    def IsPrimary(self, username: str | None) -> bool:
        return username is None or username == self.PrimaryUsername()

    def __getDBAccount(self, username: str):
        with self.engine.connect() as conn:
            return conn.execute(
                self.accountsTable.select().where(self.accountsTable.c.Username == username)
            ).mappings().fetchone()

    def __getAccount(self, username: str | None) -> dict | None:
        if self.IsPrimary(username):
            return {
                "username": self.PrimaryUsername(),
                "password": self.DashboardConfig.GetConfig("Account", "password")[1],
                "enable_totp": self.DashboardConfig.GetConfig("Account", "enable_totp")[1],
                "totp_verified": self.DashboardConfig.GetConfig("Account", "totp_verified")[1],
                "totp_key": self.DashboardConfig.GetConfig("Account", "totp_key")[1],
                "primary": True
            }
        a = self.__getDBAccount(username)
        if a is None:
            return None
        return {
            "username": a['Username'],
            "password": a['Password'],
            "enable_totp": bool(a['EnableTotp']),
            "totp_verified": bool(a['TotpVerified']),
            "totp_key": a['TotpKey'],
            "primary": False
        }

    def __updateDBAccount(self, username: str, values: dict):
        with self.engine.begin() as conn:
            conn.execute(
                self.accountsTable.update().values(values).where(self.accountsTable.c.Username == username)
            )

    def Exists(self, username: str) -> bool:
        return self.__getAccount(username) is not None

    def GetAccount(self, username: str | None) -> dict | None:
        a = self.__getAccount(username)
        if a is None:
            return None
        return {
            "username": a['username'],
            "enable_totp": a['enable_totp'],
            "totp_verified": a['totp_verified'],
            "primary": a['primary']
        }

    def GetAccounts(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                self.accountsTable.select().order_by(self.accountsTable.c.CreatedAt)
            ).mappings().fetchall()
        return [self.GetAccount(None)] + [self.GetAccount(r['Username']) for r in rows]

    def AnyTotpEnabled(self) -> bool:
        p = self.__getAccount(None)
        if p['enable_totp'] and p['totp_verified']:
            return True
        with self.engine.connect() as conn:
            return conn.execute(
                self.accountsTable.select().where(
                    db.and_(self.accountsTable.c.EnableTotp.is_(True), self.accountsTable.c.TotpVerified.is_(True))
                )
            ).first() is not None

    def CheckPassword(self, username: str, password: str) -> tuple[bool, bool]:
        a = self.__getAccount(username) if username else None
        if a is None or a['username'] != username:
            return False, False
        if not self.__checkPassword(password or "", a['password']):
            return False, False
        return True, bool(a['enable_totp'] and a['totp_verified'])

    def CheckTotp(self, username: str, totp: str) -> bool:
        a = self.__getAccount(username) if username else None
        if a is None or a['username'] != username:
            return False
        return pyotp.TOTP(a['totp_key']).verify(totp or "", valid_window=1)

    def AddAccount(self, username: str, password: str, repeatPassword: str) -> tuple[bool, str]:
        username = (username or "").strip()
        if len(username) == 0:
            return False, "Username cannot be blank."
        if self.Exists(username):
            return False, "Username already exists."
        if password is None or len(password) < 8:
            return False, "Password must be at least 8 characters"
        if password != repeatPassword:
            return False, "New passwords does not match"
        with self.engine.begin() as conn:
            conn.execute(self.accountsTable.insert().values({
                "Username": username,
                "Password": self.__hashPassword(password),
                "EnableTotp": False,
                "TotpVerified": False,
                "TotpKey": pyotp.random_base32()
            }))
        return True, ""

    def DeleteAccount(self, username: str, currentUsername: str | None) -> tuple[bool, str]:
        if self.IsPrimary(username):
            return False, "The primary account cannot be deleted."
        if username == currentUsername:
            return False, "You cannot delete the account you are signed in with."
        if not self.Exists(username):
            return False, "Account does not exist."
        with self.engine.begin() as conn:
            conn.execute(self.accountsTable.delete().where(self.accountsTable.c.Username == username))
        return True, ""

    def UpdateAccountItem(self, username: str | None, key: str, value) -> tuple[bool, str, str | None]:
        if self.IsPrimary(username):
            if key == "username" and value != self.PrimaryUsername() and self.Exists(value):
                return False, "Username already exists.", None
            status, msg = self.DashboardConfig.SetConfig("Account", key, value)
            return status, msg, (self.PrimaryUsername() if key == "username" else None)

        a = self.__getAccount(username)
        if a is None:
            return False, "Account does not exist.", None
        if key == "username":
            value = (value or "").strip()
            if len(value) == 0:
                return False, "Username cannot be blank.", None
            if value != username and self.Exists(value):
                return False, "Username already exists.", None
            self.__updateDBAccount(username, {"Username": value})
            return True, "", value
        if key == "password":
            if not self.__checkPassword(value.get("currentPassword", ""), a['password']):
                return False, "Current password does not match.", None
            if value.get("newPassword") != value.get("repeatNewPassword"):
                return False, "New passwords does not match", None
            if len(value.get("newPassword") or "") < 8:
                return False, "Password must be at least 8 characters", None
            self.__updateDBAccount(username, {"Password": self.__hashPassword(value["newPassword"])})
            return True, "", None
        if key in ("enable_totp", "totp_verified"):
            v = value if type(value) is bool else str(value).lower() in ["1", "yes", "true", "on"]
            self.__updateDBAccount(username, {"EnableTotp" if key == "enable_totp" else "TotpVerified": v})
            return True, "", None
        return False, f"{key} does not exist under Account", None

    def GetTotpProvisioningUri(self, username: str | None) -> str | None:
        a = self.__getAccount(username)
        if a is None or a['totp_verified']:
            return None
        newKey = pyotp.random_base32()
        if a['primary']:
            self.DashboardConfig.SetConfig("Account", "totp_key", newKey, True)
        else:
            self.__updateDBAccount(a['username'], {"TotpKey": newKey})
        return pyotp.totp.TOTP(newKey).provisioning_uri(name=a['username'], issuer_name="WGDashboard")

    def VerifyTotp(self, username: str | None, totp: str) -> bool:
        a = self.__getAccount(username)
        if a is None or pyotp.TOTP(a['totp_key']).now() != totp:
            return False
        if a['primary']:
            self.DashboardConfig.SetConfig("Account", "totp_verified", "true")
            self.DashboardConfig.SetConfig("Account", "enable_totp", "true")
        else:
            self.__updateDBAccount(a['username'], {"TotpVerified": True, "EnableTotp": True})
        return True
