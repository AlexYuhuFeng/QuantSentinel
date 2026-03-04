"""Parameter search samplers and early stopping rules."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import fmean, pstdev
from typing import Any, Literal


@dataclass(frozen=True)
class SearchDimension:
    """A single parameter dimension definition for search."""

    kind: Literal["int", "float", "categorical"]
    low: float | int | None = None
    high: float | int | None = None
    step: float | int | None = None
    choices: tuple[Any, ...] = ()


class ParameterSampler:
    def sample(self, *, n_candidates: int) -> list[dict[str, Any]]:
        raise NotImplementedError


class GridSampler(ParameterSampler):
    def __init__(self, *, space: dict[str, SearchDimension]) -> None:
        self._space = dict(space)

    def sample(self, *, n_candidates: int) -> list[dict[str, Any]]:
        if n_candidates <= 0:
            return []
        keys = list(self._space.keys())
        values = [self._grid_values(self._space[key]) for key in keys]
        candidates: list[dict[str, Any]] = []
        indexes = [0] * len(keys)
        while len(candidates) < n_candidates:
            candidate = {keys[i]: values[i][indexes[i]] for i in range(len(keys))}
            candidates.append(candidate)
            if not keys:
                break
            carry = len(keys) - 1
            while carry >= 0:
                indexes[carry] += 1
                if indexes[carry] < len(values[carry]):
                    break
                indexes[carry] = 0
                carry -= 1
            if carry < 0:
                break
        return candidates

    def _grid_values(self, dim: SearchDimension) -> list[Any]:
        if dim.kind == "categorical":
            return list(dim.choices)
        low = dim.low
        high = dim.high
        step = dim.step
        if low is None or high is None or step is None:
            raise ValueError("numeric dimension requires low/high/step")
        values: list[Any] = []
        cursor = low
        while cursor <= high:
            values.append(int(cursor) if dim.kind == "int" else float(cursor))
            cursor = cursor + step
        if values[-1] != high:
            values.append(int(high) if dim.kind == "int" else float(high))
        return values


class RandomSampler(ParameterSampler):
    def __init__(self, *, space: dict[str, SearchDimension], seed: int | None = None) -> None:
        self._space = dict(space)
        self._rng = random.Random(seed)

    def sample(self, *, n_candidates: int) -> list[dict[str, Any]]:
        return [self._sample_one() for _ in range(max(0, n_candidates))]

    def _sample_one(self) -> dict[str, Any]:
        candidate: dict[str, Any] = {}
        for name, dim in self._space.items():
            if dim.kind == "categorical":
                candidate[name] = self._rng.choice(dim.choices)
            elif dim.kind == "int":
                assert dim.low is not None and dim.high is not None
                candidate[name] = self._rng.randint(int(dim.low), int(dim.high))
            else:
                assert dim.low is not None and dim.high is not None
                candidate[name] = self._rng.uniform(float(dim.low), float(dim.high))
        return candidate


class BayesianSampler(ParameterSampler):
    """Simplified Bayesian/TPE-like sampler using top-k guided proposals."""

    def __init__(self, *, space: dict[str, SearchDimension], seed: int | None = None) -> None:
        self._space = dict(space)
        self._rng = random.Random(seed)
        self._observations: list[tuple[dict[str, Any], float]] = []

    def observe(self, *, params: dict[str, Any], score: float) -> None:
        self._observations.append((dict(params), float(score)))

    def sample(self, *, n_candidates: int) -> list[dict[str, Any]]:
        return [self._sample_one() for _ in range(max(0, n_candidates))]

    def _sample_one(self) -> dict[str, Any]:
        if len(self._observations) < 5:
            return RandomSampler(space=self._space, seed=self._rng.randint(1, 10**9)).sample(n_candidates=1)[0]

        sorted_obs = sorted(self._observations, key=lambda item: item[1], reverse=True)
        top = [params for params, _score in sorted_obs[: max(2, len(sorted_obs) // 3)]]
        out: dict[str, Any] = {}
        for name, dim in self._space.items():
            if dim.kind == "categorical":
                choices = [params[name] for params in top if name in params]
                out[name] = self._rng.choice(choices or list(dim.choices))
                continue

            values = [float(params[name]) for params in top if name in params]
            center = fmean(values) if values else float(dim.low or 0.0)
            spread = pstdev(values) if len(values) > 1 else max(1.0, abs(center) * 0.15)
            proposal = self._rng.gauss(center, max(1e-6, spread))
            assert dim.low is not None and dim.high is not None
            bounded = min(float(dim.high), max(float(dim.low), proposal))
            out[name] = int(round(bounded)) if dim.kind == "int" else float(bounded)
        return out


@dataclass(frozen=True)
class EarlyStoppingRule:
    max_no_improve_rounds: int = 5
    min_delta: float = 1e-6
    confidence_z: float = 1.96

    def should_stop(self, *, scores: list[float]) -> bool:
        if len(scores) <= self.max_no_improve_rounds:
            return False
        best = -math.inf
        stale = 0
        for score in scores:
            if score > best + self.min_delta:
                best = score
                stale = 0
            else:
                stale += 1
                if stale >= self.max_no_improve_rounds:
                    return True

        if len(scores) < 6:
            return False
        mean = fmean(scores)
        sigma = pstdev(scores)
        if sigma <= 0:
            return False
        half_width = self.confidence_z * sigma / math.sqrt(len(scores))
        return (mean + half_width) < best
