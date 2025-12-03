from typing import Any

from dotenv import load_dotenv
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict

load_dotenv()


class CommaListEnvSource(EnvSettingsSource):
    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        if field_name == "PEERS" and isinstance(value, str):
            value = value.strip()
            return [p.strip() for p in value.split(",")] if value else []
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(cli_parse_args=True, env_file=".env", extra="ignore")
    PROJECT_NAME: str = "distri-place"
    PROJECT_DESCRIPTION: str = "Distri-place"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    LOG_LEVEL: str = "INFO"

    NODE_ID: str = "node-1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PEERS: list[str] | str = []

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            CommaListEnvSource(cls),
            dotenv_settings,
            file_secret_settings,
        )


settings = Settings()
