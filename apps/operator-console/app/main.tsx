import React from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClientProvider} from '@tanstack/react-query';
import {UIProvider,ErrorBoundary} from '@arc/ui';
import {App} from './layouts/OperatorShell';
import {cache} from './platform';
import '@arc/ui/styles.css';
import '@arc/ui/console.css';
import './operator.css';
createRoot(document.getElementById('root')!).render(
 <React.StrictMode><QueryClientProvider client={cache}><UIProvider><ErrorBoundary><App/></ErrorBoundary></UIProvider></QueryClientProvider></React.StrictMode>
);
