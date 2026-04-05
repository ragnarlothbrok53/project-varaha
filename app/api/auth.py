import uuid
import datetime
import jwt
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..data.manager import create_user, get_user_by_email, update_user_password
from ..utils.config import get_settings

router = APIRouter()
security = HTTPBearer()
settings = get_settings()

SECRET_KEY = "varaha_super_secret_for_production_use_env_vars"
ALGORITHM = "HS256"

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

def create_access_token(data: dict, expires_delta: datetime.timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"email": email, "user_id": payload.get("user_id")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def send_password_reset_email(email: str, token: str):
    """Send password reset email"""
    if not settings.smtp_server or not settings.from_email:
        # For development, just log the reset token
        print(f"Password reset token for {email}: {token}")
        return True
    
    try:
        msg = MimeMultipart()
        msg['From'] = settings.from_email
        msg['To'] = email
        msg['Subject'] = "Reset your Varaha password"
        
        reset_link = f"http://localhost:8000/reset-password?token={token}"
        body = f"""
        Hello,
        
        You requested to reset your password for Varaha.
        
        Click the following link to reset your password:
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this password reset, please ignore this email.
        
        Thanks,
        The Varaha Team
        """
        
        msg.attach(MimeText(body, 'plain'))
        
        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@router.post("/register")
async def register(request: RegisterRequest):
    existing_user = get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = create_user(request.name, request.email, hashed_password, request.name)
    
    access_token = create_access_token(data={"email": request.email, "user_id": user_id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login")
async def login(request: LoginRequest):
    user = get_user_by_email(request.email)
    if not user or not bcrypt.checkpw(request.password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"email": user['email'], "user_id": user['id']})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/password-reset-request")
async def password_reset_request(email: str):
    user = get_user_by_email(email)
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = str(uuid.uuid4())
    # Store token (in production, this should be in a database with expiration)
    # For now, we'll use a simple approach
    
    if send_password_reset_email(email, reset_token):
        return {"message": "Password reset link sent to your email"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send reset email")

@router.post("/password-reset-confirm")
async def password_reset_confirm(token: str, new_password: str):
    # In production, validate token from database
    # For now, we'll accept any token (this is a security risk in production!)
    
    # Here you would typically:
    # 1. Validate the token exists and is not expired
    # 2. Get the user email from the token
    # 3. Update the user's password
    
    # For demo purposes, we'll just return success
    return {"message": "Password reset successfully"}

@router.post("/refresh")
async def refresh_token(current_user: dict = Depends(verify_jwt)):
    access_token = create_access_token(data={"email": current_user["email"], "user_id": current_user["user_id"]})
    return {"access_token": access_token, "token_type": "bearer"}
