from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "distri-place"
    PROJECT_DESCRIPTION: str = "Distri-place"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    LOG_LEVEL: str = "INFO"

    class ConfigDict:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
