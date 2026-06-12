"""
config/loader.py — YAML filter configuration loader.

Loads and validates filter_config.yaml, returning a FilterConfig
dataclass with the two sets used by filter_ai_relevant().

The loader is intentionally decoupled from the filter logic so that
both can be tested independently.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Default config location relative to the project root
DEFAULT_CONFIG_PATH = Path(__file__).parent / "filter_config.yaml"


@dataclass(frozen=True)
class FilterConfig:
    """
    Holds the two sets that drive the AI-relevance filter.

    Attributes
    ----------
    ai_relevant_categories : frozenset[str]
        Canonical article categories that qualify as AI/ML-relevant
        (matched against the ``category`` column after cleaning).
    ai_relevant_industries : frozenset[str]
        Company industry strings that qualify as AI/ML-relevant
        (matched against ``meta_industry`` from company_metadata.json).
    """

    ai_relevant_categories: frozenset = field(default_factory=frozenset)
    ai_relevant_industries: frozenset = field(default_factory=frozenset)


def load_filter_config(path: Path | None = None) -> FilterConfig:
    """
    Load and parse a filter configuration YAML file.

    Falls back to ``config/filter_config.yaml`` when *path* is ``None``.

    Expected YAML structure::

        ai_relevant_categories:
          - AI_ML
          - Data_Analytics

        ai_relevant_industries:
          - AI/ML
          - Data Analytics

    Parameters
    ----------
    path : Path or None
        Path to the YAML config file.  Defaults to
        ``config/filter_config.yaml`` relative to this module.

    Returns
    -------
    FilterConfig
        Parsed config with ``ai_relevant_categories`` and
        ``ai_relevant_industries`` as frozensets.

    Raises
    ------
    FileNotFoundError
        If the specified config file does not exist.
    ValueError
        If required keys are missing or values are not lists.
    """
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(
            f"Filter config not found: '{config_path}'. "
            f"Expected a YAML file with 'ai_relevant_categories' and "
            f"'ai_relevant_industries' keys."
        )

    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(
            f"Filter config '{config_path}' must be a YAML mapping at the top level."
        )

    # Validate and extract each key
    categories = _extract_list(raw, "ai_relevant_categories", config_path)
    industries  = _extract_list(raw, "ai_relevant_industries",  config_path)

    config = FilterConfig(
        ai_relevant_categories=frozenset(categories),
        ai_relevant_industries=frozenset(industries),
    )

    logger.info(
        "Loaded filter config from '%s': %d categories, %d industries",
        config_path,
        len(config.ai_relevant_categories),
        len(config.ai_relevant_industries),
    )
    logger.debug("  categories: %s", sorted(config.ai_relevant_categories))
    logger.debug("  industries:  %s", sorted(config.ai_relevant_industries))

    return config


def _extract_list(raw: dict, key: str, config_path: Path) -> list[str]:
    """Extract and validate a string-list value from the parsed YAML dict."""
    if key not in raw:
        raise ValueError(
            f"Filter config '{config_path}' is missing required key '{key}'."
        )
    value = raw[key]
    if not isinstance(value, list):
        raise ValueError(
            f"Filter config key '{key}' must be a YAML list, got {type(value).__name__}."
        )
    non_strings = [v for v in value if not isinstance(v, str)]
    if non_strings:
        raise ValueError(
            f"Filter config key '{key}' must contain only strings; "
            f"found non-string values: {non_strings}."
        )
    return value
