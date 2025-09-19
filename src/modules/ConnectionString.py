# ConnectionString.py
import configparser
import os
from sqlalchemy_utils import database_exists, create_database

# Read and parse the INI file once at startup
parser = configparser.ConfigParser(strict=False)
parser.read("wg-dashboard.ini")

# Ensure SQLite folder exists
SQLITE_PATH = "db"
os.makedirs(SQLITE_PATH, exist_ok=True)

DEFAULT_DB = "wgdashboard"
DEFAULT_LOG_DB = "wgdashboard_log"
DEFAULT_JOB_DB = "wgdashboard_job"

def ConnectionString(database_name: str) -> str:
    """
    Returns a SQLAlchemy-compatible connection string for the chosen database.
    Creates the database if it doesn't exist.
    """
    db_type = parser.get("Database", "type")
    db_prefix = parser.get("Database", "prefix")
    database_name = f"{db_prefix}{database_name}"

    if db_type == "postgresql":
        username = parser.get("Database", "username")
        password = parser.get("Database", "password")
        host = parser.get("Database", "host")
        cn = f"postgresql+psycopg://{username}:{password}@{host}/{database_name}"
    elif db_type == "mysql":
        username = parser.get("Database", "username")
        password = parser.get("Database", "password")
        host = parser.get("Database", "host")
        cn = f"mysql+pymysql://{username}:{password}@{host}/{database_name}"
    else:
        cn = f"sqlite:///{os.path.join(SQLITE_PATH, f'{database_name}.db')}"

    # Ensure database exists
    if not database_exists(cn):
        create_database(cn)

    return cn