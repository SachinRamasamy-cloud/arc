"""Explicit, complete ORM registry for migration autogeneration."""
from foundation.database.base import Base
from modules.identity.infrastructure.persistence import models as identity_models  # noqa: F401
from modules.tenancy.infrastructure.persistence import models as tenancy_models  # noqa: F401
from modules.projects.infrastructure.persistence import models as projects_models  # noqa: F401
from modules.api_credentials.infrastructure.persistence import models as api_credentials_models  # noqa: F401
from modules.wallets.infrastructure.persistence import models as wallets_models  # noqa: F401
from modules.files.infrastructure.persistence import models as files_models  # noqa: F401
from modules.executions.infrastructure.persistence import models as executions_models  # noqa: F401
from modules.realtime_events.infrastructure.persistence import models as realtime_events_models  # noqa: F401
from modules.workflows.infrastructure.persistence import models as workflows_models  # noqa: F401
from modules.notifications.infrastructure.persistence import models as notifications_models  # noqa: F401
from modules.audit.infrastructure.persistence import models as audit_models  # noqa: F401
from modules.webhooks.infrastructure.persistence import models as webhooks_models  # noqa: F401
from modules.payments.infrastructure.persistence import models as payments_models  # noqa: F401
from modules.support.infrastructure.persistence import models as support_models  # noqa: F401
from modules.privacy.infrastructure.persistence import models as privacy_models  # noqa: F401
from modules.analytics.infrastructure.persistence import models as analytics_models  # noqa: F401
from modules.metering.infrastructure.persistence import models as metering_models  # noqa: F401
from modules.invoices.infrastructure.persistence import models as invoices_models  # noqa: F401
from modules.application_data.infrastructure.persistence import models as application_data_models  # noqa: F401
from modules.uploads.infrastructure.persistence import models as uploads_models  # noqa: F401
from modules.pricing.infrastructure.persistence import models as pricing_models  # noqa: F401

__all__=["Base"]
