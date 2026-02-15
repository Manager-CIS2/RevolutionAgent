"""scheduler.py - RevolutionAgent 주기적 실행 스케줄러.

독립적으로 revolution 파이프라인을 주기적으로 실행하여
Agent가 자동으로 진화하도록 한다.

사용법:
  python -m revolution schedule start [--interval 6]
  python -m revolution schedule stop
  python -m revolution schedule status
  python -m revolution schedule register
"""

import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INTERVAL_HOURS = 6
LOG_FILE = "scheduler_log.json"


def _project_root() -> Path:
    return Path(__file__).parent.parent.resolve()


def _log_path() -> Path:
    return _project_root() / "lessons" / LOG_FILE


def _pid_path() -> Path:
    return _project_root() / ".scheduler.pid"


def _load_log() -> list:
    lp = _log_path()
    if lp.exists():
        try:
            return json.loads(lp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_log(entries: list) -> None:
    lp = _log_path()
    lp.parent.mkdir(parents=True, exist_ok=True)
    # 최근 100건만 보관
    entries = entries[-100:]
    lp.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_pipeline(auto: bool = True) -> dict:
    """revolution run 파이프라인을 subprocess로 실행."""
    cmd = [sys.executable, "-m", "revolution", "run"]
    if auto:
        cmd.append("--auto")

    try:
        r = subprocess.run(
            cmd,
            cwd=str(_project_root()),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        return {
            "success": r.returncode == 0,
            "output": r.stdout[-500:] if r.stdout else "",
            "error": r.stderr[-200:] if r.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": "timeout (300s)"}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


def run_once() -> dict:
    """파이프라인 1회 실행 + 로그 기록."""
    entry = {
        "timestamp": _now_iso(),
        "env": f"{platform.system()}:{platform.node()}",
    }

    result = _run_pipeline(auto=True)
    entry["success"] = result["success"]
    entry["output_tail"] = result["output"][-200:]
    if result["error"]:
        entry["error"] = result["error"]

    log = _load_log()
    log.append(entry)
    _save_log(log)

    return entry


def start_loop(interval_hours: float = DEFAULT_INTERVAL_HOURS) -> None:
    """주기적 실행 루프 (foreground)."""
    interval_sec = interval_hours * 3600
    pid = os.getpid()

    # PID 파일 기록
    _pid_path().write_text(str(pid), encoding="utf-8")

    print(f"  [scheduler] 시작 (PID: {pid}, 간격: {interval_hours}h)")
    print(f"  [scheduler] 종료: Ctrl+C 또는 'python -m revolution schedule stop'")

    try:
        while True:
            print(f"\n  [scheduler] 파이프라인 실행 ({_now_iso()})...")
            entry = run_once()
            status = "성공" if entry["success"] else "실패"
            print(f"  [scheduler] 결과: {status}")
            print(f"  [scheduler] 다음 실행: {interval_hours}시간 후")
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        print("\n  [scheduler] 중지됨.")
    finally:
        pp = _pid_path()
        if pp.exists():
            pp.unlink()


def start_background(interval_hours: float = DEFAULT_INTERVAL_HOURS) -> dict:
    """스케줄러를 백그라운드 프로세스로 시작."""
    if is_running():
        return {"success": False, "message": "이미 실행 중입니다."}

    cmd = [
        sys.executable, "-m", "revolution", "schedule", "start",
        "--interval", str(interval_hours),
        "--foreground",
    ]

    if platform.system() == "Windows":
        # Windows: CREATE_NO_WINDOW
        creation_flags = 0x08000000
        proc = subprocess.Popen(
            cmd,
            cwd=str(_project_root()),
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_project_root()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    # PID 기록
    _pid_path().write_text(str(proc.pid), encoding="utf-8")

    return {
        "success": True,
        "pid": proc.pid,
        "interval": interval_hours,
        "message": f"스케줄러 시작 (PID: {proc.pid}, 간격: {interval_hours}h)",
    }


def stop() -> dict:
    """실행 중인 스케줄러 중지."""
    pp = _pid_path()
    if not pp.exists():
        return {"success": False, "message": "실행 중인 스케줄러가 없습니다."}

    try:
        pid = int(pp.read_text(encoding="utf-8").strip())
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
            )
        else:
            os.kill(pid, 9)
        pp.unlink()
        return {"success": True, "message": f"스케줄러 중지됨 (PID: {pid})"}
    except (ProcessLookupError, PermissionError, ValueError) as e:
        if pp.exists():
            pp.unlink()
        return {"success": False, "message": f"중지 실패: {e}"}


def is_running() -> bool:
    """스케줄러 실행 여부 확인."""
    pp = _pid_path()
    if not pp.exists():
        return False

    try:
        pid = int(pp.read_text(encoding="utf-8").strip())
        if platform.system() == "Windows":
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
            )
            return str(pid) in r.stdout
        else:
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, PermissionError, ValueError, OSError):
        pp.unlink(missing_ok=True)
        return False


def get_status() -> dict:
    """스케줄러 상태 조회."""
    running = is_running()
    pid = None
    if running:
        try:
            pid = int(_pid_path().read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass

    log = _load_log()
    last_run = log[-1] if log else None

    return {
        "running": running,
        "pid": pid,
        "total_runs": len(log),
        "last_run": last_run,
        "success_rate": (
            f"{sum(1 for e in log if e.get('success')) / len(log) * 100:.0f}%"
            if log else "N/A"
        ),
    }


def generate_register_script() -> str:
    """OS별 시스템 스케줄러 등록 스크립트 생성."""
    python = sys.executable
    project = str(_project_root())

    if platform.system() == "Windows":
        return (
            f'schtasks /Create /SC DAILY /TN "RevolutionAgent" '
            f'/TR "\\"{python}\\" -m revolution schedule start --foreground" '
            f'/ST 06:00 /RI 360 /DU 24:00 /F'
        )
    elif platform.system() == "Darwin":
        return (
            f"# crontab -e 후 아래 추가:\n"
            f"0 */6 * * * cd {project} && {python} -m revolution run --auto"
        )
    else:
        return (
            f"# crontab -e 후 아래 추가:\n"
            f"0 */6 * * * cd {project} && {python} -m revolution run --auto"
        )
