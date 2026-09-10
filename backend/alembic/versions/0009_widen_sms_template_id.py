"""Widen sms_templates.template_id from VARCHAR(36) to VARCHAR(128).

template_id is a composite of crop_code-reason_code-language_code (up to
60+50+10 chars plus separators), not a UUID. 36 chars was too narrow --
SQLite never enforced the limit so this only surfaced against Postgres.
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_widen_sms_template_id"
down_revision = "0008_audit_log_actor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "sms_templates",
        "template_id",
        existing_type=sa.String(36),
        type_=sa.String(128),
    )


def downgrade() -> None:
    op.alter_column(
        "sms_templates",
        "template_id",
        existing_type=sa.String(128),
        type_=sa.String(36),
    )
