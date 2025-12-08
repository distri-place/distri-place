from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas import ServerNode

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(cli_parse_args=False, env_file=".env", extra="ignore")
    PROJECT_NAME: str = "distri-place-loadbalancer"
    PROJECT_DESCRIPTION: str = "Distri-place Load Balancer"
    VERSION: str = "0.1.0"

    LOG_LEVEL: str = "INFO"
    PORT: int = 8000


settings = Settings()


DEFAULT_SERVERS = [
    ServerNode(host="localhost", port=8001),
    ServerNode(host="localhost", port=8002),
    ServerNode(host="localhost", port=8003),
]

