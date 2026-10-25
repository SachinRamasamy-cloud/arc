from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
import logging
log=logging.getLogger('arc.security')

MESSAGES={
 'UNAUTHORIZED':(401,'Please sign in or check your API credentials.'),
 'INVALID_CREDENTIALS':(401,'The sign-in details could not be verified.'),
 'FORBIDDEN':(403,'You do not have permission for this action.'),
 'NOT_FOUND':(404,'The requested resource was not found.'),
 'INVALID_INPUT':(422,'Review the input and try again.'),
 'CONFLICT':(409,'This action conflicts with the current resource state.'),
 'RATE_LIMITED':(429,'Too many requests. Please wait before trying again.'),
 'INSUFFICIENT_CREDITS':(402,'There are not enough available credits for this request.'),
 'BUDGET_EXCEEDED':(402,'This request would exceed the configured spending limit.'),
 'CAPACITY_REACHED':(429,'Your concurrent processing limit has been reached.'),
 'EMAIL_UNVERIFIED':(403,'Verify your email address to continue.'),
 'MFA_REQUIRED':(403,'Enable multi-factor authentication for this action.'),
 'INVALID_CODE':(401,'The verification code is invalid or expired.'),
 'INVALID_TOKEN':(400,'This link is invalid, expired, or already used.'),
 'CSRF_FAILED':(403,'Your security session needs to be refreshed. Reload and try again.'),
 'ORIGIN_BLOCKED':(403,'This request origin is not allowed.'),
 'LIVE_UNAVAILABLE':(403,'Live access is not enabled. You can continue in the test environment.'),
 'INTEGRATION_UNAVAILABLE':(503,'This service is not configured yet. Please contact support.'),
 'SERVICE_UNAVAILABLE':(503,'The service is temporarily unavailable. Please try again.'),
 'PAYLOAD_TOO_LARGE':(413,'The input exceeds the supported size limit.'),
 'UPLOAD_NOT_READY':(409,'The file must finish verification before it can be used.'),
 'UNSUPPORTED_OPERATION':(422,'This operation or format is not supported.'),
 'POLICY_LIMIT':(422,'The requested limit exceeds your available allowance.'),
 'WORKFLOW_INVALID':(422,'The workflow has an invalid connection or unsupported operation.'),
 'STALE_DRAFT':(409,'This workflow has newer changes. Reload before saving.'),
 'PROCESSING_FAILED':(422,'Processing could not be completed for this input.'),
 'PROCESSING_TIMEOUT':(422,'Processing exceeded its execution limit.'),
 'EVENT_CURSOR_EXPIRED':(409,'Refresh the execution details before reconnecting.'),
 'WEBHOOK_BLOCKED':(422,'Enter an allowed public HTTPS endpoint.'),
 'INTERNAL_ERROR':(500,'Something went wrong. Use the request reference when contacting support.')}
class PublicError(Exception):
    def __init__(self, code, fields=None, retry_after=None):
        self.code=code if code in MESSAGES else 'INTERNAL_ERROR'
        self.fields=fields
        self.retry_after=retry_after

def problem(request, error):
    status,message=MESSAGES[error.code]
    body={'type':'about:blank','title':message,'status':status,'code':error.code,'detail':message,
          'request_id':getattr(request.state,'request_id','unavailable')}
    if error.fields: body['fields']=error.fields
    headers={}
    if error.retry_after is not None: headers['Retry-After']=str(error.retry_after)
    return JSONResponse(body,status_code=status,media_type='application/problem+json',headers=headers)

def install_handlers(app):
    @app.exception_handler(PublicError)
    async def public_handler(req,exc): return problem(req,exc)
    @app.exception_handler(RequestValidationError)
    async def validation_handler(req,exc):
        # Never include the submitted input, repr(ctx), or arbitrary validator text.
        fields=[{'field':'.'.join(str(p) for p in e['loc'] if p!='body'),'message':'Check this value.'} for e in exc.errors()[:16]]
        return problem(req,PublicError('INVALID_INPUT',fields=fields))
    @app.exception_handler(HTTPException)
    async def http_handler(req,exc):
        code={404:'NOT_FOUND',401:'UNAUTHORIZED',403:'FORBIDDEN',413:'PAYLOAD_TOO_LARGE',405:'NOT_FOUND'}.get(exc.status_code,'INVALID_INPUT')
        return problem(req,PublicError(code))
    @app.exception_handler(Exception)
    async def unknown_handler(req,exc):
        # Exception strings can contain secrets; record only its type and correlation ID.
        log.error('unhandled type=%s request_id=%s',type(exc).__name__,getattr(req.state,'request_id',''))
        return problem(req,PublicError('INTERNAL_ERROR'))
