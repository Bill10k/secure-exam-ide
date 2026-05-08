from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt

# WARNING: In a true production environment, load this from an .env file
SECRET_KEY = "secure-exam-ide-super-secret-key-123!"
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Bearer token from the Authorization header.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

async def verify_admin_role(user_payload: dict = Depends(get_current_user_token)):
    """
    Verifies that the decoded JWT token grants Admin privileges.
    Checks if 'role_type' == 2 (Admin).
    """
    role_type = user_payload.get("role_type")
    
    if role_type != 2:
        raise HTTPException(status_code=403, detail="Admin privileges required to perform this action.")
        
    return user_payload
