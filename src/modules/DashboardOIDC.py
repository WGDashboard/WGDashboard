import os
import json
import requests
from jose import jwt
import certifi
from flask import current_app

class DashboardOIDC:
    ConfigurationPath = os.getenv('CONFIGURATION_PATH', '.')
    ConfigurationFilePath = os.path.join(ConfigurationPath, 'wg-dashboard-oidc-providers.json')
    def __init__(self, mode):
        self.mode = mode
        self.providers: dict[str, dict] = {}
        self.provider_secret: dict[str, str] = {}
        self.__default = {
            "Admin": {
                'Provider': {
                    'client_id': '',
                    'client_secret': '',
                    'issuer': '',
                },
            },
            "Client": {
                'Provider': {
                    'client_id': '',
                    'client_secret': '',
                    'issuer': '',
                },
            }
        }
        
        if not os.path.exists(DashboardOIDC.ConfigurationFilePath):
            with open(DashboardOIDC.ConfigurationFilePath, "w+") as f:
                encoder = json.JSONEncoder(indent=4)
                f.write(encoder.encode(self.__default))
        
        self.ReadFile()
        
    def GetProviders(self):
        return self.providers
    
    def GetProviderNameByIssuer(self, issuer):
        for (key, val) in self.providers.items():
            if val.get('openid_configuration').get('issuer') == issuer:
                return key
        return issuer
    
    def VerifyToken(self, provider, code, redirect_uri):
        try:
            if not all([provider, code, redirect_uri]):
                return False, "Please provide all parameters"

            if provider not in self.providers.keys():
                return False, "Provider does not exist"
    
            secrete = self.provider_secret.get(provider)
            oidc_config_status, oidc_config = self.GetProviderConfiguration(provider)
            provider_info = self.providers.get(provider)
            
    
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": provider_info.get('client_id'),
                "client_secret": secrete
            }
    
            try:
                tokens = requests.post(oidc_config.get('token_endpoint'), data=data).json()
                if not all([tokens.get('access_token'), tokens.get('id_token')]):
                    print(oidc_config.get('token_endpoint'), data)
                    return False, tokens.get('error_description', None)
            except Exception as e:
                print(str(e))
                return False, str(e)
            
            access_token = tokens.get('access_token')
            id_token = tokens.get('id_token')
            jwks_uri = oidc_config.get("jwks_uri")
            issuer = oidc_config.get("issuer")
            jwks = requests.get(jwks_uri, verify=certifi.where()).json()
    
            headers = jwt.get_unverified_header(id_token)
            kid = headers["kid"]
    
            key = next(k for k in jwks["keys"] if k["kid"] == kid)
                    
            payload = jwt.decode(
                id_token,
                key,
                algorithms=[key["alg"]],
                audience=provider_info.get('client_id'),
                issuer=issuer,
                access_token=access_token
            )
            print(payload)
            return True, payload
        except Exception as e:
            current_app.logger.error('Read OIDC file failed. Reason: ' + str(e), provider, code, redirect_uri)
            return False, str(e)
    
    def GetProviderConfiguration(self, provider_name):
        if not all([provider_name]):
            return False, None
        provider = self.providers.get(provider_name)
        try:
            oidc_config = requests.get(
                f"{provider.get('issuer').strip('/')}/.well-known/openid-configuration",
                verify=certifi.where()
            ).json()
        except Exception as e:
            current_app.logger.error("Failed to get OpenID Configuration of " + provider.get('issuer'), exc_info=e)
            return False, None
        return True, oidc_config
    
    def ReadFile(self):
        decoder = json.JSONDecoder()
        try:
            providers = decoder.decode(
                open(DashboardOIDC.ConfigurationFilePath, 'r').read()
            )
            providers = providers[self.mode]
            for k in providers.keys():
                if all([providers[k]['client_id'], providers[k]['client_secret'], providers[k]['issuer']]):
                    try:
                        print("Requesting " + f"{providers[k]['issuer'].strip('/')}/.well-known/openid-configuration")
                        oidc_config = requests.get(
                            f"{providers[k]['issuer'].strip('/')}/.well-known/openid-configuration",
                            timeout=3,
                            verify=certifi.where()
                        ).json()
                        self.providers[k] = {
                            'client_id': providers[k]['client_id'],
                            'issuer': providers[k]['issuer'].strip('/'),
                            'openid_configuration': oidc_config
                        }
                        self.provider_secret[k] = providers[k]['client_secret']
                    except Exception as e:
                        current_app.logger.error("Failed to request OIDC config for this provider: " + providers[k]['issuer'].strip('/'), exc_info=e)
        except Exception as e:
            current_app.logger.error('Read OIDC file failed. Reason: ' + str(e))
            return False