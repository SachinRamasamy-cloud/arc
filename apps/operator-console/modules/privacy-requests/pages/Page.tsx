import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<><InlineNote>Requests are not automatically marked complete. Use the privacy runbook, verify authorization and record deletion/export evidence before closing a request through a reviewed operational procedure.</InlineNote><Panel><SimpleTable headings={['Reference','Workspace','Request','State','Submitted']} rows={d.items.map((r:any)=>[<code>{r.id}</code>,<code>{r.workspace_id}</code>,r.kind,<Status value={r.state}/>,dateTime(r.created_at)])}/></Panel></>
</>
}
