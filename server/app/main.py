
if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    print(f"Initializing node: {settings.NODE_ID} on port {settings.PORT} with peers: {settings.PEERS}")

    uvicorn.run("app.app:app", host=settings.HOST, port=settings.PORT, loop="asyncio", reload=True)
