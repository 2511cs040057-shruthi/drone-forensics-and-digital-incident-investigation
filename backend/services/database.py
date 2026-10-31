
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from ..models.case import Base
from ..models.user import User
from ..models.evidence import Evidence


DATABASE_URL = URL.create(
    "mysql+mysqlconnector",
    username=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "drone_forensics"),
    query={"charset": "utf8mb4"},
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


def initialize_database() -> None:
    # Register and create any missing tables, including evidence.
    # Existing tables and their records are preserved.
    Base.metadata.create_all(bind=engine)

    # Maintain compatibility with older versions of the cases table.
    columns = {
        column["name"]
        for column in inspect(engine).get_columns("cases")
    }

    with engine.begin() as connection:
        if "investigation_date" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE cases "
                    "ADD COLUMN investigation_date DATE NULL"
                )
            )

        if "updated_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE cases "
                    "ADD COLUMN updated_at DATETIME NULL "
                    "DEFAULT CURRENT_TIMESTAMP "
                    "ON UPDATE CURRENT_TIMESTAMP"
                )
            )

        connection.execute(
            text(
                "UPDATE cases "
                "SET investigation_date = COALESCE("
                "investigation_date, DATE(created_at), CURRENT_DATE"
                "), "
                "updated_at = COALESCE("
                "updated_at, created_at, CURRENT_TIMESTAMP"
                ")"
            )
        )
