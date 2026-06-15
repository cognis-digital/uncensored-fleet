"""Tests covering the hardening additions: input validation, error handling, edge cases."""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# fleet.cli — unknown slot, empty prompt, keyboard interrupt
# ---------------------------------------------------------------------------

class TestCli:
    def test_unknown_slot_pull_exits_nonzero(self):
        """fleet pull <nonexistent> must exit with a non-zero code."""
        from fleet.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["pull", "no-such-slot"])
        assert exc_info.value.code != 0

    def test_unknown_slot_up_exits_nonzero(self):
        from fleet.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["up", "no-such-slot"])
        assert exc_info.value.code != 0

    def test_unknown_slot_run_exits_nonzero(self):
        from fleet.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main(["run", "no-such-slot", "hello"])
        assert exc_info.value.code != 0

    def test_no_subcommand_returns_zero(self):
        """Calling fleet with no args should print help and return 0."""
        from fleet.cli import main

        rc = main([])
        assert rc == 0

    def test_unexpected_exception_returns_one(self, capsys):
        """An unexpected exception bubbling from a subcommand is caught and returns 1."""
        from fleet.cli import main
        from fleet import serve

        with patch.object(serve, "status", side_effect=RuntimeError("boom")):
            rc = main(["status"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "boom" in captured.err


# ---------------------------------------------------------------------------
# fleet.harness — bad response shapes, empty inputs
# ---------------------------------------------------------------------------

class TestHarness:
    def test_chat_empty_messages_raises(self):
        from fleet.harness import chat

        with pytest.raises(ValueError, match="empty"):
            chat("uncensored", [])

    def test_chat_unknown_slot_raises(self):
        from fleet.harness import chat

        with pytest.raises(ValueError, match="unknown slot"):
            chat("no-such-slot", [{"role": "user", "content": "hi"}])

    def test_chat_network_error_raises_runtime(self):
        """A URLError from urlopen must be converted to RuntimeError with a clear message."""
        import urllib.error
        from fleet.harness import chat

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with pytest.raises(RuntimeError, match="could not reach"):
                chat("uncensored", [{"role": "user", "content": "hi"}])

    def test_chat_non_json_response_raises_runtime(self):
        from fleet.harness import chat

        fake_response = MagicMock()
        fake_response.read.return_value = b"not json at all"
        fake_response.__enter__ = lambda s: s
        fake_response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_response):
            with pytest.raises(RuntimeError, match="non-JSON"):
                chat("uncensored", [{"role": "user", "content": "hi"}])

    def test_chat_missing_choices_raises_runtime(self):
        from fleet.harness import chat

        body = json.dumps({"choices": []}).encode()
        fake_response = MagicMock()
        fake_response.read.return_value = body
        fake_response.__enter__ = lambda s: s
        fake_response.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=fake_response):
            with pytest.raises(RuntimeError, match="choices"):
                chat("uncensored", [{"role": "user", "content": "hi"}])

    def test_agent_empty_task_raises(self):
        from fleet.harness import agent

        with pytest.raises(ValueError, match="empty"):
            agent("")

    def test_agent_bad_max_steps_raises(self):
        from fleet.harness import agent

        with pytest.raises(ValueError, match="max_steps"):
            agent("do something", max_steps=0)


# ---------------------------------------------------------------------------
# fleet.serve — corrupt state file
# ---------------------------------------------------------------------------

class TestServe:
    def test_load_corrupt_state_returns_empty(self, tmp_path, monkeypatch):
        """A corrupt state.json must not crash _load(); it should return empty state."""
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT { valid JSON ]]")
        import fleet.serve as serve_mod

        monkeypatch.setattr(serve_mod, "STATE", state_file)
        result = serve_mod._load()
        assert result == {"running": {}}

    def test_load_missing_running_key_returns_empty(self, tmp_path, monkeypatch):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({"other": 1}))
        import fleet.serve as serve_mod

        monkeypatch.setattr(serve_mod, "STATE", state_file)
        result = serve_mod._load()
        assert result == {"running": {}}

    def test_load_nonexistent_returns_empty(self, tmp_path, monkeypatch):
        import fleet.serve as serve_mod

        monkeypatch.setattr(serve_mod, "STATE", tmp_path / "no_state.json")
        result = serve_mod._load()
        assert result == {"running": {}}


# ---------------------------------------------------------------------------
# fleet.memory — edge cases
# ---------------------------------------------------------------------------

class TestMemory:
    def test_fallback_recall_empty_query_returns_empty(self, tmp_path):
        from fleet.memory import _Fallback

        mem = _Fallback(str(tmp_path / "mem.sqlite"))
        mem.remember("key", "value")
        assert mem.recall("") == []

    def test_fallback_remember_empty_key_is_noop(self, tmp_path):
        from fleet.memory import _Fallback

        mem = _Fallback(str(tmp_path / "mem.sqlite"))
        mem.remember("", "some value")  # must not raise
        assert mem.recall("some value") == []  # nothing stored

    def test_fallback_recall_k_clamped(self, tmp_path):
        from fleet.memory import _Fallback

        mem = _Fallback(str(tmp_path / "mem.sqlite"))
        for i in range(5):
            mem.remember("fruit", f"apple-{i}")
        results = mem.recall("apple", k=0)  # k < 1 should not raise
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# integrations.webhook — invalid stdin / bad URL
# ---------------------------------------------------------------------------

class TestWebhook:
    def _run_main(self, args, stdin_data=""):
        """Helper: run webhook.main() with patched sys.argv and stdin."""
        import integrations.webhook as wh

        with patch("sys.stdin", io.StringIO(stdin_data)):
            with patch("sys.argv", ["webhook"] + args):
                return wh.main()

    def test_empty_stdin_returns_2(self):
        assert self._run_main(["--url", "https://example.com/hook"], stdin_data="") == 2

    def test_non_json_stdin_returns_2(self):
        assert self._run_main(["--url", "https://example.com/hook"], stdin_data="not json") == 2

    def test_bad_url_scheme_returns_2(self):
        assert self._run_main(["--url", "ftp://example.com/hook"], stdin_data='{"a":1}') == 2

    def test_valid_payload_posts_and_returns_0(self):
        import integrations.webhook as wh

        fake_response = MagicMock()
        fake_response.status = 200
        fake_response.__enter__ = lambda s: s
        fake_response.__exit__ = MagicMock(return_value=False)
        payload = json.dumps({"finding": "test"})
        with patch("sys.stdin", io.StringIO(payload)):
            with patch("sys.argv", ["webhook", "--url", "https://example.com/hook"]):
                with patch("urllib.request.urlopen", return_value=fake_response):
                    rc = wh.main()
        assert rc == 0
