import './vendor/tf.min.js';
import {trainRatio} from './ratio-engine.mjs';
self.onmessage=async e=>{const {id,config}=e.data;try{await self.tf.setBackend('cpu');await self.tf.ready();const result=await trainRatio(self.tf,{...config,onProgress:progress=>self.postMessage({id,progress})});self.postMessage({id,result});}catch(error){self.postMessage({id,error:error.message});}};
