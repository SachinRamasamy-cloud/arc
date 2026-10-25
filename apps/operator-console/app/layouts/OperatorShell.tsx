import React,{useState} from 'react';

import {createRoot} from 'react-dom/client';

import {QueryClient,QueryClientProvider,useQuery,useMutation,useQueryClient} from '@tanstack/react-query';

import {createClient,ApiError,dateTime} from '@arc/client';

import {Brand,UIProvider,ErrorBoundary,Panel,PageHead,Button,Field,Badge,Status,ErrorNotice,Loading,Modal,InlineNote,Empty,useToast} from '@arc/ui';

import {ShieldCheck,LayoutDashboard,Users,Boxes,Wallet,LifeBuoy,LockKeyhole,History,ListChecks,LogOut,Check,AlertTriangle} from 'lucide-react';



import {api,cache} from '../platform';
import {Login} from '../../modules/staff-auth/pages/Login';
import {SimpleTable} from '../components/SimpleTable';
import {Page as PageOverview} from '../../modules/overview/pages/Page';
import {Page as PageCustomers} from '../../modules/customers/pages/Page';
import {Page as PageServices} from '../../modules/service-operations/pages/Page';
import {Page as PagePayments} from '../../modules/financial-reconciliation/pages/Page';
import {Page as PageSupport} from '../../modules/customer-support/pages/Page';
import {Page as PagePrivacy} from '../../modules/privacy-requests/pages/Page';
import {Page as PageAudit} from '../../modules/audit/pages/Page';
import {Page as PageRelease} from '../../modules/release-management/pages/Page';
const sections=[['overview','Overview',LayoutDashboard],['customers','Customers',Users],['services','Services',Boxes],['payments','Payments',Wallet],['support','Support',LifeBuoy],['privacy','Privacy queue',LockKeyhole],['audit','Staff audit',History],['release','Release checks',ListChecks]] as const;
export function App(){const[section,setSection]=useState('overview'),[selected,setSelected]=useState<any>(null),[reason,setReason]=useState(''),[reply,setReply]=useState('');const toast=useToast();const me=useQuery({queryKey:['staff'],queryFn:()=>api.request('/auth/me')});const data=useQuery({queryKey:['operator',section],queryFn:()=>api.request('/'+section),enabled:!!me.data,refetchInterval:section==='overview'?15000:false});const change=useMutation({mutationFn:()=>api.request(`/customers/${selected.id}`,{method:'PATCH',json:{status:selected.status==='active'?'suspended':'active',reason}}),onSuccess:()=>{setSelected(null);setReason('');void cache.invalidateQueries();toast('Customer status changed and audited.');}});const response=useMutation({mutationFn:()=>api.request(`/support/${selected.id}`,{method:'PATCH',json:{reply,state:'answered'}}),onSuccess:()=>{setSelected(null);setReply('');void cache.invalidateQueries();toast('Reply saved and queued for delivery.');}});const logout=useMutation({mutationFn:()=>api.request('/auth/logout',{method:'POST'}),onSuccess:()=>{cache.clear();location.reload();}});if(me.isLoading)return <Loading/>;if(me.error)return <Login/>;const d=data.data;
 return <div className="app-shell operator-shell"><aside className="sidebar"><div className="sidebar-brand"><Brand/><ShieldCheck size={18}/></div><div className="operator-label">INTERNAL OPERATIONS</div><nav className="side-navigation">{sections.map(([id,label,Icon])=><button className={`nav-item ${section===id?'active':''}`} key={id} onClick={()=>{setSection(id);setSelected(null);}}><Icon size={16}/><span>{label}</span></button>)}</nav><div className="sidebar-bottom"><div className="operator-identity">{me.data.user.email}</div><Button variant="ghost" onClick={()=>logout.mutate()} busy={logout.isPending}><LogOut size={15}/>Sign out</Button></div></aside><div className="app-stage"><header className="app-topbar"><div className="breadcrumb"><strong>Operator console</strong><Badge>Restricted access</Badge></div><span className="small muted">MFA verified · staff actions audited</span></header><main className="main-content"><PageHead eyebrow="PLATFORM OPERATIONS" title={sections.find(x=>x[0]===section)?.[1]||''} description="Operational metadata only. Customer secrets and private file contents are not exposed."/>{data.error?<ErrorNotice error={data.error}/>:data.isLoading?<Loading/>:d&&<>
 {section==='overview'&&<PageOverview d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='customers'&&<PageCustomers d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='services'&&<PageServices d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='payments'&&<PagePayments d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='support'&&<PageSupport d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='privacy'&&<PagePrivacy d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='audit'&&<PageAudit d={d} setSelected={setSelected} setReply={setReply}/>}
 {section==='release'&&<PageRelease d={d} setSelected={setSelected} setReply={setReply}/>}
 </>}</main></div><Modal open={!!selected&&section==='customers'} onClose={()=>setSelected(null)} title={selected?.status==='active'?'Suspend workspace':'Reactivate workspace'} description="This action affects customer operations. Provide a meaningful reason."><form className="stack" onSubmit={e=>{e.preventDefault();change.mutate();}}><Field label="Reason"><textarea minLength={10} maxLength={240} value={reason} onChange={e=>setReason(e.target.value)} required/></Field>{change.error&&<ErrorNotice error={change.error}/>}<Button variant="danger" busy={change.isPending}>Confirm audited change</Button></form></Modal><Modal open={!!selected&&section==='support'} onClose={()=>setSelected(null)} title="Reply to customer"><form className="stack" onSubmit={e=>{e.preventDefault();response.mutate();}}><Field label="Reply"><textarea value={reply} onChange={e=>setReply(e.target.value)} maxLength={4000} rows={7} required/></Field>{response.error&&<ErrorNotice error={response.error}/>}<Button busy={response.isPending}>Send reply</Button></form></Modal></div>
}
