import {energyEnsemble} from './research-core.mjs';
self.onmessage=e=>{try{self.postMessage({id:e.data.id,result:energyEnsemble(...e.data.args)});}catch(error){self.postMessage({id:e.data.id,error:error.message});}};
