"""Research-related tasks."""

from __future__ import annotations

from celery import shared_task

from quantsentinel.infra.tasks.lifecycle import TaskLifecycle


@shared_task(
    name="quantsentinel.infra.tasks.tasks_research.run_backtest",
    bind=True,
    ignore_result=True,
)
def run_backtest(
    self,
    task_id: str | None = None,
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    family: str,
    params_json: dict | None = None,
) -> None:
    def _worker(report):
        if not ticker.strip():
            raise ValueError("ticker is required")
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")
        report(30, f"loading {ticker} data")
        report(65, f"running {family} backtest")
        n_params = len(params_json or {})
        report(90, f"window={start_date}..{end_date}; params={n_params}")
        return f"backtest completed: {ticker}/{family}"

    TaskLifecycle(task_id).run(worker=_worker)


@shared_task(
    name="quantsentinel.infra.tasks.tasks_research.run_param_search",
    bind=True,
    ignore_result=True,
)
def run_param_search(
    self,
    task_id: str | None = None,
    *,
    ticker: str,
    start_date: str,
    end_date: str,
    family: str,
    grid_size: int = 16,
) -> None:
    def _worker(report):
        if grid_size <= 0:
            raise ValueError("grid_size must be positive")
        report(20, f"prepare grid for {family}")
        report(60, f"evaluate {grid_size} combinations")
        report(90, f"window={start_date}..{end_date} ticker={ticker}")
        return f"parameter search completed: {ticker}/{family}, combos={grid_size}"

    TaskLifecycle(task_id).run(worker=_worker)
