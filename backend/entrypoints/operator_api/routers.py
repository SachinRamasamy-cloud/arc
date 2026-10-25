"""Surface routing composition root: register module-owned routes."""
from fastapi import APIRouter
router=APIRouter()
from modules.platform_operations.interfaces.operator_router import router as router_0
router.include_router(router_0)
from modules.tenancy.interfaces.operator_router import router as router_1
router.include_router(router_1)
from modules.service_catalog.interfaces.operator_router import router as router_2
router.include_router(router_2)
from modules.payments.interfaces.operator_router import router as router_3
router.include_router(router_3)
from modules.support.interfaces.operator_router import router as router_4
router.include_router(router_4)
from modules.privacy.interfaces.operator_router import router as router_5
router.include_router(router_5)
from modules.audit.interfaces.operator_router import router as router_6
router.include_router(router_6)
