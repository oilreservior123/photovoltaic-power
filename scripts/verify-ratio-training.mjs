import * as tf from '@tensorflow/tfjs';import assert from 'node:assert/strict';import {trainRatio} from '../src/ratio-engine.mjs';
await tf.setBackend('cpu');await tf.ready();const before=tf.memory().numTensors;
const a=await trainRatio(tf,{ratio:[65,20,15],epochs:2,seed:7}),b=await trainRatio(tf,{ratio:[65,20,15],epochs:2,seed:7});
assert.deepEqual(a.metrics,b.metrics);assert.deepEqual(a.weights,b.weights);assert.deepEqual(a.split.counts,[273,84,63]);assert.equal(tf.memory().numTensors,before);assert.ok(a.history[1].train<a.history[0].train);console.log('Actual optimizer update, deterministic initialization, custom split and tensor cleanup passed.');
