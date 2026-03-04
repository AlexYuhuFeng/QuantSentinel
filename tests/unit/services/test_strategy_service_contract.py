from quantsentinel.services.lab_contracts import LabResultView
from quantsentinel.services.strategy_service import StrategyService


def test_strategy_service_lab_contract() -> None:
    service = StrategyService()

    families = service.available_families()
    assert families

    defaults = service.default_params(family=families[0])
    result = service.run(family=families[0], params=defaults)

    recent = service.get_recent_results(limit=5)

    assert result.family == families[0]
    assert isinstance(recent, list)
    assert isinstance(recent[0], LabResultView)
    assert recent[0].family == families[0]
    assert isinstance(recent[0].metrics_json, dict)
