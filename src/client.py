import datetime

from tzlocal import get_localzone

from functools import wraps

from flask import Blueprint, render_template, abort, request, Flask, current_app, session, redirect, url_for
import os

from modules.WireguardConfiguration import WireguardConfiguration
from modules.DashboardConfig import DashboardConfig
from modules.Email import EmailSender


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
        if not dashboardConfig.GetConfig("Clients", "enable")[1]:
            abort(404)
        
        if request.method.lower() == 'options':
            return ResponseObject(True)
    
    @client.post(f'{prefix}/api/signup')
    def ClientAPI_SignUp():
        data = request.get_json()
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
        
        data = request.get_json()
        status, oidcData = dashboardClients.SignIn_OIDC(**data)
        if not status:
            return ResponseObject(status, oidcData)

        session['Email'] = oidcData.get('email')
        session['Role'] = 'client'
        session['TotpVerified'] = True
        
        return ResponseObject()
    
    @client.post(f'{prefix}/api/signin')
    def ClientAPI_SignIn():
        data = request.get_json()
        status, msg = dashboardClients.SignIn(**data)
        if status:
            session['Email'] = data.get('Email')
            session['Role'] = 'client'
            session['TotpVerified'] = False
        return ResponseObject(status, msg)

    @client.post(f'{prefix}/api/resetPassword/generateResetToken')
    def ClientAPI_ResetPassword_GenerateResetToken():
        date = datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        emailSender = EmailSender(dashboardConfig)
        if not emailSender.ready():
            return ResponseObject(False, "We can't send you an email due to your Administrator has not setup email service. Please contact your administrator.") 
        
        data = request.get_json()
        email = data.get('Email', None)
        if not email:
            return ResponseObject(False, "Please provide a valid Email")
        
        u = dashboardClients.SignIn_UserExistence(email)
        if not u:
            return ResponseObject(False, "Please provide a valid Email")
        
        token = dashboardClients.GenerateClientPasswordResetToken(u.get('ClientID'))
        
        status, msg = emailSender.send(
            email, "[WGDashboard | Client] Reset Password",
            f"Hi {email}, \n\nIt looks like you're trying to reset your password at {date} \n\nEnter this 6 digits code on the Forgot Password to continue:\n\n{token}\n\nThis code will expire in 30 minutes for your security. If you didn’t request a password reset, you can safely ignore this email—your current password will remain unchanged.\n\nIf you need help, feel free to contact support.\n\nBest regards,\n\nWGDashboard"
        )
        
        return ResponseObject(status, msg)
    
    @client.post(f'{prefix}/api/resetPassword/validateResetToken')
    def ClientAPI_ResetPassword_ValidateResetToken():
        data = request.get_json()
        email = data.get('Email', None)
        token = data.get('Token', None)
        if not all([email, token]):
            return ResponseObject(False, "Please provide a valid Email")

        u = dashboardClients.SignIn_UserExistence(email)
        if not u:
            return ResponseObject(False, "Please provide a valid Email")
        
        return ResponseObject(status=dashboardClients.ValidateClientPasswordResetToken(u.get('ClientID'), token))
    
    @client.post(f'{prefix}/api/resetPassword')
    def ClientAPI_ResetPassword():
        data = request.get_json()
        email = data.get('Email', None)
        token = data.get('Token', None)
        password = data.get('Password', None)
        confirmPassword = data.get('ConfirmPassword', None)
        if not all([email, token, password, confirmPassword]):
            return ResponseObject(False, "Please provide a valid Email")

        u = dashboardClients.SignIn_UserExistence(email)
        if not u:
            return ResponseObject(False, "Please provide a valid Email")
        
        if not dashboardClients.ValidateClientPasswordResetToken(u.get('ClientID'), token):
            return ResponseObject(False, "Verification code is either invalid or expired")
        
        status, msg = dashboardClients.ResetClientPassword(u.get('ClientID'), password, confirmPassword)
        
        dashboardClients.RevokeClientPasswordResetToken(u.get('ClientID'), token)
        
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
        data = request.get_json()
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
        status, message = dashboardClients.UpdateClientPassword(session['ClientID'], **data)
    
        return ResponseObject(status, message)       
    
    return client