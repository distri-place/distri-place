import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.client.manager import manager as client_manager
from app.node import get_node_instance

router = APIRouter()

@router.websocket("/")
async def websocket_endpoint(ws: WebSocket):
    client_id = await client_manager.connect(ws)
    node_instance = get_node_instance()
    try:
        while True:
            data = json.loads(await ws.receive_text())
            if not isinstance(data, dict):
                continue
            match data.get("type", None):
                case 'connect':
                    await ws.send_json({
                        "type": "connected",
                        "content": {
                            "node": {
                                "id": node_instance.node_id,
                                "role": "leader" if node_instance.is_leader() else "replica",
                            },
                            "canvas": node_instance.encode_image_to_base64_png()
                        },
                    })
                case 'ping':
                    await ws.send_json({
                        "type": "pong",
                        "content": {
                            "status": await node_instance.get_status()
                        },
                    })
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        await client_manager.disconnect(client_id)