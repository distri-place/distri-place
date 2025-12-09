from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.canvas.state import Canvas
from app.dependencies import get_canvas_instance, get_node_instance
from app.raft.node import RaftNode

router = APIRouter()


class SetPixelRequest(BaseModel):
    x: int
    y: int
    color: int
    user_id: str


class SetPixelResponse(BaseModel):
    success: bool


class PixelsResponse(BaseModel):
    pixels: list[int]


@router.get("/pixels", response_model=PixelsResponse)
async def get_all_pixels(canvas: Canvas = Depends(get_canvas_instance)):
    return PixelsResponse(pixels=canvas.get_all_pixels())


@router.post("/pixel", response_model=SetPixelResponse)
async def set_pixel(request: SetPixelRequest, node: RaftNode = Depends(get_node_instance)):
    success = await node.submit_pixel(request.x, request.y, request.color)
    if not success:
        raise HTTPException(status_code=500, detail="Something went wrong")

    return SetPixelResponse(success=success)


@router.get("/status")
async def get_status():
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    return {"status": "ok"}
