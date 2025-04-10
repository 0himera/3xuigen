from fastapi import APIRouter
from app.utils.reality_keys import generate_short_id

router = APIRouter()



@router.get("/short-id")
async def get_short_id(length: int = 8):
    """
    Generate a short ID for REALITY protocol
    """
    return {"short_id": generate_short_id(length)}
