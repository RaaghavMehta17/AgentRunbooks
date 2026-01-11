from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0011_add_scim"
down_revision = "0010_add_tenancy_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Groups table
    op.create_table(
        "groups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_groups_tenant_display_name", "groups", ["tenant_id", "display_name"])

    # Group members table
    op.create_table(
        "group_members",
        sa.Column("group_id", sa.String(), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )

    # Extend user_identities with external_id
    op.add_column("user_identities", sa.Column("external_id", sa.String(), nullable=True))

    # Create SCIM provider if not exists
    op.execute(
        text(
            "INSERT INTO identity_providers (id, name, issuer, client_id, created_at) SELECT 'scim', 'SCIM', 'scim', 'scim', datetime('now') WHERE NOT EXISTS (SELECT 1 FROM identity_providers WHERE id = 'scim')"
        )
    )


def downgrade() -> None:
    op.drop_column("user_identities", "external_id")
    op.drop_table("group_members")
    op.drop_constraint("uq_groups_tenant_display_name", "groups")
    op.drop_table("groups")

