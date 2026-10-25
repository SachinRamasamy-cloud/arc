"""invoices-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy import select
from foundation.clock import now
from foundation.errors.public import PublicError
from modules.metering.public import UsageEvent
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/billing')
def billing(wid:str,request:Request,environment:str='test',month:str|None=None,db=Depends(db_session)):
    from modules.invoices.application.billing_views import billing_view
    user=actor(request,db);workspace,_=workspace_access(db,wid,user,'finance')
    return billing_view(db,request.app.state.settings,workspace,environment,month)


@router.get('/workspaces/{wid}/usage')
def usage(wid:str,request:Request,environment:str='test',month:str|None=None,db=Depends(db_session)):
    from modules.metering.application.accounting import usage_summary
    workspace_access(db,wid,actor(request,db),'finance')
    return usage_summary(db,wid,environment,month)


@router.get('/workspaces/{wid}/usage/events')
def usage_events(wid:str,request:Request,environment:str='test',month:str|None=None,limit:int=Query(50,ge=1,le=100),cursor:str|None=None,db=Depends(db_session)):
    from modules.metering.application.accounting import month_bounds
    from foundation.crypto.security import signed_token, verify_signed
    workspace_access(db,wid,actor(request,db),'finance')
    if environment not in ('test','live'): raise PublicError('INVALID_INPUT')
    start,end=month_bounds(month)
    q=select(UsageEvent).where(UsageEvent.workspace_id==wid,UsageEvent.environment==environment,UsageEvent.occurred_at>=start,UsageEvent.occurred_at<end)
    if cursor:
        c=verify_signed(cursor,request.app.state.settings,'usage_cursor')
        if (c.get('wid'),c.get('env'),c.get('start'))!=(wid,environment,start): raise PublicError('INVALID_INPUT')
        q=q.where((UsageEvent.occurred_at<c['at'])|((UsageEvent.occurred_at==c['at'])&(UsageEvent.id<c['id'])))
    rows=list(db.scalars(q.order_by(UsageEvent.occurred_at.desc(),UsageEvent.id.desc()).limit(limit+1)))
    next_cursor=None
    if len(rows)>limit:
        last=rows[limit-1];next_cursor=signed_token({'purpose':'usage_cursor','wid':wid,'env':environment,'start':start,'at':last.occurred_at,'id':last.id,'exp':now()+1800},request.app.state.settings)
    return {'items':[{k:getattr(r,k) for k in ('id','project_id','service','operation','quantity','unit','price_version','gross_milli','included_milli','prepaid_milli','occurred_at')} for r in rows[:limit]],'next_cursor':next_cursor}

