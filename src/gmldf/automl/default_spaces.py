"""Offline, versioned finite domains for explicitly listed candidate profiles."""

import copy
import math
from itertools import product

from pydantic import ValidationError

from gmldf.automl.candidates.arima import ArimaParams
from gmldf.core.config import ConfigError, MLSpec, Spec, validate_ml_intent
from gmldf.core.errors import FrameworkError
from gmldf.core.types import SearchDomain

_DEFAULTS = {
    "naive.last": {},
    "statsmodels.arima": {
        "order": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 1]],
        "trend": ["n"],
        "enforce_stationarity": [True],
        "enforce_invertibility": [True],
        "maxiter": [100],
    },
}
_PARAMETER_MODELS = {"naive.last": Spec, "statsmodels.arima": ArimaParams}


def resolve_search(spec: MLSpec) -> list[SearchDomain]:
    try:
        spec = MLSpec.model_validate(spec.model_dump())
    except ValidationError as cause:
        raise ConfigError("ml", "invalid_ml_spec") from cause
    validate_ml_intent(spec)
    if spec.task != "forecasting":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="ml.task")
    if spec.evaluation.metric != "mae":
        raise FrameworkError("CAPABILITY_UNSUPPORTED", path="ml.evaluation.metric")
    if spec.evaluation.greater_is_better not in {None, False}:
        raise ConfigError("ml.evaluation.greater_is_better", "mae_must_be_minimized")
    resolved = []
    for index, algorithm in enumerate(spec.algorithms):
        path = f"ml.algorithms.{index}"
        if algorithm.name not in _DEFAULTS:
            raise FrameworkError("CAPABILITY_UNSUPPORTED", path=f"{path}.name")
        domain = copy.deepcopy(_DEFAULTS[algorithm.name])
        overrides = algorithm.search_space or {}
        if (set(algorithm.parameters) | set(overrides)) - set(domain):
            raise ConfigError(path, "unknown_parameter")
        if set(algorithm.parameters) & set(overrides):
            raise ConfigError(path, "fixed_parameter_cannot_also_be_searched")
        domain.update(copy.deepcopy(overrides))
        domain.update({key: [copy.deepcopy(value)] for key, value in algorithm.parameters.items()})
        for key, values in domain.items():
            if not isinstance(values, list) or not 1 <= len(values) <= 128:
                raise ConfigError(f"{path}.search_space.{key}", "finite_choice_list_required")
            if any(value in values[:offset] for offset, value in enumerate(values)):
                raise ConfigError(f"{path}.search_space.{key}", "duplicate_choices")
        if math.prod(len(values) for values in domain.values()) > 4096:
            raise ConfigError(f"{path}.search_space", "domain_product_exceeds_4096")
        for values in product(*domain.values()):
            try:
                _PARAMETER_MODELS[algorithm.name].model_validate(
                    dict(zip(domain, values, strict=True))
                )
            except ValidationError as cause:
                raise ConfigError(path, "invalid_candidate_domain") from cause
        resolved.append(
            SearchDomain(
                algorithm=algorithm.name, defaults_version=f"{algorithm.name}.v1", domain=domain
            )
        )
    return resolved
