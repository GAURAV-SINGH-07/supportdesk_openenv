import asyncio
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:7860"


def print_header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(title)
    print(f"{'=' * 70}")


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def http_request(method: str, path: str, payload: dict | None = None, timeout: int = 10) -> tuple[int, dict | str]:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            status = resp.getcode()
            try:
                return status, json.loads(body)
            except json.JSONDecodeError:
                return status, body
    except URLError as e:
        raise RuntimeError(f"HTTP request failed for {method} {path}: {e}") from e


async def test_python_api() -> bool:
    print_header("1. Testing Python API")
    try:
        from supportdesk_env import SupportDeskAction, SupportDeskEnv
        ok("Imported supportdesk_env successfully")
    except Exception as e:
        fail(f"Import failed: {e}")
        return False

    all_ok = True
    tasks = ["easy_refund", "medium_fraud_and_billing", "hard_multi_queue"]

    for task_name in tasks:
        try:
            env = await SupportDeskEnv.create(task_name=task_name)
            result = await env.reset()

            assert result.observation.task_name == task_name
            assert result.reward == 0.0
            assert result.done is False
            ok(f"reset() works for task={task_name}")

            state = env.state()
            assert state.task_name == task_name
            ok(f"state() works for task={task_name}")

            first_ticket = result.observation.queue[0]

            if task_name == "easy_refund":
                actions = [
                    SupportDeskAction(action_type="classify", ticket_id="T1", value="billing"),
                    SupportDeskAction(action_type="prioritize", ticket_id="T1", value="medium"),
                    SupportDeskAction(
                        action_type="reply",
                        ticket_id="T1",
                        message="We are sorry about the duplicate charge. We will review the duplicate billing and process a refund within 3-5 business days."
                    ),
                ]
            elif task_name == "medium_fraud_and_billing":
                actions = [
                    SupportDeskAction(action_type="classify", ticket_id="T1", value="security"),
                    SupportDeskAction(action_type="prioritize", ticket_id="T1", value="urgent"),
                    SupportDeskAction(action_type="escalate", ticket_id="T1", value="risk"),
                    SupportDeskAction(
                        action_type="reply",
                        ticket_id="T1",
                        message="We have secured your account review and escalated this issue. Our team is investigating the account activity now."
                    ),
                ]
            else:
                actions = [
                    SupportDeskAction(action_type="classify", ticket_id=first_ticket.id, value="technical"),
                    SupportDeskAction(action_type="prioritize", ticket_id=first_ticket.id, value="urgent"),
                ]

            prev_score = result.info.score
            for i, action in enumerate(actions, start=1):
                result = await env.step(action)
                assert 0.0 <= result.reward <= 1.0
                assert 0.0 <= result.info.score <= 1.0
                ok(f"step() #{i} works for task={task_name} action={action.action_type}")
                if result.info.score < prev_score:
                    warn(f"Score decreased for task={task_name}; check reward shaping if unexpected")
                prev_score = result.info.score

            await env.close()

        except Exception as e:
            fail(f"Python API test failed for task={task_name}: {e}")
            all_ok = False

    return all_ok


def start_server() -> subprocess.Popen | None:
    print_header("2. Starting local server")
    cmd = [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "7860"]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as e:
        fail(f"Could not start server: {e}")
        return None

    for _ in range(20):
        time.sleep(0.5)
        try:
            status, body = http_request("GET", "/healthz")
            if status == 200 and isinstance(body, dict) and body.get("status") == "healthy":
                ok("Server started and /healthz returned healthy")
                return proc
        except Exception:
            pass

    fail("Server did not become healthy in time")
    try:
        proc.terminate()
    except Exception:
        pass
    return None


def stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def test_http_endpoints() -> bool:
    print_header("3. Testing HTTP endpoints")
    all_ok = True

    try:
        status, body = http_request("GET", "/")
        assert status == 200
        assert isinstance(body, dict)
        ok("GET / works")
    except Exception as e:
        fail(f"GET / failed: {e}")
        all_ok = False

    try:
        status, body = http_request("GET", "/healthz")
        assert status == 200
        assert isinstance(body, dict)
        assert body.get("status") == "healthy"
        ok("GET /healthz works")
    except Exception as e:
        fail(f"GET /healthz failed: {e}")
        all_ok = False

    tasks = ["easy_refund", "medium_fraud_and_billing", "hard_multi_queue"]
    for task_name in tasks:
        try:
            status, body = http_request("POST", "/reset", {"task_name": task_name})
            assert status == 200
            assert isinstance(body, dict)
            assert "observation" in body and "info" in body
            ok(f"POST /reset works for task={task_name}")
        except Exception as e:
            fail(f"POST /reset failed for task={task_name}: {e}")
            all_ok = False

    try:
        status, body = http_request("POST", "/reset", {"task_name": "easy_refund"})
        assert status == 200
        ok("Reset for easy_refund before /step test")
    except Exception as e:
        fail(f"Could not reset easy_refund before /step test: {e}")
        return False

    try:
        action = {"action_type": "classify", "ticket_id": "T1", "value": "billing"}
        status, body = http_request("POST", "/step", action)
        assert status == 200
        assert isinstance(body, dict)
        assert "reward" in body and "done" in body and "observation" in body
        ok("POST /step works")
    except Exception as e:
        fail(f"POST /step failed: {e}")
        all_ok = False

    try:
        status, body = http_request("GET", "/state")
        assert status == 200
        assert isinstance(body, dict)
        assert "task_name" in body and "tickets" in body
        ok("GET /state works")
    except Exception as e:
        fail(f"GET /state failed: {e}")
        all_ok = False

    return all_ok


def test_docker() -> bool:
    print_header("4. Testing Docker")
    if shutil.which("docker") is None:
        warn("Docker not found. Skipping Docker tests.")
        return True

    image_name = "supportdesk-openenv-test"

    try:
        result = subprocess.run(
            ["docker", "build", "-t", image_name, "."],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            fail("docker build failed")
            print(result.stdout[-2000:])
            print(result.stderr[-2000:])
            return False
        ok("docker build succeeded")
    except Exception as e:
        fail(f"docker build error: {e}")
        return False

    container_name = "supportdesk-openenv-test-container"
    run_proc = None

    try:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            text=True,
        )

        run_proc = subprocess.run(
            ["docker", "run", "-d", "--name", container_name, "-p", "7861:7860", image_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if run_proc.returncode != 0:
            fail("docker run failed")
            print(run_proc.stdout)
            print(run_proc.stderr)
            return False

        ok("docker container started")

        for _ in range(20):
            time.sleep(1)
            try:
                url = "http://127.0.0.1:7861/healthz"
                req = Request(url, method="GET")
                with urlopen(req, timeout=5) as resp:
                    if resp.getcode() == 200:
                        ok("Dockerized server responded on /healthz")
                        return True
            except Exception:
                pass

        fail("Dockerized server did not respond on /healthz")
        return False

    except Exception as e:
        fail(f"Docker runtime test error: {e}")
        return False

    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, text=True)


def test_openenv_validate() -> bool:
    print_header("5. Testing openenv validate")
    if shutil.which("openenv") is None:
        warn("openenv CLI not found. Skipping validator test.")
        warn("Install with: pip install openenv-core")
        return True

    try:
        result = subprocess.run(
            ["openenv", "validate"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            ok("openenv validate passed")
            if result.stdout.strip():
                print(result.stdout.strip())
            return True

        fail("openenv validate failed")
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())
        return False

    except Exception as e:
        fail(f"openenv validate test error: {e}")
        return False


async def main() -> None:
    overall = True

    python_ok = await test_python_api()
    overall = overall and python_ok

    server_proc = start_server()
    if server_proc is None:
        overall = False
    else:
        try:
            http_ok = test_http_endpoints()
            overall = overall and http_ok
        finally:
            stop_server(server_proc)

    docker_ok = test_docker()
    overall = overall and docker_ok

    validate_ok = test_openenv_validate()
    overall = overall and validate_ok

    print_header("FINAL RESULT")
    if overall:
        ok("All available tests passed")
        sys.exit(0)
    else:
        fail("One or more tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())