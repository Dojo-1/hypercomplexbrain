"""Locale-independent persistence for research artifacts and documentation."""

from __future__ import annotations

from aionq.evidence import EvidenceEnvelope, load_envelope, save_envelope


def test_evidence_envelope_round_trips_non_ascii_as_utf8(tmp_path):
    envelope = EvidenceEnvelope(
        claim_id="TEST-UTF8-GODELIAN",
        evidence_tag="H",
        command="simulate gerbe",
        observed_result={"statement": "Gödelian identity; §-LANG; η_ijk; Ω"},
        typed_remainders=["[R]_coh: η_ijk ≠ 0"],
        witness_notes="non-absorptive recognition of the other — preserved alterity",
    )

    path = save_envelope(envelope, tmp_path / "evidence.envelope.json")
    raw = path.read_bytes()

    assert "Gödelian".encode("utf-8") in raw
    restored = load_envelope(path)
    assert restored.observed_result == envelope.observed_result
    assert restored.typed_remainders == envelope.typed_remainders
    assert restored.witness_notes == envelope.witness_notes
