# RevolutionAgent

Antigravity Agent 기술 자가 진화 시스템.

개발 중 발생한 에러와 해결법을 학습 데이터(Lesson)로 캡처하고,
Agent의 규칙/스킬 파일에 자동 반영하여 모든 개발 환경에 배포한다.

## 사용법

```bash
# Lesson 캡처
python -m revolution capture \
  --error "ModuleNotFoundError: No module named 'xxx'" \
  --solution "pip install xxx" \
  --category "python/dependency" \
  --tags "pip,import"

# 미적용 Lesson 목록
python -m revolution list

# Lesson 분석 (적용 대상 추천)
python -m revolution analyze

# 규칙/스킬에 적용
python -m revolution apply

# 양방향 Git 동기화
python -m revolution sync

# 전체 상태
python -m revolution status

# 전체 파이프라인 한 번에 실행
python -m revolution run
```

## 파이프라인

```
에러 발생 --> capture --> analyze --> apply --> sync
                                                |
              다른 환경 <-- pull <-- GitHub <-- push
```

`run` 명령은 전체를 한 번에 실행:
```
sync(pull) --> analyze --> apply --> sync(push)
```

## 카테고리

| 카테고리               | 적용 대상                    |
| :--------------------- | :--------------------------- |
| python/dependency      | rules/coding_guide.md        |
| python/syntax          | rules/coding_guide.md        |
| python/runtime         | rules/coding_guide.md        |
| js/dependency          | rules/coding_guide.md        |
| js/syntax              | rules/coding_guide.md        |
| security/api           | rules/safety.md              |
| security/auth          | rules/safety.md              |
| security/injection     | rules/safety.md              |
| architecture/structure | skills/deep_scan/SKILL.md    |
| architecture/pattern   | skills/deep_scan/SKILL.md    |
| testing/unit           | skills/browser_test/SKILL.md |
| testing/ui             | skills/browser_test/SKILL.md |
| testing/integration    | skills/browser_test/SKILL.md |
| workflow/pdca          | rules/pdca_workflow.md       |
| workflow/git           | rules/memory.md              |
| interaction/prompt     | rules/interaction.md         |
| model/config           | rules/model_router.md        |
