"""wallets application use cases. Existing v0.2 behavior retained."""
import hashlib,json,math,secrets,time
from datetime import datetime,timezone
from sqlalchemy import select,update,func
from foundation.clock import now
from foundation.ids import uid
from foundation.crypto.security import seal
from foundation.errors.public import PublicError
from modules.wallets.public import Allowance, CreditAllocation, Ledger, Wallet
from modules.tenancy.public import Workspace

def wallet(db,wid,environment):
    value=db.scalar(select(Wallet).where(Wallet.workspace_id==wid,Wallet.environment==environment))
    if not value: raise PublicError('NOT_FOUND')
    return value


def wallet_dict(value):
    return {'balance_milli':value.balance_milli,'reserved_milli':value.held_milli,'available_milli':value.balance_milli-value.held_milli,'spent_milli':value.spent_milli,'environment':value.environment,'frozen':value.frozen}


def grant(db,wid,environment,amount,reference,description):
    if amount<=0: raise PublicError('INVALID_INPUT')
    db.execute(update(Workspace).where(Workspace.id==wid).values(name=Workspace.name))
    if db.scalar(select(Ledger.id).where(Ledger.reference==reference)): return False
    value=wallet(db,wid,environment)
    db.execute(update(Wallet).where(Wallet.id==value.id).values(balance_milli=Wallet.balance_milli+amount))
    db.add(Ledger(workspace_id=wid,environment=environment,reference=reference,kind='grant',amount_milli=amount,description=description))
    return True


def settle(db,settings,job,charge,success):
    if job.billing_state!='reserved': return
    if charge<0 or charge>job.reserved_milli: raise PublicError('INTERNAL_ERROR')
    ref='settle:'+job.id
    if db.scalar(select(Ledger.id).where(Ledger.reference==ref)): return
    included=min(charge,job.reserved_allowance_milli)
    paid=charge-included
    allocations=list(db.scalars(select(CreditAllocation).where(CreditAllocation.job_id==job.id).order_by(CreditAllocation.id)))
    # Old queued jobs can still settle safely after migration.
    reservations=[(a.allowance_id,a.reserved_milli) for a in allocations] or ([(job.allowance_id,job.reserved_allowance_milli)] if job.allowance_id else [])
    remaining=included
    for allowance_id, reserved in reservations:
        used=min(remaining,reserved);remaining-=used
        changed=db.execute(update(Allowance).where(Allowance.id==allowance_id,Allowance.held_milli>=reserved,Allowance.balance_milli>=used).values(held_milli=Allowance.held_milli-reserved,balance_milli=Allowance.balance_milli-used))
        if changed.rowcount!=1: raise PublicError('INTERNAL_ERROR')
    result=db.execute(update(Wallet).where(Wallet.workspace_id==job.workspace_id,Wallet.environment==job.environment,Wallet.held_milli>=job.reserved_paid_milli,Wallet.balance_milli>=paid).values(held_milli=Wallet.held_milli-job.reserved_paid_milli,balance_milli=Wallet.balance_milli-paid,spent_milli=Wallet.spent_milli+paid))
    if result.rowcount!=1: raise PublicError('INTERNAL_ERROR')
    job.charged_milli=charge;job.billing_state='settled' if success else 'released'
    if success:
        from modules.metering.application.accounting import record_usage
        record_usage(db,workspace_id=job.workspace_id,project_id=job.project_id,environment=job.environment,
            reference='job:'+job.id,service='processing',operation=job.operation,quantity=1,unit='job',
            price_version=job.price_version or 'development-1',gross=charge,included=included,prepaid=paid)

    db.add(Ledger(workspace_id=job.workspace_id,environment=job.environment,reference=ref,kind='debit' if paid else 'release',amount_milli=-paid,description='Processing completed' if success else 'Processing reservation released'))

