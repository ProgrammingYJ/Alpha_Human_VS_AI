"""Record completed desktop/liveness evidence without private room data."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
read = lambda name: json.loads((root / name).read_text(encoding="utf-8-sig"))
local = read("runs/desktop-liveness-local-v1/verification.json")
public = read("runs/desktop-liveness-public-v1/verification.json")
release = read("runs/site-publish/desktop-release.json")
runtime = read("runs/site-publish/desktop-current-engine.json")
startup = read(runtime["startup_path"])
assert local["passed"] and public["passed"] and all(public["checks"].values())
assert release["status"] == "succeeded" and runtime["kept_running"] and startup["models_loaded_once"]
rows = [read("runs/desktop-liveness-public-v1/" + name) for name in (
    "lane-A-game-1.json", "lane-A-game-2.json", "lane-B-game-1.json")]
gaps = [later["sent_seconds"] - earlier["ack_seconds"] for row in rows
        for earlier, later in zip(row["selection_events"], row["selection_events"][1:])]
selected = [row["selected_indices"] for row in rows]
body = f'''## 현재 결론 (2026-10-27, 버전8)

**최신 운영 화면은 컴퓨터 브라우저다.** 사용자 요청으로 이전 Android4대 계획을 대체했다. 인간은 컴퓨터 마우스로 선택하고 AI 표시 브라우저는 PC 모델이 서버로 보낸 실제 선택만 보여 준다. 기존 remote 입력·A/B·한 참가자 한 판·같은 방 다음 참가자·최소1초 선택·고정 모델은 유지한다. 컴퓨터/모니터 대수와 배치는 아직 미확정이다. 화면 기기만 바뀌며 실제 OS 마우스/PyAutoGUI 방식으로 회귀하지 않는다.

**초반 연결 끊김의 오표시 두 경로를 수정해 버전8을 게시했다.** 실제 데이터 읽기와 화면의 초기 상태 구분을 고쳤으며 GPU 추론을 빨라졌다고 보고하지 않는다. 로컬/공개 실제 CUDA 연속 검사에서 준비 완료 이후 관측한 연결 상태는 모두 정상이고, 실제15초 만료·권한·회차 검사는 계속 동작한다. 현장 모든 네트워크에서 끊김0을 보장하는 결과는 아니다.

## 원인·변경

- 첫 엔진 참가 직후는 stage=connected, engine_seen_at=null이다. 첫 heartbeat 전 정상 대기를 기존 UI가 끊김으로 표시했다. 공개 `engineHeartbeatReceived`로 수신 전 ‘PC 봇 연결 확인 중’과 수신 후 실제 만료를 구분한다. 준비 권한은 첫 알림 수신 전 부여하지 않는다.
- 이전 stateFor는 remote D1행을 await하기 전 now를 고정했다. 읽기 도중 다른 요청이 heartbeat를 커밋하면 새 seen_at이 옛 now보다 커져 정상 알림을 미래 시각으로 거부했다. `state-projection.mjs`는 remote 읽기가 끝난 뒤 시각을 잡고 serverNow·ready·connected를 동일 시각으로 만든다. 제어된 비동기 회귀 검사에서 이전 false와 수정 후 true를 재현했다.
- 3초 heartbeat·15초 만료·진짜 미래 시각 거부는 유지했다. 만료 유예를 늘리거나 stale를 숨기지 않았다. 제출 완료·0개 제출·오류 상태에서도 실제 끊김을 함께 표시한다. 추론/heartbeat 스레드·GPU 잠금·모델/전처리/임계값 동작은 바꾸지 않았다.
- 화면·CLI·PS1은 인간 화면/AI 표시 화면 기준으로 교정했고 같은 PC의 별도 창/모니터 또는 다른 컴퓨터를 사용할 수 있다. 참가자 컴퓨터에 Python/ML 설치는 필요 없으며 모델 PC만 실행기를 켠다. schema/migration·사진/학교·추가 학습 변경0이다.

## 이번 실제 검사

| 검사 | 결과·한계 |
|---|---|
| Python 전체 | 147개 통과,10.214초. 새 생존 관측 회귀6개 포함; 합성 학습 fixture를 새 학습으로 보고하지 않음 |
| Node 서버/UI | 55개 통과,1.157초. 서버42개·UI13개, 읽기 경합·실제 만료·첫 알림·권한·회차·표시 포함 |
| 실제 localhost HTTP | 기존 채점5.323초·같은 방2판7.439초·원격 생존/권한20.859초,3종 통과; 병렬 runner21.017초 |
| 정적 검사 | TypeScript·대상 UI ESLint·Python 컴파일·PowerShell 구문/BOM 통과 |
| 로컬 실제 CUDA | {len(local['liveness_samples'])}개 생존 관측, 준비 후 끊김0·새 플래그 확인·same A두판+B한판 passed=true. 모델1회 로드{local['models_loaded_once_seconds']:.3f}초 |
| 공개 실제 CUDA | {len(public['liveness_samples'])}개 생존 관측, 준비 후 끊김0·모델/표시 일치·same A두판+B한판 passed=true. 모델1회 로드{public['models_loaded_once_seconds']:.3f}초 |
| 공개 선택·간격 | 선택{sum(len(row['selection_events']) for row in rows)}회, ACK뒤 다음 전송 간격{len(gaps)}개, 최소{min(gaps):.3f}초. A1/A2/B1 선택(0부터)={selected} |
| 브라우저 | localhost 인간1920×1080·AI표시1280×720의 대기 화면 문구/가로 넘침0 확인. 실제 행사 기기/네트워크·새 live격자 크기 재측정 아님 |
| 공개 HTTP | human/bot HTTPS200·컴퓨터 표시 안내·구역 선택·패드 전용 문구 없음 확인 |

로컬 세 문제는 모두 나무≥3,0개 예측·오답·90초 timeout이었다. 따라서 로컬 이번 GPU 검사에는 실제 선택 간격 표본이0개이며 1초 실측 근거로 쓰지 않는다. 공개 세 문제는 모두 사람≥3이었고 선택/제출이 정답으로 종료됐다(A1 12.156초,A2 13.474초,B1 15.977초). 이는 같은24장 공개 시연 은행의 기능 검사이며 정확도100%·유형별40% 달성·학교 성능의 근거가 아니다. 다운로드·GPU 대기/추론·전송/타일 대기·서버 제출 시각을 추론 속도와 구분한다. 생존 관측은 약0.25초 간격의 HTTP 샘플이며 전체 시간의 무중단 보증이 아니다.

근거: [로컬 생존/모델 보고서](../runs/desktop-liveness-local-v1/verification.json), [공개 생존/모델 보고서](../runs/desktop-liveness-public-v1/verification.json), [브라우저 배치](../runs/desktop-browser-qa/layout.json), [인간 화면](../runs/desktop-browser-qa/human-desktop.png), [AI 표시 화면](../runs/desktop-browser-qa/bot-desktop.png), [공개 HTTP](../runs/site-publish/desktop-release-http.json). 실제 ML 엔진은 관리자/정답 접근0·OS입력0·학교/학습/튜닝0이다. localhost 서버 채점용 별도 테스트 프로세스만 테스트 관리자 답안을 사용한다.

## 이번 배포·현재 PC 실행기

사이트버전8 **succeeded**: commit `{release['commit_sha']}`, saved `{release['version_id']}`, deployment `{release['id']}`, 환경revision{release['env_set_revision']}. production build·source push·package·save·publish를 확인했다. 기존 공개 범위·human/bot 도메인·D1/R2·키·0000/0001 migration을 유지한다. [배포 기록](../runs/site-publish/desktop-release.json)의 URL은 `{release['url']}`다.

운영용 기존 프로세스는 이번 재조회에서0이었으므로 강제 종료 없이 최신 CLI 안내로 새 콘솔을 시작했다. PowerShell17448→venv11832→base19656의 한 Windows 실행 체인과 CUDA 모델1회 로드{startup['model_loading_seconds']:.3f}초를 확인해 켜 두었다. [시작 기록](../{runtime['startup_path']}), [생존 조회](../runs/site-publish/desktop-current-engine.json)를 남겼다. 운영 콘솔에 에이전트가 입력한 A/B 코드는0이며 특정 사용자 방 준비/경기 시작은 확인하지 않았다. 위 실제 GPU3라운드는 별도 QA 엔진이며 검증 후 종료한다. 실행기 창을 닫거나 재부팅하면 종료된다.

## 컴퓨터 운영·재현·남은 작업

인간 `https://human.marulee.dev/?lane=A`와 AI표시 `https://bot.marulee.dev/?lane=A`를 컴퓨터 브라우저에 연다. B도 lane=B다. 모델 PC에서 `Start-Alpha-Remote.cmd`를 한 번 켜고 처음에만 인간 방→AI표시 코드→PC 숨김 입력 A/B코드를 연결한다. 이후 결과에서 **다음 참가자 준비 → PC 준비 확인 → 사람이 시작**을 반복한다. AI 표시 화면이 전면에 없어도 OS 커서를 쓰지 않아 인간 마우스를 방해하지 않는다. 기존 열린 화면은 새로고침해 최신 안내를 받는다. 상세 정본은 SETUP이다.

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
# web/alpha-arena에서:
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs components/arena-state.test.mjs components/engine-status.test.mjs
# 실제 공개 QA 생성·추론·제출; 출력은 새 폴더:
.\\.venv\\Scripts\\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --execute --device cuda --output runs/desktop-liveness-check-new
.\\.venv\\Scripts\\python.exe runs/site-publish/verify_desktop_release.py
.\\.venv\\Scripts\\python.exe scripts/check_docs.py --date 2026-10-27
.\\.venv\\Scripts\\python.exe runs/site-publish/audit_docs.py
```

이번 작업 검토: 컴퓨터 브라우저 운영·첫 생존 알림 대기·D1 읽기 시각 경합을 수정해 실제 코드/비동기 회귀/HTTP/로컬·공개 CUDA/브라우저로 검증하고 버전8을 게시했다. 학교 최종 평가 전용·고정 모델·목표40% 미달성·Pi/ONNX/기존 OS 입력 경계를 유지한다. 현장 컴퓨터·모니터 배치/네트워크 리허설과 독립 품질 평가가 남았다. 관리13개 전체를 분담 재독·갱신했다. 문서 최종 점검: CHECK_PENDING

'''
status_path = root / "docs/STATUS.md"
old = status_path.read_text(encoding="utf-8")
old = old[old.index("## 현재 결론"):]
old = old.replace("## 현재 결론", "## 이전 버전7 결론", 1)
old = old.replace("## 최신 변경과 검증", "## 이전 버전7 변경과 검증", 1)
old = old.replace("## 최신 배포", "## 이전 버전7 배포", 1)
old = old.replace("## 현재 가동 기록과 부스 운영", "## 이전 버전7 당시 가동 기록과 부스 운영", 1)
old = old.replace("## 최신 경기·사진 계약", "## 이전 웹 초기 경기·사진 계약", 1)
status_path.write_text("# 현재 진행 상황\n\n최종 검토: 2026-10-27 (Asia/Pyongyang)\n\n" + body + old, encoding="utf-8")
names = ["AGENTS.md", "README.md", "docs/README.md", "docs/SETUP.md", "docs/ARCHITECTURE.md", "docs/DATASET.md", "docs/DATASET_CANDIDATES.md", "docs/EXECUTION_PLAN.md", "docs/INTEGRATION.md", "docs/ROADMAP.md", "docs/STATUS.md", "docs/CHANGELOG.md", "web/alpha-arena/README.md"]
entry = f'''## 2026-10-27 컴퓨터 화면 운영·초기 생존 상태 수정·버전8

- 최신 사용자 요청으로 Android4대 계획을 컴퓨터 브라우저 인간/AI 표시로 대체했다. 기기/모니터 대수는 미정이며 기존 PC ML·remote 선택·A/B·같은 방 참가자 교체·1초·권한은 유지한다. UI·CLI·PS1·운영 문서를 교정했다.
- 서버가 D1 읽기 전 now와 읽기 도중 새 heartbeat를 비교해 정상 연결을 false로 표시하던 경합을 재현했다. remote 읽기 후 시각으로 serverNow/ready/connected를 함께 투영하도록 고쳤다. engineHeartbeatReceived로 첫 알림 대기와 실제 만료를 구분하고 제출/0개/오류에서도 stale를 표시한다. 3초/15초·진짜 미래값 거부·라운드 CAS·단일승자는 유지하며 schema/migration 변경0이다.
- Python147개10.214초·Node55개1.157초·TypeScript·대상UI ESLint·Python컴파일·PowerShell구문/BOM 통과. 실제 localhost HTTP3종(5.323/7.439/20.859초,runner21.017초)도 통과했다.
- 실제 CUDA 로컬 A두판+B한판: 모델 로드{local['models_loaded_once_seconds']:.3f}초·생존{len(local['liveness_samples'])}샘플·준비후끊김0·passed=true. 세문제 모두나무0개오답timeout으로 실제선택간격표본0이다. 공개검사는 모델 로드{public['models_loaded_once_seconds']:.3f}초·생존{len(public['liveness_samples'])}샘플·준비후끊김0·모델/표시일치·passed=true. 사람3문제에서11선택·간격8개최소1.375초·세정답종료를 확인했다. 같은24장 재사용 연결검사로100%정확도·40%달성·학교 성능으로 일반화하지 않는다.
- localhost 브라우저 인간1920×1080/AI표시1280×720 대기 화면의 문구·가로넘침0과 스크린샷을 기록했다. 실제 행사 기기 배치와 새 live격자 검증이 아니다. 운영 중 사용자 방/답안/OS입력은 조작하지 않았고 QA 엔진의 RGB 추론만 수행했다.
- 버전8 build·source push·package·save·publish succeeded. commit `{release['commit_sha']}`, saved `{release['version_id']}`, deployment `{release['id']}`, 환경revision3이다. 기존 도메인/공개범위/D1/R2/키/0000·0001을 유지했다. human/bot HTTPS200과 최신컴퓨터안내를 확인했다. 기록은 runs/site-publish/desktop-release.json·desktop-release-http.json이다.
- 기존 운영 엔진0을 확인한 뒤 최신 콘솔17448→11832→19656을 시작해 CUDA 로드{startup['model_loading_seconds']:.3f}초와 생존을 확인하고 켜 뒀다. 에이전트 운영콘솔 A/B코드입력0·특정사용자방준비미확인이다. QA 엔진은 별도종료이며 실행기와 구분한다.
- 학교/추가학습/가중치·임계값·전처리 변경0. 40%·독립품질/학교평가·Pi/ONNX·기존OS입력·현장컴퓨터/모니터·네트워크 리허설은 미완료다. 다음은 실제 행사 배치에서 최초연결→시작→다음참가자 반복 점검이다.
- 관리13개 전체를 분담해 재독·갱신했다. 문서 최종 점검: CHECK_PENDING

### 이번에 읽고 갱신한 전체 Markdown (13개)

''' + "\n".join("- " + name for name in names) + '''

이번 작업 검토: 컴퓨터 화면 전환과 초기 연결 오표시 두 원인을 수정·배포하고 로컬/공개 실제 모델 및 생존 샘플을 검증했다. 정상 연결과 첫 대기·진짜 만료를 구분하며 실제 추론 속도 개선이나 정확도를 보장하지 않는다. 관리13개 전체 검토·검사와 미완료 경계를 기록했다.

'''
path = root / "docs/CHANGELOG.md"
old = path.read_text(encoding="utf-8")
path.write_text("# 작업 이력\n\n최종 검토: 2026-10-27 (Asia/Pyongyang)\n\n" + entry + old[old.index("## 2026-10-27"):], encoding="utf-8")
print(json.dumps({"updated": ["docs/STATUS.md", "docs/CHANGELOG.md"], "public_liveness_samples":len(public['liveness_samples'])}, ensure_ascii=False))
