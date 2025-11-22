from fastapi import APIRouter

router = APIRouter()

@router.get("/api/v1/users/test")
async def test():
    return {"message": "Simple router works!"}