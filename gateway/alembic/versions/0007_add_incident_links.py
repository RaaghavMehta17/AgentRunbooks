from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007_add_incident_links"
down_revision = "0006_add_canary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incident_links",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("pd_incident_id", sa.String(), nullable=True),
        sa.Column("jira_issue_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_incident_links_run_id", "incident_links", ["run_id"])
    op.create_index("ix_incident_links_pd", "incident_links", ["pd_incident_id"])
    op.create_index("ix_incident_links_jira", "incident_links", ["jira_issue_key"])


def downgrade() -> None:
    op.drop_index("ix_incident_links_jira", table_name="incident_links")
    op.drop_index("ix_incident_links_pd", table_name="incident_links")
    op.drop_index("ix_incident_links_run_id", table_name="incident_links")
    op.drop_table("incident_links")

