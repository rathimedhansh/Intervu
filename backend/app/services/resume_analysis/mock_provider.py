from app.services.resume_analysis.types import ResumeAnalysis
from app.services.resume_parsing import ParsedResume

# Deterministic stand-in for AI-generated resume analysis. No network calls,
# no API key required. Derives strengths/gaps directly from the sections the
# heuristic parser found, rather than understanding the resume's content.

MAX_HIGHLIGHTS = 5


def generate(parsed: ParsedResume, resume_text: str) -> ResumeAnalysis:
    strong_areas: list[str] = []
    if parsed.experience:
        strong_areas.append(f"{len(parsed.experience)} experience bullet point(s) listed.")
    if parsed.projects:
        strong_areas.append(f"{len(parsed.projects)} project(s) described.")
    if parsed.technologies:
        strong_areas.append(f"Familiarity with {', '.join(parsed.technologies[:6])}.")
    if not strong_areas:
        strong_areas.append(
            "Resume text was extracted, but no clearly labeled sections were found."
        )

    missing_details: list[str] = []
    if not parsed.projects:
        missing_details.append(
            "No dedicated 'Projects' section detected — consider adding specific "
            "projects with concrete outcomes."
        )
    if not parsed.experience:
        missing_details.append("No dedicated 'Experience' section detected.")
    if not parsed.technologies:
        missing_details.append("No specific technologies or tools were identified.")
    if not parsed.education:
        missing_details.append("No 'Education' section detected.")
    if not missing_details:
        missing_details.append(
            "Consider quantifying impact (metrics, scale, outcomes) for each bullet point."
        )

    key_projects = parsed.projects[:MAX_HIGHLIGHTS] or [
        "No specific projects identified from the resume text."
    ]
    key_technologies = parsed.technologies[:MAX_HIGHLIGHTS] or [
        "No specific technologies identified from the resume text."
    ]

    summary = (
        f"Found {len(parsed.experience)} experience item(s), {len(parsed.projects)} "
        f"project(s), {len(parsed.technologies)} technology mention(s), and "
        f"{len(parsed.education)} education item(s) in the uploaded resume."
    )

    return ResumeAnalysis(
        analyzer="mock",
        summary=summary,
        strong_areas=strong_areas[:MAX_HIGHLIGHTS],
        missing_details=missing_details[:MAX_HIGHLIGHTS],
        key_projects=key_projects,
        key_technologies=key_technologies,
    )
