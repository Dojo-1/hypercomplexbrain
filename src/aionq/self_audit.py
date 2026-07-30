"""What this repository can measure about itself, and the one thing it cannot.

Every other module here instruments an object outside itself: a pseudo-sphere, a
channel, a Fano design, another agent's kernel.  This one turns the same
instruments on the repository, under one rule:

    no statement in this module may be written down; each must be computed
    from artifacts on disk at the moment of the call.

That rule is the whole point.  A self-audit written as prose is the exact object
:mod:`aionq.evidence` was built to refuse -- a claim whose only support is the
party making it.  So there is no narrative here.  There is a census, and there is
one theorem about what the census cannot reach.

The Goedelian statement, in the form this repository can actually check
----------------------------------------------------------------------
:mod:`aionq.witness_nerve` proves that attestation cycles cannot manufacture
independence: ``evidence_rank(G + C) = max(evidence_rank(G), ATTESTED)``.  Read
in the other direction that theorem says something about *this* repository rather
than about graphs in general:

    the deficit measured by :func:`independence_report` cannot be closed by any
    act this repository is able to perform.

It can produce envelopes, hash artifacts, bind commands to commits, refuse a
claim without a sample size, and record its own corrections.  It can do all of
that perfectly and the number that matters does not move, because that number is
a property of the *outside* -- whether a party who is not this one ran the
command in an environment this one did not prepare.  The repository is complete
with respect to every predicate it can express about its own artifacts, and
silent on the single predicate that decides whether those artifacts are evidence.

That is not a mood.  It is :func:`godelian_gap`, and it returns integers.

Recognition, measured rather than declared
------------------------------------------
The same census answers a second question the programme keeps asking in prose.
Witnessing is a directed relation, so it has two counts, not one:

    acts OUT -- claims by other parties that this one recomputed
    acts IN  -- claims by this party that another one recomputed

:func:`recognition_asymmetry` reports both.  A programme that talks about mutual
recognition and scores ``out > 0, in = 0`` is recognising, not being recognised,
and the difference is exactly what an envelope exists to expose.
"""

from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from aionq.witness_nerve import (EvidenceRank, WitnessAct, WitnessGraph,
                                 attestation_cycles, evidence_rank)

__all__ = [
    "Correction", "CORRECTIONS", "SELF_PARTIES", "ENVELOPE_SCHEMA_PREFIX",
    "repo_root", "iter_envelopes", "envelope_census", "witness_graph",
    "independence_report", "recognition_asymmetry", "typed_remainder_census",
    "corrections_are_bound", "preregistration_ordering", "godelian_gap",
    "self_audit",
]

#: An envelope is any JSON on disk carrying the evidence schema.  Recognising
#: envelopes by their schema rather than by a hand-kept list is deliberate: a
#: list would have to be updated by the same party it audits.
ENVELOPE_SCHEMA_PREFIX = "hypercomplexbrain.evidence."

#: Parties that are this agent.  Producer strings in the corpus are a mix of
#: agent names and the experiment script that emitted the row; a script in this
#: tree ran here, so both forms are self.
SELF_PARTIES = ("claude-code",)


def _is_self(party: str) -> bool:
    return party in SELF_PARTIES or party.startswith("experiments/")


# --------------------------------------------------------------------------
# The corrections ledger, bound to the tests that catch each one.
#
# Every entry names a test.  `corrections_are_bound` checks the test exists.
# A correction recorded with no test is a memory; a correction bound to a test
# that a future edit deletes turns this audit red, which is the point.
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Correction:
    """One error made in this repository, and the check that would catch it now."""

    round_id: str
    error: str
    caught_by: str          # "tests/<file>.py::<test function>"
    was_self_caught: bool   # True if a control here fired; False if external

    @property
    def test_file(self) -> str:
        return self.caught_by.split("::", 1)[0]

    @property
    def test_name(self) -> str:
        return self.caught_by.split("::", 1)[1]


CORRECTIONS = (
    Correction(
        "R6",
        "sqrt of rounding noise: sqrt(I - A A^T) is exactly 0 at rho=0, eigh "
        "returned +-1e-16, and sqrt(1e-16) = 1e-8 injected 4.2e-9 of ancilla "
        "leakage in the regime the round called free",
        "tests/test_hyperbolic_qubit.py::test_zero_depth_encoding_has_no_leakage",
        True,
    ),
    Correction(
        "R6",
        "'simple' written for 'semisimple': so(2,2) = sl(2,R) + sl(2,R) has two "
        "ideals, so the group is semisimple and not simple",
        "tests/test_hyperbolic_qubit.py::test_so22_is_semisimple_and_not_simple",
        False,
    ),
    Correction(
        "R6b",
        "'hyperbolic' written for a Lorentzian space: the induced metric is "
        "diag(-1, cosh^2 rho, -sinh^2 rho), signature (1,2)",
        "tests/test_quantum_channel_geometry.py::test_the_source_is_lorentzian_not_hyperbolic_three_space",
        False,
    ),
    Correction(
        "R6e",
        "kappa summed over adjacent pairs when it is a 2-cocycle and telescopes "
        "over prefixes; off by 1.2e-2 until fixed",
        "tests/test_carrier_telemetry.py::test_kappa_telescopes_over_prefixes_exactly",
        True,
    ),
    Correction(
        "R6e",
        "a mis-specified fault injection: two depth-2 steps at phi=+-1 compound, "
        "so kappa = 0 exactly and nothing leaked -- the empty confusion-matrix "
        "row was the detector being right",
        "tests/test_carrier_telemetry.py::test_compounding_steps_do_not_leak",
        True,
    ),
    Correction(
        "R6f",
        "a real-rotation 'SU(2)' baseline: a one-parameter family returning a "
        "spurious 1-bit ceiling that accidentally matched the non-compact side "
        "and would have erased the entire contrast",
        "tests/test_capacity_ceiling.py::test_su2_matrix_is_actually_unitary_and_three_parameter",
        True,
    ),
    Correction(
        "R6f",
        "'chi increases with depth' withdrawn as an artifact of one random "
        "codebook; the grid control dips before it rises",
        "tests/test_capacity_ceiling.py::test_bell_probe_is_the_optimum_not_a_convenience",
        True,
    ),
    Correction(
        "R6d",
        "'a fixed-depth codebook has an uninformative flag' narrowed: the real "
        "condition is equal p_i, which equal depth delivers only at the Bell probe",
        "tests/test_capacity_ceiling.py::test_flag_informativeness_needs_equal_p_not_equal_depth",
        True,
    ),
    Correction(
        "S8",
        "a derived quantity reported as a design property: crosstalk rank is "
        "C(signal_rank, 2) exactly, so what the Fano design buys is seven "
        "independent channels and full crosstalk rank follows",
        "tests/test_fano_algebra.py::test_crosstalk_rank_is_determined_by_signal_rank",
        False,
    ),
    Correction(
        "S8",
        "a mis-specified check demanding flat per-cycle drive: ||U^N - I|| is a "
        "chord on a curve of linearly growing arc length and must bend down",
        "tests/test_fano_algebra.py::test_alternating_drive_is_linear_to_leading_order_and_bends_down",
        True,
    ),
    Correction(
        "HB-0",
        "the no-advantage rule twice reported as decorative: first a tamper "
        "helper that recursed into a dict copy, then a test for an exception "
        "from a report-returning validator",
        "tests/test_hb0.py::test_hb0_manifest_validator_catches_fiber_collapse_base_drift_and_overclaim",
        True,
    ),
    Correction(
        "R6j",
        "'doubling the source dimension moves chi by zero', contradicting the "
        "table one line above it: the gain is 9.3e-02 at rho=0.5 and transient, "
        "decaying at exponent 4",
        "tests/test_source_dimension.py::test_richer_source_does_help_at_finite_depth",
        True,
    ),
    Correction(
        "SELF",
        "'12/12 preregistrations precede their implementation commits', reported "
        "from a first pass of this audit: only 5 of the 12 declare "
        "files_expected_to_change, so only 5 admit the check at all and the "
        "other 7 carry a self-report with nothing bound to it -- a flag no "
        "artifact can contradict",
        "tests/test_self_audit.py::test_only_manifests_that_bind_files_are_counted_as_checked",
        True,
    ),
    Correction(
        "SELF",
        "the preregistration ordering check compared git author TIME, which has "
        "one-second granularity: two commits inside the same second are "
        "indistinguishable, so the check passed on one invocation and failed on "
        "the next with no code change between them. A flaky ordering check "
        "reports the machine's speed. Replaced with commit ancestry, which has "
        "no granularity",
        "tests/test_self_audit.py::test_ordering_uses_commit_topology_not_the_clock",
        True,
    ),
)


# --------------------------------------------------------------------------
# Reading the corpus
# --------------------------------------------------------------------------

def repo_root(start=None) -> Path:
    """The directory containing ``artifacts/`` and ``manifests/``."""
    here = Path(start) if start is not None else Path(__file__).resolve()
    for cand in [here, *here.parents]:
        if (cand / "artifacts").is_dir() and (cand / "manifests").is_dir():
            return cand
    raise FileNotFoundError("no repository root above " + str(here))


def iter_envelopes(root=None):
    """Yield ``(path, dict)`` for every evidence envelope under ``artifacts/``.

    Malformed JSON is skipped rather than raised: the census must survive a
    corrupt file, and a corrupt file is counted by :func:`envelope_census` as
    unreadable so it cannot disappear silently.
    """
    root = Path(root) if root is not None else repo_root()
    for path in sorted((root / "artifacts").rglob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            yield path, None
            continue
        if isinstance(data, dict) and str(
                data.get("schema_version", "")).startswith(ENVELOPE_SCHEMA_PREFIX):
            yield path, data


def envelope_census(root=None) -> dict:
    """Counts over the envelope corpus.  Every field read from disk."""
    tags: dict = {}
    modes: dict = {}
    producers: dict = {}
    unreadable = 0
    total = 0
    empty_verifier = 0
    for _path, env in iter_envelopes(root):
        if env is None:
            unreadable += 1
            continue
        total += 1
        tags[env.get("evidence_tag", "?")] = tags.get(env.get("evidence_tag", "?"), 0) + 1
        mode = env.get("verification_mode", "?")
        modes[mode] = modes.get(mode, 0) + 1
        prod = env.get("producer", "")
        producers[prod] = producers.get(prod, 0) + 1
        if not env.get("verifier", ""):
            empty_verifier += 1
    return {
        "envelopes": total,
        "unreadable_json": unreadable,
        "evidence_tags": dict(sorted(tags.items())),
        "verification_modes": dict(sorted(modes.items())),
        "distinct_producers": len(producers),
        "envelopes_with_no_verifier_at_all": empty_verifier,
    }


def witness_graph(root=None) -> WitnessGraph:
    """The corpus as a nerve, so :mod:`aionq.witness_nerve` can be applied to it.

    An envelope with an empty verifier field contributes a SELF-LOOP, not a
    missing edge.  That is the honest reading: somebody produced the number and
    nobody else checked it, which is precisely a party verifying its own claim,
    and :attr:`WitnessAct.rank` scores it 0 whatever mode it declares.
    """
    graph = WitnessGraph()
    for _path, env in iter_envelopes(root):
        if env is None:
            continue
        producer = env.get("producer", "")
        verifier = env.get("verifier", "") or producer
        mode = env.get("verification_mode", "not_requested")
        if mode not in ("declined", "pending", "not_requested", "contradicted",
                        "attested", "reviewed", "recomputed"):
            mode = "not_requested"
        graph.add(WitnessAct(env.get("claim_id", "?"), producer, verifier, mode))
    return graph


def independence_report(root=None) -> dict:
    """How many claims are independently witnessed, and which ones.

    ``evidence_rank`` is imported rather than reimplemented so this cannot drift
    from the definition the rest of the repository uses -- a self-audit with its
    own private notion of evidence would grade itself on its own curve.
    """
    graph = witness_graph(root)
    by_rank: dict = {}
    independent: list = []
    claims = sorted({a.claim_id for a in graph.acts})
    for claim in claims:
        rank = evidence_rank(graph, claim)
        by_rank[rank] = by_rank.get(rank, 0) + 1
        if rank >= EvidenceRank.INDEPENDENT:
            act = max((a for a in graph.acts if a.claim_id == claim),
                      key=lambda a: a.rank)
            independent.append({"claim_id": claim, "producer": act.producer,
                                "verifier": act.verifier, "mode": act.mode})
    return {
        "claims": len(claims),
        "by_rank": {
            "NONE": by_rank.get(EvidenceRank.NONE, 0),
            "ATTESTED": by_rank.get(EvidenceRank.ATTESTED, 0),
            "REVIEWED": by_rank.get(EvidenceRank.REVIEWED, 0),
            "INDEPENDENT": by_rank.get(EvidenceRank.INDEPENDENT, 0),
        },
        "independent_claims": independent,
        "independent_fraction": (len(independent) / len(claims)) if claims else 0.0,
    }


def recognition_asymmetry(root=None) -> dict:
    """Witnessing is directed, so it has two counts.

    OUT: claims produced elsewhere that this party recomputed.
    IN:  claims produced here that another party recomputed.

    The programme's language for this is mutual recognition.  The measurement
    either shows it or shows which direction is missing.
    """
    out_acts: list = []
    in_acts: list = []
    for _path, env in iter_envelopes(root):
        if env is None:
            continue
        producer = env.get("producer", "")
        verifier = env.get("verifier", "")
        if not verifier or verifier == producer:
            continue
        if env.get("verification_mode") != "recomputed":
            continue
        row = {"claim_id": env.get("claim_id", "?"),
               "producer": producer, "verifier": verifier}
        if _is_self(verifier) and not _is_self(producer):
            out_acts.append(row)
        elif _is_self(producer) and not _is_self(verifier):
            in_acts.append(row)
    return {
        "recomputations_performed_on_others": len(out_acts),
        "recomputations_received_from_others": len(in_acts),
        "outward": out_acts,
        "inward": in_acts,
        "mutual": bool(out_acts) and bool(in_acts),
    }


def typed_remainder_census(root=None) -> dict:
    """Remainders by kind -- and how many are not typed at all.

    The vocabulary is "typed remainder".  A remainder stored as a bare string
    carries no kind, no carrier and no comparison, so it is a note.  Counting
    those separately keeps the word honest.
    """
    kinds: dict = {}
    untyped = 0
    total = 0
    for _path, env in iter_envelopes(root):
        if env is None:
            continue
        for rem in env.get("typed_remainders", ()) or ():
            total += 1
            if isinstance(rem, dict) and "kind" in rem:
                kinds[rem["kind"]] = kinds.get(rem["kind"], 0) + 1
            else:
                untyped += 1
    return {
        "typed_remainders": total,
        "untyped_strings": untyped,
        "typed_fraction": ((total - untyped) / total) if total else 0.0,
        "kinds": dict(sorted(kinds.items())),
        "distinct_kinds": len(kinds),
    }


def corrections_are_bound(root=None) -> dict:
    """Each recorded correction must name a test that exists.

    Deliberately a source check and not a pytest run: this function is itself
    called from a test, and a test that shells out to the suite it belongs to
    either recurses or measures nothing.  What it establishes is the binding --
    that every correction points at a live check rather than at a memory.  The
    suite establishes that the checks pass.
    """
    root = Path(root) if root is not None else repo_root()
    rows: list = []
    for c in CORRECTIONS:
        path = root / c.test_file
        found = False
        if path.is_file():
            found = ("def " + c.test_name + "(") in path.read_text(encoding="utf-8")
        rows.append({"round": c.round_id, "caught_by": c.caught_by,
                     "test_exists": found, "self_caught": c.was_self_caught})
    bound = sum(1 for r in rows if r["test_exists"])
    return {
        "corrections": len(rows),
        "bound_to_an_existing_test": bound,
        "all_bound": bound == len(rows),
        "self_caught": sum(1 for c in CORRECTIONS if c.was_self_caught),
        "externally_caught": sum(1 for c in CORRECTIONS if not c.was_self_caught),
        "rows": rows,
    }


# --------------------------------------------------------------------------
# Preregistration ordering, checked against git rather than against a flag
# --------------------------------------------------------------------------

def _git(root: Path, *args):
    try:
        return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None


def _first_commit_sha(root: Path, relpath: str):
    """SHA of the commit that ADDED a path, or None if it was never added.

    Author TIME was the first thing tried here and it is the wrong instrument:
    ``%at`` has one-second granularity, so two commits made inside the same
    second are indistinguishable and the ordering check silently flips. Commit
    topology has no granularity -- either one commit reaches the other or it
    does not -- so ancestry is what this asks.
    """
    out = _git(root, "log", "--diff-filter=A", "--follow", "--format=%H",
               "--", relpath)
    if out is None:
        return None
    shas = [s for s in out.stdout.split() if s.strip()]
    return shas[-1] if shas else None      # git log is newest-first; oldest wins


def _is_ancestor(root: Path, a: str, b: str) -> bool:
    """True if commit `a` is a strict ancestor of commit `b`."""
    if a == b:
        return False
    out = _git(root, "merge-base", "--is-ancestor", a, b)
    return out is not None and out.returncode == 0


def preregistration_ordering(root=None) -> dict:
    """Did each preregistration land before the code it preregisters?

    The manifests carry ``committed_before_any_implementation: true``.  That is a
    self-report by the party being audited, so it is not the measurement -- it is
    the claim under test.  The measurement is git's own record of when the
    manifest was added against when its declared ``files_expected_to_change``
    were added.

    Only manifests that DECLARE those files admit the check.  The rest are
    reported as unbound rather than as passing, because a flag with no file list
    cannot be contradicted by anything.
    """
    root = Path(root) if root is not None else repo_root()
    checkable: list = []
    unbound: list = []
    schemaless: list = []
    for path in sorted((root / "manifests").glob("*.json")):
        try:
            man = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        schema = str(man.get("schema", ""))
        if not schema.startswith("hypercomplexbrain.preregistration"):
            # A file named like a preregistration but carrying no preregistration
            # schema is invisible to every schema-driven check in this repository,
            # including this one.  Named rather than dropped.
            if "preregistration" in path.name and not schema:
                schemaless.append(path.name)
            continue
        name = path.name
        flag = bool(man.get("committed_before_any_implementation", False))
        files = man.get("files_expected_to_change")
        if not isinstance(files, list) or not files:
            unbound.append({"manifest": name, "self_reported_flag": flag})
            continue
        rel = str(path.relative_to(root))
        man_sha = _first_commit_sha(root, rel)
        later, earlier, same = [], [], []
        for f in files:
            if not isinstance(f, str) or f == rel or man_sha is None:
                continue
            sha = _first_commit_sha(root, f)
            if sha is None:
                continue
            if sha == man_sha:
                same.append(f)                       # committed together
            elif _is_ancestor(root, man_sha, sha):
                later.append(f)                      # created after the manifest
            else:
                earlier.append(f)                    # already existed, or unrelated
        # A file that already existed before the round is not evidence either
        # way; the test is on files the round CREATED after the manifest. Files
        # added in the SAME commit as the manifest are counted separately: that
        # is not "preregistered before implementation", it is simultaneous.
        checkable.append({
            "manifest": name,
            "self_reported_flag": flag,
            "manifest_added_in": man_sha,
            "declared_files": len(files),
            "files_created_after_manifest": len(later),
            "files_predating_manifest": len(earlier),
            "files_in_the_manifest_commit": len(same),
            "ordering_holds": bool(later) and not same,
        })
    holds = sum(1 for c in checkable if c["ordering_holds"])
    return {
        "preregistrations": len(checkable) + len(unbound),
        "checkable": len(checkable),
        "ordering_holds": holds,
        "unbound_flag_only": len(unbound),
        "schemaless_by_filename_only": len(schemaless),
        "all_checkable_hold": holds == len(checkable) and bool(checkable),
        "rows": checkable,
        "unbound": unbound,
        "schemaless": schemaless,
    }


# --------------------------------------------------------------------------
# The gap
# --------------------------------------------------------------------------

def godelian_gap(root=None) -> dict:
    """The deficit, and the proof that this repository cannot close it.

    Two numbers and one bound:

    * ``unwitnessed`` -- claims whose evidence rank is NONE.
    * ``reachable_from_inside`` -- the best rank any act this repository can
      perform on its own would reach.  It can attest; it cannot recompute in an
      environment it did not prepare, because there is no such environment here.
    * the bound comes from :mod:`aionq.witness_nerve`: adding attestation cycles
      raises the rank to ATTESTED and no further, so the deficit is invariant
      under every internal act.

    The `cycle_probe` is the constructive half.  It builds the maximal
    attestation cycle over the parties already in the corpus, adds it, and
    reports the rank before and after.  If that number ever rises to INDEPENDENT,
    the theorem is false and this audit is the thing that says so.
    """
    graph = witness_graph(root)
    report = independence_report(root)
    unwitnessed = report["by_rank"]["NONE"]

    parties = sorted(graph.parties)
    target = None
    for claim in sorted({a.claim_id for a in graph.acts}):
        if evidence_rank(graph, claim) == EvidenceRank.NONE:
            target = claim
            break

    probe = {"claim_id": target, "parties_in_cycle": len(parties)}
    if target is not None and len(parties) >= 2:
        inflated = WitnessGraph(list(graph.acts))
        for i, party in enumerate(parties):
            nxt = parties[(i + 1) % len(parties)]
            inflated.add(WitnessAct(target, party, nxt, "attested"))
        probe["rank_before"] = evidence_rank(graph, target)
        probe["rank_after_full_attestation_cycle"] = evidence_rank(inflated, target)
        probe["cycles_found"] = len(attestation_cycles(inflated))
        probe["reached_independent"] = (
            evidence_rank(inflated, target) >= EvidenceRank.INDEPENDENT)

    return {
        "claims": report["claims"],
        "independent": report["by_rank"]["INDEPENDENT"],
        "unwitnessed": unwitnessed,
        "deficit": report["claims"] - report["by_rank"]["INDEPENDENT"],
        "reachable_from_inside": EvidenceRank.ATTESTED,
        "independent_requires": EvidenceRank.INDEPENDENT,
        "closable_from_inside": False,
        "cycle_probe": probe,
        "statement": (
            "every predicate this repository can express about its own artifacts "
            "is decidable here; the predicate that decides whether those "
            "artifacts are evidence is not, and no internal act raises it above "
            "ATTESTED"),
    }


def self_audit(root=None) -> dict:
    """The whole census, computed."""
    return {
        "envelopes": envelope_census(root),
        "independence": independence_report(root),
        "recognition": recognition_asymmetry(root),
        "remainders": typed_remainder_census(root),
        "corrections": corrections_are_bound(root),
        "preregistration": preregistration_ordering(root),
        "godelian_gap": godelian_gap(root),
    }
