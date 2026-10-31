
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    object_session,
)


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    case_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )

    case_title: Mapped[str] = mapped_column(
        String(200),
    )

    examiner_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    investigation_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        default="Open",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def get_evidence_count(self) -> int:
        """
        Count Autopsy evidence records linked to this case.
        """

        from .evidence import Evidence

        session = object_session(self)

        if session is None or self.case_id is None:
            return 0

        statement = (
            select(func.count(Evidence.evidence_id))
            .where(Evidence.case_id == self.case_id)
        )

        count = session.scalar(statement)

        return int(count or 0)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "case_number": self.case_number,
            "case_title": self.case_title,
            "examiner_name": self.examiner_name,
            "investigation_date": (
                self.investigation_date.isoformat()
                if self.investigation_date
                else None
            ),
            "description": self.description,
            "status": self.status,
            "evidence_count": self.get_evidence_count(),
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }
