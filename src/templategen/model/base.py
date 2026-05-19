"""Common Pydantic base — extra='allow' is non-negotiable for round-trip fidelity."""

from pydantic import BaseModel, ConfigDict


class RmgModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
