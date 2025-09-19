"""
Dashboard Configuration
"""
import configparser, secrets, os, pyotp, ipaddress, bcrypt
from sqlalchemy_utils import database_exists, create_database
import sqlalchemy as db
from datetime import datetime
from typing import Any
from flask import current_app
from .ConnectionString import ConnectionString, DEFAULT_DB
from .Utilities import (
    GetRemoteEndpoint, ValidateDNSAddress
)
from .DashboardAPIKey import DashboardAPIKey



class DashboardConfig:
    DashboardVersion = 'v4.3.0.1'
    ConfigurationPath = os.getenv('CONFIGURATION_PATH', '.')
    ConfigurationFilePath = os.path.join(ConfigurationPath, 'wg-dashboard.ini')
    
    def __init__(self):
        if not os.path.exists(DashboardConfig.ConfigurationFilePath):
            open(DashboardConfig.ConfigurationFilePath, "x")
        self.__config = configparser.RawConfigParser(strict=False)
        self.__config.read_file(open(DashboardConfig.ConfigurationFilePath, "r+"))
        self.hiddenAttribute = ["totp_key", "auth_req"]
        self.__default = {
            "Account": {
                "username": "admin",
                "password": "admin",
                "enable_totp": "false",
                "totp_verified": "false",
                "totp_key": pyotp.random_base32()
            },
            "Server": {
                "wg_conf_path": "/etc/wireguard",
                "awg_conf_path": "/etc/amnezia/amneziawg",
                "app_prefix": "",
                "app_ip": "0.0.0.0",
                "app_port": "10086",
                "auth_req": "true",
                "version": DashboardConfig.DashboardVersion,
                "dashboard_refresh_interval": "60000",
                "dashboard_peer_list_display": "grid",
                "dashboard_sort": "status",
                "dashboard_theme": "dark",
                "dashboard_api_key": "false",
                "dashboard_language": "en-US"
            },
            "Peers": {
                "peer_global_DNS": "1.1.1.1",
                "peer_endpoint_allowed_ip": "0.0.0.0/0",
                "peer_display_mode": "grid",
                "remote_endpoint": GetRemoteEndpoint(),
                "peer_MTU": "1420",
                "peer_keep_alive": "21"
            },
            "Other": {
                "welcome_session": "true"
            },
            "Database":{
                "type": "sqlite",
                "host": "",
                "port": "",
                "username": "",
                "password": "",
                "prefix": ""
            },
            "Email":{
                "server": "",
                "port": "",
                "encryption": "",
                "username": "",
                "email_password": "",
                "authentication_required": "true",
                "send_from": "",
                "email_template": ""
            },
            "OIDC": {
                "admin_enable": "false",
                "client_enable": "false"
            },
            "Clients": {
                "enable": "true",
            },
            "WireGuardConfiguration": {
                "autostart": ""
            }
        }

        for section, keys in self.__default.items():
            for key, value in keys.items():
                exist, currentData = self.GetConfig(section, key)
                if not exist:
                    self.SetConfig(section, key, value, True)

        self.engine = db.create_engine(ConnectionString(DEFAULT_DB))
        self.dbMetadata = db.MetaData()
        self.__createAPIKeyTable()
        self.DashboardAPIKeys = self.__getAPIKeys()
        self.APIAccessed = False
        self.SetConfig("Server", "version", DashboardConfig.DashboardVersion)

    def __createAPIKeyTable(self):
        self.apiKeyTable = db.Table('DashboardAPIKeys', self.dbMetadata,
                                    db.Column("Key", db.String(255), nullable=False, primary_key=True),
                                    db.Column("CreatedAt",
                                              (db.DATETIME if self.GetConfig('Database', 'type')[1] == 'sqlite' else db.TIMESTAMP),
                                              server_default=db.func.now()
                                              ),
                                    db.Column("ExpiredAt",
                                              (db.DATETIME if self.GetConfig('Database', 'type')[1] == 'sqlite' else db.TIMESTAMP)
                                              )
                                    )
        self.dbMetadata.create_all(self.engine)
    def __getAPIKeys(self) -> list[DashboardAPIKey]:
        try:
            with self.engine.connect() as conn:
                keys = conn.execute(self.apiKeyTable.select().where(
                    db.or_(self.apiKeyTable.columns.ExpiredAt.is_(None), self.apiKeyTable.columns.ExpiredAt > datetime.now())
                )).fetchall()
                fKeys = []
                for k in keys:
                    fKeys.append(DashboardAPIKey(k[0], k[1].strftime("%Y-%m-%d %H:%M:%S"), (k[2].strftime("%Y-%m-%d %H:%M:%S") if k[2] else None)))
                return fKeys
        except Exception as e:
            current_app.logger.error("API Keys error", e)
        return []

    def createAPIKeys(self, ExpiredAt = None):
        newKey = secrets.token_urlsafe(32)
        with self.engine.begin() as conn:
            conn.execute(
                self.apiKeyTable.insert().values({
                    "Key": newKey,
                    "ExpiredAt": ExpiredAt
                })
            )

        self.DashboardAPIKeys = self.__getAPIKeys()

    def deleteAPIKey(self, key):
        with self.engine.begin() as conn:
            conn.execute(
                self.apiKeyTable.update().values({
                    "ExpiredAt": datetime.now(),
                }).where(self.apiKeyTable.columns.Key == key)
            )

        self.DashboardAPIKeys = self.__getAPIKeys()

    def __configValidation(self, section : str, key: str, value: Any) -> tuple[bool, str]:
        if (type(value) is str and len(value) == 0
                and section not in ['Email', 'WireGuardConfiguration'] and
                (section == 'Peer' and key == 'peer_global_dns')):
            return False, "Field cannot be empty!"
        if section == "Peers" and key == "peer_global_dns" and len(value) > 0:
            return ValidateDNSAddress(value)
        if section == "Peers" and key == "peer_endpoint_allowed_ip":
            value = value.split(",")
            for i in value:
                i = i.strip()
                try:
                    ipaddress.ip_network(i, strict=False)
                except Exception as e:
                    return False, str(e)
        if section == "Server" and key == "wg_conf_path":
            if not os.path.exists(value):
                return False, f"{value} is not a valid path"
        if section == "Account" and key == "password":
            if self.GetConfig("Account", "password")[0]:
                if not self.__checkPassword(
                        value["currentPassword"], self.GetConfig("Account", "password")[1].encode("utf-8")):
                    return False, "Current password does not match."
                if value["newPassword"] != value["repeatNewPassword"]:
                    return False, "New passwords does not match"
        return True, ""

    def generatePassword(self, plainTextPassword: str):
        return bcrypt.hashpw(plainTextPassword.encode("utf-8"), bcrypt.gensalt())

    def __checkPassword(self, plainTextPassword: str, hashedPassword: bytes):
        return bcrypt.checkpw(plainTextPassword.encode("utf-8"), hashedPassword)

    def SetConfig(self, section: str, key: str, value: str | bool | list[str] | dict[str, str], init: bool = False) -> tuple[bool, str] | tuple[bool, None]:
        if key in self.hiddenAttribute and not init:
            return False, None

        if not init:
            valid, msg = self.__configValidation(section, key, value)
            if not valid:
                return False, msg

        if section == "Account" and key == "password":
            if not init:
                value = self.generatePassword(value["newPassword"]).decode("utf-8")
            else:
                value = self.generatePassword(value).decode("utf-8")

        if section == "Email" and key == "email_template":
            value = value.encode('unicode_escape').decode('utf-8')

        if section == "Server" and key == "wg_conf_path":
            if not os.path.exists(value):
                return False, "Path does not exist"

        if section not in self.__config:
            if init:
                self.__config[section] = {}
            else:
                return False, "Section does not exist"

        if ((key not in self.__config[section].keys() and init) or
                (key in self.__config[section].keys())):
            if type(value) is bool:
                if value:
                    self.__config[section][key] = "true"
                else:
                    self.__config[section][key] = "false"
            elif type(value) in [int, float]:
                self.__config[section][key] = str(value)
            elif type(value) is list:
                self.__config[section][key] = "||".join(value).strip("||")
            else:
                self.__config[section][key] = fr"{value}"
            return self.SaveConfig(), ""
        else:
            return False, f"{key} does not exist under {section}"

    def SaveConfig(self) -> bool:
        try:
            with open(DashboardConfig.ConfigurationFilePath, "w+", encoding='utf-8') as configFile:
                self.__config.write(configFile)
            return True
        except Exception as e:
            return False

    def GetConfig(self, section, key) ->tuple[bool, bool] | tuple[bool, str] | tuple[bool, list[str]] | tuple[bool, None]:
        if section not in self.__config:
            return False, None

        if key not in self.__config[section]:
            return False, None

        if section == "Email" and key == "email_template":
            return True, self.__config[section][key].encode('utf-8').decode('unicode_escape')

        if section == "WireGuardConfiguration" and key == "autostart":
            return True, list(filter(lambda x: len(x) > 0, self.__config[section][key].split("||")))

        if self.__config[section][key] in ["1", "yes", "true", "on"]:
            return True, True

        if self.__config[section][key] in ["0", "no", "false", "off"]:
            return True, False


        return True, self.__config[section][key]

    def toJson(self) -> dict[str, dict[Any, Any]]:
        the_dict = {}

        for section in self.__config.sections():
            the_dict[section] = {}
            for key, val in self.__config.items(section):
                if key not in self.hiddenAttribute:
                    the_dict[section][key] = self.GetConfig(section, key)[1]
        return the_dict
