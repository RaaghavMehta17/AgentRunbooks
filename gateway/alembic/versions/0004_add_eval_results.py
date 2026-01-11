from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_add_eval_results"
down_revision = "0003_add_approvals_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("hallu_rate", sa.Float(), nullable=False),
        sa.Column("p95_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_eval_results_created_at", "eval_results", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_created_at", table_name="eval_results")
    op.drop_table("eval_results")


