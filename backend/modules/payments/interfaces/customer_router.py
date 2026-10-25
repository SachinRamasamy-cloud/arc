"""HTTP adapter only: validate identity and delegate financial operations."""
from fastapi import APIRouter,Request,Depends,Header
from modules.payments.interfaces.schemas import Checkout
from foundation.database.dependencies import db_session
from modules.authorization.public import current_user,workspace_access,require_live
from modules.payments.application.checkout import create_checkout
router=APIRouter(prefix='/api/console/v1',tags=['customer'])
@router.post('/workspaces/{wid}/billing/checkout')
def checkout(wid:str,body:Checkout,request:Request,idempotency_key:str=Header(alias='Idempotency-Key'),db=Depends(db_session)):
    user,session=current_user(request,db)
    workspace,_=workspace_access(db,wid,user,'finance')
    require_live(request.app.state.settings,user,session)
    return create_checkout(db,request.app.state.settings,request.app.state.stripe,workspace,body.kind,idempotency_key)

@router.post('/workspaces/{wid}/billing/portal')
def billing_portal(wid:str,request:Request,db=Depends(db_session)):
    user,session=current_user(request,db)
    workspace,_=workspace_access(db,wid,user,'finance')
    require_live(request.app.state.settings,user,session)
    return {'url':request.app.state.stripe.portal(workspace)['url']}
