from datetime import datetime
import secrets
from typing import Optional
from sqlalchemy.orm import Session

from nova_manager.components.apikeys.models import APIKey


class APIKeysCRUD:
    def __init__(self, db: Session):
        self.db = db

    def generate_key(self) -> str:
        # Generate a URL-safe token; in prod consider prefixing and storing only hash
        return secrets.token_urlsafe(32)

    def create_api_key(self, name: str, organisation_id, app_id, created_by, key_type: str = "client") -> APIKey:
        key_value = self.generate_key()

        api_key = APIKey(
            name=name,
            key=key_value,
            organisation_id=organisation_id,
            app_id=app_id,
            key_type=key_type,
            is_active=True,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return api_key

    def get_by_key(self, key: str) -> Optional[APIKey]:
        return self.db.query(APIKey).filter(APIKey.key == key, APIKey.is_active == True).one_or_none()

    def list_for_app(self, organisation_id, app_id):
        # Return only active API keys for the given organisation/app
        return (
            self.db.query(APIKey)
            .filter(
                APIKey.organisation_id == organisation_id,
                APIKey.app_id == app_id,
                APIKey.is_active == True,
            )
            .all()
        )

    def deactivate_by_name(self, name: str, organisation_id, app_id) -> bool:
        """Soft-delete (deactivate) API keys with the given name for the org/app. Returns True if any rows updated."""
        keys = self.db.query(APIKey).filter(
            APIKey.name == name,
            APIKey.organisation_id == organisation_id,
            APIKey.app_id == app_id,
            APIKey.is_active == True,
        ).all()

        if not keys:
            return False

        for k in keys:
            k.is_active = False
            self.db.add(k)

        self.db.commit()
        return True
