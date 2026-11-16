import test from 'node:test';
import assert from 'node:assert/strict';
import {metrics,bootstrap,scenario,dispatch,defaults,validate,planOperations,transitionTask,parseCSV,cleaningBenefit,predictMLP} from '../src/core.mjs';
test('metrics computes bias and distinguishes percent from percentage points',()=>{
 const m=metrics([0,10,20],[0,8,24],20);assert.equal(m.mae,2);assert.ok(Math.abs(m.rmse-Math.sqrt(20/3))<1e-9);assert.equal(m.bias,2/3);assert.equal(metrics([0,0],[0,0],1).r2,null);
});
test('bootstrap resamples entire day blocks reproducibly',()=>{let r=bootstrap([[1,2],[3,4]],1000);assert.equal(r.length,1000);assert.deepEqual(r,bootstrap([[1,2],[3,4]],1000));assert.ok(r.every(x=>x>=1.5&&x<=3.5));});
test('dispatch preserves per-step power and battery balance, terminal SOC, all scenarios',()=>{
 for (let cloud of [.05,.7]) for(let method of ['none','rule','rolling']) {
 const c={...defaults,cloud};let s=scenario(c),r=dispatch(s,c,method);
 for(const x of r.rows){assert.ok(Math.abs(x.pv+x.import+x.discharge-x.load-x.charge-x.export-x.curtail)<1e-7);assert.ok(x.charge*x.discharge<1e-7);if(method!=='none')assert.ok(x.energy>=20-1e-6&&x.energy<=180+1e-6);}
 if(method!=='none') assert.ok(Math.abs(r.finalEnergy-100)<1e-6);
 assert.ok(Math.abs(r.balance.pv+r.balance.import-r.balance.load-r.balance.export-r.balance.curtail-r.balance.loss)<1e-5);
 }
});
test('zero PV gives defined utilization and feasible dispatch',()=>{let c={...defaults,capacity:0};let s=scenario(c);let r=dispatch(s,c,'rolling');assert.equal(r.balance.utilization,0);assert.ok(Number.isFinite(r.balance.cost));});
test('invalid environment and capacities are rejected',()=>{assert.throws(()=>validate({...defaults,battery:-1}));assert.throws(()=>validate({...defaults,wind:NaN}));assert.throws(()=>validate({...defaults,cloud:2}));});
test('drone wind and rain gates differ from ground robot constraints',()=>{
 assert.equal(planOperations({...defaults,wind:14},[0,1]).drone.allowed,false);
 assert.equal(planOperations({...defaults,rain:2},[0]).robot.allowed,false);
 assert.equal(planOperations(defaults,[0,1]).drone.allowed,true);
 assert.equal(planOperations({...defaults,deviceBattery:10},[0]).drone.allowed,false);
});
test('task state machine cannot skip directly from planned to complete',()=>{assert.throws(()=>transitionTask({status:'planned'},'complete'));assert.equal(transitionTask({status:'planned'},'start').status,'running');assert.equal(transitionTask({status:'running'},'pause').status,'paused');assert.equal(transitionTask({status:'paused'},'resume').status,'running');});
test('CSV rejects negative power, duplicate timestamps and unsafe labels; keeps chronological order',()=>{
 assert.throws(()=>parseCSV('timestamp,actual_kw,pred_kw\n2026-01-01T00:00,-1,0'));
 assert.throws(()=>parseCSV('timestamp,actual_kw,pred_kw\n2026-01-01T00:00,1,1\n2026-01-01T00:00,2,2'));
 const r=parseCSV('timestamp,actual_kw,pred_kw\n2026-01-02T00:00,2,3\n2026-01-01T00:00,1,1');assert.equal(r[0].actual,1);
});
test('cleaning uses net incremental energy with costs, no double counting',()=>{let r=cleaningBenefit({energy:10000,before:8,after:1,value:.5,cost:300});assert.ok(Math.abs(r.gainPct-7.60869565217)<1e-7);assert.ok(Math.abs(r.net-(r.extraEnergy*.5-300))<1e-7);});
test('exported MLP uses scaler and relu hidden activation',()=>{assert.equal(predictMLP([3],{mean:[1],scale:[2],weights:[[[2]],[[3]]],biases:[[0],[1]]}),7);});
test('CSV rejects invalid calendar dates and 24:00 rollover',()=>{for(const date of ['2026-02-30T00:00','2026-01-01T24:00','2026-13-01T00:00'])assert.throws(()=>parseCSV(`timestamp,actual_kw,pred_kw\n${date},1,1`));});
test('20,000-row metrics remain interactive',()=>{const a=Array.from({length:20000},(_,i)=>i%177),p=a.map(x=>x+1);const t=performance.now();assert.equal(metrics(a,p).mae,1);assert.ok(performance.now()-t<500,'metrics must not repeat a full-array mean per record');});
test('zero capacity does not manufacture normalized error metrics',()=>{const m=metrics([1,2],[2,3],0);assert.equal(m.nrmse,null);assert.equal(m.nmae,null);assert.equal(m.mae,1);});
