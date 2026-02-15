"""plugins.py - 사용자 정의 플러그인 시스템.

RevolutionAgent에 사용자가 특수 목적의 기능을 부가할 수 있도록
플러그인 로더/관리자를 제공한다.

플러그인 디렉토리: RevolutionAgent/plugins/
플러그인 파일: *.py (이름이 _ 로 시작하지 않는 것)

플러그인 인터페이스:
  def analyze_hook(lesson: dict) -> dict | None
  def apply_hook(lesson: dict, target: str) -> dict | None
  def info() -> dict  # name, description, version
"""

import importlib.util
import json
import sys
from pathlib import Path


def _plugins_dir() -> Path:
    return Path(__file__).parent.parent.resolve() / "plugins"


def _manifest_path() -> Path:
    return _plugins_dir() / "manifest.json"


def ensure_plugins_dir() -> Path:
    """plugins/ 디렉토리 및 __init__.py 생성."""
    d = _plugins_dir()
    d.mkdir(parents=True, exist_ok=True)
    init = d / "__init__.py"
    if not init.exists():
        init.write_text("# RevolutionAgent plugins\n", encoding="utf-8")
    return d


def discover_plugins() -> list:
    """plugins/ 디렉토리에서 플러그인 파일 탐색.

    Returns:
        플러그인 정보 목록.
    """
    d = _plugins_dir()
    if not d.exists():
        return []

    plugins = []
    for f in sorted(d.glob("*.py")):
        if f.name.startswith("_"):
            continue
        info = _load_plugin_info(f)
        if info:
            plugins.append(info)
    return plugins


def _load_plugin_info(path: Path) -> dict:
    """플러그인 파일에서 info() 호출하여 메타데이터 반환."""
    try:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        info = {}
        if hasattr(mod, "info"):
            info = mod.info()
        else:
            info = {"name": path.stem, "description": "(info 미정의)"}

        info["file"] = path.name
        info["has_analyze"] = hasattr(mod, "analyze_hook")
        info["has_apply"] = hasattr(mod, "apply_hook")

        return info
    except Exception as e:
        return {
            "name": path.stem,
            "file": path.name,
            "description": f"(로드 실패: {e})",
            "has_analyze": False,
            "has_apply": False,
            "error": str(e),
        }


def load_plugin(name: str):
    """플러그인 모듈을 로드하여 반환.

    Args:
        name: 플러그인 이름 (파일명에서 .py 제외).

    Returns:
        로드된 모듈 또는 None.
    """
    path = _plugins_dir() / f"{name}.py"
    if not path.exists():
        return None

    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def run_analyze_hooks(lesson: dict, plugins: list = None) -> list:
    """모든 플러그인의 analyze_hook을 실행.

    Args:
        lesson: 분석할 Lesson dict.
        plugins: 플러그인 이름 목록 (None이면 전체).

    Returns:
        각 플러그인의 분석 결과 목록.
    """
    results = []
    discovered = discover_plugins()

    for info in discovered:
        if plugins and info["name"] not in plugins:
            continue
        if not info.get("has_analyze"):
            continue

        mod = load_plugin(info["name"])
        if mod and hasattr(mod, "analyze_hook"):
            try:
                result = mod.analyze_hook(lesson)
                if result:
                    result["plugin"] = info["name"]
                    results.append(result)
            except Exception as e:
                results.append({
                    "plugin": info["name"],
                    "error": str(e),
                })

    return results


def run_apply_hooks(lesson: dict, target: str, plugins: list = None) -> list:
    """모든 플러그인의 apply_hook을 실행.

    Args:
        lesson: 적용할 Lesson dict.
        target: 적용 대상 파일 경로.
        plugins: 플러그인 이름 목록 (None이면 전체).

    Returns:
        각 플러그인의 적용 결과 목록.
    """
    results = []
    discovered = discover_plugins()

    for info in discovered:
        if plugins and info["name"] not in plugins:
            continue
        if not info.get("has_apply"):
            continue

        mod = load_plugin(info["name"])
        if mod and hasattr(mod, "apply_hook"):
            try:
                result = mod.apply_hook(lesson, target)
                if result:
                    result["plugin"] = info["name"]
                    results.append(result)
            except Exception as e:
                results.append({
                    "plugin": info["name"],
                    "error": str(e),
                })

    return results


def create_sample_plugin() -> Path:
    """샘플 플러그인 파일을 생성."""
    d = ensure_plugins_dir()
    sample = d / "sample_plugin.py"
    if sample.exists():
        return sample

    sample.write_text('''"""sample_plugin.py - RevolutionAgent 샘플 플러그인.

플러그인 인터페이스 구현 예시.
이 파일을 복사하여 새 플러그인을 만들 수 있다.
"""


def info() -> dict:
    """플러그인 메타데이터."""
    return {
        "name": "sample_plugin",
        "description": "샘플 플러그인 (참고용)",
        "version": "1.0.0",
        "author": "user",
    }


def analyze_hook(lesson: dict) -> dict:
    """Lesson 분석 시 호출되는 훅.

    Args:
        lesson: Lesson dict.

    Returns:
        추가 분석 결과 dict. None 반환 시 무시됨.
    """
    # 사용자 정의 분석 로직을 여기에 작성
    return {
        "recommendation": "이 Lesson은 추가 검토가 필요합니다.",
        "priority": "normal",
    }


def apply_hook(lesson: dict, target: str) -> dict:
    """Lesson 적용 시 호출되는 훅.

    Args:
        lesson: 적용할 Lesson dict.
        target: 적용 대상 파일 경로.

    Returns:
        적용 결과 dict. None 반환 시 무시됨.
    """
    # 사용자 정의 적용 로직을 여기에 작성
    return {
        "action": "log",
        "message": f"Lesson {lesson.get('id')} applied to {target}",
    }
''', encoding="utf-8")
    return sample


def list_plugins_formatted() -> str:
    """포맷된 플러그인 목록 문자열."""
    plugins = discover_plugins()
    if not plugins:
        return "  설치된 플러그인이 없습니다.\n  'python -m revolution plugin init'로 샘플을 생성하세요."

    lines = []
    for p in plugins:
        status = []
        if p.get("has_analyze"):
            status.append("analyze")
        if p.get("has_apply"):
            status.append("apply")
        hooks = ", ".join(status) if status else "없음"

        lines.append(f"  [{p['name']}] {p.get('description', '')}")
        lines.append(f"    파일: {p['file']} | 훅: {hooks}")
        if p.get("error"):
            lines.append(f"    [ERROR] {p['error']}")
        lines.append("")

    return "\n".join(lines)
