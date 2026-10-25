"""Event-only ASGI surface; exposes no management or staff API routes."""
from fastapi import APIRouter
from modules.realtime_events.interfaces.customer_router import router as customer_event_router
from modules.realtime_events.interfaces.data_router import router as data_event_router
router=APIRouter()
router.include_router(customer_event_router)
router.include_router(data_event_router)
