"""notifications-owned customer HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select, update
from foundation.clock import now
from modules.notifications.public import Notification
from foundation.database.dependencies import db_session
from modules.authorization.public import workspace_access, actor

router=APIRouter(prefix='/api/console/v1',tags=['customer'])

@router.get('/workspaces/{wid}/notifications')
def notifications(wid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user)
    return {'items':[{k:getattr(n,k) for k in ('id','category','title','message','link','read_at','created_at')} for n in db.scalars(select(Notification).where(Notification.workspace_id==wid,Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(100))]}


@router.post('/workspaces/{wid}/notifications/read')
def mark_notifications(wid:str,request:Request,db=Depends(db_session)):
    user=actor(request,db);workspace_access(db,wid,user)
    db.execute(update(Notification).where(Notification.workspace_id==wid,Notification.user_id==user.id,Notification.read_at.is_(None)).values(read_at=now()));db.commit();return {'message':'Notifications marked as read.'}

