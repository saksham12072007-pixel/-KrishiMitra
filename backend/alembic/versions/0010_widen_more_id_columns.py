"""Widen three more VARCHAR columns whose limits were too narrow for real data.

Same class of bug as 0009: these columns hold composite/prefixed ids rather
than bare UUIDs, and SQLite never enforced the varchar length so this only
surfaced against Postgres, while re-importing the local dataset.

- plots.location_precision: seed data uses "synthetic_centroid_jitter" (26
  chars) against a VARCHAR(20) column.
- satellite_data.satellite_id: values like "weather-<uuid>-<index>" (up to
  ~48 chars) against a VARCHAR(36) column.
- advisories.template_id: references sms_templates.template_id, so it needs
  to match that column's VARCHAR(128) width (widened in 0009).
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_widen_more_id_columns"
down_revision = "0009_widen_sms_template_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "plots",
        "location_precision",
        existing_type=sa.String(20),
        type_=sa.String(40),
    )
    op.alter_column(
        "satellite_data",
        "satellite_id",
        existing_type=sa.String(36),
        type_=sa.String(80),
    )
    op.alter_column(
        "advisories",
        "template_id",
        existing_type=sa.String(36),
        type_=sa.String(128),
    )


def downgrade() -> None:
    op.alter_column(
        "advisories",
        "template_id",
        existing_type=sa.String(128),
        type_=sa.String(36),
    )
    op.alter_column(
        "satellite_data",
        "satellite_id",
        existing_type=sa.String(80),
        type_=sa.String(36),
    )
    op.alter_column(
        "plots",
        "location_precision",
        existing_type=sa.String(40),
        type_=sa.String(20),
    )
