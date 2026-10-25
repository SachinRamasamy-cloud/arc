"""Package source and selected evidence; never include runtime data or font binaries."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE_DIRS={'.git','.local','.venv','node_modules','__pycache__','.pytest_cache','.next','dist','out','build','htmlcov','test-results','playwright-report'}
EVIDENCE={'backend-full-tests.txt','backend-tests.xml','native-build.log','native-configure.log','native-ctest.txt','frontend-syntax.json','frontend-logic-tests.txt','http-smoke.json','glb-validation.txt','release-check.json','verification-summary.json','network-qualification.txt'}

def include(path:Path)->bool:
    rel=path.relative_to(ROOT)
    if any(part in EXCLUDE_DIRS for part in rel.parts):return False
    if path.name=='.env' or path.name.startswith('.env.') and path.name!='.env.example':return False
    if path.suffix.lower() in {'.pyc','.sqlite','.db','.ttf','.otf','.woff','.woff2','.zip'}:return False
    if path.name in {'.coverage','SOURCE_MANIFEST.json','SHA256SUMS.txt'}:return False
    if rel.parts[0]=='artifacts' and path.name not in EVIDENCE:return False
    return path.is_file() and not path.is_symlink()

def main():
    output=ROOT.parent/'API_Provider_Modular_Clean_Architecture_v0_3.zip'
    files=sorted(p for p in ROOT.rglob('*') if include(p))
    manifest={'release':'0.3.0-modular-development','production_ready':False,'files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in files:archive.write(p,'arc-platform/'+p.relative_to(ROOT).as_posix())
        archive.writestr('arc-platform/SOURCE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names=archive.namelist()
        assert 'arc-platform/apps/website/public/models/arc-assembly.glb' in names
        assert 'arc-platform/backend/src/arc/main.py' in names
        assert all('/.env' not in name or name.endswith('.env.example') for name in names)
        assert not any(name.lower().endswith(('.woff','.woff2','.ttf','.otf','.sqlite','.pyc')) for name in names)
        for row in manifest['files']:
            assert hashlib.sha256(archive.read('arc-platform/'+row['path'])).hexdigest()==row['sha256']
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n')
    print(json.dumps({'path':str(output),'source_files':len(files),'archive_bytes':output.stat().st_size,'sha256':digest,'verified':'ZIP CRC and every source SHA-256; runtime data/secrets/fonts excluded'},indent=2))
if __name__=='__main__':main()
