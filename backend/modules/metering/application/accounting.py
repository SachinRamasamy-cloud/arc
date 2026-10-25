"""Integer-only metering and reporting shared by the API, portal and workers.

The caller owns the transaction. Acquire the workspace row before funds, jobs or
meters; no database transaction spans a Stripe/R2 request in this module.
"""
import calendar
import hashlib
import re
from datetime import datetime, timezone
from sqlalchemy import select, update, func, and_
from foundation.errors.public import PublicError
from modules.tenancy.public import Workspace
from modules.wallets.public import Wallet, Allowance, Ledger
from modules.metering.public import UsageEvent, UsageCounter
from modules.executions.public import Job
from modules.files.public import FileObject, StorageInterval, StorageStatement
from foundation.clock import now


def month_bounds(month: str | None = None, timestamp: int | None = None) -> tuple[int, int]:
    if month is not None:
        if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', month):
            raise PublicError('INVALID_INPUT')
        year, number = map(int, month.split('-'))
        start = datetime(year, number, 1, tzinfo=timezone.utc)
    else:
        start = datetime.fromtimestamp(now() if timestamp is None else timestamp, timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    return int(start.timestamp()), int(end.timestamp())


def lock_workspace(db, workspace_id: str):
    result = db.execute(update(Workspace).where(Workspace.id == workspace_id).values(name=Workspace.name))
    if result.rowcount != 1:
        raise PublicError('NOT_FOUND')


def debit_funds(db, workspace_id: str, environment: str, amount: int, timestamp: int | None = None) -> tuple[int, int]:
    """Spend included allowance first, then prepaid. Never touch reserved funds."""
    if amount < 0 or environment not in ('test', 'live'):
        raise PublicError('INVALID_INPUT')
    lock_workspace(db, workspace_id)
    at = now() if timestamp is None else timestamp
    wallet = db.scalar(select(Wallet).where(Wallet.workspace_id == workspace_id, Wallet.environment == environment).execution_options(populate_existing=True))
    if wallet is None or wallet.frozen:
        raise PublicError('FORBIDDEN')
    allowances = list(db.scalars(select(Allowance).where(Allowance.workspace_id == workspace_id, Allowance.expires_at > at, Allowance.balance_milli > Allowance.held_milli).order_by(Allowance.expires_at, Allowance.id).execution_options(populate_existing=True))) if environment == 'live' else []
    included_available = sum(a.balance_milli - a.held_milli for a in allowances)
    if included_available + wallet.balance_milli - wallet.held_milli < amount:
        raise PublicError('INSUFFICIENT_CREDITS')
    remaining = amount
    for allowance in allowances:
        take = min(remaining, allowance.balance_milli - allowance.held_milli)
        allowance.balance_milli -= take
        remaining -= take
        if not remaining:
            break
    wallet.balance_milli -= remaining
    wallet.spent_milli += remaining
    return amount - remaining, remaining


def check_project_budget(db, project, environment: str, amount: int):
    start, end = month_bounds()
    # Processing budget uses admission month, including reservations carried over
    # from the previous month. Other immediate operations use settlement month.
    jobs = db.scalar(select(func.coalesce(func.sum(Job.charged_milli), 0)).where(Job.project_id == project.id, Job.environment == environment, Job.created_at >= start, Job.created_at < end))
    holds = db.scalar(select(func.coalesce(func.sum(Job.reserved_milli), 0)).where(Job.project_id == project.id, Job.environment == environment, Job.billing_state == 'reserved'))
    other = db.scalar(select(func.coalesce(func.sum(UsageEvent.gross_milli), 0)).where(UsageEvent.project_id == project.id, UsageEvent.environment == environment, UsageEvent.service != 'processing', UsageEvent.occurred_at >= start, UsageEvent.occurred_at < end))
    if jobs + holds + other + amount > project.monthly_cap_milli:
        raise PublicError('BUDGET_EXCEEDED')


def record_usage(db, *, workspace_id, project_id, environment, reference, service,
                 operation, quantity, unit, price_version, gross, included, prepaid, at=None):
    if gross != included + prepaid or min(quantity, gross, included, prepaid) < 0:
        raise PublicError('INTERNAL_ERROR')
    entry = UsageEvent(workspace_id=workspace_id, project_id=project_id, environment=environment,
        reference=reference, service=service, operation=operation, quantity=quantity, unit=unit,
        price_version=price_version, gross_milli=gross, included_milli=included,
        prepaid_milli=prepaid, occurred_at=now() if at is None else at)
    db.add(entry)
    return entry


def bill_record_operation(db, settings, project, environment: str, reference: str, operation: str):
    """Per-1,000 rate rounded on the cumulative monthly meter, not each call."""
    lock_workspace(db, project.workspace_id)
    from modules.pricing.application.pricing import ensure_price
    ensure_price(db,settings)
    if db.scalar(select(UsageEvent.id).where(UsageEvent.reference == reference)):
        return
    start, _ = month_bounds()
    counter_id = hashlib.sha256(f'{project.id}:{environment}:records:{start}:{settings.price_version}'.encode()).hexdigest()
    counter = db.get(UsageCounter, counter_id, populate_existing=True)
    if not counter:
        counter = UsageCounter(id=counter_id, workspace_id=project.workspace_id, project_id=project.id,
            environment=environment, service='records', period_start=start, quantity=0,
            charged_milli=0, price_version=settings.price_version, rate_milli=settings.records_per_1000_milli)
        db.add(counter)
    target = ((counter.quantity + 1) * counter.rate_milli + 999) // 1000
    charge = target - counter.charged_milli
    check_project_budget(db, project, environment, charge)
    included, paid = debit_funds(db, project.workspace_id, environment, charge)
    record_usage(db, workspace_id=project.workspace_id, project_id=project.id,
        environment=environment, reference=reference, service='records', operation=operation,
        quantity=1, unit='request', price_version=counter.price_version, gross=charge, included=included, prepaid=paid)
    db.add(Ledger(workspace_id=project.workspace_id, environment=environment, reference=reference,
        kind='usage', amount_milli=-paid, description='Application data operation'))
    counter.quantity += 1
    counter.charged_milli = target


def close_storage_interval(db, file_id: str, at: int | None = None):
    db.execute(update(StorageInterval).where(StorageInterval.file_id == file_id, StorageInterval.closed_at.is_(None)).values(closed_at=now() if at is None else at))


def meter_storage(db, settings, workspace_id: str, environment: str, month: str | None = None, timestamp: int | None = None):
    """Reconcile measured bytes over time. No hidden negative balance on shortfall.

    Definition: 1 GB-month = 1e9 bytes held for 30 days. Round cumulative monthly
    charges once. Keep unsettled storage visible; block storage growth on arrears.
    """
    lock_workspace(db, workspace_id)
    start, end = month_bounds(month, timestamp)
    at = min(now() if timestamp is None else timestamp, end)
    if at < start:
        raise PublicError('INVALID_INPUT')
    identifier = hashlib.sha256(f'{workspace_id}:{environment}:storage:{start}'.encode()).hexdigest()
    statement = db.get(StorageStatement, identifier, populate_existing=True)
    if statement and at < statement.measured_until:
        return statement
    if not statement:
        from modules.pricing.application.pricing import ensure_price
        ensure_price(db,settings)
        statement = StorageStatement(id=identifier, workspace_id=workspace_id, environment=environment,
            period_start=start, period_end=end, measured_until=start, byte_seconds=0, assessed_milli=0,
            settled_milli=0, settled_byte_seconds=0, state='current', price_version=settings.price_version,
            rate_milli_gb_month=settings.storage_gb_month_milli)
        db.add(statement)
    # Database aggregates intervals. No customer payloads are loaded for billing.
    from sqlalchemy import case
    begins = case((StorageInterval.opened_at > start, StorageInterval.opened_at), else_=start)
    retained_until = case((StorageInterval.closed_at.is_(None), FileObject.expires_at), (StorageInterval.closed_at > FileObject.expires_at, FileObject.expires_at), else_=StorageInterval.closed_at)
    finishes = case((retained_until > at, at), else_=retained_until)
    total = db.scalar(select(func.coalesce(func.sum(StorageInterval.size_bytes * case((finishes > begins, finishes - begins), else_=0)), 0)).join(FileObject,FileObject.id==StorageInterval.file_id).where(
        StorageInterval.workspace_id == workspace_id, StorageInterval.environment == environment,
        StorageInterval.opened_at < at, (StorageInterval.closed_at.is_(None) | (StorageInterval.closed_at > start))))
    statement.byte_seconds = int(total)
    statement.measured_until = at
    denominator = 1_000_000_000 * 30 * 86400
    statement.assessed_milli = (statement.byte_seconds * statement.rate_milli_gb_month + denominator - 1) // denominator
    due = statement.assessed_milli - statement.settled_milli
    if due > 0 or statement.byte_seconds > (statement.settled_byte_seconds or 0):
        try:
            included, paid = debit_funds(db, workspace_id, environment, due)
        except PublicError as exc:
            if exc.code not in ('INSUFFICIENT_CREDITS', 'FORBIDDEN'):
                raise
            statement.state = 'payment_required'
            return statement
        ref = f'storage:{identifier}:{statement.byte_seconds}'
        record_usage(db, workspace_id=workspace_id, project_id=None, environment=environment,
            reference=ref, service='storage', operation='retention', quantity=statement.byte_seconds-(statement.settled_byte_seconds or 0), unit='byte_second',
            price_version=statement.price_version, gross=due, included=included, prepaid=paid, at=at - 1 if at == end else at)
        db.add(Ledger(workspace_id=workspace_id, environment=environment, reference=ref,
            kind='usage', amount_milli=-paid, description='Verified file storage'))
        statement.settled_milli = statement.assessed_milli
        statement.settled_byte_seconds = statement.byte_seconds
    statement.state = 'closed' if at == end else 'current'
    return statement


def usage_summary(db, workspace_id: str, environment: str, month: str | None = None, project_id: str | None = None):
    if environment not in ('test', 'live'):
        raise PublicError('INVALID_INPUT')
    start, end = month_bounds(month)
    filters = [UsageEvent.workspace_id == workspace_id, UsageEvent.environment == environment,
               UsageEvent.occurred_at >= start, UsageEvent.occurred_at < end]
    if project_id:
        filters.append(UsageEvent.project_id == project_id)
    rows = db.execute(select(UsageEvent.service, UsageEvent.unit,
        func.sum(UsageEvent.quantity), func.sum(UsageEvent.gross_milli), func.sum(UsageEvent.included_milli),
        func.sum(UsageEvent.prepaid_milli), func.count(UsageEvent.id)).where(*filters).group_by(UsageEvent.service, UsageEvent.unit)).all()
    items = [dict(service=r[0], unit=r[1], quantity=int(r[2]), gross_milli=int(r[3]), included_milli=int(r[4]), prepaid_milli=int(r[5]), events=r[6]) for r in rows]
    return {'period': {'start':start, 'end':end, 'timezone':'UTC', 'basis':'settled usage',
                      'month':datetime.fromtimestamp(start, timezone.utc).strftime('%Y-%m')},
            'environment':environment, 'services':items,
            'gross_milli':sum(x['gross_milli'] for x in items),
            'included_milli':sum(x['included_milli'] for x in items),
            'prepaid_milli':sum(x['prepaid_milli'] for x in items),
            'events':sum(x['events'] for x in items)}


def meter_storage_batch(database,settings,limit=100):
    """Round-robin workspace sweep; bounded work, at most once/hour/workspace."""
    with database.session() as db:
        ids=list(db.scalars(select(Workspace.id).where(Workspace.storage_checked_at<now()-3600,
            select(StorageInterval.id).where(StorageInterval.workspace_id==Workspace.id).exists())
            .order_by(Workspace.storage_checked_at,Workspace.id).limit(limit)))
    processed=0
    for wid in ids:
        with database.session() as db:
            lock_workspace(db,wid)
            for env in ('test','live'):
                first=db.scalar(select(func.min(StorageInterval.opened_at)).where(StorageInterval.workspace_id==wid,StorageInterval.environment==env))
                if first is None: continue
                arrears=list(db.scalars(select(StorageStatement).where(StorageStatement.workspace_id==wid,StorageStatement.environment==env,StorageStatement.state=='payment_required').order_by(StorageStatement.period_start).limit(12)))
                for prior in arrears:
                    meter_storage(db,settings,wid,env,datetime.fromtimestamp(prior.period_start,timezone.utc).strftime('%Y-%m'))
                last_closed=db.scalar(select(func.max(StorageStatement.period_end)).where(StorageStatement.workspace_id==wid,StorageStatement.environment==env,StorageStatement.state=='closed'))
                cursor=max(first,last_closed or first)
                # Bound catch-up to twelve periods per pass. Unpaid old periods are
                # retained and retried; do not silently skip them or erase objects.
                for _ in range(12):
                    if cursor>now(): break
                    start,end=month_bounds(timestamp=cursor)
                    month=datetime.fromtimestamp(start,timezone.utc).strftime('%Y-%m')
                    meter_storage(db,settings,wid,env,month)
                    if end>now(): break
                    cursor=end
            db.get(Workspace,wid).storage_checked_at=now();db.commit();processed+=1
    return processed
