import json, math, os, platform, sys, time, tracemalloc
import numpy as np

DS=(2,3,4,5,7)
NS=(8,16,32)
SEEDS=tuple(range(8))
Q=0.125
K=2
R=32


def bootstrap_lcb(values, seed=20260809, draws=4000):
    vals=np.asarray(values,float)
    rng=np.random.default_rng(seed)
    means=np.empty(draws)
    for i in range(draws):
        means[i]=rng.choice(vals,size=len(vals),replace=True).mean()
    return float(np.quantile(means,0.025))


def generalized_weyl_features(x,d):
    phase=2*np.pi*x/d
    return np.column_stack([np.cos(phase), np.sin(phase)])


def plant_instance(d,N,seed):
    rng=np.random.default_rng(100000*d+1000*N+seed)
    x=rng.integers(0,d,size=N)
    m=max(2,int(round(Q*N)))
    candidates=np.arange(0,N-1,2)
    if m>len(candidates):
        m=len(candidates)
    targets=np.sort(rng.choice(candidates,size=m,replace=False))
    secret=int(rng.integers(1,d)) if d>1 else 0
    for idx in targets:
        x[idx+1]=(x[idx]+secret)%d
    return x,targets,secret


def saliencies(x,d,secret,seed):
    N=len(x)
    F=generalized_weyl_features(x,d)
    z=F[:,0]+1j*F[:,1]
    shifted=np.roll(z,-1)
    omega=np.exp(2j*np.pi*secret/d)
    algebra=np.round(1.0-np.abs(shifted-omega*z)/2.0, 12)
    scalar=np.sum(F*F,axis=1)
    rng=np.random.default_rng(200000+d*1000+seed)
    A=rng.normal(size=(2,2)); q,_=np.linalg.qr(A)
    proj=F@q
    random_orth=np.abs(proj[:,0])
    alignment=((np.roll(x,-1)-x)%d==secret).astype(float)
    random=rng.random(N)
    return {"algebra":algebra,"scalar":scalar,"random_orth":random_orth,"alignment":alignment,"random":random}


def select(scores,m):
    return np.argsort(-scores,kind='stable')[:m]


def metrics(sel,targets,N):
    s=set(map(int,sel)); t=set(map(int,targets)); tp=len(s&t)
    recall=tp/len(t); precision=tp/len(s) if s else 0.; false=(len(s-t)/len(s)) if s else 0.
    return recall,precision,false


def frame_spread(x,d,secret,targets,seed):
    m=len(targets)
    recalls=[]
    for c in [0,1%d]:
        xc=(x+c)%d
        sc=saliencies(xc,d,secret,seed)["algebra"]
        recalls.append(metrics(select(sc,m),targets,len(x))[0])
    xr=(-x)%d; sr=(-secret)%d
    sc=saliencies(xr,d,sr,seed)["algebra"]
    recalls.append(metrics(select(sc,m),targets,len(x))[0])
    return float(max(recalls)-min(recalls))


def run():
    rows=[]
    tracemalloc.start()
    t0=time.perf_counter()
    for d in DS:
      for N in NS:
       for seed in SEEDS:
        x,targets,secret=plant_instance(d,N,seed); m=len(targets)
        start=time.perf_counter(); ss=saliencies(x,d,secret,seed)
        elapsed=time.perf_counter()-start
        row={"d":d,"N":N,"k":K,"r":min(R,2*N),"B":"matched-local-O(N)","seed":seed,"selected_fraction":m/N,"observer_time_s":elapsed}
        for name,s in ss.items():
            rec,pre,fh=metrics(select(s,m),targets,N)
            row[name+"_recall"]=rec; row[name+"_precision"]=pre; row[name+"_false_hotspot"]=fh
        row["frame_orbit_spread"]=frame_spread(x,d,secret,targets,seed)
        rows.append(row)
    peak=tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    summary={}
    promotion_ds=[]
    for d in DS:
        sub=[r for r in rows if r['d']==d]
        deltas=[]
        for r in sub:
            controls=max(r['random_recall'],r['scalar_recall'],r['random_orth_recall'],r['alignment_recall'])
            deltas.append(r['algebra_recall']-controls)
        mean=float(np.mean(deltas)); lcb=bootstrap_lcb(deltas,seed=300000+d)
        fs=max(r['frame_orbit_spread'] for r in sub)
        summary[str(d)]={"mean_delta_recall_at_budget":mean,"bootstrap_95_lcb":lcb,"max_frame_orbit_spread":fs,"n":len(sub),"mean_algebra_recall":float(np.mean([r['algebra_recall'] for r in sub])),"mean_alignment_recall":float(np.mean([r['alignment_recall'] for r in sub]))}
        if lcb>0.05 and fs<=1e-12: promotion_ds.append(d)
    promoted=len(promotion_ds)>=2 and any(d>3 for d in promotion_ds)
    result={
      "round":"QSigma-R1U",
      "status":"MEASURED_SELF_ATTESTED",
      "environment":{"python":sys.version.split()[0],"numpy":np.__version__,"platform":platform.platform()},
      "config":{"d":DS,"N":NS,"seeds":SEEDS,"k":K,"r_cap":R,"q_nominal":Q},
      "rows":rows,
      "summary":summary,
      "promotion_ds":promotion_ds,
      "promotion_pass":promoted,
      "kill_reason":None if promoted else "algebra-aware observer failed preregistered delta_recall gate against alignment-only/matched controls",
      "peak_tracemalloc_bytes":peak,
      "wall_time_s":time.perf_counter()-t0,
      "interpretation_ceiling":"finite synthetic local modular-relation localization only; no quantum/cognitive/asymptotic claim"
    }
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__=='__main__': run()
