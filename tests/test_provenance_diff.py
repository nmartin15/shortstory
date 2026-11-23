"""Provenance logging and human-edit diff tests."""

from src.shortstory.provenance import ProvenanceLog, percent_changed


def test_percent_changed_identical():
    report = percent_changed("hello world", "hello world")
    assert report.identical
    assert report.percent_changed == 0.0


def test_percent_changed_total_rewrite():
    report = percent_changed("aaaa bbbb cccc dddd", "xxxx yyyy zzzz wwww")
    assert report.percent_changed > 50


def test_provenance_roundtrip(tmp_path):
    log = ProvenanceLog(tmp_path / "provenance.jsonl")
    log.append(
        stage="premise",
        model="mock/x",
        temperature=0.7,
        system="sys",
        prompt="prompt",
        output="model output text",
        prompt_tokens=10,
        completion_tokens=20,
        cost_usd=0.001,
    )
    assert log.latest_output_for_stage("premise") == "model output text"
    assert len(log.read_all()) == 1
