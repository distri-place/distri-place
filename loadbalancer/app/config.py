from dotenv import load_dotenv
from pydantic import Field, field_validator
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
    SERVERS: list[ServerNode] = Field(
        default_factory=lambda: [
            ServerNode(host="node-1", port=8000),
            ServerNode(host="node-2", port=8000),
            ServerNode(host="node-3", port=8000),
        ]
    )

    @field_validator("SERVERS", mode="before")
    @classmethod
    def parse_servers(cls, v):
        if isinstance(v, str):
            servers = []
            for server in v.split(","):
                server = server.strip()
                if ":" in server:
                    host, port = server.split(":", 1)
                    servers.append(ServerNode(host=host.strip(), port=int(port.strip())))
            return servers
        return v


settings = Settings()
