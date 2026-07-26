import pytest

from loomground_solver.addons import load_addons
from loomground_solver.addons.world_model import make_snapshot, StaticContextProvider


def test_absent_config_is_pure_solver():
    runtime = load_addons({})
    assert runtime.context_provider is None and runtime.observers == ()


def test_explicit_config_loads_host_factories():
    context = lambda options: StaticContextProvider(
        make_snapshot([], created_at=options["created_at"]))
    observer = lambda options: {"observer": options["name"]}
    runtime = load_addons({"solver": {"addons": {
        "world_model": {"enabled": True, "provider": "test_host_addons:context",
                        "options": {"created_at": "2026-07-19T00:00:00Z"}},
        "metacognition": {"enabled": True,
                          "observers": ["test_host_addons:observer"],
                          "options": {"name": "gaps"}},
    }}}, authorized_factories={
        "test_host_addons:context": context,
        "test_host_addons:observer": observer,
    })
    assert runtime.context_provider.snapshot({}).digest.startswith("sha256:")
    assert runtime.observers == ({"observer": "gaps"},)


def test_enabled_addon_requires_explicit_provider():
    with pytest.raises(ValueError):
        load_addons({"addons": {"world_model": {"enabled": True}}})


def test_recommend_mode_loads_only_after_host_selection():
    context = lambda _options: StaticContextProvider(
        make_snapshot([], created_at="2026-07-19T00:00:00Z"))
    config = {"addons": {"world_model": {
        "mode": "recommend", "provider": "recommended_addon:context"}}}
    assert load_addons(config).context_provider is None
    assert load_addons(
        config,
        selected=("world_model",),
        authorized_factories={"recommended_addon:context": context},
    ).context_provider is not None


def test_active_addon_cannot_import_from_configuration():
    config = {"addons": {"world_model": {
        "enabled": True,
        "provider": "os:system",
        "options": {"command": "touch /tmp/solver-addon-import"},
    }}}

    with pytest.raises(PermissionError, match="not authorized"):
        load_addons(config)
