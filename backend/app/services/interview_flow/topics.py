# Role-agnostic technology/topic extraction from a candidate's own answer
# text, used to make a follow-up question specific ("why did you choose
# JWT...") instead of generic ("what was challenging about that..."). Not
# tied to any single role — the app accepts 19 curated roles plus arbitrary
# custom role text (see app.services.question_generation.bank), so this list
# spans web/mobile engineering, data/ML, DevOps/cloud, QA/security, and
# product/design terms rather than hard-coding a handful of roles.
#
# Longer, more specific phrases are preferred over short/generic ones (see
# extract_topic) — e.g. "machine learning model" over "model".

_KEYWORDS = (
    # Web / app frameworks
    "react", "next.js", "vue", "angular", "svelte", "django", "flask",
    "fastapi", "spring boot", "express", "node.js", "ruby on rails",
    "asp.net",
    # Mobile
    "swiftui", "swift", "kotlin", "flutter", "react native",
    "jetpack compose",
    # Languages
    "python", "javascript", "typescript", "golang", "rust", "c++", "c#",
    "php",
    # APIs / auth / protocols
    "rest api", "graphql", "grpc", "websocket", "jwt", "oauth", "api gateway",
    "webhook",
    # Data stores
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "cassandra", "sqlite", "nosql",
    # Infra / cloud / devops
    "docker", "kubernetes", "terraform", "jenkins", "github actions",
    "ci/cd", "aws", "azure", "gcp", "load balancer", "microservice",
    "serverless",
    # Data / ML
    "machine learning model", "neural network", "tensorflow", "pytorch",
    "pandas", "scikit-learn", "a/b test", "feature engineering",
    "data pipeline", "data warehouse", "spark", "airflow",
    # QA / security
    "unit test", "integration test", "selenium", "cypress",
    "penetration test", "encryption",
    # Product / design / business
    "roadmap", "user research", "wireframe", "figma", "kpi", "okr",
    "sprint", "backlog", "stakeholder", "prototype", "user persona",
    "churn", "retention",
    # General engineering concepts (checked last — broad, likely to match)
    "caching", "message queue", "rate limiter", "load testing", "database",
    "algorithm", "api",
)


def extract_topic(text: str) -> str | None:
    """Best-effort match of a known technology/topic phrase in `text`.
    Returns the longest matching phrase (most specific/natural-sounding),
    or None when nothing recognizable is present — callers must fall back
    to a generic follow-up rather than inventing a topic."""
    lower = text.lower()
    matches = [kw for kw in _KEYWORDS if kw in lower]
    if not matches:
        return None
    return max(matches, key=len)
