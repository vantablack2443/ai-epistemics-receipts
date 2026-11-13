from pathlib import Path


def test_demo_explicitly_identifies_missing_results():
    text = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert "no final study or measured results" in text
    assert "No final-study annotations" in text
    assert "subprocess" not in text
