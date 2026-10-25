import React,{useEffect,useState} from 'react';
import {useMutation,useQueryClient} from '@tanstack/react-query';
import {useNavigate} from '@tanstack/react-router';
import {ShieldCheck,LockKeyhole,KeyRound,ArrowUpRight,Plus,Download,Bell,Check,Wallet,Activity,Users,Settings as SettingsIcon,Send,Trash2,AlertTriangle} from 'lucide-react';
import {PageHead,Panel,Button,Field,Status,Badge,Loading,ErrorNotice,InlineNote,Empty,Modal,Confirm,CodeBlock,useToast} from '@arc/ui';
import {credits,dateTime,allowed} from '@arc/client';
import {api,useScope,useApi,useAction,projectPath,workspacePath} from '../../../app/platform';
import {DataTable} from '../../../modules/analytics/components/Table';
function QueryState({query}:{query:any}){return query.error?<ErrorNotice error={query.error}/>:query.isLoading?<Loading/>:null}
export function AuditPage(){const s=useScope();const q=useApi(['audit',s.wid],`/workspaces/${s.wid}/audit`);return <><PageHead eyebrow="PROTECT" title="Audit history" description="Who changed access, configuration and data controls."/><QueryState query={q}/><Panel><DataTable data={q.data?.items||[]} columns={[{accessorKey:'action',header:'Action',cell:({getValue}:any)=><code>{getValue()}</code>},{accessorKey:'actor_id',header:'Actor',cell:({getValue}:any)=><code>{getValue()||'System'}</code>},{accessorKey:'resource_id',header:'Resource',cell:({getValue}:any)=><code>{getValue()}</code>},{accessorKey:'reason',header:'Reason',cell:({getValue}:any)=>getValue()||'—'},{accessorKey:'created_at',header:'Time',cell:({getValue}:any)=>dateTime(getValue())}]} empty="No audit events yet."/></Panel></>}
