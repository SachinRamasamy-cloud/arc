import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<Panel><SimpleTable headings={['Workspace','Status','Subscription','Action']} rows={d.items.map((w:any)=>[<span key={w.id}><strong>{w.name}</strong><small className="mono block muted">{w.id}</small></span>,<Status value={w.status}/>,<Status value={w.subscription_status||'none'}/>,<Button variant="secondary" onClick={()=>setSelected(w)}>{w.status==='active'?'Suspend':'Reactivate'}</Button>])}/></Panel>
</>
}
