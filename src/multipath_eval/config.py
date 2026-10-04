"""Typed, validated experiment configuration loaded from TOML."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

FAMILIES = {"erdos_renyi", "grid", "barabasi_albert", "gml"}
METRICS = ("cost", "delay", "capacity", "outage")


class ConfigError(ValueError):
    """Raised when the config file is missing a field or has an invalid value."""


@dataclass(frozen=True)
class Range:
    low: float
    high: float


@dataclass(frozen=True)
class Setting:
    name: str
    fail_scale: float


@dataclass(frozen=True)
class TopologySpec:
    name: str
    family: str
    seeds: int
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Config:
    name: str
    seed: int
    out_dir: Path
    k: int
    demands: int
    mc_draws: int
    weight_vectors: int
    weights: dict
    cost: Range
    delay_ms: Range
    capacity: Range
    fail_prob: Range
    km_per_ms: float
    min_delay_ms: float
    settings: tuple
    topologies: tuple
    base_dir: Path


def _require(table: dict, key: str, where: str):
    if key not in table:
        raise ConfigError(f"missing '{key}' in [{where}]")
    return table[key]


def _range(table: dict, key: str) -> Range:
    r = _require(table, key, "attributes")
    low, high = float(_require(r, "low", f"attributes.{key}")), float(_require(r, "high", f"attributes.{key}"))
    if not 0 < low <= high:
        raise ConfigError(f"attributes.{key}: need 0 < low <= high, got {low}, {high}")
    return Range(low, high)


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    run = _require(raw, "run", "root")
    attrs = _require(raw, "attributes", "root")
    weights = {m: float(_require(_require(raw, "weights", "root"), m, "weights")) for m in METRICS}
    if any(w < 0 for w in weights.values()) or sum(weights.values()) <= 0:
        raise ConfigError("weights must be non-negative and not all zero")
    total = sum(weights.values())
    weights = {m: w / total for m, w in weights.items()}

    fail = _range(attrs, "fail_prob")
    if fail.high >= 1:
        raise ConfigError("attributes.fail_prob.high must be below 1")
    geo = raw.get("geo", {})

    settings = tuple(
        Setting(str(_require(s, "name", "settings")), float(_require(s, "fail_scale", "settings")))
        for s in raw.get("settings", [])
    )
    if not settings:
        raise ConfigError("at least one [[settings]] entry is required")
    if any(s.fail_scale <= 0 for s in settings):
        raise ConfigError("settings.fail_scale must be positive")

    topologies = []
    for t in raw.get("topologies", []):
        family = str(_require(t, "family", "topologies"))
        if family not in FAMILIES:
            raise ConfigError(f"unknown topology family '{family}', expected one of {sorted(FAMILIES)}")
        params = {k: v for k, v in t.items() if k not in ("name", "family", "seeds")}
        topologies.append(
            TopologySpec(str(_require(t, "name", "topologies")), family, int(_require(t, "seeds", "topologies")), params)
        )
    if not topologies:
        raise ConfigError("at least one [[topologies]] entry is required")

    cfg = Config(
        name=str(_require(run, "name", "run")),
        seed=int(_require(run, "seed", "run")),
        out_dir=Path(_require(run, "out_dir", "run")),
        k=int(_require(run, "k", "run")),
        demands=int(_require(run, "demands", "run")),
        mc_draws=int(_require(run, "mc_draws", "run")),
        weight_vectors=int(_require(run, "weight_vectors", "run")),
        weights=weights,
        cost=_range(attrs, "cost"),
        delay_ms=_range(attrs, "delay_ms"),
        capacity=_range(attrs, "capacity"),
        fail_prob=fail,
        km_per_ms=float(geo.get("km_per_ms", 200.0)),
        min_delay_ms=float(geo.get("min_delay_ms", 0.1)),
        settings=settings,
        topologies=tuple(topologies),
        base_dir=path.resolve().parent.parent,
    )
    for name, value in (("k", cfg.k), ("demands", cfg.demands), ("mc_draws", cfg.mc_draws)):
        if value < 1:
            raise ConfigError(f"run.{name} must be at least 1")
    return cfg
