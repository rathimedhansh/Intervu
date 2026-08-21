from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ParsedResumeRead(BaseModel):
    skills: list[str] = []
    projects: list[str] = []
    education: list[str] = []
    experience: list[str] = []
    technologies: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class ResumeAnalysisRead(BaseModel):
    analyzer: str
    summary: str
    strong_areas: list[str]
    missing_details: list[str]
    key_projects: list[str]
    key_technologies: list[str]

    model_config = ConfigDict(from_attributes=True)


class ResumeRead(BaseModel):
    id: int
    original_filename: str
    size_bytes: int
    created_at: datetime
    parsed: ParsedResumeRead
    analysis: ResumeAnalysisRead

    model_config = ConfigDict(from_attributes=True)
