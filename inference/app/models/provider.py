from pydantic import BaseModel


class ProviderConfig(BaseModel):
    provider: str
    available: bool
    requires_api_key: bool
    is_local: bool


class ProviderModel(BaseModel):
    id: str
    name: str
    display_name: str
    supported_actions: list[str]
