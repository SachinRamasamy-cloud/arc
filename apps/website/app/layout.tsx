import type {Metadata} from 'next';
import React from 'react';
import '@arc/ui/styles.css';
import '@arc/ui/marketing.css';
import {SiteChrome} from '../components/SiteChrome';
export const metadata:Metadata={title:{default:'Arc — Connect the service. See the work.',template:'%s · Arc'},description:'First-party data-processing APIs with visible execution, private uploads and clear usage controls.',robots:{index:false,follow:false}};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><SiteChrome>{children}</SiteChrome></body></html>}
