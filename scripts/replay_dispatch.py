"""Reproduce the five-day PPT LP replay from public-source.csv and benchmark.json."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
from scipy.optimize import linprog
ROOT=Path(__file__).resolve().parents[1]
b=json.loads((ROOT/'data/benchmark.json').read_text());raw=pd.read_csv(ROOT/'data/public-source.csv',parse_dates=['timestamp'],float_precision='round_trip')
mx=raw.loc[raw.timestamp<'2020-06-07','AC_POWER'].max();raw['slot']=raw.timestamp.dt.hour*4+raw.timestamp.dt.minute//15
profile=(raw[raw.timestamp<'2020-06-07'].groupby('slot').AC_POWER.median()/mx*177.1).reindex(range(96)).fillna(0).values
lookup={pd.Timestamp(r['time']):r['pred'] for r in b['test']};dt=.25;hours=np.arange(96)/4
load=45+8*((hours>=7)&(hours<=20))+5*np.sin(hours*2*np.pi/24)**2
price=np.where((hours>=18)&(hours<22),1.,np.where(hours<7,.3,.65))
def solve(F,L,pr,E=100):
 H=len(F);n=6*H+1;c=np.zeros(n);c[:H]=pr*dt;c[H:2*H]=-.25*dt;c[2*H:4*H]=.035*dt;c[4*H:5*H]=.2*dt;A=[];rhs=[]
 for j in range(H):
  z=np.zeros(n);z[j]=1;z[H+j]=-1;z[2*H+j]=-1;z[3*H+j]=1;z[4*H+j]=-1;A.append(z);rhs.append(L[j]-F[j])
  z=np.zeros(n);z[5*H+j+1]=1;z[5*H+j]=-1;z[2*H+j]=-.95*dt;z[3*H+j]=dt/.95;A.append(z);rhs.append(0)
 z=np.zeros(n);z[5*H]=1;A.append(z);rhs.append(E);z=np.zeros(n);z[-1]=1;A.append(z);rhs.append(100)
 bounds=[(0,250)]*H+[(0,20)]*H+[(0,100)]*(2*H)+[(0,float(v)) for v in F]+[(20,180)]*(H+1)
 r=linprog(c,A_eq=A,b_eq=rhs,bounds=bounds,method='highs');assert r.success;return r
rows=[]
for date in pd.date_range('2020-06-12','2020-06-16'):
 day=raw[raw.timestamp.dt.normalize()==date].sort_values('timestamp');assert len(day)==96
 pv=day.AC_POWER.values/mx*177.1;E=100.;arr={k:[] for k in ['import','export','charge','discharge','curtail']}
 for t in range(96):
  H=96-t;F=profile[t:].copy();now=date+pd.Timedelta(minutes=15*t);hour=lookup.get(now+pd.Timedelta(hours=1),F[min(4,H-1)])
  for j in range(min(4,H)):F[j]=pv[t]+(hour-pv[t])*(j+1)/4
  F=np.clip(F,0,177.1);r=solve(F,load[t:],price[t:],E);ch=r.x[2*H];dis=r.x[3*H];assert ch*dis<1e-6
  net=pv[t]+dis-load[t]-ch;imp=max(-net,0);exp=min(max(net,0),20);cur=max(net-20,0);E+=.95*ch*dt-dis*dt/.95
  assert 20-1e-6<=E<=180+1e-6
  assert abs(pv[t]+imp+dis-load[t]-ch-exp-cur)<1e-6
  for k,v in [('import',imp),('export',exp),('charge',ch),('discharge',dis),('curtail',cur)]:arr[k].append(v)
 assert abs(E-100)<1e-5
 Bimp=np.maximum(load-pv,0);Bexp=np.minimum(np.maximum(pv-load,0),20);Bcur=np.maximum(pv-load-20,0)
 bc=float(sum((price*Bimp-.25*Bexp)*dt));mc=float(sum((price*np.array(arr['import'])-.25*np.array(arr['export'])+.035*(np.array(arr['charge'])+np.array(arr['discharge'])))*dt));pve=float(sum(pv)*dt)
 oracle=solve(pv,load,price);oc=float(sum((price*oracle.x[:96]-.25*oracle.x[96:192]+.035*(oracle.x[192:288]+oracle.x[288:384]))*dt))
 # Same assets rule: pre-defined night charge / evening discharge with end-of-day restoration.
 E=100.;ri=[];re=[];rc=[];rch=[];rdis=[]
 for t in range(96):
  h=t/4;ch=dis=0
  if 2<=h<4:ch=min(40,(180-E)/(.95*.25))
  if 18<=h<21:dis=min(40,(E-20)*.95/.25)
  if h>=23:ch=max(0,min(100,(100-E)/(.95*(96-t)*.25)))
  E+=ch*.95*.25-dis*.25/.95;net=pv[t]+dis-load[t]-ch;ri.append(max(-net,0));re.append(min(max(net,0),20));rc.append(max(net-20,0));rch.append(ch);rdis.append(dis)
 assert abs(E-100)<1e-5
 rule=float(sum((price*np.array(ri)-.25*np.array(re)+.035*(np.array(rch)+np.array(rdis)))*.25))
 row={'date':str(date.date()),'pv':pve,'base_cost':bc,'mpc_cost':mc,'oracle_cost':oc,'saving':bc-mc,'cost_reduction':(bc-mc)/bc*100,'base_curtail':float(sum(Bcur)*dt),'mpc_curtail':float(sum(arr['curtail'])*dt),'base_util':100*(1-sum(Bcur)*dt/pve),'mpc_util':100*(1-sum(arr['curtail'])*dt/pve),'rule_cost':rule,'rule_util':100*(1-sum(rc)*dt/pve),'rule_curtail':float(sum(rc)*dt),'upgrade_saving':rule-mc};row['gain_pp']=row['mpc_util']-row['base_util'];rows.append(row)
groups=[]
for date in sorted(set(r['time'][:10] for r in b['test'])):
 rr=[r for r in b['test'] if r['day'] and r['time'].startswith(date)]
 groups.append([sum((r['actual']-r['pred'])**2 for r in rr),sum((r['actual']-r['persist'])**2 for r in rr),len(rr)])
groups=np.array(groups);rng=np.random.default_rng(42);idx=rng.integers(0,len(groups),size=(10000,len(groups)));v=groups[idx].sum(axis=1);skills=(1-np.sqrt(v[:,0]/v[:,2])/np.sqrt(v[:,1]/v[:,2]))*100
s=np.array([x['saving'] for x in rows]);ix=rng.integers(0,len(s),size=(10000,len(s)));ci=np.quantile(s[ix].mean(axis=1),[.025,.975])
st={'mean_saving':float(s.mean()),'mean_saving_ci':ci.tolist(),'cost_reduction':(sum(x['base_cost'] for x in rows)-sum(x['mpc_cost'] for x in rows))/sum(x['base_cost'] for x in rows)*100,'base_util':100*(1-sum(x['base_curtail'] for x in rows)/sum(x['pv'] for x in rows)),'mpc_util':100*(1-sum(x['mpc_curtail'] for x in rows)/sum(x['pv'] for x in rows)),'rmse_skill_ci':np.quantile(skills,[.025,.975]).tolist(),'rmse_day_blocks':len(groups),'rule_cost_reduction':(sum(x['rule_cost'] for x in rows)-sum(x['mpc_cost'] for x in rows))/sum(x['rule_cost'] for x in rows)*100,'rule_util':100*(1-sum(x['rule_curtail'] for x in rows)/sum(x['pv'] for x in rows)),'upgrade_mean_saving':float(np.mean([x['upgrade_saving'] for x in rows]))}
st['upgrade_year_net']=st['upgrade_mean_saving']*240-3000
res={'days':rows,'stats':st,'soiling':[{'before':i,'relative_gain':(.99/(1-i/100)-1)*100} for i in [3,5,8,10]]}
(ROOT/'data/replay-dispatch.json').write_text(json.dumps(res,ensure_ascii=False,separators=(',',':')))
print(json.dumps({'days':len(rows),'same_asset_cost_reduction_pct':st['rule_cost_reduction'],'losing_days':sum(x['upgrade_saving']<0 for x in rows)},ensure_ascii=False))
