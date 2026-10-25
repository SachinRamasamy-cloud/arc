import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<div className="stack">{d.items.map((t:any)=><Panel title={t.subject} action={<Status value={t.state}/>} key={t.id}><div className="panel-body"><p>{t.message}</p><small className="muted">{t.email} · {dateTime(t.created_at)}</small>{t.reply&&<div className="support-reply">{t.reply}</div>}<div className="form-actions"><Button variant="secondary" onClick={()=>{setSelected(t);setReply(t.reply||'');}}>Respond</Button></div></div></Panel>)}{!d.items.length&&<Empty title="No support requests" description="Customer and public contact requests appear here."/>}</div>
</>
}
