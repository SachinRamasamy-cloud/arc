import React,{useState,useEffect,lazy,Suspense} from 'react';
import {MotionConfig} from 'motion/react';
import {useNavigate,useParams} from '@tanstack/react-router';
import {useMutation} from '@tanstack/react-query';
import {
 LayoutDashboard,FolderKanban,Boxes,Workflow,Terminal,Plug,KeyRound,Activity,Files,
 Webhook,ScrollText,ChartNoAxesCombined,SlidersHorizontal,ShieldCheck,History,
 LockKeyhole,Wallet,Bell,Users,Settings,LifeBuoy,Search,ChevronDown,PanelLeftClose,
 PanelLeft,ArrowUpRight,LogOut,Plus,Menu,ChevronRight,BookOpen,Database, type LucideIcon
} from 'lucide-react';
import {Brand,Button,Badge,ErrorNotice,Loading,Modal,SearchInput,Empty} from '@arc/ui';
import {allowed} from '@arc/client';
import {api,queryClient,ScopeContext,useApi,projectPath,workspacePath} from '../platform';
import {quickLinks,navigationGroups,docsDestination,allDestinations,searchDestinations,findGroup, type Destination} from '../navigation';
import {Overview} from '../../modules/dashboard/pages/Overview';
import {Projects} from '../../modules/projects/pages/Projects';
import {Services} from '../../modules/service-catalog/pages/Services';
import {Playground} from '../../modules/playground/pages/Playground';
import {Executions} from '../../modules/executions/pages/Executions';
import {FilesPage} from '../../modules/files/pages/FilesPage';
import {ApplicationData} from '../../modules/application-data/pages/ApplicationData';
import {Connect} from '../../modules/connection/pages/Connect';
import {Keys} from '../../modules/api-keys/pages/Keys';
import {Webhooks} from '../../modules/webhooks/pages/Webhooks';
import {Logs} from '../../modules/request-logs/pages/Logs';
import {Limits} from '../../modules/limits/pages/Limits';
import {Security} from '../../modules/security/pages/Security';
import {AuditPage} from '../../modules/security/pages/AuditPage';
import {Privacy} from '../../modules/privacy/pages/Privacy';
import {Notifications} from '../../modules/notifications/pages/Notifications';
import {Team} from '../../modules/team-access/pages/Team';
import {SettingsPage} from '../../modules/settings/pages/SettingsPage';
import {Support} from '../../modules/support/pages/Support';
import {Analytics} from '../../modules/analytics/pages/Analytics';
import {Billing} from '../../modules/billing/pages/Billing';

const Studio=lazy(()=>import('../../modules/visual-studio/pages/Studio'));
const icons:Record<string,LucideIcon>={
 overview:LayoutDashboard,projects:FolderKanban,services:Boxes,studio:Workflow,
 playground:Terminal,connect:Plug,keys:KeyRound,executions:Activity,files:Files,
 data:Database,webhooks:Webhook,logs:ScrollText,analytics:ChartNoAxesCombined,
 limits:SlidersHorizontal,security:ShieldCheck,audit:History,privacy:LockKeyhole,
 billing:Wallet,notifications:Bell,team:Users,settings:Settings,support:LifeBuoy,docs:BookOpen,
};

export function Bootstrap({section='overview'}:{section?:string}){
 const navigate=useNavigate();
 const me=useApi(['me'],'/auth/me');
 const workspaces=useApi(['workspaces'],'/workspaces',!!me.data);
 useEffect(()=>{
  if(me.error && 'status' in me.error && me.error.status===401)void navigate({to:'/login'});
  else if(workspaces.data){
   if(!workspaces.data.items.length)void navigate({to:'/setup'});
   else void navigate({to:workspacePath(workspaces.data.items[0].id,section) as any});
  }
 },[me.error,workspaces.data,navigate,section]);
 if(me.error)return <ErrorNotice error={me.error}/>;
 if(workspaces.error)return <ErrorNotice error={workspaces.error} retry={()=>void workspaces.refetch()}/>;
 return <Loading label="Preparing your workspace"/>;
}

export function Shell(){
 const params=useParams({strict:false}) as {workspaceId:string;projectId?:string;environment?:'test'|'live';section:string};
 const navigate=useNavigate();
 const [collapsed,setCollapsed]=useState(false);
 const [mobile,setMobile]=useState(false);
 const [searchOpen,setSearchOpen]=useState(false);
 const [search,setSearch]=useState('');
 const [expanded,setExpanded]=useState<Record<string,boolean>>(()=>({[findGroup(params.section)||'BUILD']:true}));
 const me=useApi(['me'],'/auth/me');
 const all=useApi(['workspaces'],'/workspaces',!!me.data);
 const projects=useApi(['projects',params.workspaceId],`/workspaces/${params.workspaceId}/projects`,!!me.data);
 const workspace=all.data?.items.find((w:any)=>w.id===params.workspaceId);
 const project=projects.data?.items.find((p:any)=>p.id===params.projectId)||projects.data?.items.find((p:any)=>!p.archived);
 const role=workspace?.role||'viewer';
 const available=allDestinations().filter(item=>allowed(role,item.permission));
 const active=available.find(item=>item.id===params.section);
 const logout=useMutation({mutationFn:()=>api.request('/auth/logout',{method:'POST'}),onSuccess:()=>{
  queryClient.clear();api.clearSession();void navigate({to:'/login'});
 }});
 useEffect(()=>{if(me.error&&'status'in me.error&&me.error.status===401)void navigate({to:'/login'});},[me.error,navigate]);
 useEffect(()=>{
  const group=findGroup(params.section);
  if(group)setExpanded(v=>({...v,[group]:true}));
 },[params.section]);
 useEffect(()=>{
  const key=(e:KeyboardEvent)=>{
   if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){
    e.preventDefault();setSearchOpen(v=>!v);
   }
  };
  window.addEventListener('keydown',key);
  return()=>window.removeEventListener('keydown',key);
 },[]);
 function navigateTo(destination:Destination){
  setMobile(false);setSearchOpen(false);setSearch('');
  if(destination.id==='docs'){void navigate({to:'/docs'});return;}
  const path=destination.project&&project
   ? projectPath(params.workspaceId,project.id,params.environment||'test',destination.id)
   : workspacePath(params.workspaceId,destination.project?'projects':destination.id);
  void navigate({to:path as any});
 }
 const matches=searchDestinations(search,available);
 const projectMatches=search.trim()?((projects.data?.items||[]) as any[]).filter(p=>p.name.toLowerCase().includes(search.toLowerCase())).slice(0,5):[];
 if(me.isPending||all.isPending||projects.isPending)return <Loading label="Opening your workspace"/>;
 if(me.error||all.error||projects.error)return <div className="shell-error"><Brand/><ErrorNotice error={me.error||all.error||projects.error} retry={()=>{void me.refetch();void all.refetch();void projects.refetch();}}/><a href="/login">Sign in</a></div>;
 if(!workspace)return <div className="fatal"><Empty title="Workspace not available" description="Your access may have changed. Choose a workspace that belongs to your account." action={<a href="/" className="button button-primary">Choose workspace</a>}/></div>;
 const scope={wid:params.workspaceId,pid:project?.id||'',environment:params.environment||'test',role,workspace,projects:projects.data?.items||[],user:me.data.user};
 const screens:Record<string,React.ReactNode>={
  overview:<Overview/>,projects:<Projects/>,services:<Services/>,connect:<Connect/>,
  keys:<Keys/>,playground:<Playground/>,executions:<Executions/>,files:<FilesPage/>,
  data:<ApplicationData/>,studio:<Suspense fallback={<Loading label="Opening Visual Studio"/>}><Studio/></Suspense>,
  webhooks:<Webhooks/>,logs:<Logs/>,analytics:<Analytics/>,limits:<Limits/>,security:<Security/>,
  audit:<AuditPage/>,privacy:<Privacy/>,billing:<Billing/>,notifications:<Notifications/>,
  team:<Team/>,settings:<SettingsPage/>,support:<Support/>,
 };
 function navButton(item:Destination){const Icon=icons[item.icon];return <button key={item.id} type="button" aria-current={params.section===item.id?'page':undefined} title={collapsed?item.label:undefined}
  onClick={()=>navigateTo(item)} className={params.section===item.id?'nav-item active':'nav-item'}>
  <Icon size={17} aria-hidden="true"/>{!collapsed&&<span>{item.label}</span>}{!collapsed&&item.id==='studio'&&<span className="mini-tag">BETA</span>}
 </button>;}
 return <ScopeContext.Provider value={scope}><MotionConfig reducedMotion={scope.user.preferences?.reduced_motion?'always':'user'}>
  <div className={`app-shell ${collapsed?'is-collapsed':''} ${scope.user.preferences?.compact?'compact-ui':''} ${scope.user.preferences?.reduced_motion?'reduce-motion':''}`}>
   <a className="skip-link" href="#main-content">Skip to content</a>
   {mobile&&<button className="mobile-scrim" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
   <aside className={`sidebar ${mobile?'is-open':''}`} aria-label="Workspace navigation">
    <div className="sidebar-brand"><Brand small={collapsed}/><button type="button" className="icon-button collapse-toggle" aria-label={collapsed?'Expand navigation':'Collapse navigation'} onClick={()=>setCollapsed(!collapsed)}>{collapsed?<PanelLeft size={16}/>:<PanelLeftClose size={16}/>}</button></div>
    <div className="workspace-switcher"><div className="workspace-avatar">{workspace.name[0]?.toUpperCase()}</div>{!collapsed&&<select aria-label="Workspace" value={workspace.id} onChange={e=>void navigate({to:workspacePath(e.target.value,'overview') as any})}>{all.data.items.map((w:any)=><option value={w.id} key={w.id}>{w.name}</option>)}</select>}</div>
    <nav className="side-navigation" aria-label="Sections">
     <div className="nav-group nav-group-pinned">{!collapsed&&<p>QUICK ACCESS</p>}{quickLinks.filter(item=>allowed(role,item.permission)).map(navButton)}</div>
     {navigationGroups.map(group=>{
      const items=group.items.filter(item=>allowed(role,item.permission));
      if(!items.length)return null;
      const isOpen=collapsed||expanded[group.label];
      return <div className="nav-group nav-group-collapsible" key={group.label}>
       {!collapsed&&<button type="button" className="nav-group-trigger" aria-expanded={!!isOpen} onClick={()=>setExpanded(v=>({...v,[group.label]:!v[group.label]}))}>
        <span>{group.label}</span><ChevronDown size={14} className={isOpen?'chevron-open':''}/>
       </button>}
       {isOpen&&<div className="nav-group-items">{items.map(navButton)}</div>}
      </div>;
     })}
    </nav>
    <div className="sidebar-bottom">
     <button type="button" className="nav-item docs-nav-item" title="Documentation" onClick={()=>navigateTo(docsDestination)}><BookOpen size={17}/>{!collapsed&&<><span>Documentation</span><ArrowUpRight size={13}/></>}</button>
     <button type="button" className="profile-button" onClick={()=>navigateTo(available.find(v=>v.id==='settings')||quickLinks[0])} aria-label="Account settings"><span className="avatar">{scope.user.name?.slice(0,1)||'A'}</span>{!collapsed&&<span><strong>{scope.user.name}</strong><small>{role}</small></span>}</button>
    </div>
   </aside>
   <div className="app-stage">
    <header className="app-topbar"><button type="button" className="icon-button mobile-menu" aria-label="Open navigation" onClick={()=>setMobile(true)}><Menu size={19}/></button>
     <div className="breadcrumb"><span>{workspace.name}</span><ChevronRight size={13}/>{project&&active?.project?<>
      <select aria-label="Project" value={project.id} onChange={e=>void navigate({to:projectPath(scope.wid,e.target.value,scope.environment,params.section) as any})}>{scope.projects.filter((p:any)=>!p.archived).map((p:any)=><option value={p.id} key={p.id}>{p.name}</option>)}</select>
      <Badge tone={scope.environment==='test'?'warning':'success'}>{scope.environment}</Badge>
     </>:<strong>{active?.label||'Workspace'}</strong>}</div>
     <div className="topbar-actions">
      {project&&active?.project&&<select className="environment-switch" aria-label="Environment" value={scope.environment} onChange={e=>void navigate({to:projectPath(scope.wid,project.id,e.target.value,params.section) as any})}><option value="test">Test</option><option value="live">Live</option></select>}
      <button type="button" className="command-trigger" aria-label="Search pages and projects" onClick={()=>setSearchOpen(true)}><Search size={15}/><span>Find anything</span><kbd>Ctrl K</kbd></button>
      <button type="button" className="icon-button" aria-label="Notifications" onClick={()=>navigateTo(available.find(v=>v.id==='notifications')||quickLinks[0])}><Bell size={17}/></button>
      <button type="button" className="icon-button" aria-label="Sign out" disabled={logout.isPending} onClick={()=>logout.mutate()}><LogOut size={17}/></button>
     </div>
    </header>
    <main className={`main-content ${params.section==='studio'?'studio-content':''}`} id="main-content">
     {!active?<Empty title="Page not available" description="This section is unavailable to your workspace role or the URL is incorrect." action={<Button onClick={()=>navigateTo(quickLinks[0])}>Back to overview</Button>}/>
      :active.project&&!project?<Empty title="Create a project first" description="You can browse API services and documentation before creating a project. A project is only needed to submit work or create credentials." action={<Button onClick={()=>navigateTo(available.find(v=>v.id==='projects')||quickLinks[0])}><Plus size={14}/> View projects</Button>}/>
      :<React.Fragment key={`${scope.wid}:${scope.pid}:${scope.environment}:${params.section}`}>{screens[params.section]}</React.Fragment>}
    </main>
    <footer className="app-footer"><span><span className="status-dot"/> Test and production are separate.</span><button type="button" className="text-button" onClick={()=>navigateTo(docsDestination)}>Developer documentation <ArrowUpRight size={12}/></button></footer>
   </div>
   <Modal open={searchOpen} onClose={()=>setSearchOpen(false)} title="Find a page or project" description="Search by feature, operation or project name. Shortcut: Ctrl/⌘ K.">
    <SearchInput value={search} onChange={setSearch} placeholder="Try billing, storage, API keys, docs…"/>
    <div className="command-list" role="list">
     {matches.map(item=>{const Icon=icons[item.icon];return <button type="button" role="listitem" key={item.id} onClick={()=>navigateTo(item)}><Icon size={17}/><span>{item.label}</span><ArrowUpRight size={13}/></button>;})}
     {projectMatches.map((p:any)=><button type="button" role="listitem" key={p.id} onClick={()=>{setSearchOpen(false);void navigate({to:projectPath(scope.wid,p.id,'test','playground') as any});}}><FolderKanban size={17}/><span>{p.name} <small className="muted">· project</small></span><ArrowUpRight size={13}/></button>)}
     {!matches.length&&!projectMatches.length&&<p className="command-empty">No matching pages. Try “files”, “docs”, “payments” or a project name.</p>}
    </div>
   </Modal>
  </div>
 </MotionConfig></ScopeContext.Provider>;
}
