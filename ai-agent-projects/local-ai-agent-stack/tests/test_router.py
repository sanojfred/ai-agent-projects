import json, os, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import llm_router


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/chat":
            self.send_response(500); self.end_headers(); self.wfile.write(b"down"); return
        if self.path == "/chat/completions":
            assert self.headers["Authorization"] == "Bearer k1"
            out = {"choices": [{"message": {"content": "from-openrouter:" + body["messages"][-1]["content"]}}]}
        elif self.path.endswith(":generateContent"):
            assert self.headers["x-goog-api-key"] == "k2"
            out = {"candidates": [{"content": {"parts": [{"text": "from-gemini"}]}}]}
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(out).encode())


class RouterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{cls.srv.server_port}"
        os.environ.update(OLLAMA_HOST=base, OPENROUTER_BASE_URL=base, GEMINI_BASE_URL=base,
                          OPENROUTER_API_KEY="k1", OPENROUTER_MODEL="m", GEMINI_API_KEY="k2", GEMINI_MODEL="g")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_falls_back_when_ollama_fails(self):
        name, reply = llm_router.ask("hi")
        self.assertEqual(name, "openrouter")
        self.assertEqual(reply, "from-openrouter:hi")

    def test_gemini_with_system_prompt(self):
        name, reply = llm_router.ask("hi", system="be brief", order=["gemini"])
        self.assertEqual((name, reply), ("gemini", "from-gemini"))

    def test_all_fail(self):
        with self.assertRaises(llm_router.ProviderError):
            llm_router.ask("hi", order=["ollama", "nope"])


if __name__ == "__main__":
    unittest.main()
