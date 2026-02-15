"""syncer.py - 양방향 Git 동기화 모듈.

모든 개발 환경이 Lesson 제공자이자 수신자로 동작한다.
- Pull: 다른 환경의 Lesson + 적용된 규칙/스킬 수신
- Push: 로컬 Lesson + 패치를 공유
"""

import subprocess
import sys
from pathlib import Path


def _run_git(args: list, cwd: Path) -> dict:
    """Git 명령 실행.

    Args:
        args: git 인자 리스트.
        cwd: 작업 디렉토리.

    Returns:
        실행 결과 dict.
    """
    cmd = ["git"] + args
    try:
        r = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "success": r.returncode == 0,
            "stdout": r.stdout.strip(),
            "stderr": r.stderr.strip(),
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "git not found",
        }


def _is_git_repo(path: Path) -> bool:
    """Git 저장소인지 확인."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], path)
    return result["success"]


def sync_pull(repo_path: Path) -> dict:
    """원격에서 최신 변경사항 pull.

    다른 환경이 올린 Lesson + 적용된 규칙/스킬을 수신한다.

    Args:
        repo_path: Git 저장소 경로.

    Returns:
        pull 결과 dict.
    """
    if not _is_git_repo(repo_path):
        return {"success": False, "message": "Git 저장소가 아닙니다."}

    result = _run_git(["pull", "--rebase"], repo_path)
    if result["success"]:
        return {
            "success": True,
            "message": "pull 완료",
            "output": result["stdout"],
        }
    return {
        "success": False,
        "message": "pull 실패",
        "error": result["stderr"],
    }


def sync_push(repo_path: Path, message: str = None) -> dict:
    """로컬 변경사항을 원격에 push.

    로컬에서 캡처한 Lesson + 적용한 패치를 공유한다.

    Args:
        repo_path: Git 저장소 경로.
        message: 커밋 메시지.

    Returns:
        push 결과 dict.
    """
    if not _is_git_repo(repo_path):
        return {"success": False, "message": "Git 저장소가 아닙니다."}

    # 변경사항 확인
    status = _run_git(["status", "--porcelain"], repo_path)
    if not status["stdout"]:
        return {"success": True, "message": "변경사항 없음."}

    # Stage all
    add_result = _run_git(["add", "-A"], repo_path)
    if not add_result["success"]:
        return {"success": False, "message": "staging 실패", "error": add_result["stderr"]}

    # Commit
    if not message:
        message = "[revolution] auto-sync lessons and patches"
    commit_result = _run_git(["commit", "-m", message], repo_path)
    if not commit_result["success"]:
        return {"success": False, "message": "commit 실패", "error": commit_result["stderr"]}

    # Push
    push_result = _run_git(["push"], repo_path)
    if push_result["success"]:
        return {
            "success": True,
            "message": "push 완료",
            "output": push_result["stdout"],
        }
    return {
        "success": False,
        "message": "push 실패",
        "error": push_result["stderr"],
    }


def sync_both(repo_path: Path, message: str = None) -> dict:
    """양방향 동기화: pull -> push.

    Args:
        repo_path: Git 저장소 경로.
        message: 커밋 메시지.

    Returns:
        동기화 결과 dict.
    """
    # 1. Pull (다른 환경 변경사항 수신)
    pull = sync_pull(repo_path)
    if not pull["success"]:
        return {
            "success": False,
            "phase": "pull",
            "pull": pull,
            "push": None,
        }

    # 2. Push (로컬 변경사항 공유)
    push = sync_push(repo_path, message)

    return {
        "success": push["success"],
        "phase": "complete",
        "pull": pull,
        "push": push,
    }


def get_sync_status(repo_path: Path) -> dict:
    """동기화 상태 조회.

    Args:
        repo_path: Git 저장소 경로.

    Returns:
        상태 정보 dict.
    """
    if not _is_git_repo(repo_path):
        return {"is_repo": False}

    branch = _run_git(["branch", "--show-current"], repo_path)
    remote = _run_git(["remote", "get-url", "origin"], repo_path)
    status = _run_git(["status", "--porcelain"], repo_path)

    changes = status["stdout"].splitlines() if status["stdout"] else []

    return {
        "is_repo": True,
        "branch": branch["stdout"],
        "remote": remote["stdout"],
        "pending_changes": len(changes),
        "clean": len(changes) == 0,
    }
