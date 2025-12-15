from dotenv import load_dotenv
from pydantic import Field, computed_field
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
    RELOAD: bool = False

    servers_string: str = Field(
        default="node-1:8000,node-2:8000,node-3:8000",
        exclude=True,
        alias="SERVERS",
    )

    @computed_field
    def SERVERS(self) -> list[ServerNode]:
        result = []
        for server in self.servers_string.split(","):
            server = server.strip()
            if ":" in server:
                host, port = server.split(":")
                result.append(ServerNode(host=host, port=int(port)))
            else:
                result.append(ServerNode(host=server, port=8000))
        return result


settings = Settings()
