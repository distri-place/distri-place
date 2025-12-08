from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(cli_parse_args=True, env_file=".env", extra="ignore")
    PROJECT_NAME: str = "distri-place"
    PROJECT_DESCRIPTION: str = "Distri-place"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    LOG_LEVEL: str = "INFO"
    RELOAD: bool = False

    NODE_ID: str = "node-1"
    HOST: str = "0.0.0.0"
    HTTP_PORT: int = 8000
    GRPC_PORT: int = 50051
    PEERS: list[str] | str = []


settings = Settings()
