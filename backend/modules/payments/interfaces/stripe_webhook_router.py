"""Verified Stripe payment ingress; never accepts a browser success redirect as payment proof."""
import asyncio
from fastapi import APIRouter, Request
from modules.payments.application.payments import verify_event, handle_event
router=APIRouter(tags=['payment provider callbacks'])
@router.post('/api/payments/stripe/webhook')
async def stripe_event(request:Request):
    raw=await request.body()
    settings=request.app.state.settings
    event=verify_event(raw,request.headers.get('stripe-signature',''),settings.stripe_webhook_secret)
    def process():
        with request.app.state.database.session() as db:
            handled=handle_event(db,settings,request.app.state.stripe,event)
            db.commit()
            return handled
    handled=await asyncio.to_thread(process)
    return {'received':True,'processed':handled}
