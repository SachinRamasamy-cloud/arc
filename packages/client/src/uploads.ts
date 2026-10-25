import {ApiError} from './core';
type Transport={request:(path:string, options?:any)=>Promise<any>};
export type UploadOptions={sha256:string;purpose:'processing'|'storage';retentionHours:number;resumeId?:string;signal?:AbortSignal;onSession?:(id:string)=>void;onProgress?:(message:string)=>void};
/** Bounded supported files; direct data transfer never carries a portal cookie/key. */
export async function uploadFile(client:Transport,base:string,file:Blob & {name:string},options:UploadOptions,transport:typeof fetch=fetch){
 if(!/^[a-f0-9]{64}$/.test(options.sha256)||file.size>16_000_000||file.size===0)throw new ApiError('INVALID_INPUT',422);
 const type=file.name.toLowerCase().endsWith('.csv')?'text/csv':file.name.toLowerCase().endsWith('.json')?'application/json':'text/plain';
 let id=options.resumeId;
 let created:any;
 if(!id){
  options.onProgress?.('Authorizing private storage');
  created=await client.request(base,{method:'POST',json:{name:file.name,size:file.size,content_type:type,purpose:options.purpose,retention_hours:options.retentionHours,sha256:options.sha256}});
  id=created.file.id;options.onSession?.(id!);
 }
 const resource=base.split('?')[0]+'/'+id;
 if(file.size>8*1024*1024||options.resumeId){
  const session=await client.request(resource+'/multipart',{method:'POST'});
  if(session.expected_size!==file.size||session.expected_digest!==options.sha256)throw new ApiError('CONFLICT',409);
  if(['assembled','complete'].includes(session.state))return client.request(resource+'/multipart/complete',{method:'POST'});
  const done=new Set<number>(session.parts.map((part:any)=>part.number));
  for(let part=1;part<=session.total_parts;part++){
   if(done.has(part))continue;
   if(options.signal?.aborted)throw new ApiError('UPLOAD_FAILED',0);
   const signed=await client.request(resource+`/multipart/parts/${part}`,{method:'POST'});
   const chunk=file.slice((part-1)*session.part_size,Math.min(file.size,part*session.part_size));
   const response=await transport(signed.url,{method:'PUT',body:chunk,credentials:'omit',redirect:'error',signal:options.signal});
   if(!response.ok)throw new ApiError('UPLOAD_FAILED',response.status);
   done.add(part);options.onProgress?.(`${done.size} of ${session.total_parts} parts stored`);
  }
  options.onProgress?.('Checking file integrity');
  return client.request(resource+'/multipart/complete',{method:'POST'});
 }
 options.onProgress?.('Uploading directly to storage');
 const response=await transport(created.upload_url,{method:'PUT',body:file,headers:created.headers,credentials:'omit',redirect:'error',signal:options.signal});
 if(!response.ok)throw new ApiError('UPLOAD_FAILED',response.status);
 options.onProgress?.('Checking file integrity');
 return client.request(resource+'/complete',{method:'POST'});
}
