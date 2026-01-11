from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0010_add_tenancy_rbac"
down_revision = "0009_add_oidc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_projects_tenant_name", "projects", ["tenant_id", "name"])

    # Role bindings table
    op.create_table(
        "role_bindings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("subject_type", sa.String(), nullable=False),  # 'user', 'group', 'apikey'
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_role_bindings_tenant_project_subject_role",
        "role_bindings",
        ["tenant_id", "project_id", "subject_type", "subject_id", "role"],
    )

    # Add tenant_id and project_id to existing tables
    default_tenant_id = "default"  # Will be created if missing

    # Runbooks
    op.add_column("runbooks", sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("runbooks", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True))
    op.execute(text(f"UPDATE runbooks SET tenant_id = '{default_tenant_id}' WHERE tenant_id IS NULL"))

    # Policies
    op.add_column("policies", sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("policies", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True))
    op.execute(text(f"UPDATE policies SET tenant_id = '{default_tenant_id}' WHERE tenant_id IS NULL"))

    # Runs
    op.add_column("runs", sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("runs", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True))
    op.execute(text(f"UPDATE runs SET tenant_id = '{default_tenant_id}' WHERE tenant_id IS NULL"))

    # Approvals
    op.add_column("approvals", sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("approvals", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True))
    op.execute(text(f"UPDATE approvals SET tenant_id = '{default_tenant_id}' WHERE tenant_id IS NULL"))

    # Eval results
    op.add_column("eval_results", sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("eval_results", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True))
    op.execute(text(f"UPDATE eval_results SET tenant_id = '{default_tenant_id}' WHERE tenant_id IS NULL"))

    # Incident links
    op.add_column("incident_links", sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.id"), nullable=True))
    op.add_column("incident_links", sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=True))
    op.execute(text(f"UPDATE incident_links SET tenant_id = '{default_tenant_id}' WHERE tenant_id IS NULL"))

    # Make tenant_id NOT NULL after backfill
    op.alter_column("runbooks", "tenant_id", nullable=False)
    op.alter_column("policies", "tenant_id", nullable=False)
    op.alter_column("runs", "tenant_id", nullable=False)
    op.alter_column("approvals", "tenant_id", nullable=False)
    op.alter_column("eval_results", "tenant_id", nullable=False)
    op.alter_column("incident_links", "tenant_id", nullable=False)


def downgrade() -> None:
    op.drop_column("incident_links", "project_id")
    op.drop_column("incident_links", "tenant_id")
    op.drop_column("eval_results", "project_id")
    op.drop_column("eval_results", "tenant_id")
    op.drop_column("approvals", "project_id")
    op.drop_column("approvals", "tenant_id")
    op.drop_column("runs", "project_id")
    op.drop_column("runs", "tenant_id")
    op.drop_column("policies", "project_id")
    op.drop_column("policies", "tenant_id")
    op.drop_column("runbooks", "project_id")
    op.drop_column("runbooks", "tenant_id")
    op.drop_constraint("uq_role_bindings_tenant_project_subject_role", "role_bindings")
    op.drop_table("role_bindings")
    op.drop_constraint("uq_projects_tenant_name", "projects")
    op.drop_table("projects")

