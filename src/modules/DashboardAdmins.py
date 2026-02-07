"""
Dashboard Admins - Multiple admin users management
"""
import bcrypt
import sqlalchemy as db
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, asdict


@dataclass
class AdminUser:
    """Represents an admin user"""
    id: int
    username: str
    email: str
    created_at: str
    last_login: Optional[str]
    enable_totp: bool = False
    totp_verified: bool = False
    
    def toDict(self) -> dict:
        return asdict(self)


class DashboardAdmins:
    """Manages multiple admin users in the database"""
    
    def __init__(self, engine, dbType: str = 'sqlite'):
        self.engine = engine
        self.dbType = dbType
        self.dbMetadata = db.MetaData()
        self._createTable()
    
    def _createTable(self):
        """Create the DashboardAdmins table if it doesn't exist"""
        self.adminsTable = db.Table(
            'DashboardAdmins', 
            self.dbMetadata,
            db.Column("id", db.Integer, primary_key=True, autoincrement=True),
            db.Column("username", db.String(255), nullable=False, unique=True),
            db.Column("password", db.String(255), nullable=False),
            db.Column("email", db.String(255), nullable=True, default=""),
            db.Column("enable_totp", db.Boolean, default=False),
            db.Column("totp_verified", db.Boolean, default=False),
            db.Column("totp_key", db.String(255), nullable=True),
            db.Column("created_at",
                      (db.DATETIME if self.dbType == 'sqlite' else db.TIMESTAMP),
                      server_default=db.func.now()),
            db.Column("last_login",
                      (db.DATETIME if self.dbType == 'sqlite' else db.TIMESTAMP),
                      nullable=True)
        )
        self.dbMetadata.create_all(self.engine)
    
    def _hashPassword(self, plainPassword: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(plainPassword.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _checkPassword(self, plainPassword: str, hashedPassword: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(plainPassword.encode('utf-8'), hashedPassword.encode('utf-8'))
        except Exception:
            return False
    
    def getAdminCount(self) -> int:
        """Get total number of admins"""
        with self.engine.connect() as conn:
            result = conn.execute(
                db.select(db.func.count()).select_from(self.adminsTable)
            ).scalar()
            return result or 0
    
    def getAllAdmins(self) -> List[AdminUser]:
        """Get all admin users (without passwords)"""
        admins = []
        with self.engine.connect() as conn:
            result = conn.execute(
                self.adminsTable.select().order_by(self.adminsTable.c.id)
            ).fetchall()
            
            for row in result:
                admins.append(AdminUser(
                    id=row.id,
                    username=row.username,
                    email=row.email or "",
                    created_at=row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
                    last_login=row.last_login.strftime("%Y-%m-%d %H:%M:%S") if row.last_login else None,
                    enable_totp=row.enable_totp or False,
                    totp_verified=row.totp_verified or False
                ))
        return admins
    
    def getAdminByUsername(self, username: str) -> Optional[dict]:
        """Get admin by username (includes password hash for auth)"""
        with self.engine.connect() as conn:
            result = conn.execute(
                self.adminsTable.select().where(
                    self.adminsTable.c.username == username
                )
            ).fetchone()
            
            if result:
                return {
                    'id': result.id,
                    'username': result.username,
                    'password': result.password,
                    'email': result.email or "",
                    'enable_totp': result.enable_totp or False,
                    'totp_verified': result.totp_verified or False,
                    'totp_key': result.totp_key,
                    'created_at': result.created_at,
                    'last_login': result.last_login
                }
        return None
    
    def getAdminById(self, adminId: int) -> Optional[dict]:
        """Get admin by ID"""
        with self.engine.connect() as conn:
            result = conn.execute(
                self.adminsTable.select().where(
                    self.adminsTable.c.id == adminId
                )
            ).fetchone()
            
            if result:
                return {
                    'id': result.id,
                    'username': result.username,
                    'email': result.email or "",
                    'enable_totp': result.enable_totp or False,
                    'totp_verified': result.totp_verified or False,
                    'totp_key': result.totp_key,
                    'created_at': result.created_at,
                    'last_login': result.last_login
                }
        return None
    
    def authenticate(self, username: str, password: str) -> tuple[bool, Optional[dict], str]:
        """
        Authenticate an admin user
        Returns: (success, admin_data, message)
        """
        admin = self.getAdminByUsername(username)
        
        if not admin:
            return False, None, "Invalid username or password"
        
        if not self._checkPassword(password, admin['password']):
            return False, None, "Invalid username or password"
        
        # Update last login
        self.updateLastLogin(admin['id'])
        
        return True, admin, "Login successful"
    
    def addAdmin(self, username: str, password: str, email: str = "") -> tuple[bool, str]:
        """Add a new admin user"""
        # Check if username already exists
        if self.getAdminByUsername(username):
            return False, "Username already exists"
        
        # Validate username
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        # Validate password
        if len(password) < 4:
            return False, "Password must be at least 4 characters"
        
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.insert().values(
                        username=username,
                        password=self._hashPassword(password),
                        email=email,
                        enable_totp=False,
                        totp_verified=False,
                        created_at=datetime.now()
                    )
                )
            return True, "Admin created successfully"
        except Exception as e:
            return False, f"Error creating admin: {str(e)}"
    
    def updateAdmin(self, adminId: int, username: str = None, email: str = None) -> tuple[bool, str]:
        """Update admin details (not password)"""
        admin = self.getAdminById(adminId)
        if not admin:
            return False, "Admin not found"
        
        updates = {}
        if username is not None and username != admin['username']:
            # Check if new username is taken
            existing = self.getAdminByUsername(username)
            if existing and existing['id'] != adminId:
                return False, "Username already taken"
            updates['username'] = username
        
        if email is not None:
            updates['email'] = email
        
        if not updates:
            return True, "No changes to apply"
        
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.update()
                    .where(self.adminsTable.c.id == adminId)
                    .values(**updates)
                )
            return True, "Admin updated successfully"
        except Exception as e:
            return False, f"Error updating admin: {str(e)}"
    
    def changePassword(self, adminId: int, currentPassword: str, newPassword: str) -> tuple[bool, str]:
        """Change admin password (requires current password)"""
        admin = self.getAdminById(adminId)
        if not admin:
            return False, "Admin not found"
        
        # Get full admin record with password
        with self.engine.connect() as conn:
            result = conn.execute(
                self.adminsTable.select().where(self.adminsTable.c.id == adminId)
            ).fetchone()
            
            if not result:
                return False, "Admin not found"
            
            if not self._checkPassword(currentPassword, result.password):
                return False, "Current password is incorrect"
        
        if len(newPassword) < 4:
            return False, "New password must be at least 4 characters"
        
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.update()
                    .where(self.adminsTable.c.id == adminId)
                    .values(password=self._hashPassword(newPassword))
                )
            return True, "Password changed successfully"
        except Exception as e:
            return False, f"Error changing password: {str(e)}"
    
    def resetPassword(self, adminId: int, newPassword: str) -> tuple[bool, str]:
        """Reset admin password (admin action, no current password needed)"""
        admin = self.getAdminById(adminId)
        if not admin:
            return False, "Admin not found"
        
        if len(newPassword) < 4:
            return False, "Password must be at least 4 characters"
        
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.update()
                    .where(self.adminsTable.c.id == adminId)
                    .values(password=self._hashPassword(newPassword))
                )
            return True, "Password reset successfully"
        except Exception as e:
            return False, f"Error resetting password: {str(e)}"
    
    def deleteAdmin(self, adminId: int) -> tuple[bool, str]:
        """Delete an admin user"""
        # Cannot delete if only one admin remains
        if self.getAdminCount() <= 1:
            return False, "Cannot delete the last admin"
        
        admin = self.getAdminById(adminId)
        if not admin:
            return False, "Admin not found"
        
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.delete().where(self.adminsTable.c.id == adminId)
                )
            return True, f"Admin '{admin['username']}' deleted successfully"
        except Exception as e:
            return False, f"Error deleting admin: {str(e)}"
    
    def updateLastLogin(self, adminId: int):
        """Update last login timestamp"""
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.update()
                    .where(self.adminsTable.c.id == adminId)
                    .values(last_login=datetime.now())
                )
        except Exception:
            pass  # Non-critical error
    
    def updateTOTP(self, adminId: int, enable: bool, totpKey: str = None, verified: bool = False) -> tuple[bool, str]:
        """Update TOTP settings for an admin"""
        admin = self.getAdminById(adminId)
        if not admin:
            return False, "Admin not found"
        
        try:
            updates = {
                'enable_totp': enable,
                'totp_verified': verified
            }
            if totpKey:
                updates['totp_key'] = totpKey
            
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.update()
                    .where(self.adminsTable.c.id == adminId)
                    .values(**updates)
                )
            return True, "TOTP updated successfully"
        except Exception as e:
            return False, f"Error updating TOTP: {str(e)}"
    
    def migrateFromConfig(self, username: str, passwordHash: str, 
                          enableTotp: bool = False, totpKey: str = None) -> tuple[bool, str]:
        """
        Migrate admin from wg-dashboard.ini config to database.
        Used for first-time migration.
        """
        # Check if any admins exist
        if self.getAdminCount() > 0:
            return False, "Admins already exist in database"
        
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    self.adminsTable.insert().values(
                        username=username,
                        password=passwordHash,  # Already hashed
                        email="",
                        enable_totp=enableTotp,
                        totp_verified=enableTotp,  # If TOTP was enabled, it was verified
                        totp_key=totpKey,
                        created_at=datetime.now()
                    )
                )
            return True, f"Admin '{username}' migrated successfully"
        except Exception as e:
            return False, f"Error migrating admin: {str(e)}"
