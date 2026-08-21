import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Lightweight, additive-only schema patcher for the sqlite dev database.
# There's no Alembic in this project yet, and Base.metadata.create_all only
# creates missing tables — it never alters existing ones. This fills that
# one gap for the nullable columns the resume feature adds, so a database
# created before resume support keeps working without a manual reset.
# Table/column names below are fixed constants, never user input.
_NEW_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "interviews": [
        ("resume_id", "INTEGER"),
        ("camera_metrics", "JSON"),
        ("user_id", "INTEGER"),
        ("question_count", "INTEGER"),
        ("focus_categories", "JSON"),
    ],
    "questions": [
        ("source", "VARCHAR(20) DEFAULT 'bank'"),
        ("resume_topic", "VARCHAR(200)"),
        ("is_followup", "BOOLEAN DEFAULT 0"),
    ],
    "answers": [("speech_metrics", "JSON")],
    "resumes": [("user_id", "INTEGER")],
}


def run_lightweight_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in _NEW_COLUMNS.items():
            if table not in existing_tables:
                continue  # fresh DB: create_all already created it with the new columns
            existing_columns = {col["name"] for col in inspector.get_columns(table)}
            for column_name, ddl_type in columns:
                if column_name in existing_columns:
                    continue
                logger.info("Migrating schema: adding %s.%s", table, column_name)
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column_name} {ddl_type}")
                )
