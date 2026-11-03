"""
rose_effect.py - Hiệu ứng BÓ HOA hồng 3D (hồng neon) cho Streamlit.

Mô phỏng video: một bó 3 bông hồng hồng kính có cuống dài + lá, vòng tròn trắng
xiên quanh bó (có đầu sáng chạy vòng), các vệt sáng bay ngang và trái tim nổi quanh.
Lúc mở trang các hạt xoáy rồi hội tụ lại thành bó hoa, sau đó bó hoa lắc xoay nhẹ.

Cách dùng trong app.py (đặt file này cùng thư mục với app.py):

    from rose_effect import render_rose      # hoặc render_bouquet (cùng một hàm)
    render_rose(height=520)

Chạy thử riêng:  streamlit run rose_effect.py

Thiết kế nhẹ để không giật lag:
  - Vẽ bằng <canvas> 2D, hạt được gom nhóm theo màu, đường nét vẽ gộp theo lô
  - Giới hạn DPR tối đa 1.5, tự giảm số hạt nếu máy chậm (< ~45 FPS)
  - Tự dừng khi tab bị ẩn hoặc khi hiệu ứng nằm ngoài màn hình
  - Không có hiệu ứng chạm / click
"""
import json

_TEMPLATE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;background:transparent;overflow:hidden}
#wrap{position:relative;width:100%;height:100%;
  background:radial-gradient(ellipse 44% 40% at 50% 46%,rgba(255,60,140,.20),rgba(255,60,140,0) 72%)}
canvas{position:absolute;left:0;top:0;width:100%;height:100%;display:block}
</style></head>
<body><div id="wrap"><canvas id="c"></canvas></div>
<script>
(function(){
"use strict";
var CFG = __CFG__;
var canvas = document.getElementById("c");
var ctx = canvas.getContext("2d");
var W=1, H=1, DPR=1, cx=0, cy=0, S=100, F=14;
var TWO_PI = Math.PI*2;

function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
var rnd = mulberry32(20261103);
function mod(a,b){return ((a%b)+b)%b;}
function clamp01(x){return x<0?0:(x>1?1:x);}
function ease(x){return x<0.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;}

/* ================= HÌNH HỌC BÓ HOA (toạ độ thế giới, tĩnh) ================= */
/* bề mặt hoa hồng tham số -> toạ độ cục bộ (x, lên, sâu) dạng đài hoa cao */
function rosePoint(r, th, o){
  var phi = (Math.PI/2)*Math.exp(-th/(8*Math.PI));
  var q   = 1 - mod(3.6*th, TWO_PI)/Math.PI;
  var xx  = 1 - 0.5*Math.pow(1.25*q*q - 0.25, 2);
  var yy  = 1.95653*r*r*Math.pow(1.27689*r - 1, 2)*Math.sin(phi);
  var rr  = xx*(r*Math.sin(phi) + yy*Math.cos(phi));
  o[0] = rr*Math.sin(th)*0.85;
  o[1] = (xx*(r*Math.cos(phi) - yy*Math.sin(phi)) - 0.36)*1.7;
  o[2] = rr*Math.cos(th)*0.85;
}
/* 3 bông hồng: s = cỡ, p = vị trí, tz/tx = độ nghiêng, ry = xoay quanh trục hoa */
var ROSES = [
  {s:0.74, p:[ 0.05, 0.92,-0.05], tz:-0.08, tx: 0.12, ry:0.0},
  {s:0.62, p:[-0.88, 0.28, 0.10], tz: 0.52, tx: 0.10, ry:1.7},
  {s:0.60, p:[ 0.86, 0.48,-0.10], tz:-0.48, tx:-0.06, ry:3.1}
];
ROSES.forEach(function(R){
  R.cr=Math.cos(R.ry); R.sr=Math.sin(R.ry);
  R.cX=Math.cos(R.tx); R.sX=Math.sin(R.tx);
  R.cZ=Math.cos(R.tz); R.sZ=Math.sin(R.tz);
});
var _w=[0,0,0];
function toWorld(R,x,y,z,o){
  var a=x*R.cr+z*R.sr, b=-x*R.sr+z*R.cr; x=a; z=b;
  var y1=y*R.cX-z*R.sX, z1=y*R.sX+z*R.cX;
  var x2=x*R.cZ-y1*R.sZ, y2=x*R.sZ+y1*R.cZ;
  o[0]=R.p[0]+x2*R.s; o[1]=R.p[1]+y2*R.s; o[2]=R.p[2]+z1*R.s;
}

/* ---- đường nét: viền cánh, cuống, lá (gom vào các mảng điểm + đoạn) ---- */
var LPX=[], LPY=[], LPZ=[];
var SEG=[[],[],[],[]];           /* 0 viền ngoài, 1 viền trong, 2 cuống, 3 lá */
function addPoly(style, pts, closed){
  var base=LPX.length, n=pts.length, i;
  for(i=0;i<n;i++){ LPX.push(pts[i][0]); LPY.push(pts[i][1]); LPZ.push(pts[i][2]); }
  for(i=0;i<n-1;i++){ SEG[style].push(base+i, base+i+1); }
  if(closed){ SEG[style].push(base+n-1, base); }
}
var tmp=[0,0,0], loc=[0,0,0];
var TH0=-2, TH1=15*Math.PI;
var rimR=[1.0, 0.78];
ROSES.forEach(function(R){
  for(var ri=0; ri<rimR.length; ri++){
    var pts=[];
    for(var th=TH0; th<=TH1; th+=0.15){
      rosePoint(rimR[ri], th, loc); toWorld(R, loc[0],loc[1],loc[2], tmp);
      pts.push([tmp[0],tmp[1],tmp[2]]);
    }
    addPoly(ri, pts, false);
  }
});
/* cuống: Bezier bậc 3 từ đáy mỗi bông xuống một điểm buộc rồi xoè ra */
var WRAP=[0.0,-0.72,0.0];
var ENDS=[[ 0.08,-1.80, 0.12],[-0.52,-1.74,-0.12],[ 0.54,-1.76, 0.02]];
function bez(p0,p1,p2,p3,u){
  var v=1-u, a=v*v*v, b=3*v*v*u, c=3*v*u*u, d=u*u*u;
  return [a*p0[0]+b*p1[0]+c*p2[0]+d*p3[0], a*p0[1]+b*p1[1]+c*p2[1]+d*p3[1], a*p0[2]+b*p1[2]+c*p2[2]+d*p3[2]];
}
ROSES.forEach(function(R,k){
  toWorld(R, 0,-0.80,0, tmp);
  var B=[tmp[0],tmp[1],tmp[2]], E=ENDS[k];
  var P1=[B[0]+(WRAP[0]-B[0])*0.35, B[1]-0.45, B[2]+(WRAP[2]-B[2])*0.35];
  var P2=[WRAP[0]+(E[0]-WRAP[0])*0.2, WRAP[1]+0.1, WRAP[2]+(E[2]-WRAP[2])*0.2];
  var pts=[];
  for(var u=0;u<=1.0001;u+=1/30) pts.push(bez(B,P1,P2,E,u));
  addPoly(2, pts, false);
  /* 2 chiếc lá trên mỗi cuống */
  [0.34,0.58].forEach(function(uu,li){
    var P=bez(B,P1,P2,E,uu);
    var side=(li===0?-1:1)*(k===1?-1:1);
    var dx=side*0.85, dy=0.55, dz=(li===0?0.15:-0.15);
    var dl=Math.sqrt(dx*dx+dy*dy+dz*dz); dx/=dl; dy/=dl; dz/=dl;
    var nx=-dy, ny=dx, nz=0; var nl=Math.sqrt(nx*nx+ny*ny)||1; nx/=nl; ny/=nl;
    var L=0.50, Wd=0.13, a=[], b=[], v;
    for(v=0; v<=1.0001; v+=0.1){
      var w=Wd*Math.sin(Math.PI*v)*(1-0.25*v);
      a.push([P[0]+dx*L*v+nx*w, P[1]+dy*L*v+ny*w, P[2]+dz*L*v+nz*w]);
      b.push([P[0]+dx*L*v-nx*w, P[1]+dy*L*v-ny*w, P[2]+dz*L*v-nz*w]);
    }
    b.reverse();
    addPoly(3, a.concat(b), true);
    addPoly(3, [[P[0],P[1],P[2]],[P[0]+dx*L,P[1]+dy*L,P[2]+dz*L]], false);
  });
});
var NL = LPX.length;
var LP0 = new Float32Array(NL*3);
for(var li2=0; li2<NL; li2++){ LP0[li2*3]=LPX[li2]; LP0[li2*3+1]=LPY[li2]; LP0[li2*3+2]=LPZ[li2]; }
var LX=new Float32Array(NL), LY=new Float32Array(NL), LZ=new Float32Array(NL);
var SA_=[], SB_=[];
for(var si=0; si<4; si++){
  var sa=new Uint32Array(SEG[si].length/2), sb=new Uint32Array(SEG[si].length/2);
  for(var sk=0; sk<sa.length; sk++){ sa[sk]=SEG[si][sk*2]; sb[sk]=SEG[si][sk*2+1]; }
  SA_.push(sa); SB_.push(sb);
}

/* ---- hạt cánh hoa ---- */
var NP = Math.max(600, CFG.count|0);
var RX=new Float32Array(NP), RY=new Float32Array(NP), RZ=new Float32Array(NP);
var SR=new Float32Array(NP), SAn=new Float32Array(NP), SV=new Float32Array(NP);
var SH=new Float32Array(NP), SP=new Float32Array(NP), DL=new Float32Array(NP);
var SZ=new Float32Array(NP), CL=new Uint8Array(NP);
var PX=new Float32Array(NP), PY=new Float32Array(NP), PS=new Float32Array(NP), BK=new Uint8Array(NP);
var ORD=new Uint32Array(NP);
var perm=[]; for(var pi=0; pi<NP; pi++) perm.push(pi);
for(var pj=NP-1; pj>0; pj--){ var pk=Math.floor(rnd()*(pj+1)); var pt=perm[pj]; perm[pj]=perm[pk]; perm[pk]=pt; }
for(var i=0;i<NP;i++){
  var kr = rnd(); var ki = kr<0.40 ? 0 : (kr<0.72 ? 1 : 2);
  var R0 = ROSES[ki];
  var r  = 1 - 0.55*Math.pow(rnd(), 1.8);
  var th = TH0 + Math.pow((perm[i]+rnd())/NP, 0.75)*(TH1-TH0);
  rosePoint(r, th, loc); toWorld(R0, loc[0],loc[1],loc[2], tmp);
  RX[i]=tmp[0]+(rnd()-0.5)*0.01; RY[i]=tmp[1]+(rnd()-0.5)*0.01; RZ[i]=tmp[2]+(rnd()-0.5)*0.01;
  var tt = clamp01((loc[1]+0.6)/2.0);
  var s  = 0.02 + 0.34*r + 0.30*rnd() + 0.12*(1-tt);
  CL[i]  = Math.min(6, Math.floor(clamp01(s)*7));
  SR[i]=0.5+rnd()*1.2; SAn[i]=rnd()*TWO_PI; SV[i]=0.30+0.95*rnd();
  SH[i]=(rnd()-0.5)*3.0; SP[i]=rnd()*TWO_PI; DL[i]=rnd();
  var zz=rnd(); SZ[i]= zz<0.5 ? 1.8 : (zz<0.84 ? 2.5 : 3.4);
}

/* ---- vệt sáng, trái tim ---- */
var NS = CFG.streaks ? 30 : 0;
var STR_R=[],STR_A=[],STR_W=[],STR_Y=[],STR_C=[];
for(var q=0;q<NS;q++){
  STR_R.push(1.0+rnd()*1.0); STR_A.push(rnd()*TWO_PI); STR_W.push(0.55+rnd()*1.1);
  STR_Y.push((rnd()-0.5)*3.4); STR_C.push(rnd()<0.6?0:1);
}
var HN = CFG.hearts ? 10 : 0;
var HR=[],HA=[],HV=[],HY=[],HS=[];
for(var h=0;h<HN;h++){ HR.push(1.0+rnd()*0.95); HA.push(rnd()*TWO_PI); HV.push(0.22+rnd()*0.4);
  HY.push(-1.2+rnd()*3.0); HS.push(8+rnd()*7); }
var heartSprite=(function(){
  var c=document.createElement("canvas"); c.width=48; c.height=48;
  var g=c.getContext("2d"); g.translate(24,24);
  g.shadowColor="rgba(255,80,160,.95)"; g.shadowBlur=10; g.fillStyle="#ff7cc0";
  g.beginPath(); g.moveTo(0,12); g.bezierCurveTo(-18,0,-12,-14,0,-5);
  g.bezierCurveTo(12,-14,18,0,0,12); g.fill(); return c;
})();

/* ---- vòng tròn trắng xiên ---- */
var RN = CFG.ring ? 120 : 0;
var RQX=new Float32Array(RN+1), RQY=new Float32Array(RN+1), RQZ=new Float32Array(RN+1);
var rA=0.34, rB=0.50, cA=Math.cos(rA), sA=Math.sin(rA), cB=Math.cos(rB), sB=Math.sin(rB);

var PAL=["#8a1a55","#c92a74","#ff4f93","#ff7fb0","#ffa8c8","#ffd0e2","#fff0f6"];
var ALPHA=[0.34,0.60,0.80], NB=21, HALO=true;
var CNT=new Uint32Array(NB), OFF=new Uint32Array(NB);

/* ================= PHÉP CHIẾU ================= */
var cs=1, sn=0, cp=1, sp=0, bob=0, _x=0, _y=0, _z=0, _k=1;
function P(x,y,z){
  var x1=x*cs+z*sn, z1=-x*sn+z*cs;
  var yy=y+bob, y2=yy*cp-z1*sp, z2=yy*sp+z1*cp;
  _k=F/(F+z2); _x=cx+x1*S*_k; _y=cy-y2*S*_k; _z=z2;
}
function resize(){
  DPR=Math.min(window.devicePixelRatio||1,1.5);
  var b=canvas.getBoundingClientRect();
  W=Math.max(1,Math.floor(b.width)); H=Math.max(1,Math.floor(b.height));
  canvas.width=Math.floor(W*DPR); canvas.height=Math.floor(H*DPR);
  ctx.setTransform(DPR,0,0,DPR,0,0);
  S=Math.min(W*0.22, H*0.25); cx=W/2; cy=H*0.5-0.16*S;
}

/* vẽ một lô đoạn thẳng cùng kiểu: pass 0 = phía xa (mờ), pass 1 = phía gần (sáng) */
function strokeSegs(st, color, wFar, aFar, wNear, aNear, gA){
  var A=SA_[st], B=SB_[st], n=A.length, pass, k, a, b;
  ctx.strokeStyle=color;
  for(pass=0; pass<2; pass++){
    ctx.lineWidth = pass? wNear : wFar;
    ctx.globalAlpha = (pass? aNear : aFar)*gA;
    ctx.beginPath();
    for(k=0;k<n;k++){
      a=A[k]; b=B[k];
      if(((LZ[a]+LZ[b])*0.5 > 0.0) === (pass===0)){ ctx.moveTo(LX[a],LY[a]); ctx.lineTo(LX[b],LY[b]); }
    }
    ctx.stroke();
  }
}

/* ================= THỜI GIAN / KHUNG HÌNH ================= */
var t=0, last=0, active=NP, ema=16, frames=0, raf=0, visible=true, running=false;
var SPEED=CFG.speed||1;
function form(tt,d){ return ease(clamp01(((tt-0.2)/2.8 - d*0.5)/0.5)); }

function render(dt){
  t += dt*SPEED;
  var mG = clamp01((t-0.2)/3.0), gA = clamp01((t-0.9)/1.8);

  ctx.globalCompositeOperation="destination-out";
  ctx.globalAlpha=1;
  ctx.fillStyle="rgba(0,0,0,"+(0.20+0.38*mG).toFixed(3)+")";
  ctx.fillRect(0,0,W,H);
  ctx.globalCompositeOperation=CFG.blend;

  var yaw=0.30+1.05*Math.sin(t*0.42); cs=Math.cos(yaw); sn=Math.sin(yaw);
  var pitch=0.26; cp=Math.cos(pitch); sp=Math.sin(pitch);
  bob=0.03*Math.sin(t*1.3);
  var i, k, a, d, m, x, y, z, s2, bk, n;

  /* --- hạt cánh hoa --- */
  var tw=t*3;
  for(i=0;i<active;i++){
    m = mG>=1 ? 1 : form(t, DL[i]);
    if(m>=1){ x=RX[i]; y=RY[i]; z=RZ[i]; }
    else{
      a=SAn[i]+SV[i]*t;
      var sx=SR[i]*Math.cos(a)*1.3, sz=SR[i]*Math.sin(a), sy=SH[i]+0.14*Math.sin(2*a+SP[i]), im=1-m;
      x=RX[i]*m+sx*im; y=RY[i]*m+sy*im; z=RZ[i]*m+sz*im;
    }
    P(x,y,z);
    PX[i]=_x; PY[i]=_y;
    PS[i]=SZ[i]*(0.55+0.7*_k)*(0.85+0.3*Math.sin(tw+SP[i]));
    d=_z<-0.25?2:(_z<0.35?1:0);
    BK[i]=CL[i]*3+d;
  }
  CNT.fill(0);
  for(i=0;i<active;i++) CNT[BK[i]]++;
  var acc=0; for(bk=0;bk<NB;bk++){ OFF[bk]=acc; acc+=CNT[bk]; }
  for(i=0;i<active;i++) ORD[OFF[BK[i]]++]=i;
  var pos=0;
  for(bk=0;bk<NB;bk++){
    n=CNT[bk]; if(!n) continue;
    ctx.globalAlpha=ALPHA[bk%3]; ctx.fillStyle=PAL[(bk/3)|0];
    ctx.beginPath();
    for(k=0;k<n;k++){ i=ORD[pos+k]; s2=PS[i]; ctx.rect(PX[i]-s2*0.5, PY[i]-s2*0.5, s2, s2); }
    ctx.fill();
    if(bk>=6 && HALO){
      ctx.globalAlpha=ALPHA[bk%3]*0.10; ctx.beginPath();
      for(k=0;k<n;k++){ i=ORD[pos+k]; s2=PS[i]*2.4; ctx.rect(PX[i]-s2*0.5, PY[i]-s2*0.5, s2, s2); }
      ctx.fill();
    }
    pos+=n;
  }

  /* --- viền cánh, cuống, lá --- */
  if(gA>0){
    for(i=0;i<NL;i++){ P(LP0[i*3],LP0[i*3+1],LP0[i*3+2]); LX[i]=_x; LY[i]=_y; LZ[i]=_z; }
    ctx.lineCap="round"; ctx.lineJoin="round";
    strokeSegs(1,"#e0457b",0.7,0.12,0.9,0.26,gA);
    strokeSegs(0,"#ffa6c8",0.8,0.18,1.0,0.50,gA);
    strokeSegs(3,"#ffe3ee",0.7,0.30,1.0,0.65,gA);
    strokeSegs(2,"#ffb6d0",3.0,0.08,4.0,0.12,gA);      /* quầng sáng cuống */
    strokeSegs(2,"#ffffff",0.8,0.45,1.2,0.85,gA);
  }

  /* --- vòng tròn trắng xiên + đầu sáng chạy vòng --- */
  if(RN){
    var j, ang, rad, rx, ry2, rz, y1, z1, x2, y3;
    for(j=0;j<=RN;j++){
      ang=j/RN*TWO_PI; rad=1.62+0.05*Math.sin(5*ang+t*3);
      rx=rad*Math.cos(ang); ry2=0.05*Math.sin(3*ang+t*2); rz=rad*Math.sin(ang);
      y1=ry2*cB-rz*sB; z1=ry2*sB+rz*cB;
      x2=rx*cA-y1*sA; y3=rx*sA+y1*cA;
      P(x2, y3-0.05, z1); RQX[j]=_x; RQY[j]=_y; RQZ[j]=_z;
    }
    var ha=mod(t*1.1,TWO_PI), pass2;
    ctx.lineCap="round"; ctx.lineJoin="round"; ctx.strokeStyle="#ffffff";
    for(pass2=0; pass2<2; pass2++){
      ctx.lineWidth = pass2? 1.7 : 1.0; ctx.globalAlpha = pass2? 0.85 : 0.35;
      ctx.beginPath();
      for(j=0;j<RN;j++){
        if(((RQZ[j]+RQZ[j+1])*0.5>0)===(pass2===0)){ ctx.moveTo(RQX[j],RQY[j]); ctx.lineTo(RQX[j+1],RQY[j+1]); }
      }
      ctx.stroke();
    }
    ctx.strokeStyle="#ffffff";
    for(var lvl=0; lvl<2; lvl++){
      ctx.lineWidth = lvl? 3.2 : 2.2; ctx.globalAlpha = lvl? 1.0 : 0.7;
      ctx.beginPath();
      for(j=0;j<RN;j++){
        var dd = 1 - mod(j/RN*TWO_PI - ha, TWO_PI)/TWO_PI;
        if(dd > (lvl?0.90:0.74)){ ctx.moveTo(RQX[j],RQY[j]); ctx.lineTo(RQX[j+1],RQY[j+1]); }
      }
      ctx.stroke();
    }
  }

  /* --- vệt sáng bay ngang --- */
  if(NS){
    var tcz=Math.cos(0.22), tsz=Math.sin(0.22), ph, a2, hx, hy, hz, tx2, ty2, tz2, xs, ys;
    var vis=0.4+0.6*mG;
    for(var cc=0; cc<2; cc++){
      for(var pz=0; pz<2; pz++){
        ctx.lineWidth = pz? 1.4 : 0.9; ctx.strokeStyle = cc? "#ff7cc0" : "#ffffff";
        ctx.globalAlpha = (pz? 0.55 : 0.22)*vis; ctx.beginPath();
        for(var sI=0; sI<NS; sI++){
          if(STR_C[sI]!==cc) continue;
          a=STR_A[sI]+STR_W[sI]*t; a2=a-0.34;
          hx=STR_R[sI]*Math.cos(a); hz=STR_R[sI]*Math.sin(a);
          tx2=STR_R[sI]*Math.cos(a2); tz2=STR_R[sI]*Math.sin(a2);
          y=STR_Y[sI];
          xs=hx*tcz-y*tsz; ys=hx*tsz+y*tcz; P(xs,ys,hz); var hxp=_x, hyp=_y, hzp=_z;
          if((hzp>0)===(pz===0)){
            xs=tx2*tcz-y*tsz; ys=tx2*tsz+y*tcz; P(xs,ys,tz2);
            ctx.moveTo(_x,_y); ctx.lineTo(hxp,hyp);
          }
        }
        ctx.stroke();
      }
    }
  }

  /* --- trái tim --- */
  ctx.globalAlpha=0.9;
  for(var hh=0; hh<HN; hh++){
    a=HA[hh]+t*HV[hh];
    P(HR[hh]*Math.cos(a)*1.25, HY[hh]+0.15*Math.sin(t*1.3+hh), HR[hh]*Math.sin(a));
    s2=HS[hh]*(0.6+0.6*_k)*1.8;
    ctx.drawImage(heartSprite, _x-s2/2, _y-s2/2, s2, s2);
  }
  ctx.globalAlpha=1; ctx.globalCompositeOperation="source-over";
}

/* ================= VÒNG LẶP + TỰ GIẢM TẢI ================= */
function loop(now){
  if(!running) return;
  raf=requestAnimationFrame(loop);
  var dt=(now-last)/1000; last=now;
  if(dt<=0) return;
  if(dt>0.05) dt=0.05;
  ema=ema*0.95+dt*1000*0.05; frames++;
  if(frames%90===0 && ema>22){ if(HALO) HALO=false; else if(active>NP*0.35) active=Math.floor(active*0.8); }
  render(dt);
}
function start(){ if(running||!visible||document.hidden) return; running=true; last=performance.now(); raf=requestAnimationFrame(loop); }
function stop(){ running=false; cancelAnimationFrame(raf); }

resize();
if(window.innerWidth<520) active=Math.floor(NP*0.7);
var reduce=window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if(reduce){ t=6; render(0.0001); }
else{
  if("IntersectionObserver" in window){
    new IntersectionObserver(function(es){ visible=es[0].isIntersecting; if(visible) start(); else stop(); }).observe(canvas);
  }
  document.addEventListener("visibilitychange", function(){ if(document.hidden) stop(); else start(); });
  if("ResizeObserver" in window){ var rt=0; new ResizeObserver(function(){ clearTimeout(rt); rt=setTimeout(resize,120); }).observe(canvas); }
  else{ window.addEventListener("resize", resize); }
  start();
}
window.__roseDebug={ setTime:function(v){ t=v; render(0.0001); }, active:function(){return active;} };
})();
</script></body></html>
"""


def build_html(particles=2800, speed=1.0, show_hearts=True, show_ring=True,
               show_streaks=True, blend="lighter"):
    """Trả về chuỗi HTML của hiệu ứng (không cần Streamlit)."""
    cfg = {
        "count": int(particles),
        "speed": float(speed),
        "hearts": bool(show_hearts),
        "ring": bool(show_ring),
        "streaks": bool(show_streaks),
        "blend": blend,
    }
    return _TEMPLATE.replace("__CFG__", json.dumps(cfg))


def render_rose(height=520, particles=2800, speed=1.0, show_hearts=True,
                show_ring=True, show_streaks=True):
    """Hiển thị bó hoa hồng 3D trong Streamlit.

    height       : chiều cao khung (px), nên 480-600 để thấy cả cuống hoa
    particles    : số hạt cánh hoa (2000-3500 hợp lý; máy yếu dùng 1200)
    speed        : tốc độ animation (1.0 = mặc định)
    show_hearts  : bật/tắt các trái tim bay quanh
    show_ring    : bật/tắt vòng tròn trắng quanh bó hoa
    show_streaks : bật/tắt các vệt sáng bay ngang
    """
    import streamlit.components.v1 as components

    html = build_html(particles, speed, show_hearts, show_ring, show_streaks)
    components.html(html, height=int(height), scrolling=False)


render_bouquet = render_rose  # tên gọi khác, dùng cái nào cũng được


if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(page_title="Bouquet effect", layout="wide")
    st.markdown("<style>.stApp{background:#05030a}</style>", unsafe_allow_html=True)
    render_rose(height=600)
