from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPOSE_FILE = os.path.join(REPO_ROOT, "infra", "docker", "docker-compose.yml")
BACKEND_DIR = os.path.join(REPO_ROOT, "apps", "backend")


def _wait_for_url(url: str, timeout_s: int = 90) -> None:
    deadline = time.time() + timeout_s
    last_exc: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:  # noqa: S310
                r.read()
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2)

    raise RuntimeError(f"Timed out waiting for {url}. Last error: {last_exc}")


def main() -> int:
    base_url = os.getenv("OPENTTS_BASE_URL", "http://localhost:5500").rstrip("/")
    health_url = f"{base_url}/api/languages"

    # Preflight: verify Docker engine is reachable.
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True, text=True)
        subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        msg = stderr or stdout or str(exc)
        print("[smoke] docker preflight failed")
        print(msg)
        print(
            "\n[smoke] Fix: ensure Docker Desktop is running and set to Linux containers. "
            "On Windows this typically means enabling the WSL2 engine in Docker Desktop settings."
        )
        return 2

    print(f"[smoke] starting OpenTTS via compose: {COMPOSE_FILE}")
    try:
        subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"], check=True)
    except subprocess.CalledProcessError as exc:
        print("[smoke] failed to start docker compose")
        print(str(exc))
        print(
            "\n[smoke] If you see errors about dockerDesktopLinuxEngine pipe, Docker Desktop isn't running "
            "or Linux engine isn't enabled. Start Docker Desktop and retry."
        )
        return exc.returncode

    try:
        print(f"[smoke] waiting for OpenTTS: {health_url}")
        _wait_for_url(health_url, timeout_s=120)

        env = os.environ.copy()
        env.setdefault("RUN_OPENTTS_SMOKE", "1")
        env.setdefault("TTS_BACKEND", "opentts")
        env.setdefault("OPENTTS_BASE_URL", base_url)

        print("[smoke] running integration pytest")
        return subprocess.call(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-k",
                "opentts",
            ],
            cwd=BACKEND_DIR,
            env=env,
        )
    finally:
        if os.getenv("KEEP_DOCKER") == "1":
            print("[smoke] KEEP_DOCKER=1 set; leaving containers running")
        else:
            print("[smoke] stopping compose")
            subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "down"], check=False)


if __name__ == "__main__":
    raise SystemExit(main())
