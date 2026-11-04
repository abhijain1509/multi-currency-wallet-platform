from sqlalchemy.orm import Session

from app.core.currencies import validate_currency
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import LoginRequest, ProfileUpdate, SignupRequest


class AuthError(Exception):
    """Raised for authentication/registration failures."""


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def signup(self, payload: SignupRequest) -> tuple[User, str]:
        if self.users.get_by_email(payload.email):
            raise AuthError("Email already registered")
        user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            default_currency=payload.validated_currency(),
        )
        self.users.create(user)
        self.db.commit()
        self.db.refresh(user)
        return user, create_access_token(str(user.id))

    def login(self, payload: LoginRequest) -> tuple[User, str]:
        user = self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise AuthError("Invalid email or password")
        return user, create_access_token(str(user.id))

    def update_profile(self, user: User, payload: ProfileUpdate) -> User:
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.photo_url is not None:
            user.photo_url = payload.photo_url
        if payload.default_currency is not None:
            user.default_currency = validate_currency(payload.default_currency)
        self.db.commit()
        self.db.refresh(user)
        return user
