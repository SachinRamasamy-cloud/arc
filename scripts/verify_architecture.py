"""Static module-dependency and deployable-surface boundaries."""
import ast
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODULES=ROOT/'backend/modules'
EXPECTED={'identity','tenancy','projects','service_catalog','api_credentials','authorization','rate_limits','uploads','files','application_data','processing_capabilities','workflows','executions','realtime_events','webhooks','metering','pricing','wallets','subscriptions','payments','invoices','notifications','security_center','audit','privacy','support','analytics','platform_operations'}

def inspect_architecture():
    errors=[]
    active={p.name for p in MODULES.iterdir() if p.is_dir() and (p/'__init__.py').is_file()}
    for name in sorted(EXPECTED-active):errors.append('Missing domain module: '+name)
    for name in sorted(active-EXPECTED):errors.append('Unplanned domain module: '+name)
    for name in sorted(EXPECTED & active):
        p=MODULES/name
        for folder in ('domain','application','infrastructure','interfaces','tests'):
            if not (p/folder/'__init__.py').is_file():errors.append(f'{name}: missing {folder}/ package')
        if not (p/'public.py').is_file():errors.append(f'{name}: missing public contract')
        for source in p.rglob('*.py'):
            tree=ast.parse(source.read_text(),str(source))
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:imports.append(node.module)
            for other in imports:
                if other.startswith('arc.') or other=='arc':errors.append(f'{source.relative_to(ROOT)}: module depends on deprecated arc namespace')
                if other.startswith('modules.'):
                    parts=other.split('.')
                    if len(parts)>=3 and parts[1]!=name and parts[2]=='infrastructure':
                        errors.append(f'{source.relative_to(ROOT)}: direct access to {other} private infrastructure')
    # Customer and operator apps must not import one another's private UI modules.
    for appname,forbidden in [('customer-portal','operator-console'),('operator-console','customer-portal')]:
        app=ROOT/'apps'/appname
        for source in app.rglob('*.tsx'):
            if forbidden in source.read_text():errors.append(f'{source.relative_to(ROOT)}: forbidden cross-application import')
    return errors

if __name__=='__main__':
    errors=inspect_architecture()
    print(json.dumps({'status':'pass' if not errors else 'fail','expected_modules':len(EXPECTED),'violations':errors},indent=2))
    raise SystemExit(1 if errors else 0)
