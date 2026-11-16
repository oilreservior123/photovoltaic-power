"""Reproduce chronological 1-hour MLP baseline; never shuffle split dates."""
from pathlib import Path
import json,copy,time,warnings
import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
ROOT=Path(__file__).resolve().parents[1]
d=pd.read_csv(ROOT/'data/public-source.csv',parse_dates=['timestamp'],float_precision='round_trip').set_index('timestamp').asfreq('15min')
np.random.seed(42)
scale=d.AC_POWER.loc[:'2020-06-06'].max();d['p']=d.AC_POWER/scale
cols=[]
for lag in [0,1,2,3,4,8,12,24,48,92,96]:
 c='lag'+str(lag);d[c]=d.p.shift(lag);cols.append(c)
cols+=['AMBIENT_TEMPERATURE','MODULE_TEMPERATURE','IRRADIATION']
h=d.index.hour+d.index.minute/60;d['sin']=np.sin(2*np.pi*h/24);d['cos']=np.cos(2*np.pi*h/24);cols+=['sin','cos']
d['y']=d.p.shift(-4);d['target_time']=d.index+pd.Timedelta(hours=1);d['target_irrad']=d.IRRADIATION.shift(-4)
f=d.dropna(subset=cols+['y','target_irrad']);tr=f.target_time<'2020-06-07';va=(f.target_time>='2020-06-07')&(f.target_time<'2020-06-12');te=f.target_time>='2020-06-12'
Xraw=f[cols].values;y=f.y.values;scaler=StandardScaler().fit(Xraw[tr]);X=scaler.transform(Xraw)
m=MLPRegressor(hidden_layer_sizes=(64,32,16),activation='relu',alpha=.01,max_iter=1,warm_start=True,batch_size=128,learning_rate_init=.001,random_state=42)
best=999;hist=[];t0=time.time()
with warnings.catch_warnings():
 warnings.simplefilter('ignore')
 for epoch in range(180):
  m.fit(X[tr],y[tr]);vp=np.clip(m.predict(X[va]),0,1);err=np.mean((vp-y[va])**2);hist.append([epoch+1,float(m.loss_),float(err)])
  if err<best:best=err;bm=copy.deepcopy(m);be=epoch+1
m=bm;seconds=time.time()-t0;pred=np.clip(m.predict(X),0,1)
night=(f.target_time.dt.hour>=21)|(f.target_time.dt.hour<4);pred[night]=0
ridge=Ridge(alpha=5).fit(X[tr],y[tr]);rp=np.clip(ridge.predict(X),0,1);rp[night]=0
pv=f.p.values;day=f.target_irrad.values>.05
cal=abs(y[va&day]-pred[va&day]);q={str(p):float(np.quantile(cal,p,method='higher')) for p in [.5,.6,.7,.8,.9,.95]}
rows=[]
for i in np.flatnonzero(te):
 rows.append({'time':str(f.iloc[i].target_time),'actual':float(y[i]*177.1),'pred':float(pred[i]*177.1),'persist':float(pv[i]*177.1),'ridge':float(rp[i]*177.1),'day':bool(day[i]),'input':Xraw[i].tolist()})
result={'capacity':177.1,'split':[int(tr.sum()),int(va.sum()),int(te.sum())],'seed':42,'bestEpoch':be,'epochs':180,'seconds':seconds,'features':cols,'history':hist,'quantiles':q,'validationResiduals':cal.tolist(),'test':rows,'period':['2020-05-15','2020-06-17'],'inverter':'bvBOhCH3iADSZry','daily':[{'date':str(k),'energy':float(v*.25*177.1)} for k,v in d.p.groupby(d.index.date).sum().items()]}
result['validationDaytimeCount']=int((va&day).sum())
result['validationResidualsByModel']={key:abs(y[va&day]-v[va&day]).tolist() for key,v in [('pred',pred),('ridge',rp),('persist',pv)]}
result['quantilesByModel']={key:{str(p):float(np.quantile(v,p,method='higher')) for p in [.5,.6,.7,.8,.9,.95]} for key,v in result['validationResidualsByModel'].items()}
(ROOT/'data/benchmark.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
model={'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'weights':[x.tolist() for x in m.coefs_],'biases':[x.tolist() for x in m.intercepts_],'features':cols,'capacity':177.1,'seed':42,'bestEpoch':be}
(ROOT/'data/model.json').write_text(json.dumps(model,separators=(',',':')))
print(json.dumps({'split':result['split'],'bestEpoch':be,'seconds':seconds,'daytimeTest':sum(r['day'] for r in rows)}))
