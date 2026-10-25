"""tenancy-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from foundation.errors.public import PublicError
from modules.platform_operations.interfaces.schemas import OperatorAction
from modules.tenancy.public import Workspace
from foundation.database.dependencies import db_session
from modules.authorization.public import staff
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/customers')
def customers(request:Request,db=Depends(db_session)):
    staff(request,db)
    return {'items':[{k:getattr(w,k) for k in ('id','name','status','subscription_status','created_at')} for w in db.scalars(select(Workspace).order_by(Workspace.created_at.desc()).limit(100))]}


@router.patch('/customers/{wid}')
def change_customer(wid:str,body:OperatorAction,request:Request,db=Depends(db_session)):
    user=staff(request,db);workspace=db.get(Workspace,wid)
    if not workspace: raise PublicError('NOT_FOUND')
    workspace.status=body.status;audit(db,user.id,'operator.workspace_'+body.status,wid,wid,body.reason);db.commit();return {'status':workspace.status}

