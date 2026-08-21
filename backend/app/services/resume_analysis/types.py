from dataclasses import dataclass
from typing import Literal

Analyzer = Literal["mock", "anthropic"]


@dataclass
class ResumeAnalysis:
    analyzer: Analyzer
    summary: str
    strong_areas: list[str]
    missing_details: list[str]
    key_projects: list[str]
    key_technologies: list[str]

    def to_dict(self) -> dict:
        return {
            "analyzer": self.analyzer,
            "summary": self.summary,
            "strong_areas": self.strong_areas,
            "missing_details": self.missing_details,
            "key_projects": self.key_projects,
            "key_technologies": self.key_technologies,
        }
