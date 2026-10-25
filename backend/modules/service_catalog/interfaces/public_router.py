"""Public catalog metadata; never exposes unpublished internal configuration."""
from fastapi import APIRouter, Request
from modules.service_catalog.public import CATALOG
router=APIRouter(prefix='/api/public',tags=['public'])
@router.get('/catalog')
def catalog(request:Request):
    return {'items':CATALOG,'pricing_status':'published' if request.app.state.settings.pricing_approved else 'not_published','name':'Arc'}
@router.get('/config')
def config(request:Request):
    settings=request.app.state.settings
    return {'name':'Arc','environment':settings.env,'test_available':True,'live_available':settings.live_enabled,'max_file_bytes':settings.max_file_bytes,'legal_status':'approved' if settings.legal_approved else 'review_required'}
