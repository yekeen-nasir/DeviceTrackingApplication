"""Device enrollment endpoints."""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import uuid4

from libs.core.storage import Device, AgentCredential, EnrollmentToken, User
from libs.core.models import Platform, EnrollmentRequest, EnrollmentResponse
from libs.core.crypto import generate_token, generate_enrollment_token
from libs.core.logging import setup_logging
from ..db import get_db
from ..auth import get_current_user, get_admin_user

logger = setup_logging("tracker-server.routers.enroll")

router = APIRouter()

class CreateTokenRequest(BaseModel):
    expires_minutes: int = 10

class CreateTokenResponse(BaseModel):
    token: str
    expires_at: datetime

@router.post("/tokens", response_model=CreateTokenResponse)
async def create_enrollment_token(
    request: CreateTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a one-time enrollment token."""
    token = generate_enrollment_token()
    expires_at = datetime.utcnow() + timedelta(minutes=request.expires_minutes)
    
    # Store token
    enrollment_token = EnrollmentToken(
        token=token,
        owner_id=current_user.id,
        expires_at=expires_at,
        used=False
    )
    db.add(enrollment_token)
    db.commit()
    
    logger.info(f"Enrollment token created by {current_user.email}: {token}")
    
    return CreateTokenResponse(token=token, expires_at=expires_at)

@router.post("/claim", response_model=EnrollmentResponse)
async def claim_enrollment_token(
    request: EnrollmentRequest,
    db: Session = Depends(get_db)
):
    """Claim enrollment token and enroll device."""
    # Validate token
    token_record = db.query(EnrollmentToken).filter(
        EnrollmentToken.token == request.token,
        EnrollmentToken.used == False,
        EnrollmentToken.expires_at > datetime.utcnow()
    ).first()
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired enrollment token"
        )
    
    # Mark token as used
    token_record.used = True
    
    # Create device
    device = Device(
        id=uuid4(),
        owner_id=token_record.owner_id,
        display_name=request.display_name,
        platform=request.platform,
        enrolled_at=datetime.utcnow()
    )
    db.add(device)
    
    # Create device credentials
    device_token = generate_token(32)
    credential = AgentCredential(
        id=uuid4(),
        device_id=device.id,
        public_key=request.pubkey,
        device_token=device_token,
        issued_at=datetime.utcnow()
    )
    db.add(credential)
    
    db.commit()
    
    logger.info(f"Device enrolled: {device.id} ({request.display_name})")
    
    return EnrollmentResponse(
        device_id=device.id,
        device_token=device_token,
        issued_at=credential.issued_at,
        expires_at=None  # Tokens don't expire by default
    )