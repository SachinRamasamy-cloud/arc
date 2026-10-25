"""ASGI application factories. Production deploys surfaces separately."""
import asyncio,json,time,logging
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from foundation.config.settings import Settings
from foundation.database.session import Database
from modules.analytics.public import RequestLog
from foundation.ids import uid
from foundation.clock import now
from foundation.errors.public import PublicError, problem, install_handlers
from foundation.crypto.security import check_csrf, keyed_digest
from modules.rate_limits.infrastructure.limiter import Limiter, StreamGate
from modules.files.application.storage import ObjectStore
from modules.payments.application.payments import StripeGateway
from modules.identity.interfaces.auth import create_auth_router
from entrypoints.customer_api.routers import router as console_router
from entrypoints.operator_api.routers import router as operator_router
from entrypoints.public_data_api.routers import router as data_router
from modules.realtime_events.interfaces.customer_router import router as console_events_router
from modules.realtime_events.interfaces.data_router import router as data_events_router
from entrypoints.events_api.routers import router as events_router
from modules.analytics.interfaces.customer_router import router as request_logs_router
from modules.service_catalog.interfaces.public_router import router as catalog_router
from modules.processing_capabilities.interfaces.public_router import router as demo_router
from modules.support.interfaces.public_router import router as contact_router
from modules.payments.interfaces.stripe_webhook_router import router as stripe_webhook_router
from entrypoints.public_data_api.openapi_router import router as openapi_router
from entrypoints.public_data_api.docs_router import router as docs_router
from modules.files.interfaces.local_storage_router import router as local_storage_router
from modules.uploads.interfaces.local_multipart_router import router as local_multipart_router
log=logging.getLogger('arc.requests')

class SafetyMiddleware:
    def __init__(self,app,settings,database): self.app=app;self.settings=settings;self.database=database
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        scope.setdefault('state',{})
        scope['state']['request_id']=uid('req')
        peer=scope.get('client') or ('unknown',0)
        scope['state']['client_hash']=keyed_digest(peer[0],self.settings.secret_key)[:24]
        path=scope['path'];method=scope['method'];started=time.monotonic()
        maximum=self.settings.max_file_bytes if self.settings.env!='production' and path.startswith(('/api/local-storage/','/api/local-multipart/')) else self.settings.max_body_bytes
        parts=[];size=0
        try:
            if method not in ('GET','HEAD','OPTIONS'):
                while True:
                    message=await asyncio.wait_for(receive(),timeout=15)
                    if message['type']=='http.disconnect': return
                    part=message.get('body',b'');size+=len(part)
                    if size>maximum: raise PublicError('PAYLOAD_TOO_LARGE')
                    parts.append(part)
                    if not message.get('more_body'): break
            consumed=False
            async def bounded_receive():
                nonlocal consumed
                if not consumed and parts:
                    consumed=True;return {'type':'http.request','body':b''.join(parts),'more_body':False}
                return await receive()
            request=Request(scope,receive=bounded_receive)
            origin=request.headers.get('origin')
            allowed={self.settings.portal_origin,self.settings.operator_origin,self.settings.site_origin,self.settings.api_origin}
            if origin and origin not in allowed: raise PublicError('ORIGIN_BLOCKED')
            audience='console' if path.startswith('/api/console/') else 'operator' if path.startswith('/api/operator/') else None
            if audience:
                expected=self.settings.portal_origin if audience=='console' else self.settings.operator_origin
                if origin and origin!=expected: raise PublicError('ORIGIN_BLOCKED')
                if method not in ('GET','HEAD','OPTIONS'): check_csrf(request,self.settings,audience)
        except asyncio.TimeoutError:
            request=Request(scope);response=problem(request,PublicError('INVALID_INPUT'));return await response(scope,receive,send)
        except PublicError as exc:
            request=Request(scope);response=problem(request,exc);return await response(scope,receive,send)
        response_status=500;response_started=False
        async def safe_send(message):
            nonlocal response_status,response_started
            if message['type']=='http.response.start':
                response_started=True;response_status=message['status']
                headers=list(message.get('headers',[]))
                headers.extend([(b'x-request-id',scope['state']['request_id'].encode()),(b'x-content-type-options',b'nosniff'),(b'referrer-policy',b'no-referrer'),(b'x-frame-options',b'DENY'),(b'cache-control',b'no-store'),(b'content-security-policy',b"default-src 'none'; frame-ancestors 'none'")])
                if self.settings.secure_cookies: headers.append((b'strict-transport-security',b'max-age=31536000; includeSubDomains'))
                message['headers']=headers
            await send(message)
        try: await self.app(scope,bounded_receive,safe_send)
        except Exception as exc:
            log.error('request_failed type=%s reference=%s',type(exc).__name__,scope['state']['request_id'])
            if not response_started: await problem(Request(scope),PublicError('INTERNAL_ERROR'))(scope,receive,safe_send)
        finally:
            if path.startswith('/v1/') and scope['state'].get('workspace_id'):
                def record():
                    try:
                        with self.database.session() as db:
                            route=getattr(scope.get('route'),'path','/v1/unknown')
                            db.add(RequestLog(id=scope['state']['request_id'],workspace_id=scope['state'].get('workspace_id'),project_id=scope['state'].get('project_id'),environment=scope['state'].get('environment'),method=method,route=route,status=response_status,duration_ms=round((time.monotonic()-started)*1000)))
                            if scope['state'].get('key_id'):
                                from modules.api_credentials.public import ApiKey
                                from sqlalchemy import update,or_
                                db.execute(update(ApiKey).where(ApiKey.id==scope['state']['key_id'],or_(ApiKey.last_used_at.is_(None),ApiKey.last_used_at<now()-60)).values(last_used_at=now()))
                            db.commit()
                    except Exception: log.warning('request_log_unavailable reference=%s',scope['state']['request_id'])
                await asyncio.to_thread(record)

def create_app(settings=None,database=None,surface='all'):
    settings=settings or Settings()
    if settings.env=='production' and surface=='all': raise ValueError('Deploy distinct console, data and operator ASGI factories in production.')
    database=database or Database(settings.database_url)
    app=FastAPI(title='Arc '+surface,version='0.3.3',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.settings=settings;app.state.database=database;app.state.limiter=Limiter(settings)
    app.state.stream_gate=StreamGate(app.state.limiter);app.state.store=ObjectStore(settings);app.state.stripe=StripeGateway(settings)
    install_handlers(app)
    from modules.application_data.interfaces.records import api_router as records_api, console_router as records_console
    from modules.uploads.interfaces.multipart import api_router as multipart_api, console_router as multipart_console
    if surface in ('all','console'):
        app.include_router(create_auth_router('console'));app.include_router(console_router);app.include_router(records_console);app.include_router(multipart_console)
        app.include_router(console_events_router)
        app.include_router(request_logs_router)
    if surface in ('all','operator'): app.include_router(create_auth_router('operator'));app.include_router(operator_router)
    if surface in ('all','data'): app.include_router(data_router);app.include_router(records_api);app.include_router(multipart_api)
    @app.get('/health/live')
    def live(): return {'status':'ok'}
    @app.get('/health/ready')
    def ready():
        try:
            with database.session() as db: db.execute(text('SELECT 1'))
            if app.state.limiter.redis: app.state.limiter.redis.ping()
        except Exception: raise PublicError('SERVICE_UNAVAILABLE')
        return {'status':'ready'}
    if surface in ('all','console','data'):
        app.include_router(catalog_router)
        app.include_router(demo_router)
        app.include_router(contact_router)
        app.include_router(openapi_router)
        app.include_router(docs_router)
        app.include_router(stripe_webhook_router)
    if surface in ('all','data'):
        app.include_router(data_events_router)
    if surface=='events':
        app.include_router(events_router)
    if settings.env!='production' and settings.storage_mode=='local' and surface in ('all','console','data'):
        app.include_router(local_storage_router)
        app.include_router(local_multipart_router)
    app.add_middleware(SafetyMiddleware,settings=settings,database=database)
    app.add_middleware(CORSMiddleware,allow_origins=[settings.portal_origin,settings.operator_origin,settings.site_origin],allow_credentials=True,allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Content-Type','X-CSRF-Token','Authorization','Idempotency-Key','Last-Event-ID'],expose_headers=['X-Request-ID','Retry-After'])
    return app

def development(): return create_app(surface='all')
def console(): return create_app(surface='console')
def data(): return create_app(surface='data')
def operator(): return create_app(surface='operator')
