"""prod features

Revision ID: 9b2f5d7c1a4e
Revises: 4c4168f7aa2e
Create Date: 2026-06-23 18:24:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "9b2f5d7c1a4e"
down_revision: str | None = "4c4168f7aa2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blocked_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("blocker_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_blocked_user"),
    )
    op.create_index(op.f("ix_blocked_users_blocked_id"), "blocked_users", ["blocked_id"], unique=False)
    op.create_index(op.f("ix_blocked_users_blocker_id"), "blocked_users", ["blocker_id"], unique=False)
    op.create_index(op.f("ix_blocked_users_created_at"), "blocked_users", ["created_at"], unique=False)
    op.create_index(op.f("ix_blocked_users_id"), "blocked_users", ["id"], unique=False)

    op.create_table(
        "message_reactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("emoji", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_reaction"),
    )
    op.create_index(op.f("ix_message_reactions_created_at"), "message_reactions", ["created_at"], unique=False)
    op.create_index(op.f("ix_message_reactions_id"), "message_reactions", ["id"], unique=False)
    op.create_index(op.f("ix_message_reactions_message_id"), "message_reactions", ["message_id"], unique=False)
    op.create_index(op.f("ix_message_reactions_user_id"), "message_reactions", ["user_id"], unique=False)

    op.create_table(
        "user_notification_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("new_messages", sa.Boolean(), nullable=False),
        sa.Column("mentions", sa.Boolean(), nullable=False),
        sa.Column("reactions", sa.Boolean(), nullable=False),
        sa.Column("group_invites", sa.Boolean(), nullable=False),
        sa.Column("channel_updates", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_user_notification_settings_user_id"),
        "user_notification_settings",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "user_privacy_settings",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("direct_messages", sa.Enum("EVERYONE", "NOBODY", name="directmessagepolicy"), nullable=False),
        sa.Column("show_online_status", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_privacy_settings_user_id"), "user_privacy_settings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_privacy_settings_user_id"), table_name="user_privacy_settings")
    op.drop_table("user_privacy_settings")
    op.drop_index(op.f("ix_user_notification_settings_user_id"), table_name="user_notification_settings")
    op.drop_table("user_notification_settings")
    op.drop_index(op.f("ix_message_reactions_user_id"), table_name="message_reactions")
    op.drop_index(op.f("ix_message_reactions_message_id"), table_name="message_reactions")
    op.drop_index(op.f("ix_message_reactions_id"), table_name="message_reactions")
    op.drop_index(op.f("ix_message_reactions_created_at"), table_name="message_reactions")
    op.drop_table("message_reactions")
    op.drop_index(op.f("ix_blocked_users_id"), table_name="blocked_users")
    op.drop_index(op.f("ix_blocked_users_created_at"), table_name="blocked_users")
    op.drop_index(op.f("ix_blocked_users_blocker_id"), table_name="blocked_users")
    op.drop_index(op.f("ix_blocked_users_blocked_id"), table_name="blocked_users")
    op.drop_table("blocked_users")
