from typing import Optional, List
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_
from nova_manager.components.auth.models import Organisation, App, AuthUser
from nova_manager.core.security import hash_password, verify_password
from nova_manager.core.enums import UserRole


class AuthCRUD:
    """CRUD operations for authentication"""

    def __init__(self, db: Session):
        self.db = db

    def get_auth_user_by_email(self, email: str) -> Optional[AuthUser]:
        """Get auth user by email (emails stored normalized)"""
        return self.db.query(AuthUser).filter(AuthUser.email == email.lower()).first()

    def get_auth_user_by_id(self, auth_user_id: str) -> Optional[AuthUser]:
        """Get auth user by ID"""
        return self.db.query(AuthUser).filter(AuthUser.pid == auth_user_id).first()

    def create_organisation(self, name: str) -> Organisation:
        """Create a new organisation"""
        organisation = Organisation(
            pid=str(uuid4()),
            name=name
        )
        self.db.add(organisation)
        self.db.flush()
        self.db.refresh(organisation)
        return organisation

    def create_auth_user(
        self, 
        email: str, 
        password: str, 
        name: str, 
        organisation_id: str,
        role: UserRole = UserRole.MEMBER
    ) -> AuthUser:
        """Create a new auth user"""
        hashed_password = hash_password(password)
        
        auth_user = AuthUser(
            pid=str(uuid4()),
            email=email.lower(),  # Normalize email at storage
            password=hashed_password,
            name=name,
            organisation_id=organisation_id,
            role=role
        )
        self.db.add(auth_user)
        self.db.flush()
        self.db.refresh(auth_user)
        return auth_user

    def verify_user_password(self, user: AuthUser, password: str) -> bool:
        """Verify user's password"""
        return verify_password(password, user.password)

    def create_app(
        self, 
        name: str, 
        organisation_id: str, 
        description: Optional[str] = None
    ) -> App:
        """Create a new app"""
        app = App(
            pid=str(uuid4()),
            name=name,
            organisation_id=organisation_id
        )
        # Note: description field might need to be added to App model
        self.db.add(app)
        self.db.flush()
        self.db.refresh(app)
        return app

    def get_apps_by_organisation(self, organisation_id: str) -> List[App]:
        """Get all apps for an organisation"""
        return self.db.query(App).filter(App.organisation_id == organisation_id).all()

    def get_app_by_id(self, app_id: str, organisation_id: str) -> Optional[App]:
        """Get app by ID within organisation"""
        return self.db.query(App).filter(
            and_(
                App.pid == app_id,
                App.organisation_id == organisation_id
            )
        ).first()

    def user_has_apps(self, auth_user: AuthUser) -> bool:
        """Check if user's organisation has any apps"""
        return self.db.query(App).filter(
            App.organisation_id == auth_user.organisation_id
        ).count() > 0