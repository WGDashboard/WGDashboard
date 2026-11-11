"""Unit tests for the multi-administrator module (``src/modules/DashboardAdmins.py``).

The tests exercise the real module: a temporary SQLite database is created through the
project's own ``ConnectionString()`` helper, and a minimal stand-in replaces
``DashboardConfig`` (only ``GetConfig``/``SetConfig`` are used by the module).

Run with::

    pip install pytest        # pytest is not a runtime dependency
    pytest tests/ -q

No Flask application, no WireGuard configuration and no network access are required.
"""
import sys
from pathlib import Path

import bcrypt
import pyotp
import pytest
from flask import Flask

# ``DashboardAdmins`` uses relative imports (``from .DatabaseConnection import ...``): it must
# be imported as ``modules.DashboardAdmins``, with ``src/`` on the import path.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from modules.DashboardAdmins import DashboardAdmins  # noqa: E402

INI_PASSWORD = "Password1!"


class FakeConfig:
    """Minimal replacement for ``DashboardConfig`` (typed values, like the real one)."""

    def __init__(self, **account):
        self.values = {
            ("Account", "username"): "root",
            ("Account", "password"): bcrypt.hashpw(
                INI_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            ("Account", "totp_key"): "",
            ("Account", "enable_totp"): False,
            ("Account", "totp_verified"): False,
        }
        self.values.update({("Account", key): value for key, value in account.items()})
        self.set_calls = []

    def GetConfig(self, section, key):
        if (section, key) in self.values:
            return True, self.values[(section, key)]
        return False, None

    def SetConfig(self, section, key, value, init=False):
        self.values[(section, key)] = value
        self.set_calls.append((section, key, value))
        return True, None


@pytest.fixture
def config():
    return FakeConfig()


@pytest.fixture
def admins(tmp_path, monkeypatch, config):
    """A DashboardAdmins bound to a throwaway SQLite database, inside an app context."""
    monkeypatch.chdir(tmp_path)  # ConnectionString() reads ./wg-dashboard.ini
    (tmp_path / "wg-dashboard.ini").write_text("[Database]\ntype = sqlite\n", encoding="utf-8")
    app = Flask(__name__)
    with app.app_context():
        yield DashboardAdmins(config)


@pytest.fixture
def second_admin(admins):
    """A plain second administrator (no MFA) next to the imported one."""
    status, message = admins.AddAdmin("second", "second@example.com", "Second1!x", "Second1!x",
                                      CreatedBy="tests")
    assert status, message
    return admins.GetAdminByUsername("second")


def enable_totp(admins, admin_id):
    """Enrol an administrator and return its TOTP secret."""
    status, message, payload = admins.StartTotp(admin_id)
    assert status, message
    secret = payload["Secret"]
    status, message = admins.VerifyTotp(admin_id, pyotp.TOTP(secret).now())
    assert status, message
    return secret

class TestBootstrap:
    """The account of wg-dashboard.ini is imported as the first administrator."""

    def test_ini_account_becomes_the_first_administrator(self, admins):
        assert admins.Count() == 1
        admin = admins.GetAdminByUsername("root")
        assert admin is not None
        assert admin["CreatedBy"] == "wg-dashboard.ini"
        assert admin["Enabled"] == 1
        assert admin["TotpVerified"] == 0

    def test_bootstrap_is_skipped_when_the_table_is_not_empty(self, admins):
        assert admins.BootstrapFromConfig() is False
        assert admins.Count() == 1

    def test_bootstrap_needs_a_password(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "wg-dashboard.ini").write_text("[Database]\ntype = sqlite\n", encoding="utf-8")
        with Flask(__name__).app_context():
            instance = DashboardAdmins(FakeConfig(password=""))
        assert instance.Count() == 0

    def test_ini_mfa_state_is_imported(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "wg-dashboard.ini").write_text("[Database]\ntype = sqlite\n", encoding="utf-8")
        with Flask(__name__).app_context():
            instance = DashboardAdmins(FakeConfig(enable_totp=True, totp_key="JBSWY3DPEHPK3PXP",
                                                  totp_verified=True))
        assert instance.GetAdminByUsername("root")["TotpVerified"] == 1

    def test_public_never_exposes_secrets(self, admins):
        public = admins.Public(admins.GetAdminByUsername("root"))
        assert "Password" not in public
        assert "TotpKey" not in public
        assert public["Username"] == "root"
        assert public["RecoveryCodesRemaining"] == 0
        assert "CreatedBy" in public


class TestSignIn:
    def test_valid_credentials(self, admins):
        status, message, payload = admins.SignIn("root", INI_PASSWORD)
        assert status, message
        assert payload["Username"] == "root"
        assert payload["UsedRecoveryCode"] is False
        assert payload["MfaSetupRequired"] is True

    def test_wrong_password_is_refused(self, admins):
        status, message, payload = admins.SignIn("root", "not-the-password")
        assert status is False and payload is None
        assert message == "Sorry, your username or password is incorrect."

    def test_unknown_username_gives_the_same_message(self, admins):
        status, message, _ = admins.SignIn("nobody", INI_PASSWORD)
        assert status is False
        assert message == "Sorry, your username or password is incorrect."

    def test_disabled_account_is_refused(self, admins, second_admin):
        status, message = admins.SetEnabled(second_admin["AdminID"], False)
        assert status, message
        status, message, _ = admins.SignIn("second", "Second1!x")
        assert status is False
        assert message == "This administrator account is disabled."

    def test_a_wrong_password_does_not_reveal_a_disabled_account(self, admins, second_admin):
        """The 'disabled' message is only sent once the password has been checked."""
        admins.SetEnabled(second_admin["AdminID"], False)
        status, message, _ = admins.SignIn("second", "not-the-password")
        assert status is False
        assert message == "Sorry, your username or password is incorrect."

    def test_last_login_is_recorded(self, admins):
        before = admins.GetAdminByUsername("root")["LastLoginDate"]
        admins.SignIn("root", INI_PASSWORD)
        after = admins.GetAdminByUsername("root")["LastLoginDate"]
        assert after is not None
        assert after != before

    def test_otp_is_required_once_mfa_is_enabled(self, admins):
        secret = enable_totp(admins, admins.GetAdminByUsername("root")["AdminID"])
        status, message, _ = admins.SignIn("root", INI_PASSWORD)
        assert status is False
        status, message, payload = admins.SignIn("root", INI_PASSWORD, pyotp.TOTP(secret).now())
        assert status, message
        assert payload["MfaSetupRequired"] is False

    def test_wrong_otp_is_refused(self, admins):
        enable_totp(admins, admins.GetAdminByUsername("root")["AdminID"])
        status, message, _ = admins.SignIn("root", INI_PASSWORD, "not-a-code")
        assert status is False
        assert message == "Sorry, your username, password or OTP is incorrect."

class TestCrud:
    def test_add_administrator(self, admins):
        status, message = admins.AddAdmin("alice", "alice@example.com", "Alice1!x", "Alice1!x",
                                          CreatedBy="tests")
        assert status, message
        admin = admins.GetAdminByUsername("alice")
        assert admin["Enabled"] == 1
        assert admin["TotpVerified"] == 0
        assert admin["CreatedBy"] == "tests"
        assert bcrypt.checkpw(b"Alice1!x", admin["Password"].encode("utf-8"))

    @pytest.mark.parametrize("username", ["ab", "a" * 65, "bad name", "no/slash", ""])
    def test_invalid_usernames_are_refused(self, admins, username):
        status, message = admins.AddAdmin(username, "", "Alice1!x", "Alice1!x")
        assert status is False
        assert message.startswith("Username must be 3 to 64 characters")

    def test_duplicate_username_is_refused(self, admins):
        status, message = admins.AddAdmin("root", "", "Alice1!x", "Alice1!x")
        assert status is False
        assert message == "This username already exists"

    def test_password_confirmation_must_match(self, admins):
        status, message = admins.AddAdmin("alice", "", "Alice1!x", "Alice1!y")
        assert status is False
        assert message == "Passwords do not match"

    def test_weak_password_is_refused(self, admins):
        status, message = admins.AddAdmin("alice", "", "abc", "abc")
        assert status is False
        assert message == "Password must be 8 characters or more"

    def test_rename_administrator(self, admins, second_admin):
        status, message = admins.UpdateAdmin(second_admin["AdminID"], "second-renamed",
                                             "new@example.com")
        assert status, message
        assert admins.GetAdminByUsername("second-renamed")["Email"] == "new@example.com"
        assert admins.GetAdminByUsername("second") is None

    def test_rename_onto_an_existing_username_is_refused(self, admins, second_admin):
        status, message = admins.UpdateAdmin(second_admin["AdminID"], "root", "")
        assert status is False
        assert message == "This username already exists"

    def test_renaming_the_ini_account_updates_the_config(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        status, message = admins.UpdateAdmin(admin["AdminID"], "supervisor", "")
        assert status, message
        assert config.GetConfig("Account", "username")[1] == "supervisor"

    def test_set_password_requires_the_current_one(self, admins, second_admin):
        status, message = admins.SetPassword(second_admin["AdminID"], "Another1!x", "Another1!x",
                                             CurrentPassword="wrong")
        assert status is False
        assert message == "Current password does not match"

    def test_set_password(self, admins, second_admin):
        status, message = admins.SetPassword(second_admin["AdminID"], "Another1!x", "Another1!x",
                                             CurrentPassword="Second1!x")
        assert status, message
        assert admins.CheckPassword(second_admin["AdminID"], "Another1!x") is True
        assert admins.CheckPassword(second_admin["AdminID"], "Second1!x") is False


class TestGuards:
    """The installation must always keep one usable administrator."""

    def test_cannot_disable_your_own_account(self, admins):
        admin = admins.GetAdminByUsername("root")
        status, message = admins.SetEnabled(admin["AdminID"], False, CurrentAdminID=admin["AdminID"])
        assert status is False
        assert message == "You cannot disable your own account"

    def test_can_disable_when_another_enabled_administrator_exists(self, admins, second_admin):
        status, message = admins.SetEnabled(second_admin["AdminID"], False)
        assert status, message
        assert admins.CountEnabled() == 1

    def test_cannot_disable_the_last_enabled_administrator(self, admins, second_admin):
        admins.SetEnabled(second_admin["AdminID"], False)
        root = admins.GetAdminByUsername("root")
        status, message = admins.SetEnabled(root["AdminID"], False)
        assert status is False
        assert message == "At least one enabled administrator is required"
        assert admins.GetAdmin(root["AdminID"])["Enabled"] == 1

    def test_cannot_delete_your_own_account(self, admins):
        admin = admins.GetAdminByUsername("root")
        status, message = admins.DeleteAdmin(admin["AdminID"], CurrentAdminID=admin["AdminID"])
        assert status is False
        assert message == "You cannot delete your own account"

    def test_cannot_delete_the_last_enabled_administrator(self, admins, second_admin):
        admins.SetEnabled(second_admin["AdminID"], False)
        root = admins.GetAdminByUsername("root")
        status, message = admins.DeleteAdmin(root["AdminID"])
        assert status is False
        assert message == "At least one enabled administrator is required"
        assert admins.GetAdmin(root["AdminID"]) is not None

    def test_can_delete_a_disabled_administrator(self, admins, second_admin):
        admins.SetEnabled(second_admin["AdminID"], False)
        status, message = admins.DeleteAdmin(second_admin["AdminID"])
        assert status, message
        assert admins.Count() == 1

    def test_can_delete_one_of_two_enabled_administrators(self, admins, second_admin):
        status, message = admins.DeleteAdmin(second_admin["AdminID"])
        assert status, message
        assert admins.CountEnabled() == 1

    def test_unknown_administrator(self, admins):
        assert admins.SetEnabled("missing", False) == (False, "Administrator does not exist")
        assert admins.DeleteAdmin("missing") == (False, "Administrator does not exist")


class TestPortableGuard:
    def test_guards_read_the_target_table_through_derived_tables(self, admins):
        """MySQL rejects a subquery reading the table targeted by an UPDATE/DELETE (error 1093).

        Both guards must therefore count from an aliased derived table, which MySQL
        materialises before running the UPDATE/DELETE.
        """
        from sqlalchemy.dialects import mysql

        admin_count = getattr(admins, "_DashboardAdmins__AdminCount")()
        other_enabled = getattr(admins, "_DashboardAdmins__OtherEnabledAdmins")("target")
        statement = (admins.adminsTable.delete()
                     .where(admins.adminsTable.c.AdminID == "target")
                     .where(admin_count > 1)
                     .where(other_enabled))
        sql = str(statement.compile(dialect=mysql.dialect(),
                                    compile_kwargs={"literal_binds": True}))
        assert "AS all_administrators" in sql
        assert "AS other_enabled_administrators" in sql


class TestTotp:
    def test_start_totp_returns_a_pending_secret(self, admins):
        admin = admins.GetAdminByUsername("root")
        status, message, payload = admins.StartTotp(admin["AdminID"])
        assert status, message
        assert payload["Secret"]
        assert payload["Link"].startswith("otpauth://totp/")
        # Pending until verified: a half-configured MFA must never lock the account out
        assert admins.GetAdmin(admin["AdminID"])["TotpVerified"] == 0

    def test_verify_totp_activates_the_mfa(self, admins):
        admin = admins.GetAdminByUsername("root")
        _, _, payload = admins.StartTotp(admin["AdminID"])
        secret = payload["Secret"]
        status, message = admins.VerifyTotp(admin["AdminID"], pyotp.TOTP(secret).now())
        assert status, message
        assert admins.GetAdmin(admin["AdminID"])["TotpVerified"] == 1

    def test_verify_totp_refuses_a_wrong_code(self, admins):
        admin = admins.GetAdminByUsername("root")
        admins.StartTotp(admin["AdminID"])
        status, message = admins.VerifyTotp(admin["AdminID"], "012345")
        assert status is False
        assert message == "This code is not valid, please try again"

    def test_start_totp_is_refused_once_enabled(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        status, message, _ = admins.StartTotp(admin["AdminID"])
        assert status is False
        assert message == "MFA is already enabled for this administrator"

    def test_disable_totp_clears_the_secret_and_the_recovery_codes(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        admins.GenerateRecoveryCodes(admin["AdminID"])
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 10
        status, message = admins.DisableTotp(admin["AdminID"])
        assert status, message
        stored = admins.GetAdmin(admin["AdminID"])
        assert stored["TotpKey"] is None
        assert stored["TotpVerified"] == 0
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 0


    def test_a_code_from_a_superseded_secret_is_refused(self, admins):
        """A second enrolment tab replaces the pending secret: the old code must not verify."""
        admin = admins.GetAdminByUsername("root")
        _, _, first = admins.StartTotp(admin["AdminID"])
        admins.StartTotp(admin["AdminID"])
        status, _ = admins.VerifyTotp(admin["AdminID"], pyotp.TOTP(first["Secret"]).now())
        assert status is False
        assert admins.GetAdmin(admin["AdminID"])["TotpVerified"] == 0

    def test_the_ini_fallback_follows_a_confirmed_enrolment(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        secret = enable_totp(admins, admin["AdminID"])
        assert config.GetConfig("Account", "enable_totp")[1] == "true"
        assert config.GetConfig("Account", "totp_verified")[1] == "true"
        assert config.GetConfig("Account", "totp_key")[1] == secret

    def test_the_ini_fallback_follows_a_disable(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        admins.DisableTotp(admin["AdminID"])
        assert config.GetConfig("Account", "enable_totp")[1] == "false"
        assert config.GetConfig("Account", "totp_verified")[1] == "false"
        assert config.GetConfig("Account", "totp_key")[1] == ""

    def test_another_account_does_not_touch_the_ini_fallback(self, admins, config, second_admin):
        enable_totp(admins, second_admin["AdminID"])
        assert config.GetConfig("Account", "enable_totp")[1] is False


class TestRecoveryCodes:
    def test_codes_require_mfa_to_be_enabled(self, admins):
        admin = admins.GetAdminByUsername("root")
        status, message, codes = admins.GenerateRecoveryCodes(admin["AdminID"])
        assert status is False
        assert message == "MFA must be enabled before generating recovery codes"
        assert codes == []

    def test_generate_returns_ten_single_use_codes(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        status, message, codes = admins.GenerateRecoveryCodes(admin["AdminID"])
        assert status, message
        assert len(codes) == 10
        assert len(set(codes)) == 10
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 10
        assert admins.HasAnyRecoveryCodes(admin["AdminID"]) is True

    def test_a_code_is_single_use(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        _, _, codes = admins.GenerateRecoveryCodes(admin["AdminID"])
        assert admins.UseRecoveryCode(admin["AdminID"], codes[0]) is True
        assert admins.UseRecoveryCode(admin["AdminID"], codes[0]) is False
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 9

    def test_codes_are_case_and_dash_insensitive(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        _, _, codes = admins.GenerateRecoveryCodes(admin["AdminID"])
        normalized = codes[0].replace("-", "").lower()
        assert admins.UseRecoveryCode(admin["AdminID"], normalized) is True

    @pytest.mark.parametrize("code", ["", "ABCD", "0000-0000-0000-0000"])
    def test_unknown_or_malformed_codes_are_refused(self, admins, code):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        admins.GenerateRecoveryCodes(admin["AdminID"])
        assert admins.UseRecoveryCode(admin["AdminID"], code) is False

    def test_regenerating_replaces_the_previous_codes(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        _, _, first = admins.GenerateRecoveryCodes(admin["AdminID"])
        _, _, second = admins.GenerateRecoveryCodes(admin["AdminID"])
        assert admins.UseRecoveryCode(admin["AdminID"], first[0]) is False
        assert admins.UseRecoveryCode(admin["AdminID"], second[0]) is True

    def test_revoke_removes_every_code(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        admins.GenerateRecoveryCodes(admin["AdminID"])
        status, message = admins.RevokeRecoveryCodes(admin["AdminID"])
        assert status, message
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 0
        assert admins.HasAnyRecoveryCodes(admin["AdminID"]) is False

    def test_signing_in_with_a_recovery_code(self, admins):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        _, _, codes = admins.GenerateRecoveryCodes(admin["AdminID"])
        status, message, payload = admins.SignIn("root", INI_PASSWORD, codes[0])
        assert status, message
        assert payload["UsedRecoveryCode"] is True
        assert payload["MfaSetupRequired"] is False
        status, _, _ = admins.SignIn("root", INI_PASSWORD, codes[0])
        assert status is False


class TestIniSynchronisation:
    """The wg-dashboard.ini account stays a usable safety fallback."""

    def test_sync_password_from_config(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        assert admins.SyncPasswordFromConfig("Renewed1!") is True
        assert admins.CheckPassword(admin["AdminID"], "Renewed1!") is True
        assert admins.CheckPassword(admin["AdminID"], INI_PASSWORD) is False

    def test_sync_password_from_config_needs_an_account(self, admins, config):
        config.values[("Account", "username")] = "ghost"
        assert admins.SyncPasswordFromConfig("Renewed1!") is False

    def test_sync_password_from_config_ignores_an_empty_password(self, admins):
        assert admins.SyncPasswordFromConfig("") is False

    def test_rename_from_config(self, admins, config):
        config.values[("Account", "username")] = "renamed"
        assert admins.RenameFromConfig() is True
        assert admins.GetAdminByUsername("renamed") is not None
        assert admins.GetAdminByUsername("root") is None

    def test_rename_from_config_refuses_a_taken_username(self, admins, config, second_admin):
        config.values[("Account", "username")] = "second"
        assert admins.RenameFromConfig() is False
        assert admins.GetAdminByUsername("root") is not None

    def test_sync_totp_from_config(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        config.values[("Account", "enable_totp")] = True
        config.values[("Account", "totp_verified")] = True
        config.values[("Account", "totp_key")] = "JBSWY3DPEHPK3PXP"
        assert admins.SyncTotpFromConfig() is True
        stored = admins.GetAdmin(admin["AdminID"])
        assert stored["TotpKey"] == "JBSWY3DPEHPK3PXP"
        assert stored["TotpVerified"] == 1

    def test_sync_totp_from_config_requires_the_flags(self, admins, config):
        config.values[("Account", "totp_key")] = "JBSWY3DPEHPK3PXP"
        assert admins.SyncTotpFromConfig() is False
        config.values[("Account", "enable_totp")] = True
        config.values[("Account", "totp_verified")] = True
        config.values[("Account", "totp_key")] = ""
        assert admins.SyncTotpFromConfig() is False


class TestCredentialSynchronisation:
    """Docker rewrites the ini credentials on every start: the table must follow."""

    def test_a_username_rotation_reaches_the_login(self, admins, config):
        config.values[("Account", "username")] = "rotated"
        DashboardAdmins(config)  # simulates the next start, after entrypoint.sh rewrote the ini
        assert admins.GetAdminByUsername("root") is None
        status, message, _ = admins.SignIn("rotated", INI_PASSWORD)
        assert status, message

    def test_a_password_rotation_reaches_the_login(self, admins, config):
        config.values[("Account", "password")] = bcrypt.hashpw(
            b"Rotated1!", bcrypt.gensalt()).decode("utf-8")
        DashboardAdmins(config)
        assert admins.SignIn("root", "Rotated1!")[0] is True
        assert admins.SignIn("root", INI_PASSWORD)[0] is False

    def test_a_username_belonging_to_another_administrator_is_not_taken_over(self, admins, config,
                                                                            second_admin):
        config.values[("Account", "username")] = "second"
        assert admins.SyncCredentialsFromConfig() is False
        assert admins.GetAdminByUsername("root") is not None
        assert admins.GetAdminByUsername("second") is not None

    def test_unchanged_credentials_are_a_no_op(self, admins, config):
        assert admins.SyncCredentialsFromConfig() is False

    def test_other_administrators_are_not_touched(self, admins, config, second_admin):
        config.values[("Account", "password")] = bcrypt.hashpw(
            b"Rotated1!", bcrypt.gensalt()).decode("utf-8")
        assert admins.SyncCredentialsFromConfig() is True
        assert admins.CheckPassword(second_admin["AdminID"], "Second1!x") is True


class TestMfaSynchronisation:
    """Docker also writes the MFA flags: the table must follow them as well."""

    def test_disabling_mfa_in_the_ini_disables_it_and_revokes_the_codes(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        admins.GenerateRecoveryCodes(admin["AdminID"])
        config.values[("Account", "enable_totp")] = False
        config.values[("Account", "totp_verified")] = False
        assert admins.SyncMfaFromConfig() is True
        stored = admins.GetAdmin(admin["AdminID"])
        assert stored["TotpKey"] is None
        assert stored["TotpVerified"] == 0
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 0

    def test_a_rotated_secret_replaces_the_previous_one(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        enable_totp(admins, admin["AdminID"])
        admins.GenerateRecoveryCodes(admin["AdminID"])
        config.values[("Account", "enable_totp")] = True
        config.values[("Account", "totp_verified")] = True
        config.values[("Account", "totp_key")] = "MFRGGZDFMZTWQ2LK"
        assert admins.SyncMfaFromConfig() is True
        stored = admins.GetAdmin(admin["AdminID"])
        assert stored["TotpKey"] == "MFRGGZDFMZTWQ2LK"
        assert stored["TotpVerified"] == 1
        # the old recovery codes belonged to the replaced secret
        assert admins.CountRecoveryCodes(admin["AdminID"]) == 0

    def test_unchanged_mfa_is_a_no_op(self, admins, config):
        admin = admins.GetAdminByUsername("root")
        secret = enable_totp(admins, admin["AdminID"])
        config.values[("Account", "totp_key")] = secret
        assert admins.SyncMfaFromConfig() is False






