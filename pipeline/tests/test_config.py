"""
tests/test_config.py — Unit tests for config/loader.py.

Coverage:

  load_filter_config()
    - Default path loads successfully (config/filter_config.yaml exists)
    - Returns a FilterConfig with non-empty frozensets
    - Loaded values match the YAML file contents exactly
    - Custom path: valid YAML file loads correctly
    - Custom path: categories and industries become frozensets
    - FileNotFoundError when path does not exist
    - ValueError when YAML is not a mapping (e.g. a bare list)
    - ValueError when 'ai_relevant_categories' key is missing
    - ValueError when 'ai_relevant_industries' key is missing
    - ValueError when a key's value is not a list (e.g. a string)
    - ValueError when a list contains non-string values (e.g. integers)
    - Empty lists are valid (produces empty frozensets)
    - Extra unknown keys in YAML are silently ignored

  FilterConfig
    - is frozen (assignment raises FrozenInstanceError)
    - ai_relevant_categories and ai_relevant_industries are frozensets
"""

import pytest
from pathlib import Path

from config.loader import FilterConfig, load_filter_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_yaml(tmp_path: Path, content: str) -> Path:
    """Write a YAML string to a temp file and return its path."""
    p = tmp_path / "filter_config.yaml"
    p.write_text(content, encoding="utf-8")
    return p


VALID_YAML = """\
ai_relevant_categories:
  - AI_ML
  - Data_Analytics

ai_relevant_industries:
  - AI/ML
  - Data Analytics
"""


# ---------------------------------------------------------------------------
# Default config file (config/filter_config.yaml)
# ---------------------------------------------------------------------------

class TestDefaultConfig:
    def test_default_config_loads(self):
        """The shipped default config must parse without error."""
        cfg = load_filter_config()
        assert isinstance(cfg, FilterConfig)

    def test_default_config_categories_non_empty(self):
        cfg = load_filter_config()
        assert len(cfg.ai_relevant_categories) > 0

    def test_default_config_industries_non_empty(self):
        cfg = load_filter_config()
        assert len(cfg.ai_relevant_industries) > 0

    def test_default_config_contains_ai_ml_category(self):
        cfg = load_filter_config()
        assert "AI_ML" in cfg.ai_relevant_categories

    def test_default_config_contains_data_analytics_category(self):
        cfg = load_filter_config()
        assert "Data_Analytics" in cfg.ai_relevant_categories

    def test_default_config_contains_ai_ml_industry(self):
        cfg = load_filter_config()
        assert "AI/ML" in cfg.ai_relevant_industries

    def test_default_config_contains_data_analytics_industry(self):
        cfg = load_filter_config()
        assert "Data Analytics" in cfg.ai_relevant_industries

    def test_default_config_returns_frozensets(self):
        cfg = load_filter_config()
        assert isinstance(cfg.ai_relevant_categories, frozenset)
        assert isinstance(cfg.ai_relevant_industries, frozenset)


# ---------------------------------------------------------------------------
# Custom YAML path — valid inputs
# ---------------------------------------------------------------------------

class TestValidCustomConfig:
    def test_custom_path_loads(self, tmp_path):
        p = write_yaml(tmp_path, VALID_YAML)
        cfg = load_filter_config(p)
        assert isinstance(cfg, FilterConfig)

    def test_custom_categories_match_yaml(self, tmp_path):
        p = write_yaml(tmp_path, VALID_YAML)
        cfg = load_filter_config(p)
        assert cfg.ai_relevant_categories == frozenset({"AI_ML", "Data_Analytics"})

    def test_custom_industries_match_yaml(self, tmp_path):
        p = write_yaml(tmp_path, VALID_YAML)
        cfg = load_filter_config(p)
        assert cfg.ai_relevant_industries == frozenset({"AI/ML", "Data Analytics"})

    def test_single_item_lists(self, tmp_path):
        yaml_content = (
            "ai_relevant_categories:\n  - AI_ML\n"
            "ai_relevant_industries:\n  - AI/ML\n"
        )
        p = write_yaml(tmp_path, yaml_content)
        cfg = load_filter_config(p)
        assert cfg.ai_relevant_categories == frozenset({"AI_ML"})
        assert cfg.ai_relevant_industries == frozenset({"AI/ML"})

    def test_empty_lists_produce_empty_frozensets(self, tmp_path):
        yaml_content = (
            "ai_relevant_categories: []\n"
            "ai_relevant_industries: []\n"
        )
        p = write_yaml(tmp_path, yaml_content)
        cfg = load_filter_config(p)
        assert cfg.ai_relevant_categories == frozenset()
        assert cfg.ai_relevant_industries == frozenset()

    def test_extra_unknown_keys_are_ignored(self, tmp_path):
        yaml_content = VALID_YAML + "\nunknown_key: some_value\n"
        p = write_yaml(tmp_path, yaml_content)
        cfg = load_filter_config(p)  # should not raise
        assert isinstance(cfg, FilterConfig)

    def test_extended_categories_list(self, tmp_path):
        yaml_content = (
            "ai_relevant_categories:\n"
            "  - AI_ML\n  - Data_Analytics\n  - Cloud_Computing\n"
            "ai_relevant_industries:\n  - AI/ML\n"
        )
        p = write_yaml(tmp_path, yaml_content)
        cfg = load_filter_config(p)
        assert "Cloud_Computing" in cfg.ai_relevant_categories
        assert len(cfg.ai_relevant_categories) == 3


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestConfigErrors:
    def test_nonexistent_path_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Filter config"):
            load_filter_config(tmp_path / "nonexistent.yaml")

    def test_top_level_list_raises_value_error(self, tmp_path):
        p = write_yaml(tmp_path, "- item1\n- item2\n")
        with pytest.raises(ValueError, match="mapping"):
            load_filter_config(p)

    def test_missing_categories_key_raises_value_error(self, tmp_path):
        yaml_content = "ai_relevant_industries:\n  - AI/ML\n"
        p = write_yaml(tmp_path, yaml_content)
        with pytest.raises(ValueError, match="ai_relevant_categories"):
            load_filter_config(p)

    def test_missing_industries_key_raises_value_error(self, tmp_path):
        yaml_content = "ai_relevant_categories:\n  - AI_ML\n"
        p = write_yaml(tmp_path, yaml_content)
        with pytest.raises(ValueError, match="ai_relevant_industries"):
            load_filter_config(p)

    def test_categories_as_string_raises_value_error(self, tmp_path):
        yaml_content = (
            "ai_relevant_categories: AI_ML\n"
            "ai_relevant_industries:\n  - AI/ML\n"
        )
        p = write_yaml(tmp_path, yaml_content)
        with pytest.raises(ValueError, match="list"):
            load_filter_config(p)

    def test_industries_as_dict_raises_value_error(self, tmp_path):
        yaml_content = (
            "ai_relevant_categories:\n  - AI_ML\n"
            "ai_relevant_industries:\n  key: value\n"
        )
        p = write_yaml(tmp_path, yaml_content)
        with pytest.raises(ValueError, match="list"):
            load_filter_config(p)

    def test_non_string_values_in_list_raises_value_error(self, tmp_path):
        yaml_content = (
            "ai_relevant_categories:\n  - AI_ML\n  - 42\n"
            "ai_relevant_industries:\n  - AI/ML\n"
        )
        p = write_yaml(tmp_path, yaml_content)
        with pytest.raises(ValueError, match="strings"):
            load_filter_config(p)

    def test_empty_yaml_file_raises_value_error(self, tmp_path):
        p = write_yaml(tmp_path, "")
        with pytest.raises(ValueError, match="mapping"):
            load_filter_config(p)


# ---------------------------------------------------------------------------
# FilterConfig dataclass properties
# ---------------------------------------------------------------------------

class TestFilterConfigDataclass:
    def test_is_frozen(self):
        from dataclasses import FrozenInstanceError
        cfg = FilterConfig(
            ai_relevant_categories=frozenset({"AI_ML"}),
            ai_relevant_industries=frozenset({"AI/ML"}),
        )
        with pytest.raises(FrozenInstanceError):
            cfg.ai_relevant_categories = frozenset({"Cloud_Computing"})  # type: ignore[misc]

    def test_fields_are_frozensets(self):
        cfg = FilterConfig(
            ai_relevant_categories=frozenset({"AI_ML"}),
            ai_relevant_industries=frozenset({"AI/ML"}),
        )
        assert isinstance(cfg.ai_relevant_categories, frozenset)
        assert isinstance(cfg.ai_relevant_industries, frozenset)

    def test_equality(self):
        cfg1 = FilterConfig(frozenset({"AI_ML"}), frozenset({"AI/ML"}))
        cfg2 = FilterConfig(frozenset({"AI_ML"}), frozenset({"AI/ML"}))
        assert cfg1 == cfg2
