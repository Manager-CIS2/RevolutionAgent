"""analyzer.py - Lesson 분석 + 적용 대상 결정 모듈.

미적용 Lesson을 분석하여 어떤 규칙/스킬 파일에 반영할지 결정한다.
"""

import json
from pathlib import Path

from .capture import CATEGORY_MAP, list_lessons


def analyze_lesson(lesson: dict) -> dict:
    """단일 Lesson을 분석하여 적용 정보를 보강한다.

    Args:
        lesson: Lesson dict.

    Returns:
        분석 결과가 추가된 Lesson dict.
    """
    category = lesson.get("category", "")
    target = CATEGORY_MAP.get(category)

    result = {
        "id": lesson.get("id"),
        "category": category,
        "target": target,
        "target_type": None,
        "action": "append",
        "ready": False,
    }

    if target:
        if target.startswith("skills/"):
            result["target_type"] = "skill"
        else:
            result["target_type"] = "rule"
        result["ready"] = True
    else:
        result["target_type"] = "unknown"
        result["action"] = "manual"

    return result


def analyze_all(lessons_dir: Path = None) -> list:
    """모든 미적용 Lesson을 분석한다.

    Args:
        lessons_dir: lessons/ 디렉토리 경로.

    Returns:
        분석 결과 목록.
    """
    pending = list_lessons(lessons_dir, only_pending=True)
    results = []

    for lesson in pending:
        analysis = analyze_lesson(lesson)
        analysis["error_preview"] = lesson.get("error", "")[:80]
        analysis["solution_preview"] = lesson.get("solution", "")[:80]
        results.append(analysis)

    return results


def get_analysis_summary(results: list) -> dict:
    """분석 결과 요약.

    Args:
        results: analyze_all 결과.

    Returns:
        요약 dict.
    """
    total = len(results)
    ready = sum(1 for r in results if r["ready"])
    manual = total - ready

    # 대상 파일별 그룹핑
    targets = {}
    for r in results:
        t = r.get("target") or "unknown"
        targets.setdefault(t, []).append(r["id"])

    return {
        "total_pending": total,
        "ready_to_apply": ready,
        "needs_manual": manual,
        "targets": targets,
    }
