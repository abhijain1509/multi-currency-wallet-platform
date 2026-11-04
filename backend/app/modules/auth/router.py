import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    LoginRequest,
    ProfileUpdate,
    SignupRequest,
    TokenResponse,
    UserOut,
)
from app.modules.auth.service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# Server-controlled extension per allowed image type (never trust the filename).
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest, response: Response, db: Session = Depends(get_db)
) -> TokenResponse:
    try:
        user, token = AuthService(db).signup(payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> TokenResponse:
    try:
        user, token = AuthService(db).login(payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response) -> dict:
    response.delete_cookie(settings.cookie_name, path="/")
    return {"status": "logged out"}


@router.get("/profile", response_model=UserOut)
def get_profile(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)


@router.patch("/profile", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    try:
        user = AuthService(db).update_profile(current, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return UserOut.model_validate(user)


@router.post("/profile/photo", response_model=UserOut)
async def upload_photo(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    ext = _ALLOWED_IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WebP or GIF images are allowed",
        )
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {settings.max_upload_bytes // (1024 * 1024)} MB limit",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / filename).write_bytes(data)

    url = f"{settings.media_url_prefix}/{filename}"
    user = AuthService(db).update_profile(current, ProfileUpdate(photo_url=url))
    return UserOut.model_validate(user)
