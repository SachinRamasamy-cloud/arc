/** Customer navigation is data, not scattered route strings. Permissions are checked
 * again by the API: these labels only determine discoverability. */
export type Destination = {
  id: string; label: string; icon: string; permission: string;
  project: boolean; aliases?: string[];
};
export type NavigationGroup = { label: string; items: Destination[] };

export const quickLinks: Destination[] = [
  {id:'overview',label:'Overview',icon:'overview',permission:'read',project:false,aliases:['dashboard','home']},
  {id:'services',label:'API services',icon:'services',permission:'read',project:false,aliases:['catalog','products','user management','authentication','storage','notifications','realtime','scheduling']},
  {id:'playground',label:'Playground',icon:'playground',permission:'build',project:true,aliases:['test API','validate JSON','CSV']},
  {id:'connect',label:'Connect an app',icon:'connect',permission:'build',project:true,aliases:['integration','SDK','base URL','code']},
];
export const navigationGroups: NavigationGroup[] = [
  {label:'BUILD',items:[
    {id:'projects',label:'Projects',icon:'projects',permission:'read',project:false,aliases:['create project']},
    {id:'studio',label:'Visual Studio',icon:'studio',permission:'build',project:true,aliases:['workflow','nodes']},
    {id:'keys',label:'API keys',icon:'keys',permission:'keys',project:true,aliases:['credentials','secrets']},
  ]},
  {label:'OPERATIONS',items:[
    {id:'executions',label:'Executions',icon:'executions',permission:'build',project:true,aliases:['jobs','processing','runs']},
    {id:'files',label:'Files & uploads',icon:'files',permission:'files',project:true,aliases:['R2','storage','downloads']},
    {id:'data',label:'Application data',icon:'data',permission:'build',project:true,aliases:['database','records']},
    {id:'webhooks',label:'Webhooks & events',icon:'webhooks',permission:'build',project:true,aliases:['SSE','streams']},
    {id:'logs',label:'Request logs',icon:'logs',permission:'build',project:true,aliases:['debug','errors']},
    {id:'analytics',label:'Analytics',icon:'analytics',permission:'read',project:true,aliases:['performance','usage metrics']},
  ]},
  {label:'SECURITY & COST',items:[
    {id:'limits',label:'Limits & budgets',icon:'limits',permission:'security',project:true,aliases:['rate limits','quotas','spending cap']},
    {id:'security',label:'Security',icon:'security',permission:'security',project:false,aliases:['MFA','2FA','access policies']},
    {id:'audit',label:'Audit history',icon:'audit',permission:'security',project:false,aliases:['activity history']},
    {id:'privacy',label:'Data & privacy',icon:'privacy',permission:'privacy',project:false,aliases:['retention','delete','encryption']},
    {id:'billing',label:'Usage & billing',icon:'billing',permission:'finance',project:false,aliases:['Stripe','credits','payments','invoices','subscription']},
  ]},
  {label:'WORKSPACE',items:[
    {id:'team',label:'Team & access',icon:'team',permission:'read',project:false,aliases:['members','invite','roles']},
    {id:'notifications',label:'Notifications',icon:'notifications',permission:'read',project:false,aliases:['alerts','email']},
    {id:'settings',label:'Settings',icon:'settings',permission:'read',project:false,aliases:['preferences','account']},
    {id:'support',label:'Support',icon:'support',permission:'read',project:false,aliases:['contact','help','tickets']},
  ]},
];
export const docsDestination: Destination = {id:'docs',label:'Documentation',icon:'docs',permission:'read',project:false,aliases:['API reference','OpenAPI','tutorial','quickstart']};
export function allDestinations(): Destination[] {return [...quickLinks,...navigationGroups.flatMap(group=>group.items),docsDestination];}
export function findGroup(section:string): string|undefined {return navigationGroups.find(g=>g.items.some(item=>item.id===section))?.label;}
export function searchDestinations(query:string, available:Destination[]):Destination[] {
  const term=query.trim().toLocaleLowerCase();
  if(!term) return available.slice(0,9);
  return available.filter(item=>[item.label,item.id,...(item.aliases||[])].some(v=>v.toLocaleLowerCase().includes(term))).slice(0,15);
}
