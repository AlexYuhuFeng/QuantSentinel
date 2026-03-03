"""Research service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class ResearchRun:
    run_id: str
    project_id: str
    folds: list[dict[str, Any]]
    summary: dict[str, Any]


@dataclass
class ResearchProject:
    project_id: str
    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    runs: list[ResearchRun] = field(default_factory=list)


class ResearchService:
    """Project and walk-forward run manager."""

    def __init__(self) -> None:
        self._projects: dict[str, ResearchProject] = {}

    def create_project(self, *, name: str, metadata: dict[str, Any] | None = None) -> ResearchProject:
        if not name.strip():
            raise ValueError("project name is required")

        project = ResearchProject(project_id=str(uuid4()), name=name.strip(), metadata=metadata or {})
        self._projects[project.project_id] = project
        return project

    def list_projects(self) -> list[ResearchProject]:
        return list(self._projects.values())

    def get_runs(self, project_id: str) -> list[ResearchRun]:
        return [*self._require_project(project_id).runs]

    def run_walk_forward(
        self,
        *,
        project_id: str,
        returns: list[float],
        folds: int,
        trading_cost_bps: float,
        slippage_bps: float,
        max_position: float = 1.0,
        max_drawdown_limit: float = 0.2,
    ) -> ResearchRun:
        if folds < 2:
            raise ValueError("walk-forward requires at least 2 folds")
        if not returns:
            raise ValueError("returns cannot be empty")
        if max_position <= 0 or max_position > 1:
            raise ValueError("max_position must be in (0, 1]")

        project = self._require_project(project_id)
        fold_size = max(1, len(returns) // folds)

        net_cost = (trading_cost_bps + slippage_bps) / 10_000
        fold_results: list[dict[str, Any]] = []

        for fold_idx in range(folds):
            start = fold_idx * fold_size
            end = len(returns) if fold_idx == folds - 1 else (fold_idx + 1) * fold_size
            segment = returns[start:end]
            if not segment:
                continue

            adjusted = [self._apply_risk(r - net_cost, max_position=max_position) for r in segment]
            pnl = sum(adjusted)
            max_dd = abs(min(adjusted))
            if max_dd > max_drawdown_limit:
                pnl -= (max_dd - max_drawdown_limit)

            fold_results.append(
                {
                    "fold": fold_idx + 1,
                    "start": start,
                    "end": end,
                    "pnl": round(pnl, 8),
                    "max_drawdown": round(max_dd, 8),
                }
            )

        if len(fold_results) < 2:
            raise ValueError("insufficient data to produce >=2 folds")

        summary = {
            "folds": len(fold_results),
            "avg_pnl": round(sum(item["pnl"] for item in fold_results) / len(fold_results), 8),
            "worst_drawdown": max(item["max_drawdown"] for item in fold_results),
            "trading_cost_bps": trading_cost_bps,
            "slippage_bps": slippage_bps,
            "max_position": max_position,
            "max_drawdown_limit": max_drawdown_limit,
        }

        run = ResearchRun(
            run_id=str(uuid4()),
            project_id=project_id,
            folds=fold_results,
            summary=summary,
        )
        project.runs.append(run)
        return run

    def _apply_risk(self, value: float, *, max_position: float) -> float:
        clipped = max(-max_position, min(max_position, value))
        return clipped

    def _require_project(self, project_id: str) -> ResearchProject:
        if project_id not in self._projects:
            raise ValueError(f"project not found: {project_id}")
        return self._projects[project_id]
