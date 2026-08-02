from fastapi import APIRouter

router = APIRouter(prefix="/verification", tags=["Verification"])

@router.get("/")
def verify():
    return {"message": "Verification router working"}