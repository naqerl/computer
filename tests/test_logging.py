from __future__ import annotations

import importlib
import json
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _reload_logging_modules(env: dict[str, str]):
    with patch.dict(os.environ, env, clear=False):
        import cptr.env
        import cptr.utils.audit
        import cptr.utils.logger

        importlib.reload(cptr.env)
        importlib.reload(cptr.utils.logger)
        importlib.reload(cptr.utils.audit)
        return cptr.utils.logger, cptr.utils.audit


class LoggingTests(unittest.TestCase):
    def test_loguru_sinks_keep_streams_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "CPTR_DATA_DIR": tmp,
                "CPTR_AUDIT_LOG_LEVEL": "METADATA",
                "CPTR_AUDIT_LOG_PATH": str(Path(tmp) / "logs" / "audit.jsonl"),
                "CPTR_LOG_UPSTREAM_REQUESTS": "true",
                "CPTR_UPSTREAM_REQUEST_LOG_PATH": str(
                    Path(tmp) / "logs" / "upstream-requests.jsonl"
                ),
            }
            logger_mod, _ = _reload_logging_modules(env)
            logger_mod.setup_logging()

            logging.getLogger("cptr.test").info("normal app log")
            logger_mod.audit_logger().bind(
                id="audit-id",
                audit_level="METADATA",
                user={"id": "user-1"},
                method="POST",
                path="/api/admin/config",
                status_code=200,
                source_ip="127.0.0.1",
                user_agent="test",
                request_body=None,
                response_body=None,
            ).info("")
            body = {"model": "claude-sonnet", "messages": [{"role": "user", "content": "hi"}]}
            logger_mod.log_upstream_request(
                provider="anthropic",
                endpoint="https://api.anthropic.com/v1/messages",
                model="claude-sonnet",
                api_type="messages",
                body=body,
            )

            audit_lines = (Path(tmp) / "logs" / "audit.jsonl").read_text().splitlines()
            upstream_lines = (Path(tmp) / "logs" / "upstream-requests.jsonl").read_text().splitlines()

            self.assertEqual(len(audit_lines), 1)
            self.assertEqual(len(upstream_lines), 1)
            self.assertEqual(json.loads(audit_lines[0])["id"], "audit-id")
            self.assertEqual(json.loads(upstream_lines[0])["body"], body)
            self.assertNotIn("normal app log", audit_lines[0])
            self.assertNotIn("normal app log", upstream_lines[0])

    def test_upstream_logging_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "CPTR_DATA_DIR": tmp,
                "CPTR_AUDIT_LOG_LEVEL": "NONE",
                "CPTR_LOG_UPSTREAM_REQUESTS": "false",
            }
            logger_mod, _ = _reload_logging_modules(env)
            logger_mod.setup_logging()

            logger_mod.log_upstream_request(
                provider="anthropic",
                endpoint="https://api.anthropic.com/v1/messages",
                model="claude-sonnet",
                api_type="messages",
                body={"model": "claude-sonnet"},
            )

            self.assertFalse((Path(tmp) / "logs" / "upstream-requests.jsonl").exists())

    def test_audit_body_redacts_sensitive_json_fields(self):
        _, audit_mod = _reload_logging_modules({"CPTR_AUDIT_LOG_LEVEL": "REQUEST"})
        body = bytearray(
            json.dumps(
                {
                    "username": "alice",
                    "password": "secret",
                    "nested": {"api_key": "sk-test", "token": "tok"},
                }
            ).encode()
        )

        redacted = json.loads(audit_mod._decode_body(body))

        self.assertEqual(redacted["username"], "alice")
        self.assertEqual(redacted["password"], "********")
        self.assertEqual(redacted["nested"]["api_key"], "********")
        self.assertEqual(redacted["nested"]["token"], "********")

    def test_audit_context_caps_request_body(self):
        _, audit_mod = _reload_logging_modules({"CPTR_AUDIT_LOG_LEVEL": "REQUEST"})
        context = audit_mod.AuditContext(max_body_size=5)

        context.add_request(b"hello")
        context.add_request(b" world")

        self.assertEqual(bytes(context.request_body), b"hello")


if __name__ == "__main__":
    unittest.main()
