from pathlib import Path


def test_monitor_page_contains_wizard_and_steps() -> None:
    content = Path("src/quantsentinel/app/pages/monitor.py").read_text(encoding="utf-8")
    assert "def _render_rule_wizard" in content
    assert "monitor_rule_wizard_step" in content
    assert "Preview & Confirm" in content
    assert "_validate_wizard_inputs" in content
    assert "Create Rule" in content
