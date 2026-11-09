"""
Dashboard Administrators (multi-admin support)

Every administrator has full access to the dashboard, exactly like the single
account previously stored in wg-dashboard.ini.

The account of wg-dashboard.ini is imported as the first administrator when the
table is empty (first start, or database restored/recreated), so the ini file
always stays a usable safety fallback.
"""
import datetime
import re
import uuid

import bcrypt
import pyotp
import sqlalchemy as db
from flask import current_app

from .DatabaseConnection import ConnectionString
from .Utilities import ValidatePasswordStrength


class DashboardAdmins:
    UsernamePattern = re.compile(r"^[A-Za-z0-9._@-]{3,64}$")

    def __init__(self, DashboardConfig):
        self.DashboardConfig = DashboardConfig
        self.connectionString = ConnectionString("wgdashboard")
        self.engine = db.create_engine(self.connectionString)
        self.metadata = db.MetaData()
        dateType = (db.DATETIME if 'sqlite:///' in self.connectionString else db.TIMESTAMP)

        self.adminsTable = db.Table(
            'DashboardAdmins', self.metadata,
            db.Column('AdminID', db.String(36), nullable=False, primary_key=True),
            db.Column('Username', db.String(255), nullable=False, unique=True, index=True),
            db.Column('Email', db.String(255)),
            db.Column('Password', db.String(500)),
            db.Column('TotpKey', db.String(64)),
            db.Column('TotpVerified', db.Integer),
            db.Column('Enabled', db.Integer),
            db.Column('CreatedDate', dateType, server_default=db.func.now()),
            db.Column('UpdatedDate', dateType),
            db.Column('LastLoginDate', dateType),
            db.Column('CreatedBy', db.String(255)),
            extend_existing=True,
        )
        self.metadata.create_all(self.engine)
        self.BootstrapFromConfig()

    # ------------------------------------------------------------------ helpers
    def Public(self, admin: dict | None) -> dict | None:
        """Administrator data safe to send to the browser (no password hash, no TOTP key)."""
        if admin is None:
            return None
        return {
            "AdminID": admin.get("AdminID"),
            "Username": admin.get("Username"),
            "Email": admin.get("Email") or "",
            "Enabled": int(admin.get("Enabled") or 0),
            "TotpEnabled": bool(admin.get("TotpKey")) and bool(int(admin.get("TotpVerified") or 0)),
            "CreatedDate": (admin.get("CreatedDate").strftime("%Y-%m-%d %H:%M:%S")
                            if isinstance(admin.get("CreatedDate"), datetime.datetime) else admin.get("CreatedDate")),
            "LastLoginDate": (admin.get("LastLoginDate").strftime("%Y-%m-%d %H:%M:%S")
                              if isinstance(admin.get("LastLoginDate"), datetime.datetime) else admin.get("LastLoginDate")),
            "CreatedBy": admin.get("CreatedBy") or "",
        }

    def Count(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(
                db.select(db.func.count()).select_from(self.adminsTable)
            ).scalar() or 0

    def CountEnabled(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(
                db.select(db.func.count()).select_from(self.adminsTable).where(
                    self.adminsTable.c.Enabled == 1
                )
            ).scalar() or 0

    def GetAllAdmins(self) -> list[dict]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                db.select(self.adminsTable).order_by(self.adminsTable.c.Username)
            ).mappings().fetchall()
        return [self.Public(dict(r)) for r in rows]

    def GetAdmin(self, AdminID: str) -> dict | None:
        if not AdminID:
            return None
        with self.engine.connect() as conn:
            row = conn.execute(
                db.select(self.adminsTable).where(self.adminsTable.c.AdminID == AdminID)
            ).mappings().fetchone()
        return dict(row) if row else None

    def GetAdminByUsername(self, username: str) -> dict | None:
        if not username:
            return None
        with self.engine.connect() as conn:
            row = conn.execute(
                db.select(self.adminsTable).where(self.adminsTable.c.Username == username.strip())
            ).mappings().fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ bootstrap
    def BootstrapFromConfig(self) -> bool:
        """Import the wg-dashboard.ini account as first administrator if the table is empty."""
        if self.Count() > 0:
            return False
        username = self.DashboardConfig.GetConfig("Account", "username")[1]
        password = self.DashboardConfig.GetConfig("Account", "password")[1]
        totpKey = self.DashboardConfig.GetConfig("Account", "totp_key")[1]
        enableTotp = self.DashboardConfig.GetConfig("Account", "enable_totp")[1]
        if not username or not password:
            return False
        now = datetime.datetime.now()
        try:
            with self.engine.begin() as conn:
                conn.execute(self.adminsTable.insert().values(
                    AdminID=str(uuid.uuid4()),
                    Username=username.strip(),
                    Email="",
                    Password=password,
                    TotpKey=totpKey,
                    TotpVerified=1 if enableTotp else 0,
                    Enabled=1,
                    CreatedDate=now,
                    UpdatedDate=now,
                    CreatedBy="wg-dashboard.ini",
                ))
        except Exception as e:
            current_app.logger.error(f"[DashboardAdmins] Cannot import administrator from wg-dashboard.ini: {e}")
            return False
        current_app.logger.info(f"[DashboardAdmins] Administrator '{username}' imported from wg-dashboard.ini")
        return True

    # ------------------------------------------------------------------ sign in
    def SignIn(self, username: str, password: str, totp: str | None = None) -> tuple[bool, str | None, dict | None]:
        admin = self.GetAdminByUsername(username)
        if admin is None:
            return False, "Sorry, your username or password is incorrect.", None
        if int(admin.get("Enabled") or 0) != 1:
            return False, "This administrator account is disabled.", None
        try:
            valid = bcrypt.checkpw((password or "").encode("utf-8"),
                                   (admin.get("Password") or "").encode("utf-8"))
        except Exception:
            valid = False
        if not valid:
            return False, "Sorry, your username or password is incorrect.", None
        if admin.get("TotpKey") and int(admin.get("TotpVerified") or 0) == 1:
            code = str(totp or "").strip()
            if len(code) == 0 or not pyotp.TOTP(admin["TotpKey"]).verify(code, valid_window=1):
                return False, "Sorry, your username, password or OTP is incorrect.", None
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.update().values({"LastLoginDate": datetime.datetime.now()}).where(
                        self.adminsTable.c.AdminID == admin["AdminID"]
                    )
                )
            refreshed = self.GetAdmin(admin["AdminID"])
            if refreshed is not None:
                admin = refreshed
        except Exception as e:
            current_app.logger.error(f"[DashboardAdmins] Cannot update last login date: {e}")
        return True, None, self.Public(admin)

    # ------------------------------------------------------------------ CRUD
    def AddAdmin(self, username: str, Email: str, Password: str, ConfirmPassword: str,
                 CreatedBy: str = "") -> tuple[bool, str | None]:
        username = (username or "").strip()
        if not self.UsernamePattern.match(username):
            return False, "Username must be 3 to 64 characters, using letters, digits, dot, dash, underscore or @"
        if self.GetAdminByUsername(username) is not None:
            return False, "This username already exists"
        if Password != ConfirmPassword:
            return False, "Passwords do not match"
        strength, message = ValidatePasswordStrength(Password or "")
        if not strength:
            return False, message
        now = datetime.datetime.now()
        try:
            with self.engine.begin() as conn:
                conn.execute(self.adminsTable.insert().values(
                    AdminID=str(uuid.uuid4()),
                    Username=username,
                    Email=(Email or "").strip(),
                    Password=bcrypt.hashpw(Password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                    TotpKey=None,
                    TotpVerified=0,
                    Enabled=1,
                    CreatedDate=now,
                    UpdatedDate=now,
                    CreatedBy=CreatedBy,
                ))
        except Exception as e:
            current_app.logger.error(f"[DashboardAdmins] Cannot add administrator: {e}")
            return False, "Internal server error"
        return True, None

    def UpdateAdmin(self, AdminID: str, username: str, Email: str) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        username = (username or "").strip()
        if not self.UsernamePattern.match(username):
            return False, "Username must be 3 to 64 characters, using letters, digits, dot, dash, underscore or @"
        existing = self.GetAdminByUsername(username)
        if existing is not None and existing["AdminID"] != AdminID:
            return False, "This username already exists"
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.update().values({
                "Username": username,
                "Email": (Email or "").strip(),
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == AdminID))
        if admin.get("Username") == self.DashboardConfig.GetConfig("Account", "username")[1]:
            self.DashboardConfig.SetConfig("Account", "username", username)
        return True, None


    def SetPassword(self, AdminID: str, NewPassword: str, ConfirmPassword: str,
                    CurrentPassword: str | None = None) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        if CurrentPassword is not None:
            try:
                valid = bcrypt.checkpw(CurrentPassword.encode("utf-8"),
                                       (admin.get("Password") or "").encode("utf-8"))
            except Exception:
                valid = False
            if not valid:
                return False, "Current password does not match"
        if NewPassword != ConfirmPassword:
            return False, "Passwords do not match"
        strength, message = ValidatePasswordStrength(NewPassword or "")
        if not strength:
            return False, message
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.update().values({
                "Password": bcrypt.hashpw(NewPassword.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == AdminID))
        # Keep the wg-dashboard.ini safety account in sync when the same account is updated
        if admin.get("Username") == self.DashboardConfig.GetConfig("Account", "username")[1]:
            self.DashboardConfig.SetConfig("Account", "password", NewPassword, init=True)
        return True, None

    def SetEnabled(self, AdminID: str, Enabled: bool, CurrentAdminID: str | None = None) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        if not Enabled:
            if CurrentAdminID and AdminID == CurrentAdminID:
                return False, "You cannot disable your own account"
            if int(admin.get("Enabled") or 0) == 1 and self.CountEnabled() <= 1:
                return False, "At least one enabled administrator is required"
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.update().values({
                "Enabled": 1 if Enabled else 0,
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == AdminID))
        return True, None

    def DeleteAdmin(self, AdminID: str, CurrentAdminID: str | None = None) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        if CurrentAdminID and AdminID == CurrentAdminID:
            return False, "You cannot delete your own account"
        if self.Count() <= 1:
            return False, "At least one administrator is required"
        if int(admin.get("Enabled") or 0) == 1 and self.CountEnabled() <= 1:
            return False, "At least one enabled administrator is required"
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.delete().where(self.adminsTable.c.AdminID == AdminID))
        return True, None

    def SyncPasswordFromConfig(self, NewPlainPassword: str) -> bool:
        """Keep the wg-dashboard.ini account and its administrator row in sync.

        The password of the ini account is changed from the old account settings page
        or from the welcome wizard; the administrator table is the source of truth for
        sign in, so both must be updated.
        """
        username = self.DashboardConfig.GetConfig("Account", "username")[1]
        admin = self.GetAdminByUsername(username)
        if admin is None or not NewPlainPassword:
            return False
        try:
            with self.engine.begin() as conn:
                conn.execute(self.adminsTable.update().values({
                    "Password": bcrypt.hashpw(NewPlainPassword.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                    "UpdatedDate": datetime.datetime.now(),
                }).where(self.adminsTable.c.AdminID == admin["AdminID"]))
        except Exception as e:
            current_app.logger.error(f"[DashboardAdmins] Cannot synchronize the password: {e}")
            return False
        return True

    def RenameFromConfig(self) -> bool:
        """Rename the administrator row when the ini account username is changed from the wizard."""
        username = self.DashboardConfig.GetConfig("Account", "username")[1]
        if not username:
            return False
        with self.engine.connect() as conn:
            row = conn.execute(
                db.select(self.adminsTable).where(self.adminsTable.c.CreatedBy == "wg-dashboard.ini")
            ).mappings().fetchone()
        if row is None:
            return False
        existing = self.GetAdminByUsername(username)
        if existing is not None and existing["AdminID"] != row["AdminID"]:
            return False
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.update().values({
                "Username": username.strip(),
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == row["AdminID"]))
        return True

