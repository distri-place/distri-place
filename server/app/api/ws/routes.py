import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.client.manager import manager as client_manager
from app.dependencies import get_node_instance
from app.raft.node import RaftNode

router = APIRouter()


@router.websocket("/")
async def websocket_endpoint(ws: WebSocket, node: RaftNode = Depends(get_node_instance)):
    client_id = await client_manager.connect(ws)
    try:
        while True:
            data = json.loads(await ws.receive_text())
            if not isinstance(data, dict):
                continue
            match data.get("type", None):
                case "connect":
                    await ws.send_json(
                        {
                            "type": "connected",
                            "content": {
                                "node": {
                                    "id": node.node_id,
                                    "role": node.role.name,
                                },
                            },
                        }
                    )
                case "ping":
                    await ws.send_json(
                        {
                            "type": "pong",
                            "content": {"status": "ok"},
                        }
                    )
    except asyncio.CancelledError:
        pass
    except WebSocketDisconnect:
        pass
    finally:
        await client_manager.disconnect(client_id)
