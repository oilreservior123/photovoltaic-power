import {mkdir,rm,cp,readFile,writeFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import path from 'node:path';
const root=fileURLToPath(new URL('..',import.meta.url)),dist=path.join(root,'dist');
await rm(dist,{recursive:true,force:true});await mkdir(dist,{recursive:true});
for(const f of ['index.html','styles.css','src','data','docs'])await cp(path.join(root,f),path.join(dist,f),{recursive:true});
const walk=async dir=>(await Promise.all((await readdir(dir,{withFileTypes:true})).map(e=>e.isDirectory()?walk(path.join(dir,e.name)):[path.join(dir,e.name)]))).flat();
const inputs=(await walk(path.join(root,'src'))).concat(await walk(path.join(root,'data')),path.join(root,'styles.css'),path.join(root,'index.html')).sort();
const hash=createHash('sha256');for(const f of inputs)hash.update(path.relative(root,f)).update(await readFile(f));const version=hash.digest('hex').slice(0,12);
// Version the full ESM graph, worker entry points and assets so Pages/browser caches cannot mix releases.
const versionUrls=s=>s.replace(/(['"])(\.{1,2}\/[^'"\s<>]+\.(?:mjs|js|css|json|csv))\1/g,(_,q,url)=>`${q}${url}?v=${version}${q}`).replace("fetch('./data/'+file)",`fetch('./data/'+file+'?v=${version}')`);
for(const f of [path.join(dist,'index.html'),...(await walk(path.join(dist,'src'))).filter(f=>f.endsWith('.mjs'))])await writeFile(f,versionUrls(await readFile(f,'utf8')));
await writeFile(path.join(dist,'version.json'),JSON.stringify({version}));await writeFile(path.join(dist,'.nojekyll'),'');
for(const f of ['index.html','src/app.mjs','data/benchmark.json','data/model.json'])if(!(await readFile(path.join(dist,f))).length)throw Error(`Empty output: ${f}`);
console.log(`Static build ready: dist/ (${version}; relative paths; no CDN dependencies)`);
