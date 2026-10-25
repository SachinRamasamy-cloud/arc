import {QueryClient} from '@tanstack/react-query';
import {createClient} from '@arc/client';
export const api=createClient('operator',import.meta.env.VITE_API_BASE||'');
export const cache=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false,staleTime:10000},mutations:{retry:false}}});
