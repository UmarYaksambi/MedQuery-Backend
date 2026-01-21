from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from datetime import datetime
from bson import ObjectId
from .. import schemas, dependencies
from ..database import mongo_db
from ..auth_utils import role_required # Import the security dependency

router = APIRouter(prefix="/notes", tags=["Clinical Notes"])

@router.post("/", 
             response_model=dict, 
             dependencies=[Depends(role_required(["doctor", "admin"]))])
async def create_note(note: schemas.ClinicalNoteCreate):
    """
    Stores an unstructured note in MongoDB.
    RESTRICTED: Doctors and Admins only.
    """
    try:
        note_dict = note.model_dump()
        note_dict["timestamp"] = datetime.utcnow()
        
        result = await mongo_db.notes.insert_one(note_dict)
        return {"id": str(result.inserted_id), "status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save note to MongoDB: {str(e)}"
        )

@router.get("/{subject_id}", 
            response_model=List[schemas.ClinicalNote], 
            dependencies=[Depends(role_required(["doctor", "admin"]))])
async def get_patient_notes(subject_id: int):
    """
    Retrieves all documents for a specific patient from MongoDB.
    RESTRICTED: Doctors and Admins only.
    """
    try:
        cursor = mongo_db.notes.find({"subject_id": subject_id})
        notes = await cursor.to_list(length=100)
        
        # Convert MongoDB _id (ObjectId) to string for the Pydantic model
        return [
            {**note, "id": str(note["_id"])} for note in notes
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving clinical notes."
        )