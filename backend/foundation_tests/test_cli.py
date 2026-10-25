from types import SimpleNamespace

import pytest

from entrypoints import foundation_cli


def test_compatibility_launcher_uses_installed_feature_cli(monkeypatch):
    calls = []
    monkeypatch.setattr(foundation_cli, "import_module", lambda _: SimpleNamespace(main=lambda: calls.append("feature")))
    foundation_cli.platform_main()
    assert calls == ["feature"]


def test_compatibility_launcher_falls_back_to_foundation(monkeypatch, capsys):
    def missing_feature(name):
        raise ModuleNotFoundError(name="entrypoints.cli")

    monkeypatch.setattr(foundation_cli, "import_module", missing_feature)
    monkeypatch.setattr("sys.argv", ["arc", "--help"])
    with pytest.raises(SystemExit) as stopped:
        foundation_cli.platform_main()
    assert stopped.value.code == 0
    assert "migration-status" in capsys.readouterr().out


def test_compatibility_launcher_does_not_hide_broken_feature_dependencies(monkeypatch):
    def broken_feature(name):
        raise ModuleNotFoundError(name="unexpected_dependency")

    monkeypatch.setattr(foundation_cli, "import_module", broken_feature)
    with pytest.raises(ModuleNotFoundError) as error:
        foundation_cli.platform_main()
    assert error.value.name == "unexpected_dependency"
