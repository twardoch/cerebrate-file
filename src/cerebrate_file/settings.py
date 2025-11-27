#!/usr/bin/env python3
# this_file: src/cerebrate_file/settings.py

"""Configuration management for cerebrate_file package.

This module handles loading and merging configuration from:
1. Built-in default_config.toml (package defaults)
2. User config at ~/.config/cerebrate-file/config.toml
3. Project config at .cerebrate-file.toml
4. Environment variables (highest priority)
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from loguru import logger

# Use tomllib on Python 3.11+, fallback to tomli for older versions
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]

__all__ = [
    "InferenceConfig",
    "ModelConfig",
    "RateLimitConfig",
    "Settings",
    "get_settings",
    "reload_settings",
]


@dataclass
class ModelConfig:
    """Configuration for a single model."""

    name: str
    provider: str  # "cerebras", "openai", or OpenAI-compatible
    api_key_env: str
    api_base: str | None = None
    max_context_tokens: int = 131000
    max_output_tokens: int = 40000
    enabled: bool = True

    def get_api_key(self) -> str | None:
        """Get API key from environment variable."""
        return os.environ.get(self.api_key_env)

    def is_available(self) -> bool:
        """Check if this model is available (enabled and has API key)."""
        return self.enabled and self.get_api_key() is not None


@dataclass
class InferenceConfig:
    """Default inference parameters."""

    temperature: float = 0.98
    top_p: float = 0.8
    max_tokens_ratio: int = 100
    chunk_size: int = 32000
    sample_size: int = 200


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    tokens_safety_margin: int = 50000
    requests_safety_margin: int = 100
    max_retry_attempts: int = 8
    fallback_on_rate_limit: bool = True
    fallback_on_quota_exceeded: bool = True


@dataclass
class Settings:
    """Main settings container."""

    inference: InferenceConfig = field(default_factory=InferenceConfig)
    rate_limiting: RateLimitConfig = field(default_factory=RateLimitConfig)
    primary_model: ModelConfig | None = None
    fallback_models: list[ModelConfig] = field(default_factory=list)
    log_format: str = ""

    def get_model_by_name(self, name: str) -> ModelConfig | None:
        """Find a model configuration by name."""
        if self.primary_model and self.primary_model.name == name:
            return self.primary_model
        for model in self.fallback_models:
            if model.name == name:
                return model
        return None

    def get_available_fallbacks(self) -> list[ModelConfig]:
        """Get list of available fallback models (enabled with API key)."""
        return [m for m in self.fallback_models if m.is_available()]

    def get_default_model_name(self) -> str:
        """Get the default model name from primary or fallbacks."""
        if self.primary_model:
            return self.primary_model.name
        if self.fallback_models:
            return self.fallback_models[0].name
        return "zai-glm-4.6"  # Ultimate fallback


def _load_toml_file(path: Path) -> dict[str, Any]:
    """Load a TOML file and return its contents."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning(f"Failed to load config from {path}: {e}")
        return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _parse_model_config(data: dict[str, Any], key: str = "primary") -> ModelConfig | None:
    """Parse a model configuration from dict."""
    if not data:
        return None

    return ModelConfig(
        name=data.get("name", ""),
        provider=data.get("provider", "openai"),
        api_key_env=data.get("api_key_env", ""),
        api_base=data.get("api_base"),
        max_context_tokens=data.get("max_context_tokens", 131000),
        max_output_tokens=data.get("max_output_tokens", 40000),
        enabled=data.get("enabled", True),
    )


def _parse_fallback_models(models_data: dict[str, Any]) -> list[ModelConfig]:
    """Parse fallback models from config."""
    fallbacks = []

    # Check for fallback1, fallback2, fallback3, etc.
    for i in range(1, 10):  # Support up to 9 fallbacks
        key = f"fallback{i}"
        if key in models_data:
            model = _parse_model_config(models_data[key], key)
            if model and model.name:  # Only add if it has a name
                fallbacks.append(model)

    return fallbacks


def _apply_env_overrides(settings: Settings) -> None:
    """Apply environment variable overrides to settings."""
    # Inference settings
    if env_temp := os.environ.get("CEREBRATE_TEMPERATURE"):
        settings.inference.temperature = float(env_temp)
    if env_top_p := os.environ.get("CEREBRATE_TOP_P"):
        settings.inference.top_p = float(env_top_p)
    if env_chunk := os.environ.get("CEREBRATE_CHUNK_SIZE"):
        settings.inference.chunk_size = int(env_chunk)
    if env_ratio := os.environ.get("CEREBRATE_MAX_TOKENS_RATIO"):
        settings.inference.max_tokens_ratio = int(env_ratio)

    # Primary model override
    if env_model := os.environ.get("CEREBRATE_PRIMARY_MODEL"):
        if settings.primary_model:
            settings.primary_model.name = env_model

    # Rate limiting
    if env_fallback := os.environ.get("CEREBRATE_FALLBACK_ON_RATE_LIMIT"):
        settings.rate_limiting.fallback_on_rate_limit = env_fallback.lower() in (
            "true",
            "1",
            "yes",
        )
    if env_quota := os.environ.get("CEREBRATE_FALLBACK_ON_QUOTA"):
        settings.rate_limiting.fallback_on_quota_exceeded = env_quota.lower() in (
            "true",
            "1",
            "yes",
        )


def _load_settings_impl() -> Settings:
    """Load settings from all sources and merge them."""
    # 1. Load built-in defaults from package
    package_dir = Path(__file__).parent
    default_config_path = package_dir / "default_config.toml"
    config_data = _load_toml_file(default_config_path)

    if not config_data:
        logger.warning("Built-in default_config.toml not found, using hardcoded defaults")
        config_data = {}

    # 2. Load user config from ~/.config/cerebrate-file/config.toml
    user_config_dir = Path.home() / ".config" / "cerebrate-file"
    user_config_path = user_config_dir / "config.toml"
    user_config = _load_toml_file(user_config_path)
    if user_config:
        logger.debug(f"Loaded user config from {user_config_path}")
        config_data = _deep_merge(config_data, user_config)

    # 3. Load project config from .cerebrate-file.toml in current directory
    project_config_path = Path.cwd() / ".cerebrate-file.toml"
    project_config = _load_toml_file(project_config_path)
    if project_config:
        logger.debug(f"Loaded project config from {project_config_path}")
        config_data = _deep_merge(config_data, project_config)

    # Parse inference config
    inference_data = config_data.get("inference", {})
    inference = InferenceConfig(
        temperature=inference_data.get("temperature", 0.98),
        top_p=inference_data.get("top_p", 0.8),
        max_tokens_ratio=inference_data.get("max_tokens_ratio", 100),
        chunk_size=inference_data.get("chunk_size", 32000),
        sample_size=inference_data.get("sample_size", 200),
    )

    # Parse rate limiting config
    rate_data = config_data.get("rate_limiting", {})
    rate_limiting = RateLimitConfig(
        tokens_safety_margin=rate_data.get("tokens_safety_margin", 50000),
        requests_safety_margin=rate_data.get("requests_safety_margin", 100),
        max_retry_attempts=rate_data.get("max_retry_attempts", 8),
        fallback_on_rate_limit=rate_data.get("fallback_on_rate_limit", True),
        fallback_on_quota_exceeded=rate_data.get("fallback_on_quota_exceeded", True),
    )

    # Parse model configs
    models_data = config_data.get("models", {})
    primary_model = _parse_model_config(models_data.get("primary", {}), "primary")
    fallback_models = _parse_fallback_models(models_data)

    # Parse logging config
    logging_data = config_data.get("logging", {})
    log_format = logging_data.get("format", "")

    # Create settings object
    settings = Settings(
        inference=inference,
        rate_limiting=rate_limiting,
        primary_model=primary_model,
        fallback_models=fallback_models,
        log_format=log_format,
    )

    # 4. Apply environment variable overrides (highest priority)
    _apply_env_overrides(settings)

    return settings


# Cache the settings to avoid repeated file reads
_settings_cache: Settings | None = None


def get_settings() -> Settings:
    """Get the current settings, loading from config files if needed."""
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = _load_settings_impl()
    return _settings_cache


def reload_settings() -> Settings:
    """Force reload settings from config files."""
    global _settings_cache
    _settings_cache = _load_settings_impl()
    return _settings_cache
