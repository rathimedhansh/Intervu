import re
from dataclasses import dataclass, field

# Heuristic, keyword-based resume parser. PDF text extraction loses layout
# (columns, font-size cues), so this works line-by-line off common section
# header wording rather than anything more structural. Good enough to drive
# question generation; not a substitute for a real resume-parsing model.

_SECTION_HEADERS: dict[str, tuple[str, ...]] = {
    "skills": ("skills", "technical skills", "core competencies", "key skills"),
    "projects": ("projects", "personal projects", "key projects", "academic projects"),
    "education": ("education", "academic background", "academic history"),
    "experience": (
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
    ),
    "technologies": (
        "technologies",
        "tech stack",
        "tools & technologies",
        "tools and technologies",
        "languages & tools",
        "languages and tools",
    ),
}

_BULLET_PREFIX = re.compile(r"^[\-\*•●▪◦›»]+\s*")

_KNOWN_TECHNOLOGIES = (
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby",
    "PHP", "Swift", "Kotlin", "Scala", "SQL", "React", "Angular", "Vue", "Next.js",
    "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring", "Spring Boot",
    ".NET", "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "GraphQL", "REST",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "CI/CD", "Git",
    "Jenkins", "Kafka", "RabbitMQ", "Spark", "Hadoop", "Pandas", "NumPy",
    "TensorFlow", "PyTorch", "scikit-learn", "Tailwind", "HTML", "CSS", "Linux",
)


@dataclass
class ParsedResume:
    skills: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    experience: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "projects": self.projects,
            "education": self.education,
            "experience": self.experience,
            "technologies": self.technologies,
        }


def _normalize_header(line: str) -> str | None:
    candidate = line.strip().strip(":").strip().lower()
    if not candidate or len(candidate) > 40:
        return None
    for section, headers in _SECTION_HEADERS.items():
        if candidate in headers:
            return section
    return None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _guess_technologies(text: str) -> list[str]:
    lowered = text.lower()
    return [tech for tech in _KNOWN_TECHNOLOGIES if tech.lower() in lowered][:20]


def parse_sections(text: str) -> ParsedResume:
    buckets: dict[str, list[str]] = {key: [] for key in _SECTION_HEADERS}
    current: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header = _normalize_header(line)
        if header:
            current = header
            continue

        if current is None:
            continue

        cleaned = _BULLET_PREFIX.sub("", line).strip()
        if cleaned:
            buckets[current].append(cleaned)

    parsed = ParsedResume(
        skills=_dedupe(buckets["skills"]),
        projects=_dedupe(buckets["projects"]),
        education=_dedupe(buckets["education"]),
        experience=_dedupe(buckets["experience"]),
        technologies=_dedupe(buckets["technologies"]),
    )

    if not parsed.technologies:
        parsed.technologies = _guess_technologies(text)

    return parsed
