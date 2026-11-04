"""Finalize owned status/history from completed persistent-room evidence."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
read = lambda relative: json.loads((root / relative).read_text(encoding="utf-8"))
public = read("runs/continuous-booth-public-v1/verification.json")
assert public["passed"] and all(public["checks"].values())
release = read("runs/site-publish/continuous-release.json")
assert release["status"] == "succeeded"
startup_path = "runs/remote-engine/20261027-091218-5af7e178/startup.json"
startup = read(startup_path)
assert startup["models_loaded_once"] and startup["device"] == "cuda"
reports = {key: read("runs/continuous-booth-public-v1/" + filename) for key, filename in {
    "A1": "lane-A-game-1.json", "A2": "lane-A-game-2.json", "B1": "lane-B-game-1.json"}.items()}
selections = ", ".join(f'{key}={report["selected_indices"]}' for key, report in reports.items())
finals = ", ".join(f'{key}: {result["reason"]}/winner={result["winner"]}' for key, result in public["finals"].items())
public_load = public["models_loaded_once_seconds"]
documents = ["AGENTS.md", "README.md", "docs/README.md", "docs/SETUP.md", "docs/ARCHITECTURE.md",
             "docs/DATASET.md", "docs/DATASET_CANDIDATES.md", "docs/EXECUTION_PLAN.md", "docs/INTEGRATION.md",
             "docs/ROADMAP.md", "docs/STATUS.md", "docs/CHANGELOG.md", "web/alpha-arena/README.md"]
status_path = root / "docs/STATUS.md"
status = status_path.read_text(encoding="utf-8")
history = status[status.index("## 이전 후속 정보: Android 태블릿4대"):]
history = history.replace("## 현재 원격 A/B 구현과 검증 (2026-10-27)", "## 이전 버전6 원격 A/B 구현과 검증 (2026-10-27)", 1)
status_prefix = f'''# 현재 진행 상황

최종 검토: 2026-10-27 (Asia/Pyongyang)

## 현재 결론

**사이트버전7을 배포했고 remote A/B는 같은 방에서 다음 참가자를 계속 받는다.** 처음에만 각 인간 방·봇 표시 패드·PC 엔진을 연결한다. 한 판 종료 후 인간이 ‘다음 참가자 준비’를 누르고 PC 준비가 표시되면 다음 사람이 ‘대결 시작하기’를 누른다. 같은 방·코드·engine/viewer 연결과 모델을 유지한다. 한 참가자당 한 라운드이며 자동 연속 시작은 아니다. legacy OS 경로는 기존 새 방 방식이다.

**최신 코드의 사용자용 PC 봇도 켜 두었다.** 표시되는 PowerShell PID38476 → venv Python44732 → base Python42276 체인과 CUDA 모델 1회 로드6.250초를 확인했다. 이는 Windows 가상환경의 한 실행 체인이다. 에이전트는 이 운영용 콘솔에 A/B 코드를 입력하지 않았으며 방별 준비/경기 시작은 아직 확인하지 않았다. 아래 QA의 실제 사진 추론은 별도 검증 프로세스에서 실행했다.

**공개 사이트에서도 재연결 없이 A방 두 판과 독립 B방 한 판을 실제 PC CUDA로 검증했다.** 방/코드/표시 권한 유지·선택 초기화·자동 재준비·라운드별 예측/제출1회·표시 선택 일치·최소1초 선택 간격이 모두 통과했다. 기존 공개 사진24장으로 수행한 연결 검사이며 모델 정확도·40% 달성·학교 성능 검증이 아니다. 물리 Android 태블릿4대 리허설·ONNX/Pi·기존 OS 실제 입력은 미완료다.

## 최신 변경과 검증 (2026-10-27, 지속 방)

- 서버 `/api/rooms/:id/next`는 remote 인간의 종료 roundId만 수락한다. D1 batch에서 이전 선택·순서·마지막 선택 시각·ready를 비우고 lobby로 복귀한다. 방/코드/권한/누적 회차/과거 결과는 보존한다. 중복 next는 재준비를 지우지 않으며 옛 next가 새 판을 초기화하지 못한다.
- heartbeat는 roundId와 roundNumber를 함께 CAS 검사해 이전 판/이전 lobby 요청이 다음 참가자 상태를 덮지 못한다. 선택 중 종료 경합의409 round_ended와 새 round 전환을 PC가 처리한다. 진행 중 error는 같은 판에서 임의 재준비하지 않는다.
- UI는 공개 revision과 회차/단계를 비교해 늦은 폴링/요청을 배제하고 다음 판의 사진·선택·타이머를 새로 만든다. 결과의 봇 패드는 연결 유지 대기를 표시한다. PC 기본 대화형 실행은 같은 토큰의 지속 세션이며 `--once`만 기존 한 판 검사용이다. `stop A`, `stop B`, `quit`으로 종료할 수 있다.
- schema/migration 추가0, 데이터/사진·학교·가중치/전처리/임계값 변경0이다. 모델은 각 새 round의 RGB를 한 번 판별하며 정답 개수 채우기·임의 오답·같은 판 재추론을 추가하지 않았다.

| 검사 | 실제 결과 | 범위 |
|---|---|---|
| Python 전체 | 141개 통과,11.514초 | remote23개 포함. 합성 fixture를 새 모델 학습으로 해석하지 않음 |
| Node 전체 | 43개 통과,0.737초 | 서버36개·UI 회차 상태7개 |
| 실제 localhost HTTP | 3종 통과 | 기존 채점4.758초, 같은 방2판7.102초, 원격 권한/회차20.167초; 병렬 runner20.287초 |
| 종료 경합 HTTP 재검사 | 1종 통과,5.555초 | selecting/result heartbeat409 round_ended를 명시 검사; runner5.655초 |
| 정적/환경 | TypeScript·대상UI ESLint·compileall·pip check 통과 | OS 입력/물리 패드 검사가 아님 |
| 로컬 실제 CUDA | passed=true | A1/B1 나무0개, A2 건물[2,3,6], 세 판 모두오답·timeout; 모델 한 번 로드9.531초 |
| 공개 실제 CUDA | passed=true | 모델 한 번 로드{public_load:.3f}초, {selections}; {finals} |
| 공개 HTTP | human/bot HTTPS200·원격 안내 통과 | SSR HTML 확인이며 새 브라우저/물리 패드 실측은 아님 |

로컬 근거는 [연속 검증](../runs/continuous-booth-local-v1/verification.json)과 [기록된 표시/모델 비교](../runs/continuous-booth-local-v1/viewer-match.json)다. 공개 근거는 [연속 검증](../runs/continuous-booth-public-v1/verification.json)과 같은 폴더의 세 lane 보고서다. 공개 풀이기는 관리자·정답 데이터 접근0·OS입력0·물리패드0·학교/학습/튜닝0이다. Node의 별도 localhost 서버 채점 검사는 관리자 답안을 사용하는 테스트 전용이며 실제 ML 검증/엔진에는 전달하지 않는다.

## 최신 배포

사이트버전7은 **succeeded**다. source `{release['commit_sha']}`, saved version `{release['version_id']}`, deployment `{release['deployment_id']}`, 환경revision3이다. production build·정확한 source push·package·save·publish와 두 호스트 HTTPS200을 확인했다. [배포 기록](../runs/site-publish/continuous-release.json), [HTTP 확인](../runs/site-publish/continuous-release-http.json)에 근거를 남겼다. 기존 공개 범위·도메인·D1/R2·키·0000/0001 migration을 유지했다. 아래 버전6과 새 방 운영은 이전 이력이다.

## 현재 가동 기록과 부스 운영

| 항목 | 확인한 결과 |
|---|---|
| 실행기 | 표시되는 PowerShell에서 최신 `scripts/start_remote_engine.ps1` 실행, 계속 켜 둠 |
| 프로세스 | PID38476 →44732 →42276. 한 Windows venv 실행 체인 |
| 시작 기록 | [startup.json](../{startup_path}), UTC2026-10-27T00:12:25.5182856Z |
| 모델 | CUDA·models_loaded_once=true,6.250초. GUI/자격증명 기록/튜닝 없음 |
| 연결 경계 | 에이전트의 운영 콘솔 A/B 코드 입력0. 모델 로드와 특정 사용자 방의 ready/추론을 구분 |

이전 운영용 PID39972/46576/46728은 최신 수정 적용 전 재조회에서 모두 종료돼 있었고 다른 remote 엔진0을 확인했다. 기존 PID를 강제 종료하지 않았으며 최신 소스로 위 콘솔을 새로 시작했다. 현재 실행기는 검증 프로세스 정리 대상에서 제외해 켜 둔다. 정상 참가자 교체에는 재시작하지 않는다. 프로세스 생존은 확인 시점의 상태이며 창을 닫거나 PC를 재부팅하면 종료된다.

운영 절차 정본은 [SETUP](SETUP.md)이다.

1. PC 전원·인터넷과 원격 엔진 콘솔을 유지한다. 이미 켜져 있으면 중복 실행하지 않는다. 꺼져 있으면 `Start-Alpha-Remote.cmd`를 한 번 실행해 모델 로드를 기다린다.
2. Android Chrome 네 대에 인간A `https://human.marulee.dev/?lane=A`, 봇표시A `https://bot.marulee.dev/?lane=A`, 인간B `https://human.marulee.dev/?lane=B`, 봇표시B `https://bot.marulee.dev/?lane=B`를 각각 연다. 각 기기는 HTTPS 인터넷이 필요하고 같은 Wi-Fi는 필수가 아니다.
3. 최초에 인간A/B에서 각각 방을 만든 뒤 같은 레인의 봇 표시 패드에 해당 코드를 입력한다. PC 숨김 입력란에도 `A <A방 8자리 코드>`, `B <B방 8자리 코드>`를 각각 입력하고 Enter를 누른다. 입력 글자가 안 보이는 것이 정상이다.
4. 인간 패드에 PC 준비/봇 연결이 표시되면 해당 참가자가 시작한다. 공통 시작 시각은 약2초 뒤이며 A/B는 독립 진행한다. 인간은 오답 수정·재제출, 봇은 라운드별 고정 예측1회·제출1회다.
5. 종료 후 같은 인간 패드에서 **다음 참가자 준비 → PC 준비 확인 → 다음 사람이 대결 시작하기**를 반복한다. 새 방/새 코드/PC 재입력/모델 재로드가 필요 없다. 다른 레인은 계속 진행한다.
6. 운영 종료는 PC의 `quit` 또는 창 닫기다. 세션 유실/방 만료는 예외 복구로 새 방·최초 페어링이 필요하다. 원격은 F8/좌표 보정과 PC 브라우저 전면창 유지가 필요 없다.

재현 명령(검증 출력 폴더는 새 경로 사용):

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
# web/alpha-arena에서:
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs components/arena-state.test.mjs
# 프로젝트 루트에서, 실제 공개 QA방·추론·제출 생성:
.\\.venv\\Scripts\\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --execute --device cuda --output runs/continuous-booth-check-new
.\\.venv\\Scripts\\python.exe scripts/check_docs.py --date 2026-10-27
.\\.venv\\Scripts\\python.exe runs/site-publish/audit_docs.py
```

이번 작업 검토: 같은 방 다음 참가자 요청에 맞춰 서버/UI/PC 지속 세션을 구현·배포하고 로컬 및 공개 CUDA의 A두판+B한판을 확인했다. 운영용 최신 PC 콘솔을 따로 켜 두었고 A/B 코드 자동 입력은 하지 않았다. 관리13개 본문을 분담 재검토·갱신했으며 최종 문서 점검 결과는 아래 기록을 따른다. 목표40%·Android 실4대·학교 최종 평가·ONNX/Pi·OS 입력은 미완료다.

문서 최종 점검: CHECK_PENDING

'''
status_path.write_text(status_prefix + history, encoding="utf-8")
change_path = root / "docs/CHANGELOG.md"
change = change_path.read_text(encoding="utf-8")
old_entry = change[change.index("## 2026-10-27 운영 순서 안내"):]
old_entry = old_entry.replace("## 2026-10-27 운영 순서 안내·사용자용 PC 원격 엔진 가동", "## 2026-10-27 이전 최초 PC 엔진 가동·수정 전 운영안", 1)
old_entry = old_entry.replace("- 관리 대상13개를 팀이 분담해 전체 본문을 재검토·갱신한다. 이번 갱신 후 `check_docs.py --date 2026-10-27`과 별도 문서 감사의 최종 결과는 루트 점검 대기다. 이전13개 통과 결과를 이번 재실행으로 쓰지 않는다.", "- 이 최초 실행 뒤 같은 방 연속 운영 수정으로 작업 범위가 확장됐다. 당시 문서 점검 대기 상태는 위 후속 수정의 전체 검토·최종 점검으로 통합했다.", 1)
old_entry = old_entry.replace("이번 작업 검토: 사용자 요청에 따라 운영용 PC 엔진을 실제 시작하고 CUDA 모델 로드·프로세스 생존을 확인했다. 특정 방 준비/사진 추론과 구분하며 콘솔을 계속 켜 두고 내일 새 방/코드 운영 순서를 갱신했다. 코드·배포·학교·가중치/임계값 변경은 없고 관리13개 최종 문서 검사 결과는 점검 후 확정한다.", "이전 최초 실행 검토: 당시 운영용 모델 로드·생존을 확인했고 새 방/코드 운영안을 기록했다. 이후 사용자 요구로 위 지속 방 구현과 최신 엔진 실행이 이를 대체했다. 초기 프로세스는 재조회 시 종료 상태였으며 최종 결과는 위 후속 변경과 STATUS를 따른다.", 1)
change_prefix = f'''# 작업 이력

최종 검토: 2026-10-27 (Asia/Pyongyang)

## 2026-10-27 같은 방 연속 참가자·PC 지속 엔진·버전7 게시

- 사용자 후속 요청으로 정상 참가자 교체의 새 방/코드 방침을 대체했다. remote 인간 결과의 ‘다음 참가자 준비’가 같은 방/코드/engine·viewer 권한을 유지해 lobby로 원자 초기화하고, 다음 사람이 PC 재준비 후 수동 시작한다. legacy는 기존 한 판/새 방 방식이다.
- 서버 next의 종료 roundId·revision CAS/멱등 ACK, 새 start 허용, heartbeat roundId+roundNumber CAS, 종료 경합409 round_ended를 구현했다. 늦은 옛 요청이 다음 판 선택/준비를 덮지 못하게 했다. schema/migration 추가0이다.
- UI는 다음 참가자 버튼·연결 유지 안내·새 사진/선택/타이머 reset과 revision 기반 늦은 상태 거부를 추가했다. PC 대화형 기본은 지속 세션이며 같은 모델·토큰으로 라운드별 한 번만 새 RGB 추론/제출한다. --once·stop A/B·quit 경계를 유지했다.
- Python141개(11.514초), Node43개(0.737초), TypeScript·대상UI ESLint·compileall·pip check 통과다. 실제 localhost HTTP3종을 통과했고 종료 경합 명시 검사 추가 후 해당1종도5.555초에 통과했다. 테스트용 관리자 답안은 localhost 서버 채점 프로세스에만 있고 실제 ML 엔진에는 전달하지 않았다.
- 로컬 실제 CUDA 연속 검증은 passed=true다. A1/B1 나무0개·A2 건물[2,3,6]을 라운드별1회 제출하고 모두90초 timeout으로 종료했다. 모델 로드9.531초, 방/코드/표시권한 유지·선택초기화·재준비·표시/모델 일치·최소1초를 확인했다. 근거는 runs/continuous-booth-local-v1/이다.
- 버전7 production build·source push·package·save·publish가 succeeded다. commit `{release['commit_sha']}`, saved `{release['version_id']}`, deployment `{release['deployment_id']}`, 환경revision3이다. 두 기존 도메인 HTTPS200·공개 범위·D1/R2·키·기존 migration을 유지했다. 근거는 runs/site-publish/continuous-release.json과 continuous-release-http.json이다.
- 공개 실제 CUDA 연속 검증 runs/continuous-booth-public-v1/verification.json도 passed=true다. 모델1회 로드{public_load:.3f}초, {selections}; {finals}. 같은A방 두판과 독립B방, 같은연결/표시권한/코드·새사진추론·1회제출·1초간격을 확인했다. 물리 Android0·정답/관리자 접근0·OS입력0이며 정확도 표본이 아니다.
- 기존 운영용 PID39972/46576/46728은 재조회 시 모두 종료 상태였고 다른 remote 엔진0이었다. 최신 소스로 표시되는 PowerShell38476→venv44732→base42276을 시작해 CUDA 모델1회 로드6.250초와 생존을 확인하고 켜 뒀다. 기록은 {startup_path}다. 이 운영 콘솔에는 A/B 코드 입력0이며 QA엔진과 분리한다.
- 학교사진/추가학습/가중치·임계값·전처리 변경0이다. 유형별40%·독립 품질평가·학교최종평가·ONNX/Pi·물리Android4대 리허설·기존 OS입력은 미완료다. 다음은 실제 패드 네 대의 최초페어링→두판 반복·네트워크/화면 점검이다.
- 관리13개를 분담해 전체 본문을 읽고 변경/불변 검토 결과를 갱신했다. 문서 최종 점검: CHECK_PENDING

### 이번에 읽고 갱신한 전체 Markdown (13개)

''' + "\n".join("- " + name for name in documents) + '''

이번 작업 검토: 사용자 승인된 같은 방 연속 운영을 서버·화면·PC 지속 세션까지 반영하고 실제 로컬/공개 CUDA 두 회차 및 별도 B방과 버전7 게시를 검증했다. 최신 사용자 PC 콘솔은 켜 둔 상태로 모델 로드와 방 연결을 구분했다. 13개 문서 전체 갱신·최종 검사와 미완료 품질/실기기 경계를 기록했다.

'''
change_path.write_text(change_prefix + old_entry, encoding="utf-8")
print(json.dumps({"updated": ["docs/STATUS.md", "docs/CHANGELOG.md"], "public_passed": True}, ensure_ascii=False))
