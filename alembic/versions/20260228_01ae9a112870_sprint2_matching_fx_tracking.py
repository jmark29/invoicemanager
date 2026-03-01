"""sprint2_matching_fx_tracking

Revision ID: 01ae9a112870
Revises: 40a5196c80fb
Create Date: 2026-02-28 20:18:07.197042
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01ae9a112870'
down_revision: Union[str, None] = '40a5196c80fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add matching columns to bank_transactions
    with op.batch_alter_table('bank_transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('match_status', sa.String(), server_default='unmatched', nullable=False))
        batch_op.add_column(sa.Column('match_confidence', sa.Float(), nullable=True))

    # Add payment/FX tracking columns to provider_invoices
    with op.batch_alter_table('provider_invoices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_status', sa.String(), server_default='unpaid', nullable=False))
        batch_op.add_column(sa.Column('matched_transaction_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('amount_eur', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('bank_fee', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('fx_rate', sa.Float(), nullable=True))
        batch_op.create_foreign_key(
            'fk_provider_invoices_matched_transaction_id',
            'bank_transactions', ['matched_transaction_id'], ['id'],
        )

    # Backfill: mark already-linked records as matched
    op.execute("""
        UPDATE bank_transactions
        SET match_status = 'auto_matched'
        WHERE provider_invoice_id IS NOT NULL
    """)
    op.execute("""
        UPDATE provider_invoices
        SET payment_status = 'matched',
            matched_transaction_id = (
                SELECT bt.id FROM bank_transactions bt
                WHERE bt.provider_invoice_id = provider_invoices.id
                LIMIT 1
            ),
            amount_eur = CASE
                WHEN currency = 'EUR' THEN amount
                ELSE (
                    SELECT ABS(bt.amount_eur) FROM bank_transactions bt
                    WHERE bt.provider_invoice_id = provider_invoices.id
                    LIMIT 1
                )
            END
        WHERE id IN (
            SELECT DISTINCT provider_invoice_id
            FROM bank_transactions
            WHERE provider_invoice_id IS NOT NULL
        )
    """)


def downgrade() -> None:
    with op.batch_alter_table('provider_invoices', schema=None) as batch_op:
        batch_op.drop_constraint('fk_provider_invoices_matched_transaction_id', type_='foreignkey')
        batch_op.drop_column('fx_rate')
        batch_op.drop_column('bank_fee')
        batch_op.drop_column('amount_eur')
        batch_op.drop_column('matched_transaction_id')
        batch_op.drop_column('payment_status')

    with op.batch_alter_table('bank_transactions', schema=None) as batch_op:
        batch_op.drop_column('match_confidence')
        batch_op.drop_column('match_status')
