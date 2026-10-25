"""Surface routing composition root: register module-owned routes."""
from fastapi import APIRouter
router=APIRouter()
from modules.tenancy.interfaces.customer_router import router as router_0
router.include_router(router_0)
from modules.projects.interfaces.customer_router import router as router_1
router.include_router(router_1)
from modules.service_catalog.interfaces.customer_router import router as router_2
router.include_router(router_2)
from modules.rate_limits.interfaces.customer_router import router as router_3
router.include_router(router_3)
from modules.api_credentials.interfaces.customer_router import router as router_4
router.include_router(router_4)
from modules.executions.interfaces.customer_router import router as router_5
router.include_router(router_5)
from modules.files.interfaces.customer_router import router as router_6
router.include_router(router_6)
from modules.workflows.interfaces.customer_router import router as router_7
router.include_router(router_7)
from modules.webhooks.interfaces.customer_router import router as router_8
router.include_router(router_8)
from modules.notifications.interfaces.customer_router import router as router_9
router.include_router(router_9)
from modules.audit.interfaces.customer_router import router as router_10
router.include_router(router_10)
from modules.security_center.interfaces.customer_router import router as router_11
router.include_router(router_11)
from modules.invoices.interfaces.customer_router import router as router_12
router.include_router(router_12)
from modules.payments.interfaces.customer_router import router as router_13
router.include_router(router_13)
from modules.privacy.interfaces.customer_router import router as router_14
router.include_router(router_14)
from modules.support.interfaces.customer_router import router as router_15
router.include_router(router_15)
