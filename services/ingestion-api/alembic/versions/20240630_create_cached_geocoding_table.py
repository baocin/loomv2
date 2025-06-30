"""create cached geocoding table

Revision ID: 20240630_cached_geocoding
Revises: 20240622_add_os_events_tables
Create Date: 2024-06-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240630_cached_geocoding'
down_revision = '20240622_add_os_events_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create cached_geocoding table
    op.create_table(
        'cached_geocoding',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('geocoded_address', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('postal_code', sa.String(), nullable=True),
        sa.Column('place_name', sa.String(), nullable=True),
        sa.Column('place_type', sa.String(), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('use_count', sa.Integer(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient lookups
    op.create_index('idx_cached_geocoding_coords', 'cached_geocoding', ['latitude', 'longitude'])
    op.create_index('idx_cached_geocoding_last_used', 'cached_geocoding', ['last_used_at'])
    
    # Create a unique constraint on lat/lon to prevent duplicates
    op.create_unique_constraint('uq_cached_geocoding_coords', 'cached_geocoding', ['latitude', 'longitude'])


def downgrade():
    op.drop_index('idx_cached_geocoding_last_used', 'cached_geocoding')
    op.drop_index('idx_cached_geocoding_coords', 'cached_geocoding')
    op.drop_table('cached_geocoding')