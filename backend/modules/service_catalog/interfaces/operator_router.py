"""service_catalog-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from foundation.database.dependencies import db_session
from modules.authorization.public import staff
from modules.service_catalog.public import CATALOG

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/services')
def services(request:Request,db=Depends(db_session)):
    staff(request,db);return {'items':CATALOG,'change_policy':'Native capabilities and price changes require a reviewed code release. No runtime code upload is allowed.'}

