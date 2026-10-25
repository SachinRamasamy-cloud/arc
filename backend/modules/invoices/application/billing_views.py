"""Customer-safe billing projection. No browser math is authoritative."""
from sqlalchemy import select, func
from modules.wallets.public import Allowance, Ledger, Wallet
from modules.payments.public import Payment
from modules.invoices.public import Invoice
from modules.files.public import StorageStatement, FileObject
from modules.metering.public import UsageEvent
from modules.tenancy.public import Workspace
from modules.application_data.public import CustomerRecord
from modules.pricing.public import PlanPrice
from foundation.clock import now
from modules.wallets.application.use_cases import wallet_dict
from modules.metering.application.accounting import usage_summary, month_bounds


def public_catalog(settings):
    return {
        'version': settings.price_version, 'approved': settings.pricing_approved,
        'currency': settings.currency,
        'subscription': {'amount_minor': settings.stripe_plan_minor, 'interval': 'month',
            'included_milli': settings.stripe_plan_allowance_milli},
        'credit_pack': {'amount_minor': settings.stripe_credit_pack_minor, 'credits_milli': settings.stripe_credit_pack_milli},
        'rates': [
            {'service':'processing', 'unit':'job step', 'base_milli':settings.processing_base_milli,
                'per_kib_milli':settings.processing_kib_milli, 'formula':'steps × (base + max(1, ceil(input bytes / 1024)) × rate)'},
            {'service':'records', 'unit':'1,000 successful API operations', 'rate_milli':settings.records_per_1000_milli,
                'formula':'Cumulative monthly rounding; no charge for rejected or replayed writes.'},
            {'service':'storage', 'unit':'GB-month', 'rate_milli':settings.storage_gb_month_milli,
                'formula':'1 GB-month = 1,000,000,000 bytes × 30 days; verified files only.'},
        ],
        'policy': 'Included allowance is used first. Prepaid consumption is not charged again by Stripe. Platform-caused job failures release reservations.',
    }



def plan_snapshot(db,settings):
    """Preserve a Stripe price's allowance and currency across deployment changes."""
    from foundation.errors.public import PublicError
    if not settings.stripe_plan_price_id: raise PublicError('INTEGRATION_UNAVAILABLE')
    row=db.get(PlanPrice,settings.stripe_plan_price_id)
    expected=(settings.currency,settings.stripe_plan_minor,settings.stripe_plan_allowance_milli)
    if row:
        if (row.currency,row.amount_minor,row.included_milli)!=expected: raise PublicError('INTEGRATION_UNAVAILABLE')
    else:
        row=PlanPrice(id=settings.stripe_plan_price_id,price_version=settings.price_version,
           currency=settings.currency,amount_minor=settings.stripe_plan_minor,included_milli=settings.stripe_plan_allowance_milli)
        db.add(row);db.flush()
    return row

def billing_view(db, settings, workspace, environment='test', month=None):
    from modules.pricing.public import UsagePrice
    from modules.pricing.application.pricing import FIELDS
    from foundation.errors.public import PublicError
    current_usage_price=db.get(UsagePrice,settings.price_version)
    if current_usage_price and any(getattr(current_usage_price,n)!=getattr(settings,n) for n in FIELDS):raise PublicError('INTEGRATION_UNAVAILABLE')
    summary = usage_summary(db, workspace.id, environment, month)
    start, end = summary['period']['start'], summary['period']['end']
    allowances = list(db.scalars(select(Allowance).where(Allowance.workspace_id==workspace.id, Allowance.expires_at>now()))) if environment=='live' else []
    wallets = list(db.scalars(select(Wallet).where(Wallet.workspace_id==workspace.id)))
    invoice_rows = list(db.scalars(select(Invoice).where(Invoice.workspace_id==workspace.id).order_by(Invoice.created_at.desc(), Invoice.id.desc()).limit(50))) if environment=='live' else []
    statements = list(db.scalars(select(StorageStatement).where(StorageStatement.workspace_id==workspace.id, StorageStatement.environment==environment, StorageStatement.period_start==start)))
    price=db.get(PlanPrice,workspace.subscription_price) if workspace.subscription_price else None
    current_plan={'amount_minor':price.amount_minor,'currency':price.currency,'included_milli':price.included_milli,'version':price.price_version} if price else None
    all_due=db.scalar(select(func.coalesce(func.sum(StorageStatement.assessed_milli-StorageStatement.settled_milli),0)).where(StorageStatement.workspace_id==workspace.id,StorageStatement.environment==environment))
    keys=('id','status','currency','amount_due_minor','amount_paid_minor','period_start','period_end','hosted_url','pdf_url','created_at')
    return {
        'environment':environment, 'wallets':[wallet_dict(w) for w in wallets], 'usage':summary,
        'included_available_milli':sum(a.balance_milli-a.held_milli for a in allowances),
        'included_reserved_milli':sum(a.held_milli for a in allowances),
        'allowance_expires_at':min((a.expires_at for a in allowances),default=None),
        'current_plan':current_plan,
        'subscription':{'status':workspace.subscription_status, 'renews_at':workspace.period_end if not workspace.cancel_at_period_end else None,
            'period_start':workspace.period_start, 'period_end':workspace.period_end,
            'cancel_at_period_end':workspace.cancel_at_period_end, 'price_id':workspace.subscription_price},
        'prices':public_catalog(settings), 'prices_approved':settings.pricing_approved,
        'checkout_available':bool(settings.stripe_secret_key and settings.stripe_credit_price_id and settings.live_enabled),
        'subscription_checkout_available':bool(settings.stripe_secret_key and settings.stripe_plan_price_id and settings.live_enabled and workspace.subscription_status not in ('active','trialing','past_due','incomplete','unpaid','paused')),
        'portal_available':bool(settings.stripe_secret_key and workspace.stripe_customer and settings.live_enabled),
        'live_enabled':settings.live_enabled,
        'ledger':[{k:getattr(l,k) for k in ('id','environment','kind','amount_milli','description','created_at')} for l in db.scalars(select(Ledger).where(Ledger.workspace_id==workspace.id, Ledger.environment==environment, Ledger.created_at>=start, Ledger.created_at<end).order_by(Ledger.created_at.desc(),Ledger.id.desc()).limit(100))],
        'payments':[{k:getattr(p,k) for k in ('id','kind','state','currency','amount_minor','created_at')} for p in db.scalars(select(Payment).where(Payment.workspace_id==workspace.id).order_by(Payment.created_at.desc()).limit(50))] if environment=='live' else [],
        'invoices':[{k:getattr(i,k) for k in keys} for i in invoice_rows],
        'storage':[{k:getattr(s,k) for k in ('byte_seconds','assessed_milli','settled_milli','measured_until','state','price_version')} for s in statements],
        'storage_unsettled_milli':int(all_due), 'storage_selected_month_unsettled_milli':sum(s.assessed_milli-s.settled_milli for s in statements),
        'reporting_note':'Usage is grouped by settlement month in UTC. Subscription renewal follows its actual Stripe period; project caps reset by UTC calendar month.',
    }


def invoice_url(value):
    """Do not turn arbitrary provider metadata into a frontend redirect."""
    from urllib.parse import urlparse
    if not isinstance(value,str): return None
    parsed=urlparse(value)
    if parsed.scheme=='https' and parsed.hostname in ('invoice.stripe.com','pay.stripe.com','billing.stripe.com') and not parsed.username:
        return value
    return None


def sync_invoice(db, workspace, obj):
    identifier=obj.get('id')
    if not isinstance(identifier,str) or not identifier.startswith('in_'): return
    invoice=db.get(Invoice,identifier)
    if invoice and invoice.workspace_id != workspace.id:
        from foundation.errors.public import PublicError
        raise PublicError('INVALID_INPUT')
    if not invoice:
        invoice=Invoice(id=identifier,workspace_id=workspace.id,status='open',currency=obj.get('currency','usd'))
        db.add(invoice)
    # An older payment-failure event must not reverse a paid invoice.
    if invoice.status=='paid' and obj.get('status')!='paid': return
    invoice.status=obj.get('status','open')
    invoice.subscription_id=obj.get('subscription') or obj.get('parent',{}).get('subscription_details',{}).get('subscription')
    invoice.currency=obj.get('currency',invoice.currency)
    invoice.amount_due_minor=int(obj.get('amount_due') or 0)
    invoice.amount_paid_minor=int(obj.get('amount_paid') or 0)
    invoice.period_start=obj.get('period_start')
    invoice.period_end=obj.get('period_end')
    invoice.hosted_url=invoice_url(obj.get('hosted_invoice_url'))
    invoice.pdf_url=invoice_url(obj.get('invoice_pdf'))
    invoice.created_at=int(obj.get('created') or now())
    invoice.updated_at=now()
