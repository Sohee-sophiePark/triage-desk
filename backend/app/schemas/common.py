from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=100)

class APIResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: Optional[T] = None
    meta: Optional[dict] = None
    error: Optional[str] = None
