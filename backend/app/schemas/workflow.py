"""Validated workflow request and response models."""
from typing import Literal

from pydantic import BaseModel, Field


class PrepareWorkflowRequest(BaseModel):
    mode: Literal["corporate", "student"]
    source_text: str = Field(min_length=1, max_length=500_000)


class WorkflowStatus(BaseModel):
    status: str
    mode: Literal["corporate", "student"]
    model_status: str
    message: str
