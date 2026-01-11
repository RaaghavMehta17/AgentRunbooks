from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006_add_canary"
down_revision = "0005_add_security_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Canary policies table
    op.create_table(
        "canary_policies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add canary_promoted to runbooks
    op.add_column("runbooks", sa.Column("canary_promoted", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("runbooks", "canary_promoted")
    op.drop_table("canary_policies")

