"""Version labels are immutable contracts, not mutable environment nicknames."""
from sqlalchemy.exc import IntegrityError
from modules.pricing.public import UsagePrice
from foundation.errors.public import PublicError
FIELDS=('processing_base_milli','processing_kib_milli','records_per_1000_milli','storage_gb_month_milli')

def ensure_price(db,settings):
    row=db.get(UsagePrice,settings.price_version)
    values={name:getattr(settings,name) for name in FIELDS}
    if row is None:
        # Concurrent workspaces can first register the same global version. The
        # unique key resolves the race without corrupting the outer transaction.
        try:
            with db.begin_nested():
                row=UsagePrice(version=settings.price_version,**values);db.add(row);db.flush()
        except IntegrityError:
            row=db.get(UsagePrice,settings.price_version,populate_existing=True)
    if row is None or any(getattr(row,name)!=value for name,value in values.items()):raise PublicError('INTEGRATION_UNAVAILABLE')
    return row
