"""Project compact Cross-Unet: multiscale history + future-weather attention + monotone dust gate.
Independent implementation inspired by ZjuMachine/PV-power; NOT a reproduction of its full model.
"""
import torch
from torch import nn
import torch.nn.functional as F
class SoilingCrossUNet(nn.Module):
 def __init__(self,width=24,heads=4):
  super().__init__();self.width=width
  self.enc1=nn.Sequential(nn.Conv1d(8,width,5,padding=2),nn.GELU(),nn.Conv1d(width,width,3,padding=1),nn.GELU())
  self.enc2=nn.Sequential(nn.Conv1d(width,width,3,stride=2,padding=1),nn.GELU())
  self.enc3=nn.Sequential(nn.Conv1d(width,width,3,stride=2,padding=1),nn.GELU())
  self.future=nn.Linear(5,width);self.cross=nn.ModuleList([nn.MultiheadAttention(width,heads,batch_first=True) for _ in range(3)])
  self.norm=nn.LayerNorm(width);self.ff=nn.Sequential(nn.Linear(width,width*2),nn.GELU(),nn.Linear(width*2,width));self.pv=nn.Linear(width,1);self.load=nn.Linear(width,1)
  self.level_weights=nn.Parameter(torch.zeros(3));self.soil_scale=nn.Parameter(torch.tensor(0.))
 def forward(self,hist,future):
  a=self.enc1(hist.transpose(1,2));b=self.enc2(a);c=self.enc3(b);q=self.future(future[:,:,:5]);out=q
  for weight,attn,key in zip(torch.softmax(self.level_weights,0),self.cross,[a,b,c]):
   key=key.transpose(1,2);out=out+weight*attn(q,key,key,need_weights=False)[0]
  out=self.norm(out+F.interpolate(c,size=q.shape[1],mode='linear',align_corners=False).transpose(1,2));out=out+self.ff(out)
  g=future[:,:,0];temp=future[:,:,1]*50+22*g;phys=g*(1-.004*(temp-25)).clamp(.6,1.2)*.92
  clean=(phys+.12*torch.tanh(self.pv(out).squeeze(-1))).clamp(0,1)*(g>.001)
  p=clean*(1-future[:,:,5].clamp(0,.5)*2*torch.sigmoid(self.soil_scale)).clamp(0,1)
  load=(future[:,:,2]+.12*torch.tanh(self.load(out).squeeze(-1))).clamp(.1,1.)
  return p,load,clean
