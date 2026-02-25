#!/usr/bin/env python3
"""
Git-Push Helper Service
-----------------------
에이전트(openclaw-gateway)가 내부 Docker 네트워크를 통해
POST /push 를 호출하면 GitHub에 커밋·푸시를 수행합니다.

허용 경로: openclaw-config/workspace/ 및 openclaw-config/openclaw.json
(인프라 파일은 수정 불가)
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess, json, logging, os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REPO = "/repo"
ALLOWED_PATHS = [
    "openclaw-config/workspace/",
    "openclaw-config/openclaw.json",
]


def run(cmd, **kwargs):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, **kwargs)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logging.info(fmt % args)

    def do_GET(self):
        """헬스체크"""
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/push":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length)) if length else {}
            msg = str(data.get("message", "agent: update config"))[:200]

            # 허용된 경로만 스테이징
            for path in ALLOWED_PATHS:
                run(["git", "add", path])

            # 변경 사항 확인 (허용 경로만 체크)
            status = run(["git", "status", "--porcelain", "--"] + ALLOWED_PATHS)
            if not status.stdout.strip():
                self._json(200, {"status": "nothing_to_commit"})
                return

            # 커밋 (warning만 있는 경우는 성공으로 처리)
            commit = run(["git", "commit", "-m", msg])
            if commit.returncode != 0:
                stderr_lines = [l for l in commit.stderr.splitlines() if not l.lower().startswith("warning:")]
                if stderr_lines:
                    raise RuntimeError(commit.stderr)

            # 푸시 (warning만 있는 경우는 성공으로 처리)
            push = run(["git", "push", "origin", "main"])
            if push.returncode != 0:
                stderr_lines = [l for l in push.stderr.splitlines() if not l.lower().startswith("warning:")]
                if stderr_lines:
                    raise RuntimeError(push.stderr)

            logging.info("Pushed: %s", msg)
            self._json(200, {"status": "ok", "message": msg})

        except Exception as e:
            logging.error("Push failed: %s", e)
            self._json(500, {"status": "error", "error": str(e)})

    def _json(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    port = int(os.environ.get("GIT_PUSH_PORT", 7777))
    logging.info("Git-push service listening on :%d", port)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
