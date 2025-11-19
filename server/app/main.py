import argparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.ping import router as ping_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ping_router, prefix="/api/v1")


@app.get("/")
def home():
    return {"message": "Hello from server!"}


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--node-id", type=str, default="node-1", help="Node ID for this instance")
    args = parser.parse_args()

    print(f"Starting node: {args.node_id}")

    port = 8000
    if args.node_id == "node-2":
        port = 8001
    elif args.node_id == "node-3":
        port = 8002

    uvicorn.run(app, host="0.0.0.0", port=port)
