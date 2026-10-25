import React from 'react';
import {Panel,Button,Status,Badge,InlineNote,Empty} from '@arc/ui';
import {Check,AlertTriangle} from 'lucide-react';
import {dateTime} from '@arc/client';
import {SimpleTable} from '../../../app/components/SimpleTable';
export function Page({d,setSelected,setReply}: {d:any;setSelected:(value:any)=>void;setReply:(value:string)=>void}) {
return <>
<Panel><SimpleTable headings={['Action','Staff actor','Resource','Reason','Time']} rows={d.items.map((a:any)=>[a.action,<code>{a.actor_id}</code>,<code>{a.resource_id}</code>,a.reason||'—',dateTime(a.created_at)])}/></Panel>
</>
}
