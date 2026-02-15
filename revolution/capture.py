"""capture.py - Lesson 캡처 모듈.

개발 중 발생한 에러와 해결법을 학습 데이터(Lesson)로 저장한다.
"""

import json
import platform
from datetime import datetime, timezone
from pathlib import Path


# 카테고리 -> 적용 대상 매핑
CATEGORY_MAP = {
    "python/dependency": "rules/coding_guide.md",
    "python/syntax": "rules/coding_guide.md",
    "python/runtime": "rules/coding_guide.md",
    "js/dependency": "rules/coding_guide.md",
    "js/syntax": "rules/coding_guide.md",
    "security/api": "rules/safety.md",
    "security/auth": "rules/safety.md",
    "security/injection": "rules/safety.md",
    "architecture/structure": "skills/deep_scan/SKILL.md",
    "architecture/pattern": "skills/deep_scan/SKILL.md",
    "testing/unit": "skills/browser_test/SKILL.md",
    "testing/ui": "skills/browser_test/SKILL.md",
    "testing/integration": "skills/browser_test/SKILL.md",
    "workflow/pdca": "rules/pdca_workflow.md",
    "workflow/git": "rules/memory.md",
    "interaction/prompt": "rules/interaction.md",
    "model/config": "rules/model_router.md",
}

# 유효한 카테고리 목록
VALID_CATEGORIES = sorted(CATEGORY_MAP.keys())


def _now_id() -> str:
    """YYMMDD-HHMM 형식의 ID 생성."""
    now = datetime.now()
    return now.strftime("%y%m%d-%H%M")


def _now_iso() -> str:
    """ISO 형식 타임스탬프."""
    return datetime.now(timezone.utc).isoformat()


def _env_name() -> str:
    """현재 환경 식별자 (OS + hostname)."""
    return f"{platform.system()}:{platform.node()}"


def create_lesson(
    error: str,
    solution: str,
    category: str,
    tags: list = None,
    lessons_dir: Path = None,
) -> Path:
    """Lesson을 JSON 파일로 저장한다.

    Args:
        error: 에러 메시지 또는 문제 설명.
        solution: 해결 방법.
        category: 카테고리 (예: "python/dependency").
        tags: 태그 목록 (선택).
        lessons_dir: lessons/ 디렉토리 경로.

    Returns:
        생성된 Lesson 파일 경로.
    """
    if not lessons_dir:
        lessons_dir = Path(__file__).parent.parent / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    # 카테고리 유효성 검증
    if category not in CATEGORY_MAP:
        print(f"  [WARN] 알 수 없는 카테고리: {category}")
        print(f"  사용 가능: {', '.join(VALID_CATEGORIES)}")

    # 주제 추출 (카테고리의 마지막 부분)
    topic = category.split("/")[-1] if "/" in category else category
    lesson_id = f"{_now_id()}_{topic}"

    lesson = {
        "id": lesson_id,
        "error": error,
        "solution": solution,
        "category": category,
        "tags": tags or [],
        "target_rule": CATEGORY_MAP.get(category),
        "target_skill": None,
        "applied": False,
        "applied_at": None,
        "source_env": _env_name(),
        "created_at": _now_iso(),
    }

    # 스킬 대상인 경우 분리
    target = CATEGORY_MAP.get(category, "")
    if target.startswith("skills/"):
        lesson["target_skill"] = target
        lesson["target_rule"] = None

    out = lessons_dir / f"{lesson_id}.json"
    out.write_text(
        json.dumps(lesson, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


def list_lessons(lessons_dir: Path = None, only_pending: bool = True) -> list:
    """Lesson 목록 반환.

    Args:
        lessons_dir: lessons/ 디렉토리 경로.
        only_pending: True이면 미적용 Lesson만 반환.

    Returns:
        Lesson dict 목록.
    """
    if not lessons_dir:
        lessons_dir = Path(__file__).parent.parent / "lessons"
    if not lessons_dir.exists():
        return []

    lessons = []
    for f in sorted(lessons_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if only_pending and data.get("applied"):
                continue
            data["_path"] = str(f)
            lessons.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return lessons
