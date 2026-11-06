"""Stable selection over completed finite validation scores only."""

import math
from collections.abc import Iterable

from gmldf.core.config import ConfigError
from gmldf.core.types import CandidateRecord


def select_winner(
    candidates: Iterable[CandidateRecord], *, greater_is_better: bool
) -> CandidateRecord | None:
    if type(greater_is_better) is not bool:
        raise ConfigError("ml.evaluation.greater_is_better", "boolean_required")
    winner = None
    for candidate in candidates:
        score = candidate.validation_score
        if candidate.status != "succeeded" or score is None or not math.isfinite(score):
            continue
        if winner is None or (
            score > winner.validation_score
            if greater_is_better
            else score < winner.validation_score
        ):
            winner = candidate
    return winner
