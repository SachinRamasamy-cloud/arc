"""Fail closed when evidence is missing. Configuration flags alone are not release evidence."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]

def inspect_release(root:Path)->list[str]:
    problems=[]
    manifest=json.loads((root/'docs/release-evidence.json').read_text())
    for name,gate in manifest['gates'].items():
        if gate.get('status')!='passed':problems.append(name+': '+gate.get('evidence','missing evidence'))
        else:
            evidence=(root/gate.get('artifact','')).resolve()
            if root.resolve() not in evidence.parents or not evidence.is_file():problems.append(name+': approved evidence artifact missing')
    if not (root/'package-lock.json').is_file():problems.append('npm lockfile is not available')
    return problems

if __name__=='__main__':
    problems=inspect_release(ROOT)
    print(json.dumps({'release_ready':not problems,'blockers':problems},indent=2))
    sys.exit(1 if problems else 0)
