import React from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClientProvider} from '@tanstack/react-query';
import {createRootRoute,createRoute,createRouter,RouterProvider,Outlet} from '@tanstack/react-router';
import {UIProvider,ErrorBoundary,Empty} from '@arc/ui';
import {queryClient} from './platform';
import {Shell,Bootstrap} from './layouts/Shell';
import {Auth} from '../modules/onboarding/pages/Auth';
import {Setup} from '../modules/onboarding/pages/Setup';
import {DeveloperDocs} from '../modules/documentation/pages/DeveloperDocs';
import '@arc/ui/styles.css';
import '@arc/ui/console.css';
const root=createRootRoute({component:()=> <ErrorBoundary><Outlet/></ErrorBoundary>,notFoundComponent:()=> <div className="fatal"><Empty title="This page has moved off the map." description="Check the address or return to your workspace." action={<a className="button button-primary" href="/">Back to dashboard</a>}/></div>});
const index=createRoute({getParentRoute:()=>root,path:'/',component:()=> <Bootstrap/>});
const routes=[index,createRoute({getParentRoute:()=>root,path:'/docs',component:DeveloperDocs}),createRoute({getParentRoute:()=>root,path:'/setup',component:Setup}),createRoute({getParentRoute:()=>root,path:'/billing',component:()=> <Bootstrap section="billing"/>}),createRoute({getParentRoute:()=>root,path:'/w/$workspaceId/$section',component:Shell}),createRoute({getParentRoute:()=>root,path:'/w/$workspaceId/p/$projectId/e/$environment/$section',component:Shell}),...['login','signup','forgot-password','reset-password','verify-email','accept-invite'].map(mode=>createRoute({getParentRoute:()=>root,path:'/'+mode,component:()=> <Auth mode={mode}/>}))];
const router=createRouter({routeTree:root.addChildren(routes),defaultPreload:'intent',scrollRestoration:true});
declare module '@tanstack/react-router' {interface Register {router:typeof router}}
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={queryClient}><UIProvider><RouterProvider router={router}/></UIProvider></QueryClientProvider></React.StrictMode>);
