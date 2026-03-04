from quantsentinel.services.lab_contracts import LabResultView
from quantsentinel.services.research_service import ResearchService


def test_research_service_lab_contract() -> None:
    service = ResearchService()

    families = service.available_families()
    assert families

    defaults = service.default_params(family=families[0])
    project = service.create_project(name="research-lab")
    service.run_walk_forward(
        project_id=project.project_id,
        returns=[0.05, -0.01, 0.03, 0.01, -0.02, 0.02],
        folds=int(defaults["folds"]),
        trading_cost_bps=float(defaults["trading_cost_bps"]),
        slippage_bps=float(defaults["slippage_bps"]),
        max_position=float(defaults["max_position"]),
        max_drawdown_limit=float(defaults["max_drawdown_limit"]),
    )

    recent = service.get_recent_results(limit=5)

    assert isinstance(recent, list)
    assert isinstance(recent[0], LabResultView)
    assert recent[0].family == "walk_forward"
    assert "stability" in recent[0].metrics_json
