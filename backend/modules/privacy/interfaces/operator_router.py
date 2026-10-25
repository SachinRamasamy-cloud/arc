"""privacy-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from modules.privacy.public import PrivacyRequest
from foundation.database.dependencies import db_session
from modules.authorization.public import staff

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/privacy')
def privacy(request:Request,db=Depends(db_session)):
    staff(request,db)
    return {'items':[{k:getattr(t,k) for k in ('id','workspace_id','kind','state','created_at')} for t in db.scalars(select(PrivacyRequest).order_by(PrivacyRequest.created_at.desc()).limit(100))]}

