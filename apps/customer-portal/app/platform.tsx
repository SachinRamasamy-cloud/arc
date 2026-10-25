import React,{createContext,useContext} from 'react';
import {QueryClient,useQuery,useMutation,useQueryClient} from '@tanstack/react-query';
import {createClient,ApiError} from '@arc/client';
import {useToast} from '@arc/ui';
export const api=createClient('console',import.meta.env.VITE_API_BASE||'');
export const queryClient=new QueryClient({defaultOptions:{queries:{staleTime:15_000,gcTime:120_000,refetchOnWindowFocus:false,retry:(count,error)=>count<1 && error instanceof ApiError && error.status>=500},mutations:{retry:false}}});
export type Scope={wid:string;pid:string;environment:'test'|'live';role:string;workspace:any;projects:any[];user:any};
export const ScopeContext=createContext<Scope|null>(null);
export const useScope=()=>{const value=useContext(ScopeContext);if(!value)throw new Error('Scope not available');return value;};
export function useApi(key:unknown[],path:string,enabled=true,interval:number|false=false){return useQuery({queryKey:key,queryFn:()=>api.request(path),enabled,refetchInterval:interval});}
export function useAction(path:string|((body:any)=>string),method='POST',message='Changes saved.',onSuccess?:(data:any)=>void){
 const cache=useQueryClient();const toast=useToast();
 return useMutation({mutationFn:({body,headers}:{body?:any;headers?:HeadersInit}={})=>api.request(typeof path==='function'?path(body):path,{method,json:body,headers}),onSuccess:(data)=>{void cache.invalidateQueries();if(message)toast(message);onSuccess?.(data);}});
}
export function workspacePath(wid:string,section:string){return `/w/${wid}/${section}`;}
export function projectPath(wid:string,pid:string,env:string,section:string){return `/w/${wid}/p/${pid}/e/${env}/${section}`;}
export function go(path:string){window.history.pushState({},'',path);window.dispatchEvent(new PopStateEvent('popstate'));}
