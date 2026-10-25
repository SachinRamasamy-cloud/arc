import argparse,base64,secrets,time,getpass,json
from pathlib import Path
from sqlalchemy import select
from foundation.config.settings import Settings
from foundation.database.session import Database
from modules.identity.public import User
from modules.notifications.public import Mail
from modules.tenancy.public import Workspace, Membership
from modules.wallets.public import Wallet
from modules.projects.public import Project
from foundation.crypto.security import password_hash, seal, unseal
from modules.wallets.application.use_cases import grant

def main():
    parser=argparse.ArgumentParser(description='Arc local operations')
    parser.add_argument('command',choices=['migrate','worker','mail','create-operator','demo','reconcile'])
    parser.add_argument('--email')
    parser.add_argument('--workspace')
    parser.add_argument('--apply',action='store_true',help='Recover verified provider events; never issue a charge')
    args=parser.parse_args();settings=Settings();database=Database(settings.database_url)
    if args.command=='reconcile':
        from modules.payments.application.reconciliation import accounting_report, reconcile_workspace
        from modules.payments.application.payments import StripeGateway
        if not args.workspace: raise SystemExit('--workspace is required')
        if args.apply: report=reconcile_workspace(database,settings,StripeGateway(settings),args.workspace)
        else:
            with database.session() as db: report=accounting_report(db,args.workspace)
        print(json.dumps(report,indent=2));return
    if args.command=='migrate':
        from alembic.config import Config
        from alembic import command
        import database as database_package
        database_path=Path(database_package.__file__).resolve().parent
        cfg=Config();cfg.set_main_option('script_location',str(database_path));cfg.set_main_option('version_locations',str(database_path/'migrations/versions'));command.upgrade(cfg,'head');return
    if args.command=='worker':
        from modules.files.application.storage import ObjectStore
        from modules.executions.application.worker import process_one, recover_expired
        from modules.notifications.application.deliveries import deliver_mail, deliver_webhook, reminders, cleanup_expired
        store=ObjectStore(settings);last=0
        while True:
            try:
                work=process_one(database,settings,store)
                deliver_mail(database,settings);deliver_webhook(database,settings)
                if time.time()-last>60:
                    from modules.metering.application.accounting import meter_storage_batch
                    meter_storage_batch(database,settings)
                    recover_expired(database,settings);reminders(database,settings);cleanup_expired(database,settings,store);last=time.time()
                if not work: time.sleep(0.5)
            except KeyboardInterrupt: break
            except Exception as exc:
                # No exception values: secrets can appear in DB/provider exception strings.
                print('Worker operation deferred:',type(exc).__name__);time.sleep(2)
        return
    if args.command=='mail':
        if settings.env=='production': raise SystemExit('Local mailbox is not available in production.')
        with database.session() as db:
            query=select(Mail).order_by(Mail.created_at.desc()).limit(20)
            if args.email: query=query.where(Mail.recipient==args.email)
            for mail in db.scalars(query): print(mail.recipient,mail.subject,unseal(mail.body_encrypted,settings,'mail'),sep='\n')
        return
    if args.command=='demo':
        if settings.env not in ('development','test'): raise SystemExit('Demo accounts cannot be created in production.')
        from pydantic import TypeAdapter,EmailStr
        email=str(TypeAdapter(EmailStr).validate_python(args.email or 'developer@example.com')).lower();password=secrets.token_urlsafe(18)
        with database.session() as db:
            if db.scalar(select(User.id).where(User.email==email)): raise SystemExit('Account already exists. Use the normal reset flow or a different email.')
            user=User(email=email,name='Alex Morgan',verified=True,password_hash=password_hash(password));db.add(user);db.flush()
            workspace=Workspace(name='Personal workspace');db.add(workspace);db.flush()
            db.add(Membership(user_id=user.id,workspace_id=workspace.id,role='owner'))
            db.add_all([Wallet(workspace_id=workspace.id,environment='test'),Wallet(workspace_id=workspace.id,environment='live')]);db.flush()
            grant(db,workspace.id,'test',100_000,'sandbox:'+workspace.id,'Test credits — no cash value')
            db.add(Project(workspace_id=workspace.id,name='My first API',description='Development project'))
            db.commit()
        print('Customer email:',email,'\nGenerated password:',password,'\nNo live balance or fictional traffic was created.');return
    if args.command=='create-operator':
        from pydantic import TypeAdapter,EmailStr
        email=str(TypeAdapter(EmailStr).validate_python(args.email or input('Operator email: ').strip())).lower()
        password=getpass.getpass('Password (12–128 characters): ')
        secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
        with database.session() as db:
            if db.scalar(select(User.id).where(User.email==email)): raise SystemExit('Email already exists; refuse implicit privilege escalation.')
            user=User(email=email,name='Platform operator',verified=True,staff=True,password_hash=password_hash(password),totp_secret=seal(secret,settings,'totp'))
            db.add(user);db.commit()
        print('Add this key to your authenticator now. It is not retrievable through the dashboard:\n'+secret)
if __name__=='__main__': main()
