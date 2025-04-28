from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import re

from app.api.deps import get_db
from app.core.config import settings
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.schemas.auth import TokenData
from app.models.user import User

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Higher rounds for better security
)

# OAuth2 scheme for token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


# Password functions
def verify_password(plain_password, hashed_password):
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """Hash a password for storage."""
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
    """
    Validate password meets minimum security requirements.

    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    """
    if len(password) < 8:
        return False

    # Check for at least one uppercase
    if not re.search(r'[A-Z]', password):
        return False

    # Check for at least one lowercase
    if not re.search(r'[a-z]', password):
        return False

    # Check for at least one digit
    if not re.search(r'\d', password):
        return False

    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False

    return True


# User functions
def get_user_by_email(db: Session, email: str):
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user with email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


# Token functions
def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time

    Returns:
        Tuple of (encoded_jwt, expiration_datetime)
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt, expire


# Dependency to get current user from token
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Get the current user from the JWT token.

    Raises:
        UnauthorizedError: If token is invalid or user not found
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        email: str = payload.get("email")

        if user_id is None:
            raise UnauthorizedError("Invalid authentication credentials")

        token_data = TokenData(user_id=int(user_id), email=email)
    except JWTError:
        raise UnauthorizedError("Invalid authentication credentials")

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise ForbiddenError("Inactive user account")

    return user


# Use this for optional authentication (some endpoints might work with or without auth)
async def get_optional_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Get the current user if authenticated, otherwise return None.
    This is useful for endpoints that work for both authenticated and non-authenticated users.
    """
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# For routes that require authentication
def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user, failing if user account is disabled."""
    if not current_user.is_active:
        raise ForbiddenError("Inactive user account")
    return current_user


# For routes that require admin privileges
def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Get current admin user, failing if user is not an admin."""
    if not current_user.is_admin:
        raise ForbiddenError("Not authorized to perform this action")
    return current_user