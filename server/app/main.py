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
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
