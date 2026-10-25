"""payments-owned operator HTTP handlers; no duplicate route implementations."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from modules.payments.public import Payment
from foundation.database.dependencies import db_session
from modules.authorization.public import staff
from modules.audit.application.use_cases import audit

router=APIRouter(prefix='/api/operator/v1',tags=['staff only'])

@router.get('/payments')
def payments(request:Request,db=Depends(db_session)):
    staff(request,db)
    return {'items':[{k:getattr(p,k) for k in ('id','workspace_id','kind','state','currency','amount_minor','created_at')} for p in db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(100))]}


@router.get('/customers/{wid}/accounting')
def customer_accounting(wid:str,request:Request,db=Depends(db_session)):
    from modules.payments.application.reconciliation import accounting_report
    user=staff(request,db);report=accounting_report(db,wid)
    audit(db,user.id,'operator.accounting_reviewed',wid,wid);db.commit();return report

