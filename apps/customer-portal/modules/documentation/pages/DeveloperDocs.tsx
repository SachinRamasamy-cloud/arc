import React,{useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Link} from '@tanstack/react-router';
import {ArrowLeft,ArrowUpRight,BookOpen,FileCode2,Search,ShieldCheck} from 'lucide-react';
import {Brand,Button,CodeBlock,Loading,InlineNote} from '@arc/ui';

const sections=[
 {id:'start',title:'First request',keywords:'quickstart create project key',description:'Create a test project and generate a key with jobs:write. Keep the secret in your server environment, then submit a supported operation.',code:`curl -X POST "http://127.0.0.1:8000/v1/jobs" \\\n  -H "Authorization: Bearer $ARC_API_KEY" \\\n  -H "Idempotency-Key: your-stable-request-id" \\\n  -H "Content-Type: application/json" \\\n  -d '{"operation":"normalize","data":[{"name":" Ada "}],"max_credits_milli":10000}'`},
 {id:'security',title:'Authentication',keywords:'authorization scopes secrets keys',description:'Use a project-scoped Bearer key from your own backend. Never put a secret in a frontend application. Test and live keys are separate.',code:'Authorization: Bearer $ARC_API_KEY\nScopes: jobs:read, jobs:write, files:read, files:write, data:read, data:write'},
 {id:'processing',title:'Data processing',keywords:'validate csv json normalize lowercase',description:'Available operations: validate, normalize, csv_to_json and json_to_csv. Input fields are defined by the operation schema; arbitrary code is not supported.',code:'{"operation":"validate","data":[{"email":"a@example.com"}],"required_fields":["email"],"max_credits_milli":10000}'},
 {id:'files',title:'Files and uploads',keywords:'r2 direct storage multipart private data',description:'Authorize a private upload, send bytes directly to the returned signed URL, then complete and verify the object before processing. Multipart support is bounded by your account limits.',code:'POST /v1/files\nPOST /v1/files/{file_id}/complete\nGET  /v1/files/{file_id}/download'},
 {id:'events',title:'SSE and webhooks',keywords:'realtime progress events retry',description:'Read job snapshots with REST, subscribe to authenticated SSE events, or configure signed delivery callbacks in the portal. Reconnect using the last received event ID.',code:'GET /v1/jobs/{job_id}\nGET /v1/jobs/{job_id}/events\nLast-Event-ID: <last seen event>'},
 {id:'data',title:'Application data',keywords:'records database encrypt',description:'Store small encrypted JSON records per project and environment. This is a managed record API, not general SQL hosting.',code:'PUT /v1/data/{collection}/{key}\nGET /v1/data/{collection}/{key}\nDELETE /v1/data/{collection}/{key}'},
 {id:'workflow',title:'Custom workflows',keywords:'studio publish nodes pipeline',description:'Build a linear chain from approved operations, validate it, and publish an immutable version. Configure versions in the Visual Studio in your workspace.',code:'POST /v1/workflows/{workflow_id}/run'},
 {id:'billing',title:'Limits and billing',keywords:'rates credits quota pricing stripe 429',description:'Quotes come from the server. Work reserves capacity and credits before execution, settles actual usage and releases unused funds. 429 means retry after the applicable rate limit.',code:'1 credit = 1,000 milli-credits\nIdempotency-Key: stable for the same logical request\n429 Too Many Requests → respect Retry-After'},
];

export function DeveloperDocs(){
 const[search,setSearch]=useState('');
 const visible=sections.filter(s=>(s.title+' '+s.description+' '+s.keywords).toLowerCase().includes(search.toLowerCase()));
 const schema=useQuery({queryKey:['public-openapi-v1'],queryFn:async({signal})=>{
  const response=await fetch('/v1/openapi.json',{signal});
  if(!response.ok)throw new Error('API reference unavailable');
  return response.json();
 },staleTime:300_000,retry:false});
 const operations=Object.entries(schema.data?.paths||{}).flatMap(([path,value])=>Object.entries(value as Record<string,any>).filter(([method])=>['get','post','put','delete','patch'].includes(method)).map(([method,operation])=>({path,method,summary:(operation as any)?.summary||'API operation'})));
 const apiOrigin=import.meta.env.VITE_PUBLIC_API_URL||'http://127.0.0.1:8000';
 return <div className="developer-docs">
  <header className="docs-global-header"><Brand/><span className="docs-global-label"><BookOpen size={16}/> Developer documentation</span><Link to="/" className="button button-secondary"><ArrowLeft size={15}/> Back to workspace</Link></header>
  <div className="docs-intro"><p className="eyebrow">DEVELOPER GUIDE</p><h1>Connect an API in minutes.</h1><p>Supported operations, secure credentials, examples and accurate billing behavior—all in one place.</p><div className="docs-search-large"><Search size={18}/><input type="search" aria-label="Search the API guide" placeholder="Search APIs, files, webhooks, billing…" value={search} onChange={e=>setSearch(e.target.value)}/></div></div>
  <div className="docs-columns"><nav aria-label="Guide sections" className="docs-local-nav"><p>GUIDE</p>{sections.map(item=><a href={'#'+item.id} key={item.id}>{item.title}</a>)}<a href="#api-reference">API reference</a></nav><div className="docs-articles">
   {visible.map(s=><section id={s.id} key={s.id} className="docs-article"><h2>{s.title}</h2><p>{s.description}</p><CodeBlock code={s.code} language={s.id==='start'?'cURL':'API example'}/></section>)}
   {!visible.length&&<div className="docs-article"><h2>No matching topics</h2><p>Try searching for processing, uploads, SSE, authentication, or billing.</p><Button variant="secondary" onClick={()=>setSearch('')}>Show all topics</Button></div>}
   <section id="api-reference" className="docs-article"><h2>Public API reference</h2><p>These methods come from the API server's published OpenAPI contract. Internal staff endpoints are not included.</p>
    {schema.isPending?<Loading label="Loading public API methods"/>:schema.error?<InlineNote tone="warning">The API server isn't reachable. The guides above remain available. Start FastAPI to load the live method list. <button className="text-button" onClick={()=>void schema.refetch()}>Retry</button></InlineNote>:<div className="docs-methods">{operations.map(item=><div className="docs-method-row" key={item.method+item.path}><code>{item.method.toUpperCase()}</code><code>{item.path}</code><span>{item.summary}</span></div>)}</div>}
    <a className="text-button" href={apiOrigin+'/v1/openapi.json'} target="_blank" rel="noreferrer"><FileCode2 size={16}/> Download OpenAPI JSON <ArrowUpRight size={14}/></a>
   </section>
   <InlineNote><ShieldCheck size={15}/> Your production API keys belong on your backend. Platform auth and commercial identity-as-a-service are separate products.</InlineNote>
  </div></div>
 </div>;
}
