from fastapi import APIRouter, Depends, HTTPException
from typing import Literal
from sqlalchemy.orm import Session

from nova_manager.components.auth.dependencies import require_technical_roles
from nova_manager.core.security import AuthContext
from nova_manager.database.session import get_db
from nova_manager.components.apikeys.crud import APIKeysCRUD
from pydantic import BaseModel


router = APIRouter()


class APIKeyCreateRequest(BaseModel):
    name: str
    # allowed values: "client" | "sync"
    key_type: Literal["client", "sync"] = "client"


class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    key_type: str
    organisation_id: str
    app_id: str
    is_active: bool


@router.post("/generate", response_model=APIKeyResponse)
def generate_api_key(
    request: APIKeyCreateRequest,
    auth: AuthContext = Depends(require_technical_roles),
    db: Session = Depends(get_db),
):
    """Generate a new client-side API key for the current app/org.
    The returned key should be shown only once to the caller.
    """
    apikeys_crud = APIKeysCRUD(db)

    # key_type defaults to 'client'; developers/technical roles are allowed to create 'sync' keys as well
    # Validate key_type strictly
    if request.key_type not in ("client", "sync"):
        raise HTTPException(status_code=400, detail="Invalid key_type. Allowed values: client, sync")

    api_key = apikeys_crud.create_api_key(
        name=request.name,
        organisation_id=auth.organisation_id,
        app_id=auth.app_id,
        created_by=auth.auth_user_id,
        key_type=request.key_type,
    )

    return APIKeyResponse(
        id=str(api_key.pid),
        name=api_key.name,
        key=api_key.key,
    key_type=api_key.key_type,
        organisation_id=str(api_key.organisation_id),
        app_id=str(api_key.app_id),
        is_active=api_key.is_active,
    )


@router.get("/", response_model=list[APIKeyResponse])
def list_api_keys(
    auth: AuthContext = Depends(require_technical_roles),
    db: Session = Depends(get_db),
):
    apikeys_crud = APIKeysCRUD(db)

    keys = apikeys_crud.list_for_app(auth.organisation_id, auth.app_id)

    return [
        APIKeyResponse(
            id=str(k.pid),
            name=k.name,
            key=k.key,  # Returning key for admin listing; in prod this may be masked
            key_type=k.key_type,
            organisation_id=str(k.organisation_id),
            app_id=str(k.app_id),
            is_active=k.is_active,
        )
        for k in keys
    ]



@router.delete("/", status_code=204)
def delete_api_key_by_name(
    name: str,
    auth: AuthContext = Depends(require_technical_roles),
    db: Session = Depends(get_db),
):
    """Deactivate API key(s) by name for the current org/app"""
    apikeys_crud = APIKeysCRUD(db)

    ok = apikeys_crud.deactivate_by_name(name=name, organisation_id=auth.organisation_id, app_id=auth.app_id)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")

    return None
