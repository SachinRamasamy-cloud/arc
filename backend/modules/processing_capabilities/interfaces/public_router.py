"""Rate-limited sample that executes the actual native engine."""
from fastapi import APIRouter, Request
from modules.processing_capabilities.public import run_native
router=APIRouter(prefix='/api/public',tags=['public demo'])
@router.post('/demo')
def demo(request:Request):
    request.app.state.limiter.check([('publicdemo:'+request.state.client_hash,5)])
    settings=request.app.state.settings
    sample={'operation':'normalize','data':[{'name':'  Ada Lovelace  ','email':' ADA@EXAMPLE.TEST '},{'name':' Grace Hopper ','email':' GRACE@EXAMPLE.TEST '}],'lowercase':['email']}
    return {'mode':'cloud','sample':True,'result':run_native(settings,sample)}
