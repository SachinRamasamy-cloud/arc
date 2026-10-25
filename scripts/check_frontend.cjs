/** Syntax/import smoke check. This is NOT a dependency-backed TypeScript build. */
const fs=require('node:fs');
const path=require('node:path');
let ts;
try{ts=require('typescript')}catch{const fallback=process.env.ARC_TYPESCRIPT_PATH;if(!fallback)throw new Error('Install dependencies or set ARC_TYPESCRIPT_PATH.');ts=require(fallback)}
const root=path.resolve(__dirname,'..');
const files=[];
function walk(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){if(['node_modules','.next','dist','out','.git'].includes(e.name))continue;const p=path.join(dir,e.name);if(e.isDirectory())walk(p);else if(/\.(tsx?|mjs)$/.test(p)&&!p.endsWith('.d.ts'))files.push(p)}}
for(const name of ['apps','packages','sdk/typescript'])walk(path.join(root,name));
let errors=[];
const hasFile=p=>[p,p+'.ts',p+'.tsx',p+'.js',p+'.css',path.join(p,'index.ts'),path.join(p,'index.tsx')].some(f=>fs.existsSync(f)&&fs.statSync(f).isFile());
for(const file of files){
 const text=fs.readFileSync(file,'utf8');
 const source=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true,file.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS);
 const result=ts.transpileModule(text,{fileName:file,reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX,isolatedModules:true}});
 for(const d of [...source.parseDiagnostics,...result.diagnostics])if(d.category===ts.DiagnosticCategory.Error)errors.push(path.relative(root,file)+': '+ts.flattenDiagnosticMessageText(d.messageText,' '));
 function visit(n){if((ts.isImportDeclaration(n)||ts.isExportDeclaration(n))&&n.moduleSpecifier&&ts.isStringLiteral(n.moduleSpecifier)){const m=n.moduleSpecifier.text;if(m.startsWith('.')&&!hasFile(path.resolve(path.dirname(file),m)))errors.push(path.relative(root,file)+': missing local import '+m)}ts.forEachChild(n,visit)}visit(source);
}
console.log(JSON.stringify({check:'frontend syntax and local import resolution',files:files.length,errors,limitations:['Does not resolve installed third-party types or verify package exports.','Does not execute React, WebGL, routing or browser layouts.','Run npm run typecheck, npm run build and npm run test:e2e after dependency installation.']},null,2));
process.exitCode=errors.length?1:0;
