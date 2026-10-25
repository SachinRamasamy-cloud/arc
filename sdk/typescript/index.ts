/** Server-side client. Never bundle the secret API key into a browser application. */
export type Operation='validate'|'normalize'|'csv_to_json'|'json_to_csv';
export type RunInput={operation:Operation;data?:unknown;file_id?:string;required_fields?:string[];mappings?:Record<string,string>;lowercase?:string[];max_credits_milli?:number};
export type Job={id:string;state:'queued'|'running'|'succeeded'|'failed'|'canceled';result?:unknown;charged_milli:number;error_code?:string};
export class ArcError extends Error {
 constructor(readonly status:number,readonly code:string,readonly requestId:string){super(`API request failed (${status}, ${code}). Reference: ${requestId}`);}
}
export class ArcClient {
 constructor(private readonly baseURL:string,private readonly secret:string,private readonly transport:typeof fetch=fetch){if(!secret)throw new Error('A server-side API key is required.');}
 private async request<T>(path:string,init:RequestInit={}):Promise<T>{
  const headers=new Headers(init.headers);headers.set('Authorization',`Bearer ${this.secret}`);
  const response=await this.transport(this.baseURL.replace(/\/$/,'')+path,{...init,headers,redirect:'error',signal:init.signal||AbortSignal.timeout(30_000)});
  const body=await response.json().catch(()=>({}));
  if(!response.ok){const code=typeof body.code==='string'&&/^[A-Z_]{1,64}$/.test(body.code)?body.code:'INTERNAL_ERROR';const ref=response.headers.get('x-request-id')||'';throw new ArcError(response.status,code,/^req_[a-f0-9]{32}$/.test(ref)?ref:'');}
  return body as T;
 }
 run(input:RunInput,idempotencyKey:string):Promise<{job:Job;created:boolean}>{
  if(!idempotencyKey)throw new Error('Keep one idempotency key per logical operation.');
  return this.request('/v1/jobs',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':idempotencyKey},body:JSON.stringify(input)});
 }
 job(id:string):Promise<{job:Job}>{if(!/^run_[a-zA-Z0-9]+$/.test(id))throw new Error('Invalid job ID.');return this.request('/v1/jobs/'+id);}
}
