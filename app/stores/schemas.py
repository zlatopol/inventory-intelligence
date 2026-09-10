from pydantic import BaseModel, ConfigDict


class StoreCreate(BaseModel):

    name: str


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
