import uvicorn

from app.config import settings
from app.utils import logger as _  # noqa: F401 - Import to configure logging


def main():
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.RELOAD,
    )


if __name__ == "__main__":
    main()
