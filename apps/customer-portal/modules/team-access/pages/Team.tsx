import React,{useState} from 'react';
import {useMutation,useQueryClient} from '@tanstack/react-query';
import {Plus,Users,Mail,ShieldCheck,RefreshCw,UserRound} from 'lucide-react';
import {PageHead,Panel,Button,Field,Badge,Loading,ErrorNotice,InlineNote,Empty,Modal,Confirm} from '@arc/ui';
import {dateTime} from '@arc/client';
import {api,useScope,useApi,useAction} from '../../../app/platform';
import {DataTable} from '../../analytics/components/Table';

type Member={id:string;user_id:string;name:string;email:string;role:string};
type Invitation={id:string;email:string;role:string;expires_at:number};
type TeamResponse={items:Member[];invites:Invitation[];can_manage:boolean};

export function Team(){
 const scope=useScope(),cache=useQueryClient();
 const query=useApi(['members',scope.wid],`/workspaces/${scope.wid}/members`);
 const [inviteOpen,setInviteOpen]=useState(false);
 const [email,setEmail]=useState('');
 const [role,setRole]=useState('developer');
 const [remove,setRemove]=useState<Member|null>(null);
 const invite=useAction(`/workspaces/${scope.wid}/members/invite`,'POST','Invitation queued for delivery.',()=>{
  setInviteOpen(false);setEmail('');setRole('developer');
 });
 const deletion=useMutation({mutationFn:()=>api.request(`/workspaces/${scope.wid}/members/${remove!.id}`,{method:'DELETE'}),onSuccess:()=>{
  setRemove(null);void cache.invalidateQueries({queryKey:['members',scope.wid]});
 }});
 const data=query.data as TeamResponse|undefined;
 const canManage=!!data?.can_manage;
 const canRemove=(member:Member)=>canManage&&member.role!=='owner'&&member.user_id!==scope.user.id&&(member.role!=='admin'||scope.role==='owner');
 const columns=[
  {accessorKey:'name',header:'Member',cell:({row}:any)=><div className="member-cell"><span className="member-avatar">{row.original.name?.charAt(0)?.toUpperCase()||'U'}</span><div><strong>{row.original.name||'Workspace member'}</strong>{row.original.user_id===scope.user.id&&<small> You</small>}</div></div>},
  {accessorKey:'email',header:'Email'},
  {accessorKey:'role',header:'Workspace role',cell:({getValue}:any)=><Badge tone={getValue()==='owner'?'success':'neutral'}>{getValue()}</Badge>},
  {id:'access',header:'Access',cell:({row}:any)=>canRemove(row.original)?<Button variant="ghost" onClick={()=>setRemove(row.original)}>Remove</Button>:<span className="muted small">{row.original.role==='owner'?'Protected owner':'View only'}</span>}
 ];
 return <>
  <PageHead eyebrow="WORKSPACE" title="Team & access" description="See who belongs to this workspace. Invitations and role changes are controlled by workspace permissions."
   action={canManage?<Button onClick={()=>setInviteOpen(true)}><Plus size={15}/> Invite teammate</Button>:undefined}/>
  {query.isPending?<Panel><div className="panel-body"><Loading label="Loading team members"/></div></Panel>
   :query.error?<ErrorNotice error={query.error} retry={()=>void query.refetch()}/>
   :<>
    <div className="team-summary"><div><Users size={18}/><strong>{data!.items.length}</strong><span>{data!.items.length===1?'member':'members'}</span></div><div><Mail size={18}/><strong>{canManage?data!.invites.length:'—'}</strong><span>{canManage?'pending invitations':'invitations managed by admins'}</span></div><Button variant="ghost" onClick={()=>void query.refetch()}><RefreshCw size={14}/> Refresh</Button></div>
    <Panel title="Members"><DataTable data={data!.items} columns={columns} empty="No members found. Refresh this page or contact support."/></Panel>
    {canManage&&<Panel title="Pending invitations"><div className="team-invitations">
      {data!.invites.length?data!.invites.map(item=><div className="team-invite-row" key={item.id}><Mail size={16}/><div><strong>{item.email}</strong><small>Invited as {item.role} · expires {dateTime(item.expires_at)}</small></div><Badge tone="warning">Pending</Badge></div>):<Empty icon={<Mail size={22}/>} title="No outstanding invitations" description="Invite a teammate when you're ready to collaborate." action={<Button variant="secondary" onClick={()=>setInviteOpen(true)}>Invite someone</Button>}/>}
     </div></Panel>}
    <InlineNote><ShieldCheck size={15}/> All members can view this directory. Only owners and admins can invite or remove teammates. The owner cannot be removed through this screen.</InlineNote>
   </>}
  {deletion.error&&<ErrorNotice error={deletion.error}/>}
  <Modal open={inviteOpen} onClose={()=>{setInviteOpen(false);invite.reset();}} title="Invite a teammate" description="Send an invitation to join this workspace. They can use their own account.">
   <form className="stack" onSubmit={e=>{e.preventDefault();if(canManage)invite.mutate({body:{email:email.trim(),role}});}}>
    <Field label="Email address" hint="Use the email address your teammate will sign in with."><input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} maxLength={254} required/></Field>
    <Field label="Role"><select value={role} onChange={e=>setRole(e.target.value)}>{['developer',...(scope.role==='owner'?['admin']:[]),'billing','viewer'].map(r=><option value={r} key={r}>{r[0].toUpperCase()+r.slice(1)}</option>)}</select></Field>
    <p className="small muted">Developer: builds APIs. Billing: invoices and credits. Viewer: read-only. Admin: workspace settings and access.</p>
    {invite.error&&<ErrorNotice error={invite.error}/>}
    <Button type="submit" busy={invite.isPending} disabled={!canManage||!email.trim()}>Send invitation</Button>
   </form>
  </Modal>
  <Confirm open={!!remove} onClose={()=>setRemove(null)} onConfirm={()=>deletion.mutate()} title="Remove workspace access?" description="This person will lose access to this workspace, but their other workspaces will remain unchanged." busy={deletion.isPending}/>
 </>;
}
