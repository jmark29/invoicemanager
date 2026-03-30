"""sprint4_import_reconciliation

Add invoice import support (source, original_file_path, period dates),
line item config link, and invoice_line_item_sources table for
many-to-many traceability between line items and provider invoices.

Revision ID: a3b4c5d6e7f8
Revises: 01ae9a112870
Create Date: 2026-03-30 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "01ae9a112870"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists in a table (handles prior create_all)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in result)


def upgrade() -> None:
    # -- Add columns to generated_invoices (skip if already exist) --
    with op.batch_alter_table("generated_invoices") as batch_op:
        if not _column_exists("generated_invoices", "source"):
            batch_op.add_column(
                sa.Column("source", sa.String(), server_default="generated", nullable=False)
            )
        if not _column_exists("generated_invoices", "original_file_path"):
            batch_op.add_column(
                sa.Column("original_file_path", sa.String(), nullable=True)
            )
        if not _column_exists("generated_invoices", "period_start"):
            batch_op.add_column(
                sa.Column("period_start", sa.Date(), nullable=True)
            )
        if not _column_exists("generated_invoices", "period_end"):
            batch_op.add_column(
                sa.Column("period_end", sa.Date(), nullable=True)
            )

    # -- Add line_item_config_id to generated_invoice_items --
    if not _column_exists("generated_invoice_items", "line_item_config_id"):
        op.execute(
            "ALTER TABLE generated_invoice_items "
            "ADD COLUMN line_item_config_id INTEGER REFERENCES line_item_definitions(id)"
        )

    # -- Create invoice_line_item_sources table --
    op.create_table(
        "invoice_line_item_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "line_item_id",
            sa.Integer(),
            sa.ForeignKey("generated_invoice_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_invoice_id",
            sa.Integer(),
            sa.ForeignKey("provider_invoices.id"),
            nullable=False,
        ),
        sa.Column("amount_contributed", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
        ),
    )

    # -- Backfill: create source records from existing line items --
    # For items with provider_invoice_id (direct costs)
    op.execute(
        """
        INSERT INTO invoice_line_item_sources (line_item_id, provider_invoice_id, amount_contributed)
        SELECT id, provider_invoice_id, amount
        FROM generated_invoice_items
        WHERE provider_invoice_id IS NOT NULL
        """
    )
    # For items with distribution_source_id (distributed costs)
    op.execute(
        """
        INSERT INTO invoice_line_item_sources (line_item_id, provider_invoice_id, amount_contributed)
        SELECT id, distribution_source_id, amount
        FROM generated_invoice_items
        WHERE distribution_source_id IS NOT NULL
          AND distribution_source_id NOT IN (
              SELECT provider_invoice_id FROM invoice_line_item_sources
              WHERE line_item_id = generated_invoice_items.id
          )
        """
    )


def downgrade() -> None:
    op.drop_table("invoice_line_item_sources")

    with op.batch_alter_table("generated_invoice_items") as batch_op:
        batch_op.drop_column("line_item_config_id")

    with op.batch_alter_table("generated_invoices") as batch_op:
        batch_op.drop_column("period_end")
        batch_op.drop_column("period_start")
        batch_op.drop_column("original_file_path")
        batch_op.drop_column("source")
