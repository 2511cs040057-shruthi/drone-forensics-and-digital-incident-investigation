
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .case import Base


class Evidence(Base):
    __tablename__ = "autopsy_evidence"

    __table_args__ = (
        UniqueConstraint(
            "autopsy_export_id",
            "autopsy_object_id",
            name="uq_evidence_autopsy_export_object",
        ),
    )

    evidence_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Must match cases.case_id: signed BIGINT.
    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cases.case_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    source_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    autopsy_export_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    autopsy_object_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="Pending",
    )

    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    case = relationship("Case")

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "case_id": self.case_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "sha256": self.sha256,
            "storage_path": self.storage_path,
            "source_path": self.source_path,
            "autopsy_export_id": self.autopsy_export_id,
            "autopsy_object_id": self.autopsy_object_id,
            "verification_status": self.verification_status,
            "imported_at": (
                self.imported_at.isoformat()
                if self.imported_at
                else None
            ),
        }
