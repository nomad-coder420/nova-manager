from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from nova_manager.core.security import verify_token, decode_token_ignore_expiry, create_auth_context, AuthContext

# OAuth2 scheme for extracting Bearer tokens
security = HTTPBearer()


async def get_current_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> AuthContext:
    """Extract and validate auth context from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Ensure this is an access token (not refresh token)
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cannot be used for API access",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return create_auth_context(payload)


async def require_org_context(
    auth: AuthContext = Depends(get_current_auth)
) -> AuthContext:
    """Require user to have organisation context (for org-level operations)"""
    if not auth.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation context required"
        )
    return auth


async def require_app_context(
    auth: AuthContext = Depends(get_current_auth)
) -> AuthContext:
    """Require user to have app context (for app-level operations)"""
    if not auth.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation context required"
        )
    
    if not auth.app_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="App context required. Please create an app first."
        )
    
    return auth


async def get_current_auth_ignore_expiry(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[AuthContext]:
    """Extract auth context from JWT token ignoring expiration (for refresh operations)"""
    try:
        token = credentials.credentials
        payload = decode_token_ignore_expiry(token)
        
        # Ensure this is an access token (not refresh token)
        if payload.get("type") == "refresh":
            return None
        
        return create_auth_context(payload)
    except:
        # If token is invalid, return None instead of raising exception
        return None