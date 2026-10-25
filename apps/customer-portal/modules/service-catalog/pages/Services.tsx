import React,{useMemo,useState} from 'react';
import {useNavigate} from '@tanstack/react-router';
import {ArrowUpRight,ArrowRight,Braces,FileJson2,Radio,Database,Workflow,Bell,HardDrive,CalendarClock,UserRound,Activity,Search,BookOpen,Plus} from 'lucide-react';
import {PageHead,Panel,Button,Badge,Empty,Loading,ErrorNotice} from '@arc/ui';
import {useScope,useApi,projectPath,workspacePath} from '../../../app/platform';

const icons:Record<string,React.ReactNode>={data:<Braces size={21}/>,files:<FileJson2 size={21}/>,events:<Radio size={21}/>,records:<Database size={21}/>,workflows:<Workflow size={21}/>,identity:<UserRound size={21}/>,storage:<HardDrive size={21}/>,notifications:<Bell size={21}/>,realtime:<Activity size={21}/>,scheduling:<CalendarClock size={21}/>};
const destinations:Record<string,string>={data:'playground',files:'files',events:'webhooks',records:'data',workflows:'studio'};
const groups:Record<string,string>={data:'Processing',files:'Processing',events:'Processing',records:'Application backend',workflows:'Processing',identity:'Application backend',storage:'Application backend',notifications:'Communications',realtime:'Communications',scheduling:'Automation'};
type Service={id:string;name:string;description:string;status:'available'|'roadmap';operations:string[];engine?:string};
export function Services(){
 const scope=useScope(),navigate=useNavigate();
 const query=useApi(['services'],'/services');
 const [search,setSearch]=useState('');
 const [filter,setFilter]=useState<'all'|'available'|'roadmap'>('all');
 const [category,setCategory]=useState('all');
 const products=(query.data?.items||[]) as Service[];
 const categories=Array.from(new Set(products.map(p=>groups[p.id]||'Other')));
 const filtered=useMemo(()=>products.filter(p=>{
  const matches=(p.name+' '+p.description+' '+p.operations.join(' ')).toLowerCase().includes(search.toLowerCase());
  return matches&&(filter==='all'||p.status===filter)&&(category==='all'||groups[p.id]===category);
 }),[products,search,filter,category]);
 function openService(service:Service){
  if(service.status!=='available')return;
  const destination=destinations[service.id];
  if(!scope.pid){void navigate({to:workspacePath(scope.wid,'projects') as any});return;}
  void navigate({to:projectPath(scope.wid,scope.pid,scope.environment,destination) as any});
 }
 return <>
  <PageHead eyebrow="API SERVICES" title="Find the service you need." description="Integrate ready-made APIs directly into your application. The service catalog is available before you create a project."
   action={<Button variant="secondary" onClick={()=>void navigate({to:'/docs'})}><BookOpen size={15}/> API docs</Button>}/>
  {!query.isPending&&!query.error&&<><div className="catalog-overview"><div><strong>{products.filter(p=>p.status==='available').length}</strong><span>Available services</span></div><div><strong>{products.filter(p=>p.status==='roadmap').length}</strong><span>Planned services</span></div><div><strong>Test first</strong><span>Try supported operations without live billing</span></div></div>
  <div className="catalog-tools">
   <label className="catalog-search"><Search size={17}/><input type="search" aria-label="Find an API service" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search validation, storage, login, events…"/></label>
   <div className="catalog-filters" role="group" aria-label="Service availability">{[['all','All'],['available','Available'],['roadmap','Planned']].map(([id,label])=><button type="button" key={id} aria-pressed={filter===id} onClick={()=>setFilter(id as any)}>{label}</button>)}</div>
   <label className="catalog-category">Category <select value={category} onChange={e=>setCategory(e.target.value)}><option value="all">All categories</option>{categories.map(c=><option value={c} key={c}>{c}</option>)}</select></label>
  </div>
  </>}
  {query.isPending?<Loading label="Loading API catalog"/>:query.error?<ErrorNotice error={query.error} retry={()=>void query.refetch()}/>:filtered.length===0?<Empty title="No matching services" description="Try another service name or reset the filters." action={<Button variant="secondary" onClick={()=>{setSearch('');setFilter('all');setCategory('all');}}>Reset filters</Button>}/>:<div className="service-grid catalog-grid">
   {filtered.map(service=><Panel key={service.id} className={`service-card catalog-card ${service.status==='roadmap'?'catalog-future':''}`}>
    <div className="catalog-card-head"><div className="service-icon">{icons[service.id]||<Braces size={21}/>}</div><Badge tone={service.status==='available'?'success':'neutral'}>{service.status==='available'?'Available':'Planned'}</Badge></div>
    <span className="catalog-label">{groups[service.id]||'Other'}</span>
    <h2>{service.name}</h2><p>{service.description}</p>
    {service.operations.length>0?<div className="tag-list">{service.operations.map(op=><code key={op}>{op}</code>)}</div>:<p className="small muted catalog-soon">This product isn't available for integration or billing yet.</p>}
    <div className="catalog-card-actions">
     {service.status==='available'?<Button onClick={()=>openService(service)}>{scope.pid?'Open service':'Create a project'} <ArrowRight size={14}/></Button>:<span className="small muted">Not available for requests yet</span>}
     <button className="text-button" type="button" onClick={()=>void navigate({to:'/docs'})}>Integration guide <ArrowUpRight size={13}/></button>
    </div>
   </Panel>)}
  </div>}
 </>;
}
