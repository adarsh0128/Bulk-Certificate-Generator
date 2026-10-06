"""Initial schema

Revision ID: 20261006_initial
Revises: 
Create Date: 2026-10-06 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20261006_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("organization_name", sa.String(length=255), nullable=True),
        sa.Column("course_name", sa.String(length=255), nullable=True),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signatory_name", sa.String(length=255), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("pending_count", sa.Integer(), nullable=False),
        sa.Column("processing_count", sa.Integer(), nullable=False),
        sa.Column("successful_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_generation_jobs_id"), "generation_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_generation_jobs_status"), "generation_jobs", ["status"], unique=False)

    op.create_table(
        "recipients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recipients_email"), "recipients", ["email"], unique=False)
    op.create_index(op.f("ix_recipients_job_id"), "recipients", ["job_id"], unique=False)
    op.create_index(op.f("ix_recipients_status"), "recipients", ["status"], unique=False)

    op.create_table(
        "certificates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("recipient_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["recipients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipient_id"),
    )
    op.create_index(op.f("ix_certificates_job_id"), "certificates", ["job_id"], unique=False)
    op.create_index(op.f("ix_certificates_recipient_id"), "certificates", ["recipient_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_certificates_recipient_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_job_id"), table_name="certificates")
    op.drop_table("certificates")
    op.drop_index(op.f("ix_recipients_status"), table_name="recipients")
    op.drop_index(op.f("ix_recipients_job_id"), table_name="recipients")
    op.drop_index(op.f("ix_recipients_email"), table_name="recipients")
    op.drop_table("recipients")
    op.drop_index(op.f("ix_generation_jobs_status"), table_name="generation_jobs")
    op.drop_index(op.f("ix_generation_jobs_id"), table_name="generation_jobs")
    op.drop_table("generation_jobs")
