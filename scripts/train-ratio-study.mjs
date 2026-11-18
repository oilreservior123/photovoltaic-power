import * as tf from '@tensorflow/tfjs';
import {trainRatio} from '../src/ratio-engine.mjs';
import {STUDY,aggregateRuns} from '../src/ratio-core.mjs';
import {writeFile} from 'node:fs/promises';
await tf.setBackend('cpu');await tf.ready();const runs=[];
for(const ratio of STUDY.ratios)for(const seed of STUDY.seeds){const result=await trainRatio(tf,{ratio,seed,epochs:STUDY.epochs,onProgress:p=>{if(p.epoch%10===0)console.log(ratio.join('/'),seed,p.epoch,p.validation);}});runs.push(result);await writeFile(new URL('../data/cross-ratio-study.json',import.meta.url),JSON.stringify({study:STUDY,runs,summary:STUDY.ratios.filter(r=>runs.filter(x=>String(x.split.ratio)===String(r)).length===3).map(r=>({ratio:r,metrics:aggregateRuns(runs.filter(x=>String(x.split.ratio)===String(r)))}))}));console.log('done',ratio.join('/'),seed,result.seconds,result.metrics.test.nrmse);}
