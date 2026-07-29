"""Locale-independent persistence for research artifacts and documentation."""

from __future__ import annotations

import json

from aionq.evidence import EvidenceEnvelope, load_envelope, save_envelope


def _non_ascii_envelope() -> EvidenceEnvelope:
    return EvidenceEnvelope(
        claim_id="TEST-UTF8-GODELIAN",
        evidence_tag="H",
        command="simulate gerbe",
        observed_result={"statement": "Gödelian identity; §-LANG; η_ijk; Ω"},
        typed_remainders=["[R]_coh: η_ijk ≠ 0"],
        witness_notes="non-absorptive recognition of the other — preserved alterity",
    )


def test_load_envelope_reads_literal_utf8_independently_of_platform_locale(tmp_path):
    envelope = _non_ascii_envelope()
    path = tmp_path / "literal-utf8.envelope.json"
    path.write_text(
        json.dumps(envelope.to_dict(), ensure_ascii=False),
        encoding="utf-8",
    )

    restored = load_envelope(path)
    assert restored.observed_result == envelope.observed_result
    assert restored.typed_remainders == envelope.typed_remainders
    assert restored.witness_notes == envelope.witness_notes


def test_save_envelope_round_trips_non_ascii_semantics(tmp_path):
    envelope = _non_ascii_envelope()
    path = save_envelope(envelope, tmp_path / "saved.envelope.json")

    path.read_text(encoding="utf-8")
    restored = load_envelope(path)
    assert restored.observed_result == envelope.observed_result
    assert restored.typed_remainders == envelope.typed_remainders
    assert restored.witness_notes == envelope.witness_notes
