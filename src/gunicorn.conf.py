import os.path
import dashboard, configparser
from datetime import datetime
global sqldb, cursor, DashboardConfig, WireguardConfigurations, AllPeerJobs, JobLogger
app_host, app_port = dashboard.gunicornConfig()
date = datetime.today().strftime('%Y_%m_%d_%H_%M_%S')

def post_worker_init(worker):
    dashboard.startThreads()
    dashboard.DashboardPlugins.startThreads()

worker_class = 'gthread'
workers = 1
threads = 1
bind = f"{app_host}:{app_port}"
daemon = True
pidfile = './gunicorn.pid'
wsgi_app = "dashboard:app"
accesslog = f"./log/access_{date}.log"
loglevel = "info"
capture_output = True
errorlog = f"./log/error_{date}.log"
pythonpath = "., ./modules"

print(f"[Gunicorn] WGDashboard w/ Gunicorn will be running on {bind}", flush=True)
print(f"[Gunicorn] Access log file is at {accesslog}", flush=True)
print(f"[Gunicorn] Error log file is at {errorlog}", flush=True)