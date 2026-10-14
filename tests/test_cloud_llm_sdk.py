"""CloudLLMAnalyzer against a local OpenAI-compatible server: guards openai SDK major bumps."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.ai.cloud_llm import CloudLLMAnalyzer
from src.core import config

ANSWER = '{"severity": "none", "is_usable": true, "bonus_points": 5}'


class _FakeOpenAI(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body.get("stream"):
            self._send("text/event-stream", self._sse_chunks())
        else:
            self._send("application/json", json.dumps(self._completion()).encode())

    def _send(self, content_type: str, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    @staticmethod
    def _completion() -> dict:
        return {
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": "test",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ANSWER},
                    "finish_reason": "stop",
                }
            ],
        }

    @staticmethod
    def _sse_chunks() -> bytes:
        half = len(ANSWER) // 2
        events = [
            {
                "id": "c1",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "test",
                "choices": [{"index": 0, "delta": {"content": part}, "finish_reason": None}],
            }
            for part in (ANSWER[:half], ANSWER[half:])
        ]
        lines = [f"data: {json.dumps(e)}\n\n" for e in events] + ["data: [DONE]\n\n"]
        return "".join(lines).encode()

    def log_message(self, *args):  # keep test output quiet
        pass


@pytest.fixture
def analyzer(monkeypatch, tmp_path):
    server = HTTPServer(("127.0.0.1", 0), _FakeOpenAI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setenv("AI_GATEWAY_API_KEY", "test-key")
    monkeypatch.setenv("AI_GATEWAY_URL", f"http://127.0.0.1:{server.server_port}/v1")
    yield CloudLLMAnalyzer(provider="vercel")
    server.shutdown()


def test_streamed_completion_is_assembled_and_parsed(analyzer):
    assert analyzer.enabled
    text = analyzer._send_llm_request("system", "user")
    assert analyzer._parse_json_response(text)["bonus_points"] == 5


def test_async_completion_returns_message_content(analyzer):
    text = asyncio.run(analyzer._send_llm_request_async("system", "user"))
    assert analyzer._parse_json_response(text)["severity"] == "none"
