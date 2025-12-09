from pydantic import BaseModel, Field


class ServerNode(BaseModel):
    host: str = Field(...)
    port: int = Field(...)

    @property
    def http_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws/"
