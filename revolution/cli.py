"""cli.py - RevolutionAgent CLI 진입점.

사용법:
  python -m revolution capture --error "..." --solution "..." --category "..."
  python -m revolution list
  python -m revolution analyze
  python -m revolution apply
  python -m revolution sync
  python -m revolution status
  python -m revolution run
"""

import argparse
import json
import sys
from pathlib import Path

from .capture import create_lesson, list_lessons, VALID_CATEGORIES
from .analyzer import analyze_all, get_analysis_summary
from .applier import apply_all
from .syncer import sync_pull, sync_push, sync_both, get_sync_status


def _project_root() -> Path:
    """RevolutionAgent 프로젝트 루트."""
    return Path(__file__).parent.parent.resolve()


def _lessons_dir() -> Path:
    """lessons/ 디렉토리."""
    return _project_root() / "lessons"


def _repo_root() -> Path:
    """1.AgentDev Git 저장소 루트."""
    return _project_root().parent.resolve()


def _print_line():
    print("=" * 50)


# -- 명령어 핸들러 --

def cmd_capture(args):
    """Lesson 캡처."""
    out = create_lesson(
        error=args.error,
        solution=args.solution,
        category=args.category,
        tags=args.tags.split(",") if args.tags else [],
        lessons_dir=_lessons_dir(),
    )
    _print_line()
    print("  Lesson 캡처 완료")
    _print_line()
    print(f"  파일: {out.name}")
    print(f"  카테고리: {args.category}")
    print(f"  에러: {args.error[:60]}...")
    print(f"  해결: {args.solution[:60]}...")


def cmd_list(args):
    """미적용 Lesson 목록."""
    pending = list_lessons(_lessons_dir(), only_pending=True)
    all_lessons = list_lessons(_lessons_dir(), only_pending=False)

    _print_line()
    print(f"  Lesson 현황 (전체: {len(all_lessons)}, 미적용: {len(pending)})")
    _print_line()

    if not pending:
        print("  미적용 Lesson이 없습니다.")
        return

    for l in pending:
        target = l.get("target_rule") or l.get("target_skill") or "미정"
        print(f"  [{l['id']}] {l['category']}")
        print(f"    에러: {l['error'][:60]}")
        print(f"    대상: {target}")
        print(f"    환경: {l.get('source_env', '?')}")
        print()


def cmd_analyze(args):
    """미적용 Lesson 분석."""
    results = analyze_all(_lessons_dir())
    summary = get_analysis_summary(results)

    _print_line()
    print("  Lesson 분석 결과")
    _print_line()
    print(f"  미적용: {summary['total_pending']}개")
    print(f"  적용 준비: {summary['ready_to_apply']}개")
    print(f"  수동 처리: {summary['needs_manual']}개")
    print()

    if summary["targets"]:
        print("  대상 파일별 분배:")
        for target, ids in summary["targets"].items():
            print(f"    {target}: {len(ids)}개")
            for lid in ids:
                print(f"      - {lid}")
    print()

    if summary["ready_to_apply"] > 0:
        print("  --> 'python -m revolution apply' 로 적용하세요.")


def cmd_apply(args):
    """Lesson 적용 (사용자 승인 후)."""
    auto = getattr(args, 'auto', False)
    results = apply_all(_lessons_dir(), auto_approve=auto)

    _print_line()
    print("  Lesson 적용 결과")
    _print_line()

    success = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    for r in success:
        print(f"  [OK] {r['id']} --> {r['target']} (+{r['lines_added']}줄)")
        print(f"       백업: {Path(r['backup']).name}")

    for r in failed:
        print(f"  [FAIL] {r['id']}: {r.get('reason', '?')}")

    print()
    print(f"  성공: {len(success)}개, 실패: {len(failed)}개")

    if success:
        print("  --> 'python -m revolution sync' 로 동기화하세요.")


def cmd_sync(args):
    """양방향 Git 동기화."""
    repo = _repo_root()

    _print_line()
    print("  양방향 동기화")
    _print_line()

    result = sync_both(repo)

    print(f"  Pull: {result['pull']['message']}")
    print(f"  Push: {result['push']['message']}" if result["push"] else "  Push: 건너뜀")
    print(f"  결과: {'완료' if result['success'] else '실패'}")


def cmd_status(args):
    """전체 상태 요약."""
    all_lessons = list_lessons(_lessons_dir(), only_pending=False)
    pending = [l for l in all_lessons if not l.get("applied")]
    applied = [l for l in all_lessons if l.get("applied")]
    sync_stat = get_sync_status(_repo_root())

    _print_line()
    print("  RevolutionAgent 상태")
    _print_line()
    print(f"  Lesson 전체: {len(all_lessons)}개")
    print(f"    적용 완료: {len(applied)}개")
    print(f"    미적용: {len(pending)}개")
    print()
    print(f"  Git 저장소: {'연결됨' if sync_stat.get('is_repo') else '없음'}")
    if sync_stat.get("is_repo"):
        print(f"    브랜치: {sync_stat.get('branch')}")
        print(f"    리모트: {sync_stat.get('remote')}")
        print(f"    미커밋 변경: {sync_stat.get('pending_changes')}개")

    # 카테고리별 통계
    if all_lessons:
        print()
        print("  카테고리별 분포:")
        cats = {}
        for l in all_lessons:
            c = l.get("category", "?")
            cats[c] = cats.get(c, 0) + 1
        for c, n in sorted(cats.items()):
            print(f"    {c}: {n}개")


def cmd_run(args):
    """전체 파이프라인 한 번에 실행.

    sync(pull) --> analyze --> apply --> sync(push)
    """
    repo = _repo_root()

    _print_line()
    print("  Revolution 전체 파이프라인 실행")
    _print_line()

    # 1. Pull
    print("\n  [1/4] Pull (다른 환경 변경사항 수신)...")
    pull = sync_pull(repo)
    print(f"    {pull['message']}")
    if not pull["success"]:
        print("    파이프라인 중단.")
        return

    # 2. Analyze
    print("\n  [2/4] Analyze (미적용 Lesson 분석)...")
    results = analyze_all(_lessons_dir())
    summary = get_analysis_summary(results)
    print(f"    미적용: {summary['total_pending']}개")
    print(f"    적용 준비: {summary['ready_to_apply']}개")

    if summary["ready_to_apply"] == 0:
        print("    적용할 Lesson이 없습니다.")
        return

    # 3. Apply (사용자 승인)
    print("\n  [3/4] Apply (규칙/스킬에 패치 적용)...")
    auto = getattr(args, 'auto', False)
    apply_results = apply_all(_lessons_dir(), auto_approve=auto)
    success = [r for r in apply_results if r.get("success")]
    failed = [r for r in apply_results if not r.get("success")]
    print(f"    성공: {len(success)}개, 실패: {len(failed)}개")
    for r in success:
        print(f"      [OK] {r['id']} --> {r['target']}")
    for r in failed:
        print(f"      [FAIL] {r['id']}: {r.get('reason')}")

    # 4. Push
    print("\n  [4/4] Push (변경사항 공유)...")
    push = sync_push(repo, "[revolution] auto-apply lessons")
    print(f"    {push['message']}")

    print()
    _print_line()
    print("  파이프라인 완료")
    _print_line()


def main():
    parser = argparse.ArgumentParser(
        description="RevolutionAgent - Agent 기술 자가 진화 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  capture   에러/해결법을 Lesson으로 캡처
  list      미적용 Lesson 목록
  analyze   Lesson 분석 (적용 대상 추천)
  apply     분석된 Lesson을 규칙/스킬에 적용
  sync      양방향 Git 동기화
  status    전체 상태 요약
  run       전체 파이프라인 실행 (sync->analyze->apply->sync)

categories:
  """ + "\n  ".join(VALID_CATEGORIES),
    )
    sub = parser.add_subparsers(dest="command", help="실행할 명령")

    # capture
    cap = sub.add_parser("capture", help="Lesson 캡처")
    cap.add_argument("--error", "-e", required=True, help="에러 메시지")
    cap.add_argument("--solution", "-s", required=True, help="해결 방법")
    cap.add_argument("--category", "-c", required=True, help="카테고리")
    cap.add_argument("--tags", "-t", help="태그 (쉼표 구분)")

    sub.add_parser("list", help="미적용 Lesson 목록")
    sub.add_parser("analyze", help="Lesson 분석")

    apply_p = sub.add_parser("apply", help="Lesson 적용 (사용자 승인)")
    apply_p.add_argument("--auto", action="store_true", help="승인 없이 자동 적용")

    sub.add_parser("sync", help="양방향 동기화")
    sub.add_parser("status", help="전체 상태")

    run_p = sub.add_parser("run", help="전체 파이프라인 실행")
    run_p.add_argument("--auto", action="store_true", help="승인 없이 자동 적용")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    handlers = {
        "capture": cmd_capture,
        "list": cmd_list,
        "analyze": cmd_analyze,
        "apply": cmd_apply,
        "sync": cmd_sync,
        "status": cmd_status,
        "run": cmd_run,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
