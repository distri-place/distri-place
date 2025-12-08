from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(cli_parse_args=True, env_file=".env", extra="ignore")
    PROJECT_NAME: str = "distri-place-loadbalancer"
    PROJECT_DESCRIPTION: str = "Distri-place Load Balancer"
    VERSION: str = "0.1.0"

    LOG_LEVEL: str = "INFO"
    PORT: int = 8000


settings = Settings()
