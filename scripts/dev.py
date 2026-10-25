"""Start the local API, worker, public site, portal and operator. Ctrl+C stops all."""
from pathlib import Path
import os,signal,subprocess,sys,time,shutil
ROOT=Path(__file__).resolve().parents[1]

def main():
    if not (ROOT/'.env').exists():raise SystemExit('Run python scripts/bootstrap.py first.')
    if not (ROOT/'native/build/arc-engine').exists():raise SystemExit('Build native/build/arc-engine first.')
    if not (ROOT/'node_modules').exists():raise SystemExit('Run npm install first; inspect and commit the lockfile.')
    npm=shutil.which('npm')
    if not npm:raise SystemExit('Node.js/npm is required.')
    env={**os.environ,'PYTHONPATH':str(ROOT/'backend')+os.pathsep+str(ROOT/'backend/src')}
    commands=[[sys.executable,'-m','uvicorn','entrypoints.application:development','--factory','--host','127.0.0.1','--port','8000','--no-access-log'],[sys.executable,'-m','entrypoints.cli.main','worker'],[npm,'run','dev:web'],[npm,'run','dev:portal'],[npm,'run','dev:operator']]
    children=[]
    try:
        for command in commands:children.append(subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True))
        print('Public :3000 · Customer :5173 · Operator :5174 · API :8000. Use 127.0.0.1 consistently.')
        while all(p.poll() is None for p in children):time.sleep(0.5)
        raise SystemExit('A development process stopped. Review its output above.')
    except KeyboardInterrupt:pass
    finally:
        for p in children:
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        for p in children:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL)
if __name__=='__main__':main()
