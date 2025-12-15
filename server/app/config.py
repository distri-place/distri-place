from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas import PeerNode

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

    peers_string: str = Field(
        default="node-2:node-2:8000:8001,node-2:node-3:8000:8001",
        exclude=True,
        alias="PEERS",
    )

    @computed_field
    def PEERS(self) -> list[PeerNode]:
        result: list[PeerNode] = []
        if not self.peers_string:
            return result

        for peer in self.peers_string.split(","):
            peer = peer.strip()
            if ":" in peer:
                parts = peer.split(":")
                if len(parts) == 4:
                    node_id, host, http_port, grpc_port = parts
                    result.append(
                        PeerNode(
                            node_id=node_id,
                            host=host,
                            http_port=int(http_port),
                            grpc_port=int(grpc_port),
                        )
                    )
                elif len(parts) == 2:
                    node_id, host = parts
                    result.append(
                        PeerNode(node_id=node_id, host=host, http_port=8000, grpc_port=8001)
                    )
                else:
                    result.append(PeerNode(node_id=peer, host=peer, http_port=8000, grpc_port=8001))
            else:
                result.append(PeerNode(node_id=peer, host=peer, http_port=8000, grpc_port=8001))
        return result


settings = Settings()
