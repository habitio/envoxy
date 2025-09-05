"""create product table

Revision ID: 0001_create_product
Revises: 
Create Date: 2025-09-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_product'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'aux_products',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('updated', sa.DateTime(), nullable=False),
        sa.Column('href', sa.String(length=1024), nullable=False),
        sa.Column('sku', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('cdata', sa.JSON(), nullable=True),
        sa.Column('price_cents', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('aux_idx_products_sku', 'aux_products', ['sku'], unique=False)


def downgrade():
    op.drop_index('aux_idx_products_sku', table_name='aux_products')
    op.drop_table('aux_products')
