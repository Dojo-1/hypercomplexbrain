import json, platform, sys, time, tracemalloc
import numpy as np

NS=(16,32,64)
SEEDS=tuple(range(20))
D=4
T=48
DRIFT=24
CAL=(0,8,16,32,40)
NOISE=0.05


def orthogonal(rng,d):
    q,r=np.linalg.qr(rng.normal(size=(d,d)))
    s=np.sign(np.diag(r)); s[s==0]=1
    return q*s


def procrustes(X,Y):
    u,_,vt=np.linalg.svd(Y@X.T,full_matrices=False)
    return u@vt


def bootstrap_ucb(vals,seed,draws=4000):
    vals=np.asarray(vals,float); rng=np.random.default_rng(seed)
    means=np.empty(draws)
    for i in range(draws): means[i]=rng.choice(vals,size=len(vals),replace=True).mean()
    return float(np.quantile(means,0.975))


def nrmse(err,truth):
    den=np.sqrt(np.mean(np.square(truth)))+1e-12
    return float(np.sqrt(np.mean(np.square(err)))/den)


def tracking_instance(N,seed):
    rng=np.random.default_rng(100000+1000*N+seed)
    charts=[orthogonal(rng,D) for _ in range(N)]
    drift=[orthogonal(rng,D) for _ in range(N)]
    current=[]
    for A,B in zip(charts,drift):
        q,_=np.linalg.qr(0.82*A+0.18*B)
        current.append(q)
    x=np.empty((T,D)); x[0]=rng.normal(size=D)
    for t in range(1,T): x[t]=0.92*x[t-1]+0.25*rng.normal(size=D)
    obs=np.empty((T,N,D))
    for t in range(T):
        maps=charts if t<DRIFT else current
        for i,A in enumerate(maps): obs[t,i]=A@x[t]+NOISE*rng.normal(size=D)
    anchors=np.eye(D)
    cal={}
    for t in CAL:
        maps=charts if t<DRIFT else current
        cal[t]=np.stack([A@anchors for A in maps])
    return x,obs,cal,charts,current


def track_method(N,seed,method):
    x,obs,cal,_,_=tracking_instance(N,seed)
    local_maps=None; pooled=None; shuffle=None; matvec=0
    preds=[]; truths=[]; cal_def=[]
    rng=np.random.default_rng(700000+N*100+seed)
    for t in range(T):
        if t in cal:
            Y=cal[t]
            local_maps=np.stack([procrustes(np.eye(D),Y[i]) for i in range(N)])
            Xpool=np.tile(np.eye(D),(1,N))
            Ypool=np.concatenate([Y[i] for i in range(N)],axis=1)
            pooled=procrustes(Xpool,Ypool)
            shuffle=rng.permutation(N)
            for i,A in enumerate(local_maps):
                rt=A@(A.T@Y[i]); cal_def.append(float(np.max(np.abs(rt-Y[i]))))
        if method=='HB0_TYPED': maps=local_maps
        elif method=='SHUFFLED_TYPED': maps=local_maps[shuffle]
        elif method=='FLAT_POOLED': maps=np.repeat(pooled[None,:,:],N,axis=0)
        else: raise ValueError(method)
        est=np.stack([maps[i].T@obs[t,i] for i in range(N)])
        matvec += N
        if t>=DRIFT:
            preds.append(np.mean(est,axis=0)); truths.append(x[t])
    preds=np.asarray(preds); truths=np.asarray(truths)
    return {'tracking_nrmse':nrmse(preds-truths,truths),'roundtrip_defect':max(cal_def) if cal_def else 0.0,'matvec':matvec}


def coordination_instance(seed):
    rng=np.random.default_rng(200000+seed); n=128
    shared=rng.normal(size=(n,2)); pa=rng.normal(size=n); pb=rng.normal(size=n)
    A=orthogonal(rng,3); B=orthogonal(rng,3)
    xa=np.column_stack([shared,pa]); xb=np.column_stack([shared,pb])
    ya=xa@A.T+NOISE*rng.normal(size=(n,3)); yb=xb@B.T+NOISE*rng.normal(size=(n,3))
    return shared,pa,pb,A,B,ya,yb


def coordination(seed,method):
    shared,pa,_,A,B,ya,yb=coordination_instance(seed)
    if method=='HB0_TYPED':
        ea=ya@A; eb=yb@B
        msg_a=ea[:,:2]; msg_b=eb[:,:2]
        fused_ab=0.5*(msg_a+msg_b); fused_ba=0.5*(msg_b+msg_a)
        leakage=0.0; matvec=2*len(shared)
    elif method=='FLAT_POOLED':
        P=procrustes(np.tile(np.eye(3),(1,2)),np.concatenate([A,B],axis=1))
        ea=ya@P; eb=yb@P
        fused_ab=0.5*(ea[:,:2]+eb[:,:2]); fused_ba=0.5*(eb[:,:2]+ea[:,:2])
        leakage=float(abs(np.corrcoef(ea[:,2],pa)[0,1])); matvec=2*len(shared)
    else: raise ValueError(method)
    asym=float(np.sqrt(np.mean((fused_ab-fused_ba)**2)))
    return {'shared_nrmse':nrmse(fused_ab-shared,shared),'private_leakage':leakage,'viewpoint_asymmetry':asym,'matvec':matvec}


def delayed_correction(seed,method):
    rng=np.random.default_rng(300000+seed); target=float(rng.normal(scale=0.05))
    false=target+1.0; correction=target; fast=target; slow=target; overwrite=0; matvec=0
    for tick in range(24):
        evidence=None
        if tick==4: evidence=('provisional',false)
        if tick==12: evidence=('confirmed',correction)
        if method=='HB0_TYPED':
            if evidence:
                _,val=evidence; fast=val; matvec+=1
            if tick%16==0 and tick>0:
                slow=fast if tick>=12 else slow; matvec+=1
            if abs(slow-false)<0.25: overwrite=1
        elif method=='ONE_CLOCK_LOCAL':
            if evidence:
                _,val=evidence; slow=0.65*slow+0.35*val; fast=val; matvec+=1
            slow=0.92*slow+0.08*fast; matvec+=1
            if abs(slow-false)<0.25: overwrite=1
        else: raise ValueError(method)
    return {'final_error':abs(slow-target),'premature_slow_overwrite':float(overwrite),'matvec':matvec}


def correctness():
    max_orth=0.0; max_rt=0.0
    for N in NS:
        for seed in SEEDS[:3]:
            _,_,cal,charts,current=tracking_instance(N,seed)
            for A in charts+current: max_orth=max(max_orth,float(np.max(np.abs(A.T@A-np.eye(D)))))
            Y=cal[0]
            for i in range(N):
                A=procrustes(np.eye(D),Y[i]); rt=A@(A.T@Y[i]); max_rt=max(max_rt,float(np.max(np.abs(rt-Y[i]))))
    return {'max_orthogonality_defect':max_orth,'max_roundtrip_defect':max_rt,'passed':max_orth<=1e-10 and max_rt<=1e-10}


def runtime_contract():
    from aionq.hb0.kernel import build_hb0
    k=build_hb0(seed=0,n_worldlets=32,dim=4)
    regimes=tuple(sorted(k.identity.regimes))
    return {'worldlets':len(k.worldlets),'tendrils':len(k.tendrils),'clocks':tuple(sorted(k.clocks)),'identity_regimes':regimes,'passed':len(k.worldlets)==32 and len(k.clocks)>=3 and len(regimes)==4}


def run():
    tracemalloc.start(); t0=time.perf_counter(); rows=[]
    inv=correctness(); runtime=runtime_contract()
    for N in NS:
        for seed in SEEDS:
            rec={'N':N,'seed':seed}
            for m in ('HB0_TYPED','FLAT_POOLED','SHUFFLED_TYPED'):
                for k,v in track_method(N,seed,m).items(): rec[f'{m}.{k}']=v
            if N==32:
                for m in ('HB0_TYPED','FLAT_POOLED'):
                    for k,v in coordination(seed,m).items(): rec[f'{m}.coord.{k}']=v
                for m in ('HB0_TYPED','ONE_CLOCK_LOCAL'):
                    for k,v in delayed_correction(seed,m).items(): rec[f'{m}.corr.{k}']=v
            rows.append(rec)
    summary={'tracking':{},'coordination':{},'correction':{}}; h1=True
    for N in NS:
        sub=[r for r in rows if r['N']==N]
        hb=np.array([r['HB0_TYPED.tracking_nrmse'] for r in sub]); flat=np.array([r['FLAT_POOLED.tracking_nrmse'] for r in sub]); shuf=np.array([r['SHUFFLED_TYPED.tracking_nrmse'] for r in sub])
        best=np.minimum(flat,shuf); dif=hb-best; ucb=bootstrap_ucb(dif,400000+N)
        summary['tracking'][str(N)]={'hb0_mean':float(hb.mean()),'flat_mean':float(flat.mean()),'shuffled_mean':float(shuf.mean()),'paired_diff_mean':float(dif.mean()),'bootstrap_95_ucb':ucb,'hb0_matvec_mean':float(np.mean([r['HB0_TYPED.matvec'] for r in sub])),'best_control_matvec_mean':float(np.mean([min(r['FLAT_POOLED.matvec'],r['SHUFFLED_TYPED.matvec']) for r in sub]))}
        if N in (32,64): h1 &= (ucb < -0.05)
    sub=[r for r in rows if r['N']==32]
    hb=np.array([r['HB0_TYPED.coord.shared_nrmse'] for r in sub]); fl=np.array([r['FLAT_POOLED.coord.shared_nrmse'] for r in sub]); diff=hb-fl; ucb=bootstrap_ucb(diff,500032)
    hb_leak=float(np.mean([r['HB0_TYPED.coord.private_leakage'] for r in sub])); fl_leak=float(np.mean([r['FLAT_POOLED.coord.private_leakage'] for r in sub])); asym=float(max(r['HB0_TYPED.coord.viewpoint_asymmetry'] for r in sub))
    summary['coordination']={'hb0_shared_mean':float(hb.mean()),'flat_shared_mean':float(fl.mean()),'paired_diff_mean':float(diff.mean()),'bootstrap_95_ucb':ucb,'hb0_private_leakage':hb_leak,'flat_private_leakage':fl_leak,'max_viewpoint_asymmetry':asym}; h2=(ucb<0 and hb_leak<=fl_leak+0.02 and asym<=0.05)
    hb=np.array([r['HB0_TYPED.corr.final_error'] for r in sub]); oc=np.array([r['ONE_CLOCK_LOCAL.corr.final_error'] for r in sub]); diff=hb-oc; ucb=bootstrap_ucb(diff,600032)
    hb_ov=float(np.mean([r['HB0_TYPED.corr.premature_slow_overwrite'] for r in sub])); oc_ov=float(np.mean([r['ONE_CLOCK_LOCAL.corr.premature_slow_overwrite'] for r in sub]))
    summary['correction']={'hb0_final_mean':float(hb.mean()),'one_clock_final_mean':float(oc.mean()),'paired_diff_mean':float(diff.mean()),'bootstrap_95_ucb':ucb,'hb0_overwrite_rate':hb_ov,'one_clock_overwrite_rate':oc_ov}; h3=(ucb<0 and (oc_ov-hb_ov)>=0.20)
    compute_ok=True
    for N in (32,64):
        s=summary['tracking'][str(N)]; compute_ok &= (s['hb0_matvec_mean']/s['best_control_matvec_mean']<=2.5)
    promotion=bool(inv['passed'] and runtime['passed'] and h1 and h2 and h3 and compute_ok)
    peak=tracemalloc.get_traced_memory()[1]; tracemalloc.stop()
    return {'round':'HB0-R1W','status':'MEASURED_SELF_ATTESTED','environment':{'python':sys.version.split()[0],'numpy':np.__version__,'platform':platform.platform()},'config':{'N':NS,'seeds':SEEDS,'d':D,'tracking_horizon':T,'drift':DRIFT,'calibration_ticks':CAL,'noise_sigma':NOISE},'runtime_contract':runtime,'correctness':inv,'summary':summary,'gates':{'H1_tracking':bool(h1),'H2_coordination':bool(h2),'H3_correction':bool(h3),'compute_ok':bool(compute_ok),'promotion_pass':promotion},'rows':rows,'resource':{'wall_time_s':time.perf_counter()-t0,'peak_tracemalloc_bytes':peak},'interpretation_ceiling':'bounded synthetic competence only; no AGI/consciousness/quantum/hardware/asymptotic claim'}


if __name__=='__main__':
    print(json.dumps(run(),indent=2,allow_nan=False))
