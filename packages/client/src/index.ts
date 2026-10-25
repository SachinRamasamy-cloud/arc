export * from './core';
import { ApiError, normalizeError } from './core';
export type Audience='console'|'operator';
export function createClient(audience:Audience,base='') {
  let csrf='';
  const prefix='/api/'+audience+'/v1';
  async function refreshCsrf() {
    const response=await fetch(base+prefix+'/auth/csrf',{credentials:'include',cache:'no-store'});
    if(!response.ok)throw new ApiError('SERVICE_UNAVAILABLE',response.status);
    const body=await response.json();csrf=body.csrf_token;return csrf;
  }
  async function request<T=any>(path:string,options:RequestInit & {json?:unknown}={}):Promise<T>{
    const {json,...init}=options;const method=(init.method||'GET').toUpperCase();
    if(!['GET','HEAD'].includes(method) && !csrf)await refreshCsrf();
    const headers=new Headers(init.headers);
    if(json!==undefined)headers.set('Content-Type','application/json');
    if(!['GET','HEAD'].includes(method))headers.set('X-CSRF-Token',csrf);
    let response:Response;
    try{ response=await fetch(base+prefix+path,{...init,method,headers,body:json!==undefined?JSON.stringify(json):init.body,credentials:'include',cache:'no-store'}); }
    catch{ throw new ApiError('NETWORK_ERROR'); }
    let body:any;
    try{body=await response.json();}catch{body={};}
    if(!response.ok){
      const error=normalizeError(body,response.status);
      if(error.code==='CSRF_FAILED')csrf='';
      throw error; // Mutations are never blindly replayed.
    }
    if(body.csrf_token)csrf=body.csrf_token;
    return body as T;
  }
  return {request,refreshCsrf,base,prefix,clearSession(){csrf='';}};
}
export {uploadFile} from './uploads';
