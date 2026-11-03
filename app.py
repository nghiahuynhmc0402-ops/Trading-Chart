"""
rose_effect.py - Hiệu ứng bông hồng hạt 3D (hồng neon) cho Streamlit.

Mô phỏng lại hiệu ứng trong video: các hạt xoáy thành dải sáng, hội tụ thành
bông hồng 3D xoay chậm, có vòng tròn trắng quanh gốc và các trái tim bay quanh.
Chu kỳ lặp: xoáy -> hội tụ -> bông hồng -> tan ra -> xoáy ...

Cách dùng trong app.py (đặt file này cùng thư mục với app.py):

    from rose_effect import render_rose
    render_rose(height=460)

Chạy thử riêng:  streamlit run rose_effect.py

Thiết kế nhẹ để không giật lag:
  - Vẽ bằng <canvas> 2D, các hạt được gom theo nhóm màu (rất ít lệnh vẽ / khung hình)
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
  background:radial-gradient(ellipse 46% 42% at 50% 56%,rgba(255,40,150,.20),rgba(255,40,150,0) 72%)}
canvas{position:absolute;left:0;top:0;width:100%;height:100%;display:block}
</style></head>
<body><div id="wrap"><canvas id="c"></canvas></div>
<script>
(function(){
"use strict";
var CFG = __CFG__;
var canvas = document.getElementById("c");
var ctx = canvas.getContext("2d");
var W=1, H=1, DPR=1, cx=0, cy=0, S=100, F=3.4;
var TWO_PI = Math.PI*2;

function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);
  t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
var rnd = mulberry32(20261103);
function mod(a,b){return ((a%b)+b)%b;}
function clamp01(x){return x<0?0:(x>1?1:x);}
function ease(x){return x<0.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;}

/* ---------- hạt ---------- */
var NP = Math.max(300, CFG.count|0);
var NR = CFG.ring ? 360 : 0;
var NT = NP + NR;
var RX=new Float32Array(NP), RY=new Float32Array(NP), RZ=new Float32Array(NP);
var SR=new Float32Array(NP), SA=new Float32Array(NP), SV=new Float32Array(NP);
var SH=new Float32Array(NP), SP=new Float32Array(NP), DL=new Float32Array(NP);
var SZ=new Float32Array(NP), CL=new Uint8Array(NP);
var JR=new Float32Array(NR);
var BK=new Uint8Array(NT), PX=new Float32Array(NT), PY=new Float32Array(NT), PS=new Float32Array(NT);
var ORD=new Uint32Array(NT);

/* bông hồng 3D (công thức hoa hồng tham số) */
var perm = []; for (var pi=0; pi<NP; pi++) perm.push(pi);
for (var pj=NP-1; pj>0; pj--){ var pk=Math.floor(rnd()*(pj+1)); var pt=perm[pj]; perm[pj]=perm[pk]; perm[pk]=pt; }
for (var i=0;i<NP;i++){
  var r  = 1 - 0.55*Math.pow(rnd(), 1.8);
  var th = -2 + Math.pow((perm[i]+rnd())/NP, 0.75)*(15*Math.PI+2);
  var phi = (Math.PI/2)*Math.exp(-th/(8*Math.PI));
  var q  = 1 - mod(3.6*th, TWO_PI)/Math.PI;
  var xx = 1 - 0.5*Math.pow(1.25*q*q - 0.25, 2);
  var yy = 1.95653*r*r*Math.pow(1.27689*r - 1, 2)*Math.sin(phi);
  var rr = xx*(r*Math.sin(phi) + yy*Math.cos(phi));
  var X = rr*Math.sin(th), Y = rr*Math.cos(th), Z = xx*(r*Math.cos(phi) - yy*Math.sin(phi));
  RX[i] = X*1.2 + (rnd()-0.5)*0.015;
  RZ[i] = Y*1.2 + (rnd()-0.5)*0.015;
  RY[i] = (Z-0.36)*1.5;
  var tt = clamp01((Z+0.2)/1.15);
  var s  = 0.04 + 0.34*r + 0.26*rnd() + 0.14*(1-tt);
  CL[i]  = Math.min(6, Math.floor(clamp01(s)*7));
  SR[i] = 0.5 + rnd()*1.1;
  SA[i] = rnd()*TWO_PI;
  SV[i] = 0.30 + 0.95*rnd();
  SH[i] = (rnd()-0.5)*1.7;
  SP[i] = rnd()*TWO_PI;
  DL[i] = rnd();
  var z = rnd(); SZ[i] = z<0.55 ? 1.3 : (z<0.86 ? 1.9 : 2.7);
}
for (var j=0;j<NR;j++){ JR[j] = j/NR*TWO_PI; }

/* trái tim */
var HN = CFG.hearts ? 9 : 0;
var HR=[],HA=[],HV=[],HY=[],HS=[];
for (var h=0;h<HN;h++){
  HR.push(1.05+rnd()*1.1); HA.push(rnd()*TWO_PI); HV.push(0.25+rnd()*0.45);
  HY.push(-0.45+rnd()*1.5); HS.push(8+rnd()*7);
}
var heartSprite = (function(){
  var c=document.createElement("canvas"); c.width=48; c.height=48;
  var g=c.getContext("2d"); g.translate(24,24);
  g.shadowColor="rgba(255,60,160,.95)"; g.shadowBlur=10; g.fillStyle="#ff6fba";
  g.beginPath(); g.moveTo(0,12); g.bezierCurveTo(-18,0,-12,-14,0,-5);
  g.bezierCurveTo(12,-14,18,0,0,12); g.fill(); return c;
})();

var PAL = ["#7a0f6b","#b3168a","#e0239f","#ff3fae","#ff7cc6","#ffb3dc","#ffe6f4","#ffffff","#ffffff","#ffffff"];
var ALPHA = [0.30,0.55,0.85];
var NB = 30, HALO = true;
var CNT = new Uint32Array(NB), OFF = new Uint32Array(NB);

/* ---------- thời gian ---------- */
var SW=2.8, CV=2.8, HD=6.6, DS=2.4, T=SW+CV+HD+DS, T0=1.6;
function form(c,d){
  if (c<SW) return 0;
  if (c<SW+CV) return ease(clamp01(((c-SW)/CV - d*0.5)/0.5));
  if (c<SW+CV+HD) return 1;
  return 1 - ease(clamp01(((c-SW-CV-HD)/DS - d*0.5)/0.5));
}

/* ---------- kích thước ---------- */
function resize(){
  DPR = Math.min(window.devicePixelRatio||1, 1.5);
  var b = canvas.getBoundingClientRect();
  W = Math.max(1, Math.floor(b.width)); H = Math.max(1, Math.floor(b.height));
  canvas.width = Math.floor(W*DPR); canvas.height = Math.floor(H*DPR);
  ctx.setTransform(DPR,0,0,DPR,0,0);
  cx = W/2; cy = H*0.55; S = Math.min(W*0.23, H*0.30);
}

/* ---------- khung hình ---------- */
var t=0, last=0, active=NP, ema=16, frames=0, raf=0, visible=true, running=false;
var SPEED = CFG.speed || 1;

function render(dt){
  t += dt*SPEED;
  var c = (t+T0) % T;
  var mG = form(c,0.25);

  ctx.globalCompositeOperation="destination-out";
  ctx.globalAlpha=1;
  ctx.fillStyle="rgba(0,0,0,"+(0.16+0.46*mG).toFixed(3)+")";
  ctx.fillRect(0,0,W,H);
  ctx.globalCompositeOperation=CFG.blend;

  var yaw=t*0.5, cs=Math.cos(yaw), sn=Math.sin(yaw);
  var pitch=0.38, cp=Math.cos(pitch), sp=Math.sin(pitch);
  var pulse = 1 + 0.025*Math.sin(t*1.8);
  var tw = t*3;
  var i, x, y, z, m, a, sr, im, x1, z1, y2, z2, k, d, lv, bk;

  for (i=0;i<active;i++){
    m = form(c, DL[i]);
    if (m>=1){ x=RX[i]*pulse; y=RY[i]*pulse; z=RZ[i]*pulse; }
    else {
      a = SA[i]+SV[i]*t; sr = SR[i];
      var sx = sr*Math.cos(a)*1.4, sz = sr*Math.sin(a), sy = SH[i]+0.14*Math.sin(2*a+SP[i]);
      if (m<=0){ x=sx; y=sy; z=sz; }
      else { im=1-m; x=RX[i]*m+sx*im; y=RY[i]*m+sy*im; z=RZ[i]*m+sz*im; }
    }
    x1 = x*cs + z*sn; z1 = -x*sn + z*cs;
    y2 = y*cp - z1*sp; z2 = y*sp + z1*cp;
    k = F/(F+z2);
    PX[i] = cx + x1*S*k; PY[i] = cy - y2*S*k;
    PS[i] = SZ[i]*(0.55+0.7*k)*(0.85+0.3*Math.sin(tw+SP[i]));
    d = z2 < -0.3 ? 2 : (z2 < 0.5 ? 1 : 0);
    BK[i] = CL[i]*3 + d;
  }

  /* vòng tròn trắng quanh gốc */
  var rv = 0.35 + 0.65*mG, ra = t*0.8, base = NP;
  for (var j=0;j<NR;j++){
    a = JR[j] + ra;
    x = 1.62*Math.cos(a); z = 1.62*Math.sin(a); y = -0.80 + 0.03*Math.sin(a*3+t);
    x1 = x*cs + z*sn; z1 = -x*sn + z*cs;
    y2 = y*cp - z1*sp; z2 = y*sp + z1*cp;
    k = F/(F+z2);
    i = base + j;
    PX[i] = cx + x1*S*k; PY[i] = cy - y2*S*k; PS[i] = 1.3*(0.6+0.6*k);
    lv = (1 - mod(a - ra*2, TWO_PI)/TWO_PI) * rv;          /* đầu sáng, đuôi mờ */
    d = z2 < -0.3 ? 2 : (z2 < 0.5 ? 1 : 0);
    BK[i] = (lv>0.55 ? 9 : (lv>0.28 ? 8 : 7))*3 + d;
  }

  /* gom nhóm theo màu rồi vẽ (ít lệnh vẽ nhất) */
  var total = active + NR, n;
  CNT.fill(0);
  for (i=0;i<active;i++) CNT[BK[i]]++;
  for (i=NP;i<NP+NR;i++) CNT[BK[i]]++;
  var acc=0; for (bk=0;bk<NB;bk++){ OFF[bk]=acc; acc+=CNT[bk]; }
  for (i=0;i<active;i++) ORD[OFF[BK[i]]++]=i;
  for (i=NP;i<NP+NR;i++) ORD[OFF[BK[i]]++]=i;
  var pos=0, s2;
  for (bk=0;bk<NB;bk++){
    n = CNT[bk]; if (!n) continue;
    ctx.globalAlpha = ALPHA[bk%3];
    ctx.fillStyle = PAL[(bk/3)|0];
    ctx.beginPath();
    for (var q2=0;q2<n;q2++){
      i = ORD[pos+q2]; s2 = PS[i];
      ctx.rect(PX[i]-s2*0.5, PY[i]-s2*0.5, s2, s2);
    }
    ctx.fill();
    if (bk >= 9 && HALO){
      ctx.globalAlpha = ALPHA[bk%3]*0.09;
      ctx.beginPath();
      for (var q3=0;q3<n;q3++){
        i = ORD[pos+q3]; s2 = PS[i]*2.5;
        ctx.rect(PX[i]-s2*0.5, PY[i]-s2*0.5, s2, s2);
      }
      ctx.fill();
    }
    pos += n;
  }

  /* trái tim bay quanh */
  ctx.globalAlpha = 0.9;
  for (var hh=0; hh<HN; hh++){
    a = HA[hh] + t*HV[hh];
    x = HR[hh]*Math.cos(a)*1.4; z = HR[hh]*Math.sin(a); y = HY[hh] + 0.15*Math.sin(t*1.3+hh);
    x1 = x*cs + z*sn; z1 = -x*sn + z*cs;
    y2 = y*cp - z1*sp; z2 = y*sp + z1*cp;
    k = F/(F+z2);
    s2 = HS[hh]*(0.6+0.6*k)*2;
    ctx.drawImage(heartSprite, cx + x1*S*k - s2/2, cy - y2*S*k - s2/2, s2, s2);
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
}

/* ---------- vòng lặp + tự giảm tải ---------- */
function loop(now){
  if (!running) return;
  raf = requestAnimationFrame(loop);
  var dt = (now-last)/1000; last = now;
  if (dt<=0) return;
  if (dt>0.05) dt=0.05;
  ema = ema*0.95 + dt*1000*0.05; frames++;
  if (frames%90===0 && ema>22){ if (HALO) HALO=false; else if (active>NP*0.35) active=Math.floor(active*0.8); }
  render(dt);
}
function start(){
  if (running || !visible || document.hidden) return;
  running = true; last = performance.now(); raf = requestAnimationFrame(loop);
}
function stop(){ running=false; cancelAnimationFrame(raf); }

resize();
if (CFG.count && window.innerWidth < 520) active = Math.floor(NP*0.65);

var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
if (reduce){
  t = SW+CV+1.0-T0; render(0.0001);
} else {
  if ("IntersectionObserver" in window){
    new IntersectionObserver(function(es){
      visible = es[0].isIntersecting; if (visible) start(); else stop();
    }).observe(canvas);
  }
  document.addEventListener("visibilitychange", function(){ if (document.hidden) stop(); else start(); });
  if ("ResizeObserver" in window){
    var rt=0; new ResizeObserver(function(){ clearTimeout(rt); rt=setTimeout(resize,120); }).observe(canvas);
  } else { window.addEventListener("resize", resize); }
  start();
}
window.__roseDebug = { setTime:function(v){ t=v; render(0.0001); }, active:function(){return active;} };
})();
</script></body></html>
"""


def build_html(particles=2800, speed=1.0, show_hearts=True, show_ring=True, blend="lighter"):
    """Trả về chuỗi HTML của hiệu ứng (không cần Streamlit)."""
    cfg = {
        "count": int(particles),
        "speed": float(speed),
        "hearts": bool(show_hearts),
        "ring": bool(show_ring),
        "blend": blend,
    }
    return _TEMPLATE.replace("__CFG__", json.dumps(cfg))


def render_rose(height=460, particles=2800, speed=1.0, show_hearts=True, show_ring=True):
    """Hiển thị bông hồng hạt 3D trong Streamlit.

    height      : chiều cao khung (px)
    particles   : số hạt của bông hồng (2000-3500 là hợp lý; máy yếu dùng 1200)
    speed       : tốc độ animation (1.0 = mặc định)
    show_hearts : bật/tắt các trái tim bay quanh
    show_ring   : bật/tắt vòng tròn trắng quanh gốc
    """
    import streamlit.components.v1 as components

    html = build_html(particles, speed, show_hearts, show_ring)
    components.html(html, height=int(height), scrolling=False)


if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(page_title="Rose effect", layout="wide")
    st.markdown("<style>.stApp{background:#05030a}</style>", unsafe_allow_html=True)
    render_rose(height=560)
