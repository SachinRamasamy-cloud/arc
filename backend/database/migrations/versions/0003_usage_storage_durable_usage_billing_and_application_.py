"""durable usage billing and application storage

Revision ID: 0003_usage_storage
Revises: 0002_retention_marker
Create Date: 2026-10-24 21:22:50.880204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_usage_storage'
down_revision: Union[str, Sequence[str], None] = '0002_retention_marker'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('usage_prices',
       sa.Column('version',sa.String(64),primary_key=True),
       sa.Column('processing_base_milli',sa.BigInteger(),nullable=False),
       sa.Column('processing_kib_milli',sa.BigInteger(),nullable=False),
       sa.Column('records_per_1000_milli',sa.BigInteger(),nullable=False),
       sa.Column('storage_gb_month_milli',sa.BigInteger(),nullable=False),
       sa.Column('created_at',sa.BigInteger(),nullable=False))
    op.create_table('plan_prices',
       sa.Column('id',sa.String(128),primary_key=True),
       sa.Column('price_version',sa.String(64),nullable=False),
       sa.Column('currency',sa.String(8),nullable=False),
       sa.Column('amount_minor',sa.BigInteger(),nullable=False),
       sa.Column('included_milli',sa.BigInteger(),nullable=False),
       sa.Column('created_at',sa.BigInteger(),nullable=False))
    # Frozen schema; defaults keep existing populated installations upgradeable.
    op.create_table('invoices',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('subscription_id', sa.String(length=128), nullable=True),
    sa.Column('status', sa.String(length=32), nullable=False),
    sa.Column('currency', sa.String(length=8), nullable=False),
    sa.Column('amount_due_minor', sa.BigInteger(), nullable=False),
    sa.Column('amount_paid_minor', sa.BigInteger(), nullable=False),
    sa.Column('period_start', sa.BigInteger(), nullable=True),
    sa.Column('period_end', sa.BigInteger(), nullable=True),
    sa.Column('hosted_url', sa.Text(), nullable=True),
    sa.Column('pdf_url', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_workspace_created', 'invoices', ['workspace_id', 'created_at'], unique=False)
    op.create_table('storage_statements',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('environment', sa.String(length=8), nullable=False),
    sa.Column('period_start', sa.BigInteger(), nullable=False),
    sa.Column('period_end', sa.BigInteger(), nullable=False),
    sa.Column('measured_until', sa.BigInteger(), nullable=False),
    sa.Column('byte_seconds', sa.BigInteger(), nullable=False),
    sa.Column('assessed_milli', sa.BigInteger(), nullable=False),
    sa.Column('settled_milli', sa.BigInteger(), nullable=False),
    sa.Column('settled_byte_seconds', sa.BigInteger(), nullable=False),
    sa.Column('state', sa.String(length=24), nullable=False),
    sa.Column('price_version', sa.String(length=64), nullable=False),
    sa.Column('rate_milli_gb_month', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'environment', 'period_start')
    )
    op.create_table('customer_records',
    sa.Column('id', sa.String(length=48), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('project_id', sa.String(length=48), nullable=False),
    sa.Column('environment', sa.String(length=8), nullable=False),
    sa.Column('collection', sa.String(length=64), nullable=False),
    sa.Column('record_key', sa.String(length=128), nullable=False),
    sa.Column('encrypted_data', sa.Text(), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.Column('updated_at', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('project_id', 'environment', 'collection', 'record_key')
    )
    op.create_index('ix_records_cursor', 'customer_records', ['project_id', 'environment', 'collection', 'record_key'], unique=False)
    op.create_table('mutation_receipts',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('project_id', sa.String(length=48), nullable=False),
    sa.Column('environment', sa.String(length=8), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('response_encrypted', sa.Text(), nullable=False),
    sa.Column('response_bytes', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.Column('expires_at', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_records_workspace_quota','customer_records',['workspace_id','environment','size_bytes'])
    op.create_index('ix_receipts_workspace_quota','mutation_receipts',['workspace_id','environment','expires_at','response_bytes'])
    op.create_index(op.f('ix_mutation_receipts_expires_at'), 'mutation_receipts', ['expires_at'], unique=False)
    op.create_table('usage_counters',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('project_id', sa.String(length=48), nullable=False),
    sa.Column('environment', sa.String(length=8), nullable=False),
    sa.Column('service', sa.String(length=40), nullable=False),
    sa.Column('period_start', sa.BigInteger(), nullable=False),
    sa.Column('quantity', sa.BigInteger(), nullable=False),
    sa.Column('charged_milli', sa.BigInteger(), nullable=False),
    sa.Column('price_version', sa.String(length=64), nullable=False),
    sa.Column('rate_milli', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_usage_counter_scope', 'usage_counters', ['workspace_id', 'environment', 'period_start'], unique=False)
    op.create_table('usage_events',
    sa.Column('id', sa.String(length=48), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('project_id', sa.String(length=48), nullable=True),
    sa.Column('environment', sa.String(length=8), nullable=False),
    sa.Column('reference', sa.String(length=200), nullable=False),
    sa.Column('service', sa.String(length=40), nullable=False),
    sa.Column('operation', sa.String(length=60), nullable=False),
    sa.Column('quantity', sa.BigInteger(), nullable=False),
    sa.Column('unit', sa.String(length=32), nullable=False),
    sa.Column('price_version', sa.String(length=64), nullable=False),
    sa.Column('gross_milli', sa.BigInteger(), nullable=False),
    sa.Column('included_milli', sa.BigInteger(), nullable=False),
    sa.Column('prepaid_milli', sa.BigInteger(), nullable=False),
    sa.Column('occurred_at', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('quantity >= 0 AND gross_milli >= 0 AND included_milli >= 0 AND prepaid_milli >= 0 AND gross_milli = included_milli + prepaid_milli'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('reference')
    )
    op.create_index('ix_usage_project_period', 'usage_events', ['project_id', 'environment', 'occurred_at'], unique=False)
    op.create_index('ix_usage_workspace_period', 'usage_events', ['workspace_id', 'environment', 'occurred_at', 'id'], unique=False)
    op.create_table('multipart_uploads',
    sa.Column('file_id', sa.String(length=48), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('provider_id', sa.Text(), nullable=False),
    sa.Column('state', sa.String(length=24), nullable=False),
    sa.Column('part_size', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('file_id')
    )
    op.create_index(op.f('ix_multipart_uploads_workspace_id'), 'multipart_uploads', ['workspace_id'], unique=False)
    op.create_table('storage_intervals',
    sa.Column('id', sa.String(length=48), nullable=False),
    sa.Column('workspace_id', sa.String(length=48), nullable=False),
    sa.Column('project_id', sa.String(length=48), nullable=False),
    sa.Column('environment', sa.String(length=8), nullable=False),
    sa.Column('file_id', sa.String(length=48), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('opened_at', sa.BigInteger(), nullable=False),
    sa.Column('closed_at', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('file_id')
    )
    op.create_index('ix_storage_intervals_scope', 'storage_intervals', ['workspace_id', 'environment', 'opened_at'], unique=False)
    op.create_table('credit_allocations',
    sa.Column('id', sa.String(length=48), nullable=False),
    sa.Column('job_id', sa.String(length=48), nullable=False),
    sa.Column('allowance_id', sa.String(length=128), nullable=False),
    sa.Column('reserved_milli', sa.BigInteger(), nullable=False),
    sa.CheckConstraint('reserved_milli > 0'),
    sa.ForeignKeyConstraint(['allowance_id'], ['allowances.id'], ),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('job_id', 'allowance_id')
    )
    op.create_index(op.f('ix_credit_allocations_job_id'), 'credit_allocations', ['job_id'], unique=False)
    op.add_column('files', sa.Column('expected_digest', sa.String(length=64), nullable=True))
    op.add_column('files', sa.Column('purpose', sa.String(length=16), server_default=sa.text("'processing'"), nullable=False))
    op.add_column('files', sa.Column('retention_hours', sa.Integer(), server_default=sa.text('24'), nullable=False))
    op.create_index('ix_files_workspace_state', 'files', ['workspace_id', 'state'], unique=False)
    op.add_column('jobs', sa.Column('price_version', sa.String(length=64), server_default=sa.text("'legacy-v0.1'"), nullable=False))
    op.add_column('jobs', sa.Column('input_bytes', sa.BigInteger(), server_default=sa.text('0'), nullable=False))
    op.add_column('jobs', sa.Column('price_snapshot', sa.JSON(), server_default=sa.text("'{}'"), nullable=False))
    op.create_index('ix_jobs_project_active', 'jobs', ['project_id', 'environment', 'state'], unique=False)
    op.create_index('ix_jobs_project_budget', 'jobs', ['project_id', 'environment', 'created_at'], unique=False)
    op.create_index('ix_jobs_workspace_period', 'jobs', ['workspace_id', 'environment', 'created_at'], unique=False)
    op.add_column('payments', sa.Column('request_key', sa.String(length=128), nullable=True))
    op.add_column('payments', sa.Column('price_id', sa.String(length=128), nullable=True))
    op.add_column('payments', sa.Column('checkout_url', sa.Text(), nullable=True))
    op.add_column('payments', sa.Column('checkout_expires_at', sa.BigInteger(), nullable=True))
    op.create_index('ix_payments_pending', 'payments', ['workspace_id', 'kind', 'state', 'checkout_expires_at'], unique=False)
    op.create_index('uq_payments_request_key', 'payments', ['request_key'], unique=True)
    op.create_index('ix_logs_project_period', 'request_logs', ['project_id', 'environment', 'created_at'], unique=False)
    op.add_column('workspaces', sa.Column('period_start', sa.BigInteger(), nullable=True))
    op.add_column('workspaces', sa.Column('cancel_at_period_end', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('workspaces', sa.Column('subscription_price', sa.String(length=128), nullable=True))
    op.add_column('workspaces', sa.Column('storage_checked_at', sa.BigInteger(), server_default=sa.text('0'), nullable=False))



    # Existing settled jobs become reporting entries only. Never debit a wallet
    # again; old prepaid charge lives in its settlement ledger entry.
    import time
    import uuid
    connection = op.get_bind()
    rows = connection.execute(sa.text("""SELECT j.id,j.workspace_id,j.project_id,j.environment,j.operation,
        j.charged_milli,j.completed_at,j.created_at,
        COALESCE((SELECT -SUM(l.amount_milli) FROM credit_ledger l
          WHERE l.reference='settle:' || j.id),j.charged_milli) AS prepaid
        FROM jobs j WHERE j.billing_state='settled' AND j.state='succeeded'""")).mappings()
    for row in rows:
        gross=int(row['charged_milli']); paid=max(0,min(gross,int(row['prepaid'])))
        connection.execute(sa.text("""INSERT INTO usage_events
         (id,workspace_id,project_id,environment,reference,service,operation,quantity,unit,
          price_version,gross_milli,included_milli,prepaid_milli,occurred_at)
         VALUES (:id,:wid,:pid,:env,:ref,'processing',:operation,1,'job','legacy-v0.1',:gross,:included,:paid,:at)"""),
         dict(id='use_'+uuid.uuid4().hex,wid=row['workspace_id'],pid=row['project_id'],env=row['environment'],
         ref='job:'+row['id'],operation=row['operation'],gross=gross,included=gross-paid,paid=paid,at=row['completed_at'] or row['created_at']))
    # Storage billing starts at upgrade, never retroactively before the meter existed.
    at=int(time.time())
    files=connection.execute(sa.text("SELECT id,workspace_id,project_id,environment,size FROM files WHERE state='ready' AND expires_at>:at"),dict(at=at)).mappings()
    for row in files:
        connection.execute(sa.text("""INSERT INTO storage_intervals
        (id,workspace_id,project_id,environment,file_id,size_bytes,opened_at,closed_at)
        VALUES (:id,:wid,:pid,:env,:fid,:size,:at,NULL)"""),
        dict(id='sti_'+uuid.uuid4().hex,wid=row['workspace_id'],pid=row['project_id'],env=row['environment'],fid=row['id'],size=row['size'],at=at))


def downgrade() -> None:
    """Downgrade only an unused migration; restore a backup for populated data."""
    for table in ('usage_events','customer_records','invoices','storage_intervals','plan_prices','usage_prices'):
        if op.get_bind().execute(sa.text(f'SELECT COUNT(*) FROM {table}')).scalar():
            raise RuntimeError('Refusing to discard usage or customer data. Restore the reviewed backup instead.')
    # Frozen schema; defaults keep existing populated installations upgradeable.
    op.drop_table('usage_prices')
    op.drop_table('plan_prices')
    op.drop_column('workspaces', 'storage_checked_at')
    op.drop_column('workspaces', 'subscription_price')
    op.drop_column('workspaces', 'cancel_at_period_end')
    op.drop_column('workspaces', 'period_start')
    op.drop_index('ix_logs_project_period', table_name='request_logs')
    op.drop_index('uq_payments_request_key', table_name='payments')
    op.drop_index('ix_payments_pending', table_name='payments')
    op.drop_column('payments', 'checkout_expires_at')
    op.drop_column('payments', 'checkout_url')
    op.drop_column('payments', 'price_id')
    op.drop_column('payments', 'request_key')
    op.drop_index('ix_jobs_workspace_period', table_name='jobs')
    op.drop_index('ix_jobs_project_budget', table_name='jobs')
    op.drop_index('ix_jobs_project_active', table_name='jobs')
    op.drop_column('jobs', 'price_snapshot')
    op.drop_column('jobs', 'input_bytes')
    op.drop_column('jobs', 'price_version')
    op.drop_index('ix_files_workspace_state', table_name='files')
    op.drop_column('files', 'retention_hours')
    op.drop_column('files', 'purpose')
    op.drop_column('files', 'expected_digest')
    op.drop_index(op.f('ix_credit_allocations_job_id'), table_name='credit_allocations')
    op.drop_table('credit_allocations')
    op.drop_index('ix_storage_intervals_scope', table_name='storage_intervals')
    op.drop_table('storage_intervals')
    op.drop_index(op.f('ix_multipart_uploads_workspace_id'), table_name='multipart_uploads')
    op.drop_table('multipart_uploads')
    op.drop_index('ix_usage_workspace_period', table_name='usage_events')
    op.drop_index('ix_usage_project_period', table_name='usage_events')
    op.drop_table('usage_events')
    op.drop_index('ix_usage_counter_scope', table_name='usage_counters')
    op.drop_table('usage_counters')
    op.drop_index(op.f('ix_mutation_receipts_expires_at'), table_name='mutation_receipts')
    op.drop_index('ix_receipts_workspace_quota',table_name='mutation_receipts')
    op.drop_table('mutation_receipts')
    op.drop_index('ix_records_cursor', table_name='customer_records')
    op.drop_index('ix_records_workspace_quota',table_name='customer_records')
    op.drop_table('customer_records')
    op.drop_table('storage_statements')
    op.drop_index('ix_invoices_workspace_created', table_name='invoices')
    op.drop_table('invoices')
