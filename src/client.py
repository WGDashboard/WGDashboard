from tzlocal import get_localzone

from functools import wraps

from flask import Blueprint, render_template, abort, request, Flask, current_app, session, redirect, url_for
import os

from modules.WireguardConfiguration import WireguardConfiguration
from modules.DashboardConfig import DashboardConfig

def ResponseObject(status=True, message=None, data=None, status_code = 200) -> Flask.response_class:
    response = Flask.make_response(current_app, {
        "status": status,
        "message": message,
        "data": data
    })
    response.status_code = status_code
    response.content_type = "application/json"
    return response



from modules.DashboardClients import DashboardClients
def createClientBlueprint(wireguardConfigurations: dict[WireguardConfiguration], dashboardConfig: DashboardConfig, dashboardClients: DashboardClients):
        
    client = Blueprint('client', __name__, template_folder=os.path.abspath("./static/dist/WGDashboardClient"))
    prefix = f'{dashboardConfig.GetConfig("Server", "app_prefix")[1]}/client'

    def login_required(f):
        @wraps(f)
        def func(*args, **kwargs):
            if session.get("Email") is None or session.get("TotpVerified") is None or not session.get("TotpVerified") or session.get("Role") != "client":
                return ResponseObject(False, "Unauthorized access.", data=None, status_code=401)
        
            if not dashboardClients.GetClient(session.get("ClientID")):
                session.clear()
                return ResponseObject(False, "Unauthorized access.", data=None, status_code=401)
            
            return f(*args, **kwargs)
        return func
    
    @client.before_request
    def clientBeforeRequest():
        if request.method.lower() == 'options':
            return ResponseObject(True)
    
    @client.post(f'{prefix}/api/signup')
    def ClientAPI_SignUp():
        data = request.json
        status, msg = dashboardClients.SignUp(**data)
        return ResponseObject(status, msg)

    @client.get(f'{prefix}/api/signin/oidc/providers')
    def ClientAPI_SignIn_OIDC_GetProviders():
        _, oidc = dashboardConfig.GetConfig("OIDC", "client_enable")
        if not oidc:
            return ResponseObject(status=False, message="OIDC is disabled")
        
        return ResponseObject(data=dashboardClients.OIDC.GetProviders())
    
    @client.post(f'{prefix}/api/signin/oidc')
    def ClientAPI_SignIn_OIDC():
        _, oidc = dashboardConfig.GetConfig("OIDC", "client_enable")
        if not oidc:
            return ResponseObject(status=False, message="OIDC is disabled")
        
        data = request.json
        status, oidcData = dashboardClients.SignIn_OIDC(**data)
        if not status:
            return ResponseObject(status, oidcData)

        session['Email'] = oidcData.get('email')
        session['Role'] = 'client'
        session['TotpVerified'] = True
        
        return ResponseObject()
    
    @client.post(f'{prefix}/api/signin')
    def ClientAPI_SignIn():
        data = request.json
        status, msg = dashboardClients.SignIn(**data)
        if status:
            session['Email'] = data.get('Email')
            session['Role'] = 'client'
            session['TotpVerified'] = False
        return ResponseObject(status, msg)

    @client.get(f'{prefix}/api/signout')
    def ClientAPI_SignOut():
        if session.get("SignInMethod") == "OIDC":
            dashboardClients.SignOut_OIDC()
        session.clear()
        return ResponseObject(True)
    
    @client.get(f'{prefix}/api/signin/totp')
    def ClientAPI_SignIn_TOTP():
        token = request.args.get('Token', None)
        if not token:
            return ResponseObject(False, "Please provide TOTP token")
        
        status, msg = dashboardClients.SignIn_GetTotp(token)
        return ResponseObject(status, msg)

    @client.post(f'{prefix}/api/signin/totp')
    def ClientAPI_SignIn_ValidateTOTP():
        data = request.json
        token = data.get('Token', None)
        userProvidedTotp = data.get('UserProvidedTOTP', None)
        if not all([token, userProvidedTotp]):
            return ResponseObject(False, "Please fill in all fields")
        status, msg = dashboardClients.SignIn_GetTotp(token, userProvidedTotp)
        if status:
            if session.get('Email') is None:
                return ResponseObject(False, "Sign in status is invalid", status_code=401)
            session['TotpVerified'] = True
            profile = dashboardClients.GetClientProfile(session.get("ClientID"))
            
            return ResponseObject(True, data={
                "Email": session.get('Email'),
                "Profile": profile
            })
        return ResponseObject(status, msg)
    
    @client.get(prefix)
    def ClientIndex():
        return render_template('client.html')
    
    @client.get(f'{prefix}/api/serverInformation')
    def ClientAPI_ServerInformation():
        return ResponseObject(data={
            "ServerTimezone": str(get_localzone())
        })
    
    @client.get(f'{prefix}/api/validateAuthentication')
    @login_required
    def ClientAPI_ValidateAuthentication():
        return ResponseObject(True)
    
    @client.get(f'{prefix}/api/configurations')
    @login_required
    def ClientAPI_Configurations():
        return ResponseObject(True, data=dashboardClients.GetClientAssignedPeers(session['ClientID']))
    
    @client.get(f'{prefix}/api/settings/getClientProfile')
    @login_required
    def ClientAPI_Settings_GetClientProfile():
        return ResponseObject(data={
            "Email": session.get("Email"),
            "SignInMethod": session.get("SignInMethod"),
            "Profile": dashboardClients.GetClientProfile(session.get("ClientID"))
        })
    
    @client.post(f'{prefix}/api/settings/updatePassword')
    @login_required
    def ClientAPI_Settings_UpdatePassword():
        data = request.get_json()
        status, message = dashboardClients.UpdateClientPassword(session['Email'], **data)
    
        return ResponseObject(status, message)
    
    return client