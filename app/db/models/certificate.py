from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    recipient_id: Mapped[str] = mapped_column(ForeignKey("recipients.id"), unique=True, nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("generation_jobs.id"), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    recipient: Mapped[Recipient] = relationship(back_populates="certificate")
    job: Mapped[GenerationJob] = relationship(back_populates="certificates")

    def __repr__(self) -> str:
        return f"Certificate(id={self.id}, recipient_id={self.recipient_id})"


from app.db.models.recipient import Recipient
from app.db.models.job import GenerationJob
