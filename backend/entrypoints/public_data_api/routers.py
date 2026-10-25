"""Surface routing composition root: register module-owned routes."""
from fastapi import APIRouter
router=APIRouter()
from modules.executions.interfaces.data_router import router as router_0
router.include_router(router_0)
from modules.files.interfaces.data_router import router as router_1
router.include_router(router_1)
