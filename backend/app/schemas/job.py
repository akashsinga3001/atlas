# backend/app/schemas/job.py

from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class JobTriggerRequest(BaseModel):
    """ Schema for triggering a job. """
    job_name: str = Field(..., description="The name of the job to be triggered")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional dictionary containing parameters for the job")
