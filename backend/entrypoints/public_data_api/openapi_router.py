"""Published machine-readable consumer contracts."""
from fastapi import APIRouter
from fastapi.openapi.utils import get_openapi
from entrypoints.public_data_api.routers import router as data_router
from modules.application_data.interfaces.records import api_router as records_api
from modules.uploads.interfaces.multipart import api_router as multipart_api
from modules.realtime_events.interfaces.data_router import router as events_api
router=APIRouter(tags=['API contract'])
@router.get('/v1/openapi.json')
def published_openapi():
    schema=get_openapi(title='Arc Processing API',version='1.0.0',routes=[*data_router.routes,*records_api.routes,*multipart_api.routes,*events_api.routes])
    schema.setdefault('components',{})['securitySchemes']={'ApiKey':{'type':'http','scheme':'bearer','description':'Project-scoped, server-side API secret.'}}
    schema['security']=[{'ApiKey':[]}]
    return schema
