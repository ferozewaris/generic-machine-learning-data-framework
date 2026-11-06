import pytest

from gmldf.automl.selection import select_winner
from gmldf.core.config import ConfigError
from gmldf.core.types import CandidateRecord


def record(name, score, status="succeeded"):
    return CandidateRecord(
        trial_id=name, algorithm=name, status=status, parameters={}, validation_score=score
    )


@pytest.mark.parametrize("maximize,expected", [(False, "second"), (True, "third")])
def test_finite_validation_scores_rank_in_declared_direction(maximize, expected):
    trials = [record("first", 0.0), record("second", -3.0), record("third", 10.0)]
    assert select_winner(trials, greater_is_better=maximize).trial_id == expected


def test_equal_scores_keep_first_declared_candidate():
    first = record("first", 2.0)
    assert select_winner([first, record("second", 2.0)], greater_is_better=False) is first


def test_failed_skipped_missing_and_nonfinite_scores_cannot_win():
    winner = record("valid", 4.0)
    trials = [
        record("failed", 0.0, "failed"),
        record("skipped", 1.0, "skipped"),
        record("missing", None),
        winner,
    ]
    for value in [float("nan"), float("inf"), float("-inf")]:
        trials.append(
            CandidateRecord.model_construct(
                trial_id="invalid",
                algorithm="invalid",
                status="succeeded",
                parameters={},
                validation_score=value,
            )
        )
    assert select_winner(trials, greater_is_better=False) is winner


def test_no_completed_finite_candidate_has_no_winner():
    assert select_winner([], greater_is_better=False) is None
    assert select_winner([record("failed", None, "failed")], greater_is_better=False) is None


@pytest.mark.parametrize("direction", [None, 1, 0, "min"])
def test_metric_direction_cannot_be_silently_coerced(direction):
    with pytest.raises(ConfigError):
        select_winner([], greater_is_better=direction)
