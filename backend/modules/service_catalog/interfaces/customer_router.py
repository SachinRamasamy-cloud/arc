"""service_catalog-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from foundation.database.dependencies import db_session
from modules.authorization.public import actor
from modules.service_catalog.public import CATALOG

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/services')
def services(request:Request,db=Depends(db_session)):
    actor(request,db);return {'items':CATALOG}

