"""applier.py - 규칙/스킬 파일 패치 모듈.

분석된 Lesson을 실제 규칙/스킬 파일에 반영한다.
패치 전 .bak 백업을 생성하고, 1000라인 제한을 체크한다.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .capture import CATEGORY_MAP, list_lessons
from .analyzer import analyze_lesson


# Antigravity 설정 디렉토리
def _gemini_dir() -> Path:
    """~/.gemini/antigravity/ 경로."""
    return Path.home() / ".gemini" / "antigravity"


MAX_LINES = 1000


def _backup_file(target: Path) -> Path:
    """패치 전 백업 파일 생성.

    Args:
        target: 백업할 파일 경로.

    Returns:
        백업 파일 경로.
    """
    bak = target.with_suffix(target.suffix + ".bak")
    shutil.copy2(target, bak)
    return bak


def _build_patch_block(lesson: dict) -> str:
    """Lesson을 규칙/스킬 파일에 추가할 텍스트 블록으로 변환.

    Args:
        lesson: Lesson dict.

    Returns:
        추가할 텍스트 블록.
    """
    lines = []
    lines.append("")
    lines.append(f"- **[Revolution {lesson['id']}]** `{lesson['category']}`:")
    lines.append(f"  - 문제: {lesson['error']}")
    lines.append(f"  - 해결: {lesson['solution']}")
    if lesson.get("tags"):
        tags_str = ", ".join(lesson["tags"])
        lines.append(f"  - 태그: {tags_str}")
    return "\n".join(lines) + "\n"


def apply_lesson(lesson: dict, gemini_dir: Path = None) -> dict:
    """단일 Lesson을 대상 파일에 적용한다.

    Args:
        lesson: Lesson dict.
        gemini_dir: ~/.gemini/antigravity/ 경로.

    Returns:
        적용 결과 dict.
    """
    if not gemini_dir:
        gemini_dir = _gemini_dir()

    analysis = analyze_lesson(lesson)
    if not analysis["ready"]:
        return {
            "id": lesson["id"],
            "success": False,
            "reason": "적용 대상을 결정할 수 없습니다.",
        }

    target_rel = analysis["target"]
    target_path = gemini_dir / target_rel

    if not target_path.exists():
        return {
            "id": lesson["id"],
            "success": False,
            "reason": f"대상 파일 없음: {target_rel}",
        }

    # 라인 수 체크
    content = target_path.read_text(encoding="utf-8")
    current_lines = len(content.splitlines())
    patch = _build_patch_block(lesson)
    patch_lines = len(patch.splitlines())

    if current_lines + patch_lines > MAX_LINES:
        return {
            "id": lesson["id"],
            "success": False,
            "reason": f"1000라인 초과 ({current_lines} + {patch_lines})",
        }

    # 백업 생성
    bak = _backup_file(target_path)

    # 패치 적용 (파일 끝에 추가)
    with open(target_path, "a", encoding="utf-8") as f:
        f.write(patch)

    return {
        "id": lesson["id"],
        "success": True,
        "target": target_rel,
        "backup": str(bak),
        "lines_added": patch_lines,
    }


def mark_applied(lesson: dict) -> None:
    """Lesson 파일에 applied: true 기록.

    Args:
        lesson: Lesson dict (_path 키 필수).
    """
    path = lesson.get("_path")
    if not path:
        return

    lesson_path = Path(path)
    if not lesson_path.exists():
        return

    data = json.loads(lesson_path.read_text(encoding="utf-8"))
    data["applied"] = True
    data["applied_at"] = datetime.now(timezone.utc).isoformat()

    lesson_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _prompt_approve(lesson: dict, analysis: dict) -> bool:
    """사용자에게 Lesson 적용 승인을 요청한다.

    Args:
        lesson: Lesson dict.
        analysis: 분석 결과 dict.

    Returns:
        승인 여부.
    """
    print(f"\n  --- Lesson 적용 승인 요청 ---")
    print(f"  ID: {lesson['id']}")
    print(f"  카테고리: {lesson['category']}")
    print(f"  에러: {lesson['error'][:80]}")
    print(f"  해결: {lesson['solution'][:80]}")
    print(f"  대상: {analysis['target']}")
    try:
        answer = input("  적용할까요? (y/n): ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def apply_all(
    lessons_dir: Path = None,
    gemini_dir: Path = None,
    auto_approve: bool = False,
) -> list:
    """모든 미적용 Lesson을 적용한다.

    Args:
        lessons_dir: lessons/ 디렉토리 경로.
        gemini_dir: ~/.gemini/antigravity/ 경로.
        auto_approve: True면 사용자 확인 없이 자동 적용.

    Returns:
        적용 결과 목록.
    """
    pending = list_lessons(lessons_dir, only_pending=True)
    results = []

    for lesson in pending:
        analysis = analyze_lesson(lesson)
        if not analysis["ready"]:
            results.append({
                "id": lesson["id"],
                "success": False,
                "reason": "수동 처리 필요",
            })
            continue

        # 사용자 승인 절차
        if not auto_approve:
            if not _prompt_approve(lesson, analysis):
                results.append({
                    "id": lesson["id"],
                    "success": False,
                    "reason": "사용자가 거부함",
                })
                continue

        result = apply_lesson(lesson, gemini_dir)
        if result["success"]:
            mark_applied(lesson)
        results.append(result)

    return results
