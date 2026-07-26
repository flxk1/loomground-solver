# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 flxk1
"""Explicit host-side activation for optional Solver add-ons."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .world_model import ContextProvider


def _factory(reference: str, authorized: Mapping[str, Callable[..., Any]]):
    if ":" not in reference:
        raise ValueError("add-on provider must use 'module:factory' syntax")
    factory = authorized.get(reference)
    if factory is None:
        raise PermissionError(
            f"add-on factory {reference!r} is not authorized by the host")
    if not callable(factory):
        raise TypeError(f"add-on factory {reference!r} is not callable")
    return factory


@dataclass(frozen=True)
class AddonRuntime:
    context_provider: ContextProvider | None = None
    observers: tuple[Any, ...] = ()


def load_addons(
    config: Mapping[str, Any],
    *,
    selected=(),
    authorized_factories: Mapping[str, Callable[..., Any]] | None = None,
) -> AddonRuntime:
    """Resolve host-authorized adapters. Advice never calls this function.

    ``selected`` is the host's explicit per-run/manual authorization for add-ons
    configured in recommendation/manual mode. Legacy ``enabled=true`` remains an
    explicit activation instruction. ``authorized_factories`` is the host-owned
    registry of callable implementations; configuration strings never import code.
    """
    root = config.get("solver", config)
    addons = root.get("addons", {})
    world = addons.get("world_model", {})
    meta = addons.get("metacognition", {})
    provider = None
    observers = []
    selected = set(selected)
    authorized = authorized_factories or {}
    world_mode = world.get("mode")
    world_active = bool(world.get("enabled", False)) or world_mode == "required" or (
        world_mode == "recommend" and "world_model" in selected)
    meta_mode = meta.get("mode")
    meta_active = bool(meta.get("enabled", False)) or meta_mode == "scheduled" or (
        meta_mode == "manual" and "metacognition" in selected)
    if world_mode == "off":
        world_active = False
    if meta_mode == "off":
        meta_active = False
    if world_active:
        reference = world.get("provider")
        if not reference:
            raise ValueError("enabled world_model requires a provider")
        provider = _factory(str(reference), authorized)(dict(world.get("options", {})))
        if not isinstance(provider, ContextProvider):
            raise TypeError("world-model factory did not return a ContextProvider")
    if meta_active:
        for reference in meta.get("observers", ()):
            observers.append(
                _factory(str(reference), authorized)(dict(meta.get("options", {}))))
    return AddonRuntime(provider, tuple(observers))
