"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create initial tables."""
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('role', sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('platform', sa.Enum('linux', 'windows', 'macos', 'termux', name='platform'), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(), nullable=True),
        sa.Column('lost', sa.Boolean(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('last_ip', postgresql.INET(), nullable=True),
        sa.Column('last_asn', sa.Integer(), nullable=True),
        sa.Column('last_location', sa.JSON(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_devices_last_seen_at', 'devices', ['last_seen_at'])
    op.create_index('idx_devices_owner_id', 'devices', ['owner_id'])
    
    # Create agent_credentials table
    op.create_table(
        'agent_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('device_token', sa.String(255), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_token')
    )
    
    # Create telemetry_events table
    op.create_table(
        'telemetry_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('hostname', sa.String(255), nullable=True),
        sa.Column('os', sa.String(100), nullable=True),
        sa.Column('wifi', sa.JSON(), nullable=True),
        sa.Column('battery', sa.Integer(), nullable=True),
        sa.Column('ip', postgresql.INET(), nullable=True),
        sa.Column('asn', sa.Integer(), nullable=True),
        sa.Column('location', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_telemetry_device_ts', 'telemetry_events', ['device_id', 'ts'])
    
    # Create commands table
    op.create_table(
        'commands',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('SHOW_MESSAGE', 'PLAY_CHIME', 'INCREASE_HEARTBEAT', 'LOCK_SCREEN', 'PING', name='commandtype'), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'ACKED', 'DONE', 'FAILED', name='commandstatus'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('must_ack', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Enum('NO_HEARTBEAT', 'NEW_IP', 'NEW_WIFI', name='alerttype'), nullable=False),
        sa.Column('severity', sa.Enum('info', 'warning', 'critical', name='alertseverity'), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create enrollment_tokens table
    op.create_table(
        'enrollment_tokens',
        sa.Column('token', sa.String(255), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('token')
    )

def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('enrollment_tokens')
    op.drop_table('alerts')
    op.drop_table('commands')
    op.drop_table('telemetry_events')
    op.drop_table('agent_credentials')
    op.drop_table('devices')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS platform')
    op.execute('DROP TYPE IF EXISTS commandtype')
    op.execute('DROP TYPE IF EXISTS commandstatus')
    op.execute('DROP TYPE IF EXISTS alerttype')
    op.execute('DROP TYPE IF EXISTS alertseverity')
