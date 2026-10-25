import React,{useState} from 'react';

import {createRoot} from 'react-dom/client';

import {QueryClient,QueryClientProvider,useQuery,useMutation,useQueryClient} from '@tanstack/react-query';

import {createClient,ApiError,dateTime} from '@arc/client';

import {Brand,UIProvider,ErrorBoundary,Panel,PageHead,Button,Field,Badge,Status,ErrorNotice,Loading,Modal,InlineNote,Empty,useToast} from '@arc/ui';

import {ShieldCheck,LayoutDashboard,Users,Boxes,Wallet,LifeBuoy,LockKeyhole,History,ListChecks,LogOut,Check,AlertTriangle} from 'lucide-react';



import {api,cache} from '../../../app/platform';
export function Login(){const[email,setEmail]=useState(''),[password,setPassword]=useState(''),[code,setCode]=useState('');const login=useMutation({mutationFn:()=>api.request('/auth/login',{method:'POST',json:{email,password,code}}),onSuccess:()=>{cache.clear();void cache.invalidateQueries();location.reload();}});return <main className="operator-login"><Brand/><div className="staff-badge"><ShieldCheck size={15}/> INTERNAL OPERATIONS</div><h1>Authorized staff only.</h1><p>Customer portal credentials do not grant operator access.</p><form className="stack" onSubmit={e=>{e.preventDefault();login.mutate();}}><Field label="Work email"><input type="email" autoComplete="username" value={email} onChange={e=>setEmail(e.target.value)} required/></Field><Field label="Password"><input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></Field><Field label="Authenticator code"><input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={e=>setCode(e.target.value)} required/></Field>{login.error&&<ErrorNotice error={login.error}/>}<Button busy={login.isPending}>Enter operator console</Button></form><p className="small muted">Staff accounts are provisioned by an authorized operator. There is no public administrator signup.</p></main>}

