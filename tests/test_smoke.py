from fleet.models import resolve
from fleet import __version__

def test_registry():
    s = resolve()
    assert set(("reasoning", "coding", "uncensored")).issubset(s)
    for slot, spec in s.items():
        assert spec["port"] and spec["repo"] and spec["file"]

def test_cli_importable():
    from fleet.cli import main
    assert callable(main) and __version__
