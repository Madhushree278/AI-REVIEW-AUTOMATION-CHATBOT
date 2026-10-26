from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User, UserRole, InternProfile, AuditLog
from app.schemas.schemas import UserCreate, UserLogin, UserOut, Token
from app.core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=UserOut)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if email already registered
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Validate role
    role_str = user_in.role.upper()
    if role_str not in [UserRole.ADMIN.value, UserRole.MENTOR.value, UserRole.INTERN.value]:
        role_str = UserRole.INTERN.value

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=role_str,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Log audit
    audit = AuditLog(
        action="USER_REGISTERED",
        actor_id=user.id,
        details=f"Registered account with role {role_str} for {user.email}"
    )
    db.add(audit)
    db.commit()

    return user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated."
        )

    intern_id = None
    if user.role == UserRole.INTERN.value:
        profile = db.query(InternProfile).filter(InternProfile.user_id == user.id).first()
        if profile:
            intern_id = profile.intern_id

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user,
        intern_id=intern_id
    )

@router.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    intern_id = None
    if user.role == UserRole.INTERN.value:
        profile = db.query(InternProfile).filter(InternProfile.user_id == user.id).first()
        if profile:
            intern_id = profile.intern_id

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user,
        intern_id=intern_id
    )

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    intern_profile = None
    if current_user.role == UserRole.INTERN.value:
        intern_profile = db.query(InternProfile).filter(InternProfile.user_id == current_user.id).first()
    
    return {
        "user": current_user,
        "intern_profile": intern_profile
    }
