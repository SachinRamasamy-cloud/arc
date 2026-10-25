from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from foundation.database.base import Base

class Database:
    def __init__(self, url):
        kwargs = {'pool_pre_ping': True}
        if url.startswith('sqlite'):
            kwargs['connect_args']={'check_same_thread': False, 'timeout': 30}
            if ':memory:' in url:
                from sqlalchemy.pool import StaticPool
                kwargs['poolclass']=StaticPool
            else:
                path=url.split('///',1)[-1]
                Path(path).parent.mkdir(parents=True,exist_ok=True)
        else:
            kwargs.update(pool_size=10,max_overflow=10,pool_timeout=10,pool_recycle=1800,pool_use_lifo=True)
            kwargs['connect_args']={'options':'-c statement_timeout=15000 -c lock_timeout=5000'}
        self.engine=create_engine(url,**kwargs)
        if url.startswith('sqlite'):
            @event.listens_for(self.engine,'connect')
            def configure_sqlite(conn, record):
                conn.execute('PRAGMA foreign_keys=ON')
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA busy_timeout=30000')
        self.Session=sessionmaker(self.engine,expire_on_commit=False)
    @contextmanager
    def session(self):
        with self.Session() as db:
            try: yield db
            finally: db.rollback()
    def create_test_schema(self): Base.metadata.create_all(self.engine)

def tenant_context(db, workspace_id):
    if db.bind.dialect.name=='postgresql':
        db.execute(text("SELECT set_config('app.workspace_id', :wid, true)"),{'wid':workspace_id})
