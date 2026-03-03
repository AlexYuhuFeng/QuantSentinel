import pytest

from quantsentinel.services.research_service import ResearchService


def test_research_service_project_and_walk_forward() -> None:
    service = ResearchService()
    project = service.create_project(name="trend-lab")

    run = service.run_walk_forward(
        project_id=project.project_id,
        returns=[0.05, -0.02, 0.03, 0.01, -0.04, 0.02],
        folds=3,
        trading_cost_bps=5,
        slippage_bps=2,
        max_position=0.5,
        max_drawdown_limit=0.15,
    )

    assert run.project_id == project.project_id
    assert run.summary["folds"] >= 2
    assert len(service.get_runs(project.project_id)) == 1


def test_research_service_requires_min_folds() -> None:
    service = ResearchService()
    project = service.create_project(name="wf")

    with pytest.raises(ValueError):
        service.run_walk_forward(
            project_id=project.project_id,
            returns=[0.1, 0.2],
            folds=1,
            trading_cost_bps=1,
            slippage_bps=1,
        )
