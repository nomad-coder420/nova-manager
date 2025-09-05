from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import BaseModel

from nova_manager.core.config import JWT_SECRET_KEY
from nova_manager.core.enums import UserRole

# Password hashing with bcrypt (12 rounds for security)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30


class AuthContext(BaseModel):
    """Auth context extracted from JWT token"""

    auth_user_id: str
    organisation_id: str
    app_id: Optional[str] = None  # Can be None before app creation
    email: str
    role: UserRole  # User role in the organization


class SDKAuthContext(BaseModel):
    """SDK auth context extracted from JWT token"""

    organisation_id: str
    app_id: str


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with salt"""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""

    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token (longer expiry)"""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update(
        {"exp": expire, "iat": datetime.now(timezone.utc), "type": "refresh"}
    )
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_token_ignore_expiry(token: str) -> dict:
    """Decode JWT token ignoring expiration (for refresh operations)"""

    try:
        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_auth_context(payload: dict) -> AuthContext:
    """Create AuthContext from JWT payload"""

    return AuthContext(
        auth_user_id=payload.get("auth_user_id", ""),
        organisation_id=payload.get("organisation_id", ""),
        app_id=payload.get("app_id", ""),
        email=payload.get("email", ""),
        role=payload.get("role", "member"),
    )


# SDK API Key Functions for Client SDK Authentication
def create_sdk_api_key(data: dict) -> str:
    """
    Create a deterministic SDK API key for client SDK authentication.
    Same data will always generate the same API key.

    Args:
        data: Dict containing organisation_id and app_id
              Example: {"organisation_id": "uuid", "app_id": "uuid"}

    Returns:
        SDK API key in format: nova_sk_<jwt_token>
    """

    to_encode = data.copy()
    to_encode.update({"type": "sdk_api_key"})

    # Create static JWT (no timestamps for deterministic behavior)
    token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return f"nova_sk_{token}"


def validate_sdk_api_key(api_key: str) -> dict:
    """
    Validate an SDK API key and extract organisation_id and app_id.
    Ultra-fast validation with no database lookups required.

    Args:
        api_key: The SDK API key to validate

    Returns:
        Dict with organisation_id and app_id if valid, None if invalid
    """

    try:
        # Check API key format
        if not api_key.startswith("nova_sk_"):
            raise Exception("Invalid SDK API key")

        # Extract JWT token
        token = api_key[8:]  # Remove "nova_sk_" prefix

        # Decode JWT
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

        # Verify this is an SDK API key token
        if payload.get("type") != "sdk_api_key":
            raise Exception("Invalid SDK API key")

        # Return extracted data
        return payload

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid SDK API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_sdk_auth_context(payload: dict) -> SDKAuthContext:
    """
    Create SDKAuthContext for SDK API key authentication.

    Args:
        payload: Dict containing organisation_id and app_id

    Returns:
        SDKAuthContext configured for SDK authentication
    """

    return SDKAuthContext(
        organisation_id=payload.get("organisation_id", ""),
        app_id=payload.get("app_id", ""),
    )
