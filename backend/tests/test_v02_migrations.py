from pathlib import Path
import time
import pytest
from alembic.config import Config
from alembic import command
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata
from sqlalchemy import create_engine,MetaData,select,func
from arc.models import Base,Job,Ledger,FileObject,Wallet,UsageEvent,StorageInterval,now
from conftest import ROOT


def migration_config(monkeypatch,owner,tmp_path):
    target='sqlite:///'+str(tmp_path/'upgrade.sqlite')
    for name,value in {'DATABASE_URL':target,'SECRET_KEY':owner['settings'].secret_key,'ENCRYPTION_KEY':owner['settings'].encryption_key,'ENV':'test'}.items():monkeypatch.setenv('ARC_'+name,value)
    cfg=Config(str(ROOT/'backend/alembic.ini'));cfg.set_main_option('script_location',str(ROOT/'backend/alembic'))
    return cfg,create_engine(target)


def test_fresh_migration_matches_models(owner,tmp_path,monkeypatch):
    cfg,engine=migration_config(monkeypatch,owner,tmp_path)
    command.upgrade(cfg,'head');command.upgrade(cfg,'head')
    with engine.connect() as con:
        assert compare_metadata(MigrationContext.configure(con),Base.metadata)==[]
    command.downgrade(cfg,'0002_retention_marker');command.upgrade(cfg,'head')
    engine.dispose()


def test_populated_upgrade_backfills_reporting_without_recharging(owner,tmp_path,monkeypatch):
    cfg,engine=migration_config(monkeypatch,owner,tmp_path);command.upgrade(cfg,'0002_retention_marker')
    with owner['db'].session() as db:
        job=Job(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',operation='validate',idempotency_key='legacy',fingerprint='a'*64,input_data={},state='succeeded',billing_state='settled',reserved_milli=600,charged_milli=600,reserved_paid_milli=200,reserved_allowance_milli=400,completed_at=now())
        db.add(job);db.flush()
        db.add(Ledger(workspace_id=owner['wid'],environment='test',reference='settle:'+job.id,kind='debit',amount_milli=-200,description='Legacy settlement'))
        db.add(FileObject(workspace_id=owner['wid'],project_id=owner['pid'],environment='test',name='a.csv',content_type='text/csv',expected_size=2,size=2,state='ready',object_key='tenant/old-file',expires_at=now()+86400))
        db.commit()
        before=db.scalar(select(Wallet.balance_milli).where(Wallet.workspace_id==owner['wid'],Wallet.environment=='test'))
    meta=MetaData();meta.reflect(engine)
    for name in ('users','workspaces','memberships','projects','wallets','allowances','files','jobs','credit_ledger'):
        table=meta.tables[name]
        with owner['db'].engine.connect() as source,engine.begin() as destination:
            rows=list(source.execute(select(Base.metadata.tables[name])).mappings())
            for row in rows:destination.execute(table.insert().values(**{k:v for k,v in row.items() if k in table.columns}))
    cutoff=now();command.upgrade(cfg,'head')
    with engine.connect() as con:
        usage=con.execute(select(UsageEvent.__table__)).mappings().one()
        assert usage['gross_milli']==600 and usage['included_milli']==400 and usage['prepaid_milli']==200
        assert usage['price_version']=='legacy-v0.1'
        assert con.execute(select(Wallet.balance_milli).where(Wallet.environment=='test')).scalar()==before
        assert con.execute(select(StorageInterval.opened_at)).scalar()>=cutoff
    command.upgrade(cfg,'head')
    with engine.connect() as con:assert con.execute(select(func.count(UsageEvent.id))).scalar()==1
    with pytest.raises(RuntimeError,match='Refusing to discard'):command.downgrade(cfg,'0002_retention_marker')
    engine.dispose()
