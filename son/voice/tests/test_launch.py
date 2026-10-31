"""Hidden-entry boundaries; no real credentials, console prompt or network."""
import getpass
import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from voice_app.launch import main, private_key


class LaunchTests(unittest.TestCase):
    def test_redirected_stdin_never_prompts_or_echoes(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdin.isatty", return_value=False), patch("getpass.getpass") as prompt:
            with self.assertRaises(ValueError):
                private_key()
            prompt.assert_not_called()

    def test_getpass_fallback_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdin.isatty", return_value=True), patch("getpass.getpass", side_effect=getpass.GetPassWarning):
            with self.assertRaises(ValueError):
                private_key()

    def test_local_launch_does_not_print_or_persist_secret(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdin.isatty", return_value=True), patch("getpass.getpass", return_value="synthetic-test-key"), patch("uvicorn.run") as run, redirect_stdout(output):
            self.assertEqual(main(["--port", "8001"]), 0)
            self.assertNotIn("OPENAI_API_KEY", os.environ)
            self.assertEqual(run.call_args.kwargs["host"], "127.0.0.1")
            self.assertEqual(run.call_args.kwargs["port"], 8001)
            self.assertFalse(run.call_args.kwargs["access_log"])
        self.assertNotIn("synthetic-test-key", output.getvalue())

    def test_cancelled_input_starts_no_server(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdin.isatty", return_value=True), patch("getpass.getpass", side_effect=KeyboardInterrupt), patch("uvicorn.run") as run, redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 1)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
