from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.client.routes import router as client_router
from app.api.ws.routes import router as ws_router
from app.dependencies import get_node


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(client_router, prefix="/client")
    app.include_router(ws_router, prefix="/ws")

    @app.get("/")
    def home(node=Depends(get_node)):
        """Health check endpoint."""
        return {
            "message": f"Hello from {node.node_id}!",
            "node_id": node.node_id,
            "status": "active",
        }

    return app


# Create the app instance for uvicorn
app = create_app()
