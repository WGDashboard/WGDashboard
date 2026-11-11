"""
Dashboard Administrators (multi-admin support)

Every administrator has full access to the dashboard, exactly like the single
account previously stored in wg-dashboard.ini.

The account of wg-dashboard.ini is imported as the first administrator when the
table is empty (first start, or database restored/recreated), so the ini file
always stays a usable safety fallback.
"""
import datetime
import hashlib
import re
import secrets
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
        self.recoveryCodesTable = db.Table(
            'DashboardAdminsRecoveryCodes', self.metadata,
            db.Column('CodeID', db.String(36), nullable=False, primary_key=True),
            db.Column('AdminID', db.String(36), nullable=False, index=True),
            db.Column('CodeHash', db.String(255), nullable=False),
            db.Column('UsedDate', dateType),
            db.Column('CreatedDate', dateType, server_default=db.func.now()),
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
            "RecoveryCodesRemaining": self.CountRecoveryCodes(admin.get("AdminID")),
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
        genericFailure = "Sorry, your username or password is incorrect."
        if admin is None:
            return False, genericFailure, None
        try:
            valid = bcrypt.checkpw((password or "").encode("utf-8"),
                                   (admin.get("Password") or "").encode("utf-8"))
        except Exception:
            valid = False
        if not valid:
            return False, genericFailure, None
        # Disclosing that the account is disabled is only done once the password has been
        # checked: otherwise an unauthenticated caller could enumerate disabled accounts.
        if int(admin.get("Enabled") or 0) != 1:
            return False, "This administrator account is disabled.", None
        usedRecoveryCode = False
        if admin.get("TotpKey") and int(admin.get("TotpVerified") or 0) == 1:
            code = str(totp or "").strip()
            totpValid = len(code) > 0 and pyotp.TOTP(admin["TotpKey"]).verify(code, valid_window=1)
            if not totpValid and len(code) > 0:
                # A recovery code can be used instead of the TOTP code (single use)
                usedRecoveryCode = self.UseRecoveryCode(admin["AdminID"], code)
            if not totpValid and not usedRecoveryCode:
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
        payload = self.Public(admin)
        payload["UsedRecoveryCode"] = usedRecoveryCode
        payload["MfaSetupRequired"] = not (admin.get("TotpKey") and int(admin.get("TotpVerified") or 0) == 1)
        return True, None, payload

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

    def __AdminCount(self):
        """SQL expression: total number of administrator rows.

        The count is wrapped in an aliased *derived table* on purpose: MySQL refuses a
        subquery that reads the table targeted by the enclosing UPDATE/DELETE
        ("You can't specify target table ... for update in FROM clause", error 1093),
        while a materialised derived table is accepted. PostgreSQL and SQLite accept both,
        so this form is the portable one.
        """
        allAdmins = (db.select(db.literal(1))
                     .select_from(self.adminsTable)
                     .subquery("all_administrators"))
        return db.select(db.func.count()).select_from(allAdmins).scalar_subquery()

    def __OtherEnabledAdmins(self, AdminID: str):
        """SQL condition: at least one *other* administrator is enabled.

        The rule "one enabled administrator must remain" is evaluated inside the UPDATE/DELETE
        statement itself, so two concurrent requests cannot both pass a separate count check and
        leave the installation without a usable account. Same derived-table form as
        __AdminCount() for MySQL compatibility.
        """
        otherEnabled = (db.select(db.literal(1))
                        .select_from(self.adminsTable)
                        .where(db.and_(self.adminsTable.c.Enabled == 1,
                                       self.adminsTable.c.AdminID != AdminID))
                        .subquery("other_enabled_administrators"))
        return db.select(db.func.count()).select_from(otherEnabled).scalar_subquery() >= 1

    def SetEnabled(self, AdminID: str, Enabled: bool, CurrentAdminID: str | None = None) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        if not Enabled and CurrentAdminID and AdminID == CurrentAdminID:
            return False, "You cannot disable your own account"
        with self.engine.begin() as conn:
            query = self.adminsTable.update().values({
                "Enabled": 1 if Enabled else 0,
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == AdminID)
            if not Enabled:
                query = query.where(db.or_(self.adminsTable.c.Enabled != 1,
                                           self.__OtherEnabledAdmins(AdminID)))
            result = conn.execute(query)
            if result.rowcount == 1:
                return True, None
        if not Enabled and int(admin.get("Enabled") or 0) == 1:
            return False, "At least one enabled administrator is required"
        return False, "Administrator does not exist"

    def DeleteAdmin(self, AdminID: str, CurrentAdminID: str | None = None) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        if CurrentAdminID and AdminID == CurrentAdminID:
            return False, "You cannot delete your own account"
        with self.engine.begin() as conn:
            result = conn.execute(
                self.adminsTable.delete().where(db.and_(
                    self.adminsTable.c.AdminID == AdminID,
                    self.__AdminCount() > 1,
                    db.or_(self.adminsTable.c.Enabled != 1,
                           self.__OtherEnabledAdmins(AdminID)),
                ))
            )
            if result.rowcount == 1:
                return True, None
        if int(admin.get("Enabled") or 0) == 1:
            return False, "At least one enabled administrator is required"
        return False, "At least one administrator is required"

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


    def SyncTotpFromConfig(self) -> bool:
        """Copy the TOTP state of the wg-dashboard.ini account to its administrator row.

        Used by the legacy enrolment wizard (sessions without admin_id): the wizard writes
        enable_totp / totp_key in the ini file, the multi-administrator gate reads the table.
        """
        username = self.DashboardConfig.GetConfig("Account", "username")[1]
        admin = self.GetAdminByUsername(username)
        if admin is None:
            return False
        enabled = self.DashboardConfig.GetConfig("Account", "enable_totp")[1] and \
            self.DashboardConfig.GetConfig("Account", "totp_verified")[1]
        if not enabled:
            return False
        totpKey = self.DashboardConfig.GetConfig("Account", "totp_key")[1]
        if not totpKey:
            return False
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.update().values({
                "TotpKey": totpKey,
                "TotpVerified": 1,
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == admin["AdminID"]))
        current_app.logger.info(f"[DashboardAdmins] MFA state imported from wg-dashboard.ini for '{username}'")
        return True

    # ------------------------------------------------------------------ MFA (TOTP)
    def CheckPassword(self, AdminID: str, PlainPassword: str) -> bool:
        admin = self.GetAdmin(AdminID)
        if admin is None or not PlainPassword:
            return False
        try:
            return bcrypt.checkpw(PlainPassword.encode("utf-8"),
                                  (admin.get("Password") or "").encode("utf-8"))
        except Exception:
            return False

    def __SyncIniMfa(self, admin: dict | None, enabled: bool, totpKey: str = "") -> None:
        """Keep the wg-dashboard.ini fallback in sync with a confirmed MFA change.

        The ini account is re-imported when the database is recreated: without this, the
        fallback would restore an obsolete secret (or an MFA that was disabled since).
        """
        if admin is None:
            return
        if admin.get("Username") != self.DashboardConfig.GetConfig("Account", "username")[1]:
            return
        try:
            self.DashboardConfig.SetConfig("Account", "enable_totp", "true" if enabled else "false")
            self.DashboardConfig.SetConfig("Account", "totp_verified", "true" if enabled else "false")
            # totp_key is a hidden attribute: writing it requires init=True
            self.DashboardConfig.SetConfig("Account", "totp_key", totpKey if enabled else "", True)
        except Exception as e:
            current_app.logger.error(f"[DashboardAdmins] Cannot synchronize the ini MFA state: {e}")

    def StartTotp(self, AdminID: str) -> tuple[bool, str | None, dict | None]:
        """Generate a new TOTP secret for an administrator and return the provisioning link.

        The secret stays "pending" (TotpVerified = 0) until VerifyTotp() succeeds, so a
        half-configured MFA can never lock the account out.
        """
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist", None
        if admin.get("TotpKey") and int(admin.get("TotpVerified") or 0) == 1:
            return False, "MFA is already enabled for this administrator", None
        secret = pyotp.random_base32()
        with self.engine.begin() as conn:
            # Conditional on the account still being unverified: two enrolment tabs must not
            # overwrite each other's pending secret (nor replace a verified one).
            result = conn.execute(self.adminsTable.update().values({
                "TotpKey": secret,
                "TotpVerified": 0,
                "UpdatedDate": datetime.datetime.now(),
            }).where(db.and_(
                self.adminsTable.c.AdminID == AdminID,
                db.or_(self.adminsTable.c.TotpVerified.is_(None),
                       self.adminsTable.c.TotpVerified != 1),
            )))
            if result.rowcount != 1:
                return False, "MFA is already enabled for this administrator", None
        link = pyotp.TOTP(secret).provisioning_uri(
            name=admin.get("Username"), issuer_name="WGDashboard")
        return True, None, {"Secret": secret, "Link": link}

    def VerifyTotp(self, AdminID: str, Code: str) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        if not admin.get("TotpKey"):
            return False, "No MFA setup in progress, please start again"
        if int(admin.get("TotpVerified") or 0) == 1:
            return False, "MFA is already enabled for this administrator"
        pendingSecret = admin["TotpKey"]
        if not pyotp.TOTP(pendingSecret).verify(str(Code or "").strip(), valid_window=1):
            return False, "This code is not valid, please try again"
        with self.engine.begin() as conn:
            # Only the secret that was just verified may be marked as enabled: another tab may
            # have replaced it in the meantime, and the submitted code would not match it.
            result = conn.execute(self.adminsTable.update().values({
                "TotpVerified": 1,
                "UpdatedDate": datetime.datetime.now(),
            }).where(db.and_(
                self.adminsTable.c.AdminID == AdminID,
                self.adminsTable.c.TotpKey == pendingSecret,
                db.or_(self.adminsTable.c.TotpVerified.is_(None),
                       self.adminsTable.c.TotpVerified != 1),
            )))
            if result.rowcount != 1:
                return False, "The MFA setup changed while this code was verified, please try again"
        self.__SyncIniMfa(admin, True, pendingSecret)
        return True, None

    def DisableTotp(self, AdminID: str) -> tuple[bool, str | None]:
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist"
        with self.engine.begin() as conn:
            conn.execute(self.adminsTable.update().values({
                "TotpKey": None,
                "TotpVerified": 0,
                "UpdatedDate": datetime.datetime.now(),
            }).where(self.adminsTable.c.AdminID == AdminID))
        self.RevokeRecoveryCodes(AdminID)
        self.__SyncIniMfa(admin, False)
        return True, None

    # ------------------------------------------------------------------ recovery codes
    RecoveryAlphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    RecoveryCodeCount = 10

    def __NormalizeRecoveryCode(self, code: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", str(code or "")).upper()

    def __HashRecoveryCode(self, code: str) -> str:
        return hashlib.sha256(self.__NormalizeRecoveryCode(code).encode("utf-8")).hexdigest()

    def CountRecoveryCodes(self, AdminID: str) -> int:
        if not AdminID:
            return 0
        with self.engine.connect() as conn:
            return conn.execute(
                db.select(db.func.count()).select_from(self.recoveryCodesTable).where(
                    db.and_(
                        self.recoveryCodesTable.c.AdminID == AdminID,
                        self.recoveryCodesTable.c.UsedDate.is_(None),
                    )
                )
            ).scalar() or 0

    def HasAnyRecoveryCodes(self, AdminID: str) -> bool:
        """True as soon as recovery codes have been generated once (used or not).

        Used to decide whether the current password is required to generate again.
        """
        if not AdminID:
            return False
        with self.engine.connect() as conn:
            return conn.execute(
                db.select(db.func.count()).select_from(self.recoveryCodesTable).where(
                    self.recoveryCodesTable.c.AdminID == AdminID
                )
            ).scalar() > 0

    def GenerateRecoveryCodes(self, AdminID: str) -> tuple[bool, str | None, list[str]]:
        """Replace all recovery codes of an administrator with 10 new single use codes.

        Only the SHA-256 hash of each code is stored, so the plain codes are shown once.
        """
        admin = self.GetAdmin(AdminID)
        if admin is None:
            return False, "Administrator does not exist", []
        if not (admin.get("TotpKey") and int(admin.get("TotpVerified") or 0) == 1):
            return False, "MFA must be enabled before generating recovery codes", []
        plainCodes = []
        rows = []
        now = datetime.datetime.now()
        for _ in range(self.RecoveryCodeCount):
            groups = ["".join(secrets.choice(self.RecoveryAlphabet) for _ in range(4)) for _ in range(4)]
            code = "-".join(groups)
            plainCodes.append(code)
            rows.append({
                "CodeID": str(uuid.uuid4()),
                "AdminID": AdminID,
                "CodeHash": self.__HashRecoveryCode(code),
                "UsedDate": None,
                "CreatedDate": now,
            })
        with self.engine.begin() as conn:
            conn.execute(self.recoveryCodesTable.delete().where(
                self.recoveryCodesTable.c.AdminID == AdminID))
            conn.execute(self.recoveryCodesTable.insert(), rows)
        return True, None, plainCodes

    def RevokeRecoveryCodes(self, AdminID: str) -> tuple[bool, str | None]:
        with self.engine.begin() as conn:
            conn.execute(self.recoveryCodesTable.delete().where(
                self.recoveryCodesTable.c.AdminID == AdminID))
        return True, None

    def UseRecoveryCode(self, AdminID: str, Code: str) -> bool:
        """Consume a recovery code. Returns True when the code was valid and unused.

        The "still unused" test and the write happen in a single UPDATE, so two sign-ins running
        concurrently can never both consume the same code.
        """
        normalized = self.__NormalizeRecoveryCode(Code)
        if len(normalized) != 16:
            return False
        codeHash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        with self.engine.begin() as conn:
            result = conn.execute(
                self.recoveryCodesTable.update()
                .values({"UsedDate": datetime.datetime.now()})
                .where(db.and_(
                    self.recoveryCodesTable.c.AdminID == AdminID,
                    self.recoveryCodesTable.c.CodeHash == codeHash,
                    self.recoveryCodesTable.c.UsedDate.is_(None),
                ))
            )
            return result.rowcount == 1

