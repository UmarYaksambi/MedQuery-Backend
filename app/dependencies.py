from .database import SessionLocal
from fastapi import Depends, HTTPException, status
from typing import List
from . import auth_utils
from .auth_utils import role_required, get_current_user

def role_required(allowed_roles: List[str]):
    """
    Dependency to check if the current user has one of the allowed roles.
    """
    def role_checker(current_user = Depends(auth_utils.get_current_user)):
        # Check if the user's role is in the list of allowed roles
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the necessary permissions to perform this action."
            )
        return current_user
    
    return role_checker

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()