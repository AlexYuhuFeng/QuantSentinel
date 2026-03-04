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
        report(30, f"loading {ticker} data")
        report(65, f"running {family} backtest")
        report(90, f"window={start_date}..{end_date}")

    TaskLifecycle(task_id).run(
        worker=_worker,
        success_detail=f"backtest completed: {ticker}/{family}",
    )


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
        report(20, f"prepare grid for {family}")
        report(60, f"evaluate {grid_size} combinations")
        report(90, f"window={start_date}..{end_date} ticker={ticker}")

    TaskLifecycle(task_id).run(
        worker=_worker,
        success_detail=f"parameter search completed: {ticker}/{family}, combos={grid_size}",
    )
