from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0009_add_oidc"
down_revision = "0008_add_feature_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Identity providers
    op.create_table(
        "identity_providers",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("issuer", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # User identities (link users to IdP)
    op.create_table(
        "user_identities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider_id", sa.String(), sa.ForeignKey("identity_providers.id"), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("groups", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_identities_provider_subject", "user_identities", ["provider_id", "subject"])

    # Extend users table
    op.add_column("users", sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    # Ensure email index exists (may already exist)
    try:
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    except Exception:
        pass  # Index may already exist


def downgrade() -> None:
    op.drop_index("ix_user_identities_provider_subject", table_name="user_identities")
    op.drop_table("user_identities")
    op.drop_table("identity_providers")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_disabled")

