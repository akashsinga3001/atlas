# backend/app/schemas/base.py
"""
Base Pydantic schema for the application. All other schemas should inherit from this base class to ensure consistency and to include any common configuration or validation logic.
"""

from typing import Optional, Any, List, Dict, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID

T = TypeVar("T")


class BaseResponse(BaseModel):

    class Config:
        from_attributes = True
        json_encoders = { datetime: lambda v: v.isoformat(), UUID: lambda v: str(v) }


class Pagination(BaseModel):
    total: int = Field(..., description="Total number of items available")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Indicates if there is a next page")
    has_prev: bool = Field(..., description="Indicates if there is a previous page")

    @classmethod
    def create(cls, total: int, page: int, per_page: int) -> "Pagination":
        pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(total=total, page=page, per_page=per_page, pages=pages, has_next=page < pages, has_prev=page > 1)


class PaginatedResponse(BaseResponse, Generic[T]):
    success: bool = Field(..., description="Indicates if the request was successful")
    message: str = Field(None, description="Optional message providing additional information about the response")
    data: List[T] = Field(..., description="List of items for the current page")
    pagination: Pagination = Field(..., description="Pagination metadata for the response")
    errors: Optional[Dict[str, Any]] = Field(None, description="Optional dictionary containing error details if the request was not successful")

    class Config:
        json_schema_extra = { "example": { "success": True, "message": "Data retrieved successfully", "data": [], "pagination": { "total": 100, "page": 1, "per_page": 10, "pages": 10, "has_next": True, "has_prev": False }, "errors": None } }


class APIResponse(BaseResponse, Generic[T]):
    success: bool = Field(..., description="Indicates if the request was successful")
    message: str = Field(None, description="Optional message providing additional information about the response")
    data: Optional[T] = Field(None, description="The main data payload of the response")
    errors: Optional[Dict[str, Any]] = Field(None, description="Optional dictionary containing error details if the request was not successful")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional dictionary containing additional metadata about the response")

    class Config:
        json_schema_extra = { "example": { "success": True, "message": "Operation completed successfully", "data": None, "errors": None, "meta": None } }


class ErrorResponse(BaseResponse):
    success: bool = Field(False, description="Indicates that the request was not successful")
    message: str = Field(..., description="A message describing the error that occurred")
    errors: Optional[Dict[str, Any]] = Field(None, description="Optional dictionary containing additional error details")

    class Config:
        json_schema_extra = { "example": { "success": False, "message": "An error occurred while processing the request", "errors": { "field_name": "Error details for this field"} } }


class SuccessResponse(BaseResponse):
    success: bool = Field(True, description="Indicates that the request was successful")
    message: str = Field(..., description="A message describing the successful operation")
    data: Optional[Any] = Field(None, description="Optional data payload containing the result of the successful operation")

    class Config:
        json_schema_extra = { "example": { "success": True, "message": "Operation completed successfully", "data": { "key": "value"} } }
