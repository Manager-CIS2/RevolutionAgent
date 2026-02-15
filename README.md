# RevolutionAgent

Agent 기술 자가 진화 시스템.
개발 중 발생한 에러와 해결법을 Lesson으로 캡처하고, 규칙/스킬 파일에 자동 반영한다.

## 프로젝트 구조

```
RevolutionAgent/
├── revolution/              # Python CLI 패키지
│   ├── __init__.py
│   ├── __main__.py          # 진입점
│   ├── cli.py               # CLI 명령어 라우팅
│   ├── capture.py           # Lesson 캡처
│   ├── analyzer.py          # Lesson 분석 (적용 대상 결정)
│   ├── applier.py           # 규칙/스킬 파일 패치
│   ├── syncer.py            # 양방향 Git 동기화
│   ├── plugins.py           # 플러그인 시스템
│   └── scheduler.py         # 주기적 자동 실행
├── lessons/                 # Lesson JSON 파일 저장소
├── plugins/                 # 사용자 정의 플러그인
├── templates/               # Lesson 템플릿
└── README.md
```

## Quick Start

```powershell
cd "u:\CEO data\GDnano\A. Project\1. AgentDev\RevolutionAgent"

# 현재 상태 확인
python -m revolution status

# 에러 발생 시 Lesson 캡처
python -m revolution capture `
  --error "ModuleNotFoundError: No module named 'xxx'" `
  --solution "pip install xxx" `
  --category "python/dependency" `
  --tags "pip,import"

# 미적용 Lesson 확인 및 적용
python -m revolution list
python -m revolution analyze
python -m revolution apply
```

## 실전 워크플로우

### 에러 발생 -> 해결 -> 학습 사이클

```
에러 발생 ──> capture ──> analyze ──> apply ──> sync
                                                  │
             다른 환경 <── pull <── GitHub <── push
```

**1단계: 에러 캡처**
```powershell
python -m revolution capture `
  -e "TypeError: Cannot read property 'map' of undefined" `
  -s "API 응답이 null일 때 빈 배열로 fallback 처리" `
  -c "js/syntax" `
  -t "react,api,nullcheck"
```

**2단계: 분석**
```powershell
python -m revolution analyze
# 출력: 적용 대상 파일과 분배 확인
```

**3단계: 적용**
```powershell
# 개별 승인
python -m revolution apply

# 전체 자동 적용 (승인 생략)
python -m revolution apply --auto
```

**4단계: 동기화**
```powershell
python -m revolution sync
# pull -> push 양방향 동기화
```

**한 번에 실행**
```powershell
python -m revolution run           # 각 Lesson마다 승인 요청
python -m revolution run --auto    # 전체 자동 실행
```

### 방안 제시 (propose)

미적용 Lesson이 있을 때 대화형으로 처리 방안을 선택할 수 있다.

```powershell
python -m revolution propose
# 1. 전체 자동 적용
# 2. 개별 승인 적용
# 3. 분석만 수행
# 4. 전체 파이프라인
```

---

## 명령어 레퍼런스

| 명령어     | 설명                          | 예시                                |
| :--------- | :---------------------------- | :---------------------------------- |
| `capture`  | 에러/해결법을 Lesson으로 저장 | `-e "에러" -s "해결" -c "카테고리"` |
| `list`     | 미적용 Lesson 목록            | `python -m revolution list`         |
| `analyze`  | 적용 대상 분석 + 추천         | `python -m revolution analyze`      |
| `apply`    | 규칙/스킬 파일에 패치 적용    | `--auto` 옵션으로 자동 승인         |
| `sync`     | 양방향 Git 동기화             | `python -m revolution sync`         |
| `status`   | 전체 상태 요약                | Lesson/Git/스케줄러/플러그인        |
| `run`      | 전체 파이프라인 실행          | sync -> analyze -> apply -> sync    |
| `propose`  | 대화형 방안 제시              | 1~4번 선택                          |
| `schedule` | 스케줄러 관리                 | start/stop/status/register          |
| `plugin`   | 플러그인 관리                 | list/init/remove                    |

---

## 카테고리 맵

Lesson의 카테고리에 따라 적용 대상 파일이 자동 결정된다.

| 카테고리                 | 적용 대상                      |
| :----------------------- | :----------------------------- |
| `python/dependency`      | `rules/coding_guide.md`        |
| `python/syntax`          | `rules/coding_guide.md`        |
| `python/runtime`         | `rules/coding_guide.md`        |
| `js/dependency`          | `rules/coding_guide.md`        |
| `js/syntax`              | `rules/coding_guide.md`        |
| `security/api`           | `rules/safety.md`              |
| `security/auth`          | `rules/safety.md`              |
| `security/injection`     | `rules/safety.md`              |
| `architecture/structure` | `skills/deep_scan/SKILL.md`    |
| `architecture/pattern`   | `skills/deep_scan/SKILL.md`    |
| `testing/unit`           | `skills/browser_test/SKILL.md` |
| `testing/ui`             | `skills/browser_test/SKILL.md` |
| `testing/integration`    | `skills/browser_test/SKILL.md` |
| `workflow/pdca`          | `rules/pdca_workflow.md`       |
| `workflow/git`           | `rules/memory.md`              |
| `interaction/prompt`     | `rules/interaction.md`         |
| `model/config`           | `rules/model_router.md`        |

---

## Agent 스킬 연동

RevolutionAgent는 Antigravity Agent 시스템과 3가지 방식으로 연동된다.

### 1. `/rev` 명령어 (대화 중 수동 호출)
Agent 대화 중 사용자가 `/rev`를 입력하면 revolution 스킬이 활성화된다.
- 유사 에러 검색
- 미적용 Lesson 확인
- 에러 기록 요청

### 2. 자동 트리거 (Agent 판단)
- 코딩 중 에러 발생 시 -> 유사 Lesson 검색 + 자동 캡처
- `/refac` PDCA Check 단계 -> 과거 Lesson 참조
- 새 환경 세팅 시 -> 미적용 Lesson 확인 및 제안

### 3. error_bridge (setup 스크립트 연동)
`antigravity-env/core/error_bridge.py`가 설치/배포 중 발생한 에러를 자동으로 Lesson으로 변환하여 `RevolutionAgent/lessons/`에 저장한다.

```
setup.ps1/setup.sh 에러 -> error_bridge.py -> lessons/*.json
```

---

## 스케줄러

정기적으로 revolution 파이프라인을 자동 실행한다.

```powershell
# 백그라운드 시작 (6시간 간격)
python -m revolution schedule start

# 간격 변경 (12시간)
python -m revolution schedule start --interval 12

# 상태 확인
python -m revolution schedule status

# 중지
python -m revolution schedule stop

# 1회 수동 실행
python -m revolution schedule run-once

# OS 시스템 스케줄러 등록 (Windows: schtasks, Linux/macOS: cron)
python -m revolution schedule register
```

---

## 플러그인

사용자 정의 분석/적용 로직을 플러그인으로 확장할 수 있다.

```powershell
# 플러그인 초기화 (샘플 생성)
python -m revolution plugin init

# 목록 확인
python -m revolution plugin list

# 제거
python -m revolution plugin remove --name sample_plugin
```

### 플러그인 인터페이스

`plugins/` 디렉토리에 `.py` 파일을 추가하면 자동 인식된다.

```python
def info() -> dict:
    return {"name": "my_plugin", "description": "설명", "version": "1.0.0"}

def analyze_hook(lesson: dict) -> dict | None:
    # Lesson 분석 시 추가 로직
    return {"recommendation": "...", "priority": "high"}

def apply_hook(lesson: dict, target: str) -> dict | None:
    # Lesson 적용 시 추가 로직
    return {"action": "log", "message": "적용 완료"}
```

---

## Lesson JSON 형식

```json
{
  "id": "260215-1232_dependency",
  "error": "에러 메시지",
  "solution": "해결 방법",
  "category": "python/dependency",
  "tags": ["pip", "import"],
  "target_rule": "rules/coding_guide.md",
  "target_skill": null,
  "applied": false,
  "applied_at": null,
  "source_env": "Windows:DESKTOP-ABC",
  "created_at": "2026-02-15T03:32:00+00:00"
}
```

---

## 파이프라인 흐름

```
[수동] capture -> lessons/*.json
                      |
              [자동] analyze -> 적용 대상 결정
                      |
              [승인] apply -> ~/.gemini/antigravity/rules/* 또는 skills/* 패치
                      |
              [자동] sync -> Git push (다른 환경에 공유)
                      |
             [다른 환경] pull -> 동일 Lesson + 패치 수신
```
