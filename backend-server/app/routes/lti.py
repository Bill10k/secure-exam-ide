from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import jwt

from ..database import get_db
from .. import models, schemas

router = APIRouter(
    prefix="/api/launch",
    tags=["lti"],
)

# For Option A, this would be the shared secret. 
# For now, we will just decode without verification to get the architecture working.
# SECURITY WARNING: In production, you MUST verify the signature!
# SECRET_KEY = "your-shared-secret"

@router.post("/validate", response_model=schemas.LaunchResponse)
def validate_launch(request: schemas.LaunchRequest, db: Session = Depends(get_db)):
    try:
        # Decode the JWT without verification for now (Option A scaffolding)
        # To verify: payload = jwt.decode(request.jwt, SECRET_KEY, algorithms=["HS256"])
        payload = jwt.decode(request.jwt, options={"verify_signature": False})
        
        # Extract LTI 1.3 standard claims (these keys depend on the exact Moodle/LTI payload)
        # Using typical LTI 1.3 claims as an example:
        context_id = payload.get("https://purl.imsglobal.org/spec/lti/claim/context", {}).get("id", "unknown_context")
        resource_link_id = payload.get("https://purl.imsglobal.org/spec/lti/claim/resource_link", {}).get("id", "unknown_resource")
        user_id = payload.get("sub", "unknown_user")
        
        # Create a new exam session record
        db_session = models.ExamSession(
            context_id=context_id,
            resource_link_id=resource_link_id,
            user_id=user_id,
            raw_jwt=request.jwt,
            status="initialized"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        return schemas.LaunchResponse(
            message="Launch validated and session initialized successfully.",
            session=db_session
        )

    except jwt.DecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JWT payload")
    except Exception as e:
        # Catch-all for database errors or missing payload data during this prototype phase
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal Server Error: {str(e)}")
