"""Train a compact physical soiling-aware Cross-Unet on explicitly synthetic scenarios."""
from pathlib import Path
import numpy as np,json,copy,time,datetime,hashlib
import torch
from cross_model import SoilingCrossUNet
ROOT=Path(__file__).resolve().parents[1];torch.set_num_threads(2);torch.manual_seed(42);np.random.seed(42)
CAP=177.1

def day(date,rng,soil):
 doy=date.timetuple().tm_yday;hour=np.arange(96)/4;daylight=12+2.2*np.sin((doy-80)*2*np.pi/365);rise=12-daylight/2;solar=np.maximum(0,np.sin((hour-rise)/daylight*np.pi));solar[(hour<rise)|(hour>rise+daylight)]=0
 season=20+13*np.sin((doy-100)*2*np.pi/365);cloud=float(rng.uniform(.05,.75));cloudCurve=np.clip(cloud+.12*np.sin(hour*1.2+rng.uniform(0,6))+.06*rng.normal(size=96),0,.95)
 irradiance=solar*(1-.7*cloudCurve);temp=season+5*np.sin((hour-7)/12*np.pi);wind=np.clip(rng.normal(5,1.5,96),0,15)
 board=temp+22*irradiance;clean=irradiance*(1-.004*(board-25)).clip(.6,1.2)*.92
 pv=(clean*(1-soil)+.006*rng.normal(size=96)*solar).clip(0,1)
 load=(.27+.055*((hour>=7)&(hour<21))+.015*np.sin(hour*np.pi/12)**2+.012*np.sin(doy*.11)+rng.normal(0,.006,96)).clip(.15,.6)
 # Synthetic issued forecast: biased but noisy radiation and temperature, not measured future weather.
 nwp=np.clip(irradiance*1.10+.035*solar*np.sin(hour*.8+rng.uniform(0,6))+.015*solar*rng.normal(size=96),0,1.1)
 tpred=temp+1.2+rng.normal(0,.5,96);loadprior=.27+.055*((hour>=7)&(hour<21))+.015*np.sin(hour*np.pi/12)**2
 soilprior=np.clip(soil+rng.normal(0,.004),.005,.25)
 hist=np.stack([pv,load,irradiance,temp/50,wind/20,np.full(96,soilprior),np.sin(hour*np.pi/12),np.cos(hour*np.pi/12)],-1).astype('float32')
 future=np.stack([nwp,tpred/50,loadprior,np.sin(hour*np.pi/12),np.cos(hour*np.pi/12),np.full(96,soilprior)],-1).astype('float32')
 return hist,future,np.stack([pv,load],-1).astype('float32'),clean.astype('float32'),{'date':date.isoformat(),'cloud':round(cloud,3),'soil':round(soil,4),'temperature':round(float(temp.mean()),2),'weather':'多云' if cloud>.5 else '高污染' if soil>.12 else '晴间多云'}
rng=np.random.default_rng(42);allDays=[];soil=.04;start=datetime.date(2025,1,1)
for i in range(421):
 soil=min(.2,soil+.0025)
 if i%23==0:soil=.015
 allDays.append(day(start+datetime.timedelta(days=i),rng,soil))
h=np.stack([allDays[i-1][0] for i in range(1,421)]);f=np.stack([allDays[i][1] for i in range(1,421)]);y=np.stack([allDays[i][2] for i in range(1,421)])
# 420 target-day groups: 294 train / 63 validation / 63 test. History is allowed from already observed days.
slices={'train':slice(0,294),'validation':slice(294,357),'test':slice(357,420)}
H=torch.from_numpy(h);F=torch.from_numpy(f);Y=torch.from_numpy(y);model=SoilingCrossUNet();optim=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
best=float('inf');bestEpoch=0;history=[];t0=time.perf_counter()
for epoch in range(1,81):
 model.train();perm=torch.randperm(294);losses=[]
 for idx in perm.split(32):
  optim.zero_grad();p,l,_=model(H[idx],F[idx]);loss=((p-Y[idx,:,0])**2).mean()+.5*((l-Y[idx,:,1])**2).mean();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optim.step();losses.append(float(loss.detach()))
 model.eval()
 with torch.no_grad():
  p,l,_=model(H[294:357],F[294:357]);val=float(((p-Y[294:357,:,0])**2).mean()+.5*((l-Y[294:357,:,1])**2).mean())
 if val<best:best=val;bestEpoch=epoch;state=copy.deepcopy(model.state_dict())
 history.append({'epoch':epoch,'train':float(np.mean(losses)),'validation':val})
 if epoch%20==0:print('epoch',epoch,'validation',round(val,6),flush=True)
model.load_state_dict(state);model.eval()
with torch.no_grad():
 pred,load,clean=model(H,F);masked=F.clone();masked[:,:,5]=0;maskpred,_,_=model(H,masked)
pred=pred.numpy();load=load.numpy();clean=clean.numpy();maskpred=maskpred.numpy();physics=(f[:,:,0]*(1-.004*(f[:,:,1]*50+22*f[:,:,0]-25)).clip(.6,1.2)*.92*(1-f[:,:,5])).clip(0,1)
persist=h[:,:,0]
def metric(a,p,mask):
 e=p[mask]-a[mask];return {'mae_kw':float(abs(e).mean()*CAP),'nmae':float(abs(e).mean()*100),'nrmse':float(np.sqrt((e**2).mean())*100),'bias_kw':float(e.mean()*CAP),'n':int(mask.sum())}
mask=f[357:,:,0]>.02;a=y[357:,:,0];m={k:metric(a,v[357:],mask) for k,v in [('cross',pred),('physics',physics),('persistence',persist),('masked_soil',maskpred)]}
cal=y[294:357,:,0]-pred[294:357];calLoad=y[294:357,:,1]-load[294:357];q={str(level):float(np.quantile(abs(cal)[f[294:357,:,0]>.02],level,method='higher')*CAP) for level in [.8,.9,.95]}
test=[]
for j in range(357,420):
 meta=allDays[j+1][4];maskj=f[j,:,0]>.02;e=pred[j]-y[j,:,0]
 test.append({**meta,'actual':(y[j,:,0]*CAP).round(5).tolist(),'pred':(pred[j]*CAP).round(5).tolist(),'load_actual':(y[j,:,1]*CAP).round(5).tolist(),'load_pred':(load[j]*CAP).round(5).tolist(),'physics':(physics[j]*CAP).round(5).tolist(),'persistence':(persist[j]*CAP).round(5).tolist(),'clean':(clean[j]*CAP).round(5).tolist(),'daylight':maskj.tolist(),'metrics':metric(y[j,:,0],pred[j],maskj)})
# Seven future-looking scenario days; issued synthetic NWP, not live weather or observed field power.
fut=[];previous=day(datetime.date(2026,11,18),np.random.default_rng(318),.08)
for j in range(7):
 date=datetime.date(2026,11,19)+datetime.timedelta(days=j);cur=day(date,np.random.default_rng(1000+j),.08+.0025*j)
 with torch.no_grad():p,l,cl=model(torch.from_numpy(previous[0][None]),torch.from_numpy(cur[1][None]))
 fut.append({**cur[4],'pv':(p[0].numpy()*CAP).round(5).tolist(),'load':(l[0].numpy()*CAP).round(5).tolist(),'irradiance_forecast':(cur[1][:,0]*1000).round(2).tolist(),'soil_prior':float(cur[1][0,5])});next_hist=cur[0].copy();next_hist[:,0]=p[0].numpy();next_hist[:,1]=l[0].numpy();next_hist[:,2]=cur[1][:,0];next_hist[:,3]=cur[1][:,1];next_hist[:,4]=.25;previous=list(cur);previous[0]=next_hist
covered={str(level):float(np.mean([(np.abs(np.array(t['pred'])-np.array(t['actual']))[t['daylight']]<=q[str(level)]).mean() for t in test])*100) for level in [.8,.9,.95]}
# Equal-day block bootstrap skill against physical baseline, never resample individual timestamps.
groups=[]
for j in range(357,420):
 mm=f[j,:,0]>.02;groups.append([float(((pred[j,mm]-y[j,mm,0])**2).sum()),float(((physics[j,mm]-y[j,mm,0])**2).sum())])
groups=np.array(groups);br=np.random.default_rng(42);sums=groups[br.integers(0,63,(2000,63))].sum(1);skills=(1-np.sqrt(sums[:,0]/sums[:,1]))*100
result={'schema_version':1,'model_name':'蒙尘感知多模态 Cross-Unet（项目轻量实现）','evidence':'synthetic_training_actual_computation','official_reproduction':False,'capacity_kwp':CAP,'seed':42,'split':{'ratio':[70,15,15],'counts':[294,63,63],'unit':'目标日','train_end':allDays[294][4]['date'],'validation_start':allDays[295][4]['date'],'validation_end':allDays[357][4]['date'],'test_start':allDays[358][4]['date'],'test_end':allDays[420][4]['date']},'parameters':sum(p.numel() for p in model.parameters()),'epochs':80,'best_epoch':bestEpoch,'training_seconds':round(time.perf_counter()-t0,3),'torch_version':torch.__version__,'metrics':m,'history':history,'quantiles_kw':q,'coverage':covered,'skill_ci':np.quantile(skills,[.025,.975]).tolist(),'test':test,'validation_residuals_kw':(cal*CAP).round(5).tolist(),'validation_load_residuals_kw':(calLoad*CAP).round(5).tolist(),'future':fut,'feature_schema':{'history':['pv_pu','load_pu','ghi_pu','temperature_c_div50','wind_ms_div20','soil_loss_fraction','hour_sin','hour_cos'],'future':['nwp_ghi_pu','nwp_temp_c_div50','load_prior_pu','hour_sin','hour_cos','soil_loss_prior']},'samples':[{'sample_id':'DAY-'+allDays[j+1][4]['date'],'split':split,'history_shape':[96,8],'future_shape':[96,6],'target_shape':[96,2],'history_first':h[j,0].tolist(),'forecast_first_daylight':f[j,40].tolist(),'target_at_10h_kw':(y[j,40]*CAP).tolist(),'issued_at':allDays[j][4]['date']+'T23:45:00+08:00','target_date':allDays[j+1][4]['date']} for split,j in [('train',0),('validation',294),('test',357)]]}
(ROOT/'data/cross-experiment.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
(ROOT/'data/cross-weights.json').write_text(json.dumps({'model':'project_soiling_cross_unet','parameters':{k:v.tolist() for k,v in state.items()},'seed':42,'width':24,'heads':4,'training_evidence':'synthetic'},separators=(',',':')))
(ROOT/'data/cross-model-card.json').write_text(json.dumps({k:v for k,v in result.items() if k not in ['test','validation_residuals_kw','validation_load_residuals_kw','future','history']},ensure_ascii=False,indent=2))
(ROOT/'data/cross-samples.json').write_text(json.dumps({'schema':result['feature_schema'],'samples':result['samples'],'note':'合成样本；滞后日观测与起报时已知预报分开；无测试标签进入训练'},ensure_ascii=False,indent=2))
print(json.dumps({'best_epoch':bestEpoch,'seconds':result['training_seconds'],'parameters':result['parameters'],'metrics':m,'coverage':covered,'skill_ci':result['skill_ci']},ensure_ascii=False),flush=True)
