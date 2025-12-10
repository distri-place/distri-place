from pydantic import BaseModel, Field


class PeerNode(BaseModel):
    node_id: str = Field(...)
    host: str = Field(...)
    http_port: int = Field(...)
    grpc_port: int = Field(...)

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.http_port}"

    @property
    def grpc_address(self) -> str:
        return f"{self.host}:{self.grpc_port}"
