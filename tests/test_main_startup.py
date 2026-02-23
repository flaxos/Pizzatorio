from __future__ import annotations

import sys

import pytest

import main


class _DisplayNotReady:
    @staticmethod
    def init() -> None:
        return None

    @staticmethod
    def get_init() -> bool:
        return False


class _FakePygameDisplayDown:
    error = RuntimeError
    display = _DisplayNotReady()

    @staticmethod
    def init() -> None:
        return None


def test_gameui_reports_display_startup_failure(monkeypatch):
    monkeypatch.setattr(main, "pygame", _FakePygameDisplayDown)

    with pytest.raises(RuntimeError, match="--headless"):
        main.GameUI(object())


class _BrokenGameUI:
    def __init__(self, sim):
        raise RuntimeError("Display subsystem is unavailable. Relaunch with --headless.")


def test_main_handles_gameui_startup_error(monkeypatch, capsys):
    monkeypatch.setattr(main, "GameUI", _BrokenGameUI)
    monkeypatch.setattr(sys, "argv", ["pizzatorio"])

    with pytest.raises(SystemExit) as exc:
        main.main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Startup error:" in captured.err
    assert "--headless" in captured.err
