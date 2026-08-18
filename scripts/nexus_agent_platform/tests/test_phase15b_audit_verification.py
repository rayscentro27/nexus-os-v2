from __future__ import annotations


def test_phase15b_audit_integrity_and_unverified_free_server_boundary():
    from phase15b_audit.verify_audit import verify

    result = verify()
    assert result["status"] == "PASS"
    assert result["placement_integrity"] == "PASS"
    assert result["score_integrity"] == "PASS"
    assert result["hardware_placement_verification"].startswith("PARTIAL")
    assert result["free_server_verification"].startswith("UNVERIFIED")
    assert result["installation_performed"] is False
    assert result["provider_mutation_performed"] is False
