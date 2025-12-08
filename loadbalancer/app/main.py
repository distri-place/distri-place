import uvicorn

from app.config import settings
from app.utils import logger as _  # noqa: F401 - Import to configure logging


def main():
    from app.utils.logger import LOGGING_CONFIG

    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=settings.PORT,
        log_config=LOGGING_CONFIG,
        reload=settings.RELOAD,
    )


if __name__ == "__main__":
    main()
