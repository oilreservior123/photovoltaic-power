import {mkdir,rm,cp,readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('..',import.meta.url)),dist=path.join(root,'dist');
await rm(dist,{recursive:true,force:true});await mkdir(dist,{recursive:true});
for(const f of ['index.html','styles.css','src','data','docs'])await cp(path.join(root,f),path.join(dist,f),{recursive:true});
await writeFile(path.join(dist,'.nojekyll'),'');
for(const f of ['index.html','src/app.mjs','data/benchmark.json','data/model.json'])if(!(await readFile(path.join(dist,f))).length)throw Error(`Empty output: ${f}`);
console.log('Static build ready: dist/ (all paths relative, no CDN dependencies)');
