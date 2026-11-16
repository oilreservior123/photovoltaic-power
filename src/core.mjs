export const defaults={capacity:177.1,battery:200,batteryPower:100,wind:5,temp:32,dust:8,cloud:.2,rain:0,loadScale:1,exportLimit:20,risk:.8,deviceBattery:90,cleanCost:280,energyValue:.55};
export const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export const sum=a=>a.reduce((s,x)=>s+x,0);
export const mean=a=>a.length?sum(a)/a.length:0;
export function quantile(a,q){if(!a.length)return 0;const b=[...a].sort((a,b)=>a-b),i=(b.length-1)*q;return b[Math.floor(i)]+(b[Math.ceil(i)]-b[Math.floor(i)])*(i%1);}
export function metrics(actual,pred,capacity=177.1){if(!actual.length||actual.length!==pred.length)throw Error('实际值与预测值应等长且非空');const actualMean=mean(actual);const e=actual.map((x,i)=>pred[i]-x),sse=sum(e.map(x=>x*x)),v=sum(actual.map(x=>(x-actualMean)**2)),mae=mean(e.map(Math.abs)),rmse=Math.sqrt(sse/e.length);return {mae,rmse,bias:mean(e),nmae:capacity>0?mae/capacity*100:null,nrmse:capacity>0?rmse/capacity*100:null,r2:v>1e-12?1-sse/v:null,n:e.length};}
export function bootstrap(blocks,n=2000){let seed=42;const rnd=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};return Array.from({length:n},()=>{const a=[];for(let i=0;i<blocks.length;i++)a.push(...blocks[Math.floor(rnd()*blocks.length)]);return mean(a);});}
export function validate(c){const bounds={capacity:[0,100000],battery:[0,100000],batteryPower:[0,50000],wind:[0,40],temp:[-30,75],dust:[0,50],cloud:[0,1],rain:[0,30],loadScale:[.1,10],exportLimit:[0,50000],risk:[0,1],deviceBattery:[0,100],cleanCost:[0,100000],energyValue:[0,5]};for(const [k,[a,b]] of Object.entries(bounds)){if(!Number.isFinite(c[k])||c[k]<a||c[k]>b)throw Error(`${k}超出允许范围 ${a}–${b}`);}return c;}
export function scenario(c){validate(c);return Array.from({length:96},(_,i)=>{const h=i/4,sun=Math.max(0,Math.sin((h-6)/14*Math.PI)),irr=sun*(1-c.cloud*(.4+.35*Math.sin(h*1.7)**2)),heat=Math.max(0,c.temp+22*irr-25),clean=c.capacity*irr*Math.max(.6,1-.004*heat)*.92,pv=clean*(1-c.dust/100),forecast=c.capacity*sun*(1-c.cloud*.59)*Math.max(.6,1-.004*Math.max(0,c.temp+22*sun-25))*.92*(1-c.dust/100),load=(45+8*(h>=7&&h<=20)+5*Math.sin(h*Math.PI/12)**2)*c.loadScale,price=h>=18&&h<22?1:h<7?.3:.65;return {i,h,label:`${String(Math.floor(h)).padStart(2,'0')}:${i%4?'15 30 45'.split(' ')[i%4-1]:'00'}`,pv,clean,forecast,load,price};});}
export function dispatch(input,c,method='rolling'){
 validate(c);const eta=.95,dt=.25,cap=method==='none'?0:c.battery,lo=.1*cap,hi=.9*cap,E0=.5*cap,pmax=cap?c.batteryPower:0;
 const N=cap?32:0,step=N?(hi-lo)/N:0,levels=Array.from({length:N+1},(_,i)=>lo+i*step);let energy=E0;const rows=[];
 const flows=(r,de)=>{const charge=Math.max(0,de)/eta/dt,discharge=Math.max(0,-de)*eta/dt,net=r.load+charge-r.pv-discharge,imp=Math.max(0,net),exp=Math.min(c.exportLimit,Math.max(0,-net)),curtail=Math.max(0,-net-exp);return {charge,discharge,import:imp,export:exp,curtail};};
 const cost=(r,f)=>(f.import*r.price-f.export*.25+.035*(f.charge+f.discharge))*dt;
 for(let t=0;t<input.length;t++){
  const r=input[t];let de=0;
  if(cap&&method==='rolling'){
   // Backward discrete dynamic programming; only current PV is observed, future values use forecast.
   let V=levels.map(x=>Math.abs(x-E0)<1e-7?0:1e15),choice=0;
   for(let k=input.length-1;k>=t;k--){const frow={...input[k],pv:k===t?r.pv:Math.max(0,input[k].forecast*(1-.10*c.risk))},W=new Array(N+1).fill(1e15);let pick=new Array(N+1).fill(0);
    for(let a=0;a<=N;a++){for(let b=0;b<=N;b++){const d=levels[b]-levels[a];if(d>pmax*eta*dt+1e-8||-d>pmax/eta*dt+1e-8)continue;const f=flows(frow,d),v=cost(frow,f)+.02*f.curtail*dt+V[b];if(v<W[a]){W[a]=v;pick[a]=b;}}}
    if(k===t)choice=pick[Math.round((energy-lo)/step)];V=W;
   }de=levels[choice]-energy;
  }else if(cap&&method==='rule'){
   const remaining=input.length-t-1,maxFutureCharge=remaining*pmax*eta*dt,maxFutureDis=remaining*pmax/eta*dt;
   if(r.pv>r.load)de=Math.min((r.pv-r.load)*eta*dt,hi-energy,pmax*eta*dt);
   else if(r.price>=.99)de=-Math.min((r.load-r.pv)/eta*dt,energy-lo,pmax/eta*dt);
   de=clamp(de,Math.max(lo-energy,E0-maxFutureCharge-energy),Math.min(hi-energy,E0+maxFutureDis-energy));
   de=clamp(de,-pmax/eta*dt,pmax*eta*dt);
  }
  const f=flows(r,de);rows.push({...r,...f,energy,energyNext:energy+de,cost:cost(r,f)});energy+=de;
 }
 const integrate=k=>sum(rows.map(r=>r[k]))*dt,balance={pv:integrate('pv'),load:integrate('load'),import:integrate('import'),export:integrate('export'),charge:integrate('charge'),discharge:integrate('discharge'),curtail:integrate('curtail'),cost:sum(rows.map(r=>r.cost)),loss:integrate('charge')-integrate('discharge')-(energy-E0)};
 balance.utilization=balance.pv?100*(1-balance.curtail/balance.pv):0;balance.storageDelta=energy-E0;balance.residual=balance.pv+balance.import-balance.load-balance.export-balance.curtail-balance.loss-balance.storageDelta;
 return {method,rows,balance,finalEnergy:energy};
}
export function planOperations(c,selected){validate(c);const n=selected.length;let droneReasons=[],robotReasons=[];if(c.wind>8)droneReasons.push('风速超过8米/秒');if(c.rain>0)droneReasons.push('存在降雨');if(c.temp>45||c.temp<0)droneReasons.push('环境温度超出演练范围0–45℃');if(c.deviceBattery<30)droneReasons.push('设备电量低于30%');if(!n)droneReasons.push('未选择区域');if(c.rain>0)robotReasons.push('降雨期间暂停干式清扫');if(c.wind>12)robotReasons.push('风速超过12米/秒');if(c.temp>45)robotReasons.push('高温需冷却后复核');if(c.deviceBattery<25)robotReasons.push('机器人电量低于25%');if(!n)robotReasons.push('未选择区域');return {drone:{allowed:!droneReasons.length,reasons:droneReasons,minutes:Math.ceil(n*1.8+8),battery:Math.ceil(n*1.2+12),route:[...selected].sort((a,b)=>Math.floor(a/8)-Math.floor(b/8)||((Math.floor(a/8)%2)?b-a:a-b))},robot:{allowed:!robotReasons.length,reasons:robotReasons,minutes:Math.ceil(n*3+10),battery:Math.ceil(n*1.8+10)}};}
export function transitionTask(task,event){const m={planned:{start:'running',cancel:'cancelled'},running:{pause:'paused',complete:'completed',cancel:'cancelled'},paused:{resume:'running',cancel:'cancelled'}};const status=m[task.status]?.[event];if(!status)throw Error('该任务状态不支持此操作');return {...task,status};}
export function parseCSV(text){text=text.replace(/^\uFEFF/,'');const lines=text.trim().split(/\r?\n/);if(lines.length<2)throw Error('CSV缺少数据行');const head=lines[0].split(',').map(x=>x.trim()),ti=head.indexOf('timestamp'),ai=head.indexOf('actual_kw'),pi=head.indexOf('pred_kw');if([ti,ai,pi].some(x=>x<0))throw Error('需要timestamp,actual_kw,pred_kw三列');const seen=new Set();return lines.slice(1).filter(x=>x.trim()).map((line,i)=>{const a=line.split(','),raw=a[ti]?.trim();if(!/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2})?(?:Z)?$/.test(raw))throw Error(`第${i+2}行时间应为YYYY-MM-DDTHH:mm`);const parts=raw.match(/\d+/g).map(Number),[yr,mo,da,hr,mi,se=0]=parts,check=new Date(Date.UTC(yr,mo-1,da,hr,mi,se));if(yr<100||hr>23||mi>59||se>59||check.getUTCFullYear()!==yr||check.getUTCMonth()!==mo-1||check.getUTCDate()!==da)throw Error(`第${i+2}行日期不存在或时间超出范围`);const time=check.getTime(),actual=Number(a[ai]),pred=Number(a[pi]);if(!Number.isFinite(time)||a[ai]?.trim()===''||a[pi]?.trim()===''||![actual,pred].every(x=>Number.isFinite(x)&&x>=0))throw Error(`第${i+2}行时间或功率无效`);if(seen.has(time))throw Error(`第${i+2}行时间重复`);seen.add(time);return {time,timestamp:raw,actual,pred};}).sort((a,b)=>a.time-b.time);}
export function cleaningBenefit({energy,before,after,value,cost}){const gainPct=((1-after/100)/(1-before/100)-1)*100,extraEnergy=energy*gainPct/100;return {gainPct,extraEnergy,gross:extraEnergy*value,net:extraEnergy*value-cost};}
export function predictMLP(input,model){let x=input.map((v,i)=>(v-model.mean[i])/model.scale[i]);for(let l=0;l<model.weights.length;l++){const w=model.weights[l];x=model.biases[l].map((b,j)=>{const z=b+sum(x.map((v,i)=>v*w[i][j]));return l===model.weights.length-1?z:Math.max(0,z);});}return x[0];}
export function wilson(k,n,z=1.96){if(!n)return [0,0];const p=k/n,d=1+z*z/n,c=(p+z*z/(2*n))/d,r=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [Math.max(0,c-r),Math.min(1,c+r)];}
export function spectralMix(wavelength,soil){const base=.075+.018*Math.sin(wavelength/90)+.025*(wavelength-400)/2100,dust=.22+.12*Math.sin((wavelength-350)/1200)+.05*Math.cos(wavelength/70);return (1-soil)*base+soil*dust;}

export function taskGate(task,tasks,environment,availableBattery){const p=planOperations({...environment,deviceBattery:availableBattery},task.regions)[task.type],reasons=[...p.reasons];if(tasks.some(t=>t.id!==task.id&&t.type===task.type&&['running','paused'].includes(t.status)))reasons.push('同一设备已有运行或暂停任务');if(availableBattery<task.battery+(task.type==='drone'?20:15))reasons.push('剩余电量不足任务与返航余量');return {allowed:reasons.length===0,reasons};}
