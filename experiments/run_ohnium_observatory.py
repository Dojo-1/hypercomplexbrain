#!/usr/bin/env python3
"""Build the Ohnium V2 R40 evidence artifact and live atlas.

Run from the repository root:

    PYTHONPATH=src python experiments/run_ohnium_observatory.py

The HTML is a screen projection of the full vector telemetry stored in the JSON;
the JSON remains the evidence surface.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from aionq.evidence import (  # noqa: E402
    EvidenceEnvelope,
    current_commit,
    environment_digest,
    file_digest,
    save_envelope,
)
from aionq.ohnium_observability import (  # noqa: E402
    CARRIER_ORDER,
    FRAMES,
    atlas_payload,
    build_ohnium_atlas,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "ohnium_v2"
JSON_OUT = OUT / "ohnium_atlas.json"
HTML_OUT = OUT / "ohnium_atlas.html"
ENVELOPE_OUT = OUT / "ohnium_atlas.envelope.json"
PREREG = ROOT / "manifests" / "ohnium_v2_observability_preregistration.json"
SOURCE = ROOT / "src" / "aionq" / "ohnium_observability.py"
TEST = ROOT / "tests" / "test_ohnium_observability.py"
FORMAL = ROOT / "formal" / "OhniumObservatory.lean"
RUNNER = Path(__file__).resolve()
COMMAND = "PYTHONPATH=src python experiments/run_ohnium_observatory.py"


def _html(payload: dict) -> str:
    embedded = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OHM · Ohnium R40 Observatory</title>
<style>
:root{--ink:#d9f8ff;--muted:#7194a4;--line:#16394b;--cyan:#40f5e2;
--violet:#a67cff;--gold:#ffc857;--red:#ff5277;--bg:#03080d;--panel:#07131d}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 50% 0,#102132 0,#03080d 48%);
color:var(--ink);font:13px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;min-height:100vh}
header{display:flex;gap:22px;align-items:center;padding:18px 24px;border-bottom:1px solid var(--line);
background:#03090fcc;backdrop-filter:blur(10px);position:sticky;top:0;z-index:4}
h1{font-size:16px;letter-spacing:.18em;margin:0;color:var(--cyan)} .sub{color:var(--muted)}
.badge{border:1px solid #275469;border-radius:999px;padding:5px 10px}
main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px;padding:14px;max-width:1800px;margin:auto}
.stage,.panel{border:1px solid var(--line);border-radius:14px;background:#05101acc;box-shadow:0 20px 80px #0008}
.stage{position:relative;min-height:720px;overflow:hidden}.panel{padding:14px}
canvas{width:100%;height:720px;display:block}.controls{position:absolute;left:18px;right:18px;bottom:15px;
display:grid;grid-template-columns:auto 1fr auto auto;gap:12px;align-items:center;padding:11px 14px;
border:1px solid #1a4658;background:#030b12e8;border-radius:12px}
button,select{background:#071b27;color:var(--ink);border:1px solid #245367;border-radius:8px;padding:7px 10px}
input[type=range]{width:100%;accent-color:var(--cyan)}
.metric{display:grid;grid-template-columns:1fr auto;gap:7px;border-bottom:1px solid #102b39;padding:7px 0}
.value{color:var(--cyan)} .fail{color:var(--red)} .ok{color:#71ff9c}
.carrier{display:grid;grid-template-columns:54px 1fr 52px;gap:8px;align-items:center;margin:8px 0}
.bar{height:7px;border-radius:9px;background:#10242f;overflow:hidden}.bar i{display:block;height:100%;
background:linear-gradient(90deg,var(--violet),var(--cyan));border-radius:9px}
h2{font-size:12px;letter-spacing:.16em;color:var(--gold);margin:16px 0 8px}
.vector{height:80px;display:flex;align-items:flex-end;gap:2px;border:1px solid #102b39;padding:6px;border-radius:8px}
.vector i{flex:1;min-width:2px;background:var(--violet);opacity:.8}
.note{font-size:11px;color:var(--muted);margin-top:12px}.phase{font-size:34px;color:var(--gold);line-height:1}
@media(max-width:980px){main{grid-template-columns:1fr}.stage{min-height:570px}canvas{height:570px}}
</style>
</head>
<body>
<header><h1>OHM · OHNIUM R40</h1><span class="sub">observable ascent under motion</span>
<span class="badge">R → H → O → CD32 → A<sub>n</sub></span>
<span class="badge">A / U / M typed cadence</span></header>
<main>
<section class="stage"><canvas id="cosmos"></canvas>
<div class="controls"><button id="play">PLAY</button><input id="frame" type="range" min="0" max="39" value="0">
<select id="endpoint"></select><span id="frameLabel">R40 · 00</span></div></section>
<aside class="panel">
<div style="display:flex;justify-content:space-between"><div><div class="sub">ACTIVE PHASE</div>
<div class="phase" id="phase">A</div></div><div style="text-align:right"><div class="sub">DOMINANT CARRIER</div>
<h1 id="dominant">R</h1></div></div>
<h2>PROOF PRESSURE</h2><div id="pressure"></div>
<h2>CARRIER ENERGY</h2><div id="energies"></div>
<h2>PROJECTION VIOLENCE · LANDING VECTOR</h2><div class="vector" id="vector"></div>
<div class="note" id="landing"></div>
<h2>WEAVE / DEWEAVE</h2><div id="weave" class="note"></div>
<div class="note">The screen is a Poincaré/ring projection. The embedded JSON retains every carrier
vector, bridge ledger, discarded coordinate, typed remainder, and return defect. A/U/M names do not
assert a spiritual or physical quantum effect.</div>
</aside></main>
<script id="atlas-data" type="application/json">""" + embedded + """</script>
<script>
const D=JSON.parse(document.getElementById("atlas-data").textContent);
const canvas=document.getElementById("cosmos"),ctx=canvas.getContext("2d");
const slider=document.getElementById("frame"),selector=document.getElementById("endpoint");
let frame=0,endpoint=0,timer=null;
D.endpoints.forEach((e,i)=>{const o=document.createElement("option");o.value=i;o.textContent=e.id;selector.appendChild(o)});
function resize(){const r=canvas.getBoundingClientRect(),d=devicePixelRatio||1;canvas.width=r.width*d;canvas.height=r.height*d;ctx.setTransform(d,0,0,d,0,0);draw()}
function line(x1,y1,x2,y2,color,w=1,a=.45){ctx.globalAlpha=a;ctx.strokeStyle=color;ctx.lineWidth=w;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();ctx.globalAlpha=1}
function dot(x,y,r,color,a=1){ctx.globalAlpha=a;ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1}
function draw(){
 const w=canvas.clientWidth,h=canvas.clientHeight,f=D.endpoints[endpoint].frames[frame],cx=w*.52,cy=h*.43;
 ctx.clearRect(0,0,w,h);const grad=ctx.createRadialGradient(cx,cy,0,cx,cy,Math.max(w,h)*.65);
 grad.addColorStop(0,"#102d3c");grad.addColorStop(.45,"#06131e");grad.addColorStop(1,"#02070b");ctx.fillStyle=grad;ctx.fillRect(0,0,w,h);
 // Split light cone.
 line(cx,cy,cx-w*.42,cy+h*.34,"#3bd7ff",1.2,.26);line(cx,cy,cx+w*.42,cy+h*.34,"#3bd7ff",1.2,.26);
 line(cx,cy,cx-w*.42,cy-h*.34,"#ff5b8d",1.2,.18);line(cx,cy,cx+w*.42,cy-h*.34,"#ff5b8d",1.2,.18);
 // Carrier rings: screen projection of five heterogeneous carriers.
 const colors=["#40f5e2","#74a9ff","#a67cff","#ffc857","#ff5277"];
 f.carriers.forEach((c,i)=>{const r=64+i*43;ctx.strokeStyle=colors[i];ctx.globalAlpha=.17+.08*(f.dominant_carrier===c.carrier);
 ctx.lineWidth=f.dominant_carrier===c.carrier?3:1;ctx.beginPath();ctx.ellipse(cx,cy,r,r*.46,frame*.018+i*.17,0,Math.PI*2);ctx.stroke();ctx.globalAlpha=1;
 const a=frame*.15+i*1.21;dot(cx+Math.cos(a)*r,cy+Math.sin(a)*r*.46,3+(f.dominant_carrier===c.carrier?3:0),colors[i],.9)});
 // Fano braid as a heptagram, colored by algebra-valued rank gate.
 const fr=100,fy=cy-210,pts=[];for(let i=0;i<7;i++){const a=-Math.PI/2+i*Math.PI*2/7;pts.push([cx+Math.cos(a)*fr,fy+Math.sin(a)*fr])}
 for(let i=0;i<7;i++){const j=(i+3)%7;line(...pts[i],...pts[j],f.proof_pressure.fano_joint_rank===28?"#9f7cff":"#ff5277",1.2,.48)}
 pts.forEach(p=>dot(p[0],p[1],4,"#d5c8ff"));
 // Poincare disk point and swirl.
 const dp=f.proof_pressure.disk_point,dx=cx+w*.32,dy=cy-h*.23,dr=85;ctx.strokeStyle="#28536a";ctx.beginPath();ctx.arc(dx,dy,dr,0,Math.PI*2);ctx.stroke();
 for(let k=0;k<48;k++){const a=k*.38+frame*.06,r=dr*(k/48);dot(dx+Math.cos(a)*r,dy+Math.sin(a)*r,1.2,"#40f5e2",.32)}
 dot(dx+dp[0]*dr,dy+dp[1]*dr,6,"#ffc857");
 // Other local worlds: each endpoint remains its own fiber.
 D.endpoints.forEach((e,i)=>{const a=i*Math.PI*2/D.endpoints.length+frame*.012,rr=Math.min(w,h)*.37;
 const x=cx+Math.cos(a)*rr,y=cy+Math.sin(a)*rr*.57;dot(x,y,i===endpoint?9:5,i===endpoint?"#40f5e2":"#56788a",.9);line(cx,cy,x,y,"#2c6076",1,.25)});
 updatePanel(f);
}
function row(name,value,ok=true){return `<div class="metric"><span>${name}</span><span class="${ok?"value":"fail"}">${value}</span></div>`}
function updatePanel(f){
 document.getElementById("phase").textContent=f.phase;document.getElementById("dominant").textContent=f.dominant_carrier;
 document.getElementById("frameLabel").textContent=`R40 · ${String(frame).padStart(2,"0")}`;
 const p=f.proof_pressure,ok=p.failures.length===0;document.getElementById("pressure").innerHTML=
 row("status",ok?"COHERENT":p.failures.join(" · "),ok)+row("Fano ranks",`${p.fano_signal_rank}/${p.fano_crosstalk_rank}/${p.fano_joint_rank}`,p.fano_joint_rank===28)+
 row("light-cone defect",p.light_cone_defect.toExponential(2),p.light_cone_defect<1e-10)+
 row("swirl defect",p.swirl_defect.toExponential(2),p.swirl_defect<1e-10)+
 row("ring defect",p.carrier_ring_defect.toExponential(2),p.carrier_ring_defect<1e-10);
 document.getElementById("energies").innerHTML=f.carriers.map(c=>`<div class="carrier"><span>${c.carrier}</span><span class="bar"><i style="width:${Math.min(100,c.energy*100)}%"></i></span><span>${c.energy.toFixed(3)}</span></div>`).join("");
 const b=f.bridges[f.bridges.length-1],v=b.projection_violence.discarded_vector,max=Math.max(...v.map(Math.abs),1e-12);
 document.getElementById("vector").innerHTML=v.map(x=>`<i style="height:${Math.max(2,Math.abs(x)/max*68)}px;background:${x<0?"#ff5277":"#a67cff"}"></i>`).join("");
 document.getElementById("landing").textContent=`${b.projection_violence.landing_carrier} · rank loss ${b.projection_violence.rank_loss} · energy loss ${b.projection_violence.energy_loss.toFixed(6)} · return defect ${b.return_path.reconstruction_defect.toExponential(2)}`;
 document.getElementById("weave").textContent=`${f.weave.action.toUpperCase()} · ${f.weave.reason}`;
}
function setFrame(n){frame=(n+40)%40;slider.value=frame;draw()}
slider.oninput=()=>setFrame(+slider.value);selector.onchange=()=>{endpoint=+selector.value;draw()};
document.getElementById("play").onclick=(ev)=>{if(timer){clearInterval(timer);timer=null;ev.target.textContent="PLAY"}else{timer=setInterval(()=>setFrame(frame+1),220);ev.target.textContent="PAUSE"}};
addEventListener("resize",resize);resize();
</script></body></html>"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    atlas = build_ohnium_atlas()
    payload = atlas_payload(atlas)

    baseline_frames = [
        frame for endpoint in atlas.endpoints for frame in endpoint.frames
    ]
    checks = {
        "three_endpoint_fibers": len(atlas.endpoints) == 3,
        "r40_complete": (
            len(baseline_frames) == 3 * FRAMES
            and all(
                tuple(frame.index for frame in endpoint.frames)
                == tuple(range(FRAMES))
                for endpoint in atlas.endpoints
            )
        ),
        "carrier_order_complete": all(
            tuple(item.carrier for item in frame.carrier_trace) == CARRIER_ORDER
            for frame in baseline_frames
        ),
        "baseline_coherent": all(
            frame.proof_pressure.coherent for frame in baseline_frames
        ),
        "returns_close": all(
            bridge.return_path.closes_with_sidecar
            for frame in baseline_frames
            for bridge in frame.bridges
        ),
        "faults_caught": all(probe.caught for probe in atlas.fault_probes),
        "eight_quality_vector": (
            len(atlas.governance.qualities) == 8
            and atlas.governance.promotion_forbidden
        ),
        "full_vectors_retained": all(
            len(frame.bridges[-1].violence.discarded_vector) == 32
            for frame in baseline_frames
        ),
    }
    payload["checks"] = checks
    payload["verdict"] = (
        "ALL REGISTERED OHNIUM GATES HOLD"
        if all(checks.values())
        else "OHNIUM GATE FAILURE"
    )
    JSON_OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    HTML_OUT.write_text(_html(payload), encoding="utf-8")

    envelope = EvidenceEnvelope(
        claim_id="ARCH-OHM-V2_OBSERVABLE_ASCENT",
        evidence_tag="M",
        command=COMMAND,
        observed_result={
            "endpoint_fibers": len(atlas.endpoints),
            "frames": len(baseline_frames),
            "carrier_observations": sum(
                len(frame.carrier_trace) for frame in baseline_frames
            ),
            "bridge_ledgers": sum(
                len(frame.bridges) for frame in baseline_frames
            ),
            "faults_caught": {
                probe.fault: probe.caught for probe in atlas.fault_probes
            },
            "hamiltonian_energy": atlas.governance.total_energy,
            "verdict": payload["verdict"],
        },
        commit_sha=current_commit(ROOT),
        working_directory=".",
        environment=environment_digest(),
        input_hashes=[
            file_digest(path)
            for path in (PREREG, SOURCE, TEST, FORMAL, RUNNER)
        ],
        seeds=[20260728],
        raw_artifacts={
            "artifacts/ohnium_v2/ohnium_atlas.json": file_digest(JSON_OUT),
        },
        producer="experiments/run_ohnium_observatory.py",
        verifier="",
        verification_mode="not_requested",
        typed_remainders=[
            {
                "kind": "empirical_residual",
                "carrier": "CD32 orthogonal complement of A_n",
                "comparison": (
                    "the full discarded vector is stored in the JSON; its "
                    "squared norm is secondary telemetry"
                ),
            },
            {
                "kind": "semantic_remainder",
                "carrier": "A/U/M naming",
                "comparison": (
                    "phonetic source acknowledged; no spiritual or physical "
                    "quantum effect inferred"
                ),
            },
            {
                "kind": "scope_remainder",
                "carrier": "evidence lattice",
                "comparison": (
                    "same-repository deterministic evidence; not independent "
                    "verification or quantum-hardware evidence"
                ),
            },
        ],
    )
    save_envelope(envelope, ENVELOPE_OUT)
    print(
        json.dumps(
            {
                "verdict": payload["verdict"],
                "checks": checks,
                "json": str(JSON_OUT),
                "html": str(HTML_OUT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
