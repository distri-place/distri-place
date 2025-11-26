from fastapi import APIRouter
from pydantic import BaseModel

from app.client.manager import manager as client_manager
from app.node import get_node_instance

router = APIRouter()


class SetPixelRequest(BaseModel):
    x: int
    y: int
    color: str
    user_id: str


@router.get("/pixels")
async def get_initial_pixels():
    return {"pixels": []}


@router.post("/pixel")
async def set_pixel(request: SetPixelRequest):
    return {
        "success": await get_node_instance().set_pixel(
            request.x,
            request.y,
            request.color,
            request.user_id,
        )
    }


@router.get("/pixel/{x}/{y}")
async def get_pixel(x: int, y: int):
    return {"x": x, "y": y, "color": "#FFFFFF"}


@router.get("/status")
async def get_status():
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    return {"status": "ok"}
