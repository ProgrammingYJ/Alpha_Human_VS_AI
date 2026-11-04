from pathlib import Path

root = Path(__file__).resolve().parents[2]
def read(name):
    return (root / name).read_text(encoding='utf-8-sig')
def write(name, text):
    (root / name).write_text(text.rstrip() + '\n', encoding='utf-8')

write('README.md', r'''# 알파 AI vs 인간 CAPTCHA

최종 검토: 2026-10-26 (Asia/Pyongyang)

송내고등학교 알파 동아리의 인간·AI CAPTCHA 대결 프로젝트입니다. 사용자 요청으로 인간용·봇용 웹사이트와 사진 등록도 이번 범위에 포함했습니다. Windows RTX 4070 Laptop PC에서 모델을 학습하고 PC와 Raspberry Pi 4B에서 각각 추론·타일 클릭하는 것이 목표입니다.

- [인간 화면](https://human.marulee.dev): 새 대기실 생성·시작·타일 선택.
- [봇 화면](https://bot.marulee.dev): 같은 대기실에 연결하는 ML 봇 전용 화면.
- [사진 관리](https://human.marulee.dev/admin): Sites 소유자 계정으로 로그인 후 사진·비공개 라벨 등록.

두 호스트는 같은 Cloudflare Worker·D1·R2를 공유합니다. 실제 게시 버전·HTTPS/API 결과는 [현재 상태](docs/STATUS.md)가 정본입니다. **공개 사진은행은 아직 비어 있습니다.** 학교 사진은 촬영 전이며 로컬 Kaggle 시연34장은 공개 재배포 허가를 일괄 확인하지 않아 운영 사이트에 넣지 않았습니다.

## 경기와 사진

| 문제 | 정답 타일 수 |
|---|---|
| 사람이 3명 이상인 사진 | 2~4개 무작위 |
| 나무가 3그루 이상인 사진 | 3~4개 무작위 |
| 건물이 있는 사진 | 2~4개 무작위 |
| 연못이 있는 사진 | 2~4개 무작위 |

네 유형 중 하나와 독립 사진9장을 추첨해 양쪽에 같은 배열을 제공합니다. 봇 준비 후 인간이 시작하면 약2초 뒤 공통 서버 시각부터 타이머가 흐릅니다. **한 참가자당 한 판이며 먼저 모든 정답을 고르고 오답을 제외해 제출한 쪽이 승리하면 즉시 종료됩니다.** 오답이면 같은 문제·시작 시각으로 수정·재제출할 수 있습니다. 다음 참가자는 새 방과 새 연결 코드로 봇을 다시 연결합니다. 기본90초 제한은 미확정 운영 가안입니다.

사진 관리에서 사람 수, 나무 정확 수 또는3그루 이상 여부, 건물·연못, 원본 그룹·출처·사용 메모를 확인해 올립니다. 모르는 값은 미확인으로 둡니다. 원본·연속촬영·크롭은 같은 그룹으로 기록합니다. 모든 정답 수를 지원하려면 사람/건물/연못 각각 최소4양성7음성, 나무4양성6음성의 독립 그룹이 필요합니다. 부족하면 시작하지 않습니다. 정답은 서버에만 있으며 모델에 실제 정답 수·라벨·원본 파일명을 전달하지 않습니다.

## 모델과 실제 확인 범위

사람 수는 **SSDLite320 MobileNetV3 Large**, 건물·연못은 **MobileNetV3 Small**의 기존 제한 학습 v1을 사용합니다. 두 모델은 검토된 Kaggle train17장/41장으로 각각1epoch만 추가 학습했고 대규모 COCO/ImageNet 사전학습을 이미 거쳤습니다. **YOLO는 사용하지 않았습니다.** 나무3그루 이상은 존재 점수로 셀 수 없어 별도 공식 사전학습 **Grounding DINO Tiny**를 고정해 연결했습니다. 나무 모델의 프로젝트 추가 학습은 없습니다.

실제 CUDA에서 저장 RGB 시연4문제를 실행했습니다. 건물 문제는 선택 집합이 맞았고 사람 수·나무 수·연못은 틀렸습니다. 재사용 시연 사진의 기능 검사이며 일반 정확도25%나 목표40% 달성의 근거가 아닙니다. 조건별 선택·시간·한계는 STATUS에 기록했습니다. v1과 나무 임계값을 이 실패에 맞춰 재튜닝하지 않았습니다.

화면 RGB→ML→좌표→최소1초 간격 타일 클릭·제출 경로는 코드로 구현했습니다. **실제 OS 화면 캡처·마우스 클릭·제출은0회**입니다. 브라우저 URL 검증 실패로 도구가 화면 제어를 중단했으며 다른 입력 도구로 우회하지 않았습니다. 기본 설정은 `calibrated=false`이며 좌표는 실측 전입니다. 현재 봇은 한 판에 고정 ML 선택을 한 번 제출하고 오답 자동 재시도는 없습니다. 상대가 이기면 남은 입력을 취소합니다.

기존 4정답·5오답 평가에서 유형별 약40%라는 개발 목표는 아직 달성하지 못했습니다. 기존8조건과 현재 웹4종·가변 정답 수의 성능을 섞지 않습니다. 충분한 새 Kaggle train/선택val/미사용audit를 먼저 정해야 합니다. **학교 사진은 문제·모델 고정 후 최종 평가 전용**이며 학습·개발 검증·모델 선택·튜닝에 쓰지 않습니다. ONNX 출력 동등성·Pi 기기/추론/GUI 입력도 남아 있습니다.

## 실행과 문서

```powershell
cd "$env:USERPROFILE\Desktop\Alpha-Captcha-AI"
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/run_booth_bot.py --help
.\.venv\Scripts\python.exe scripts/verify_booth_models.py --device cuda --output runs/booth-model-smoke-new
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-26
```

저장 RGB 명령은 새 결과 폴더를 사용하며 화면을 조작하지 않습니다. 실제 봇은 [환경 설정](docs/SETUP.md)과 [웹 소스 안내](web/alpha-arena/README.md)를 따라 물리 좌표를 보정한 뒤 사용합니다. 공개 질문 외 내부 정답과 사진URL로 풀이하거나 HTTP 제출로 화면 클릭을 대신하지 않습니다. 준비 버튼은 봇 화면에서 누릅니다.

Python은 프로젝트 `.venv`, 웹은 `web/alpha-arena/`의 Node22/Vinext 소스입니다. 데이터·모델·학교 사진·키·가상환경은 웹 소스 및 배포 자산에서 제외합니다. 기존 설치 스냅샷은 `requirements/windows-py312.lock.txt`, 새 나무 선택 의존성은 `requirements/booth-tree.txt`를 함께 확인합니다. 전체 문서는 [색인](docs/README.md), 실제 수치·재현은 [STATUS](docs/STATUS.md), 변경 이력은 [CHANGELOG](docs/CHANGELOG.md)에 있습니다.

이번 작업 검토: 최신 웹 제작 승인과4종·한 참가자 한 판·첫 완벽정답 즉시 종료를 반영했다. 공개 사진은행 공백, 기존 두 제한 모델과 별도 사전학습 나무 후보, 저장RGB 실제 실패와 목표40% 미달성, 화면 제어 중단·OS0회·Pi/ONNX 미완료를 실제 결과와 대조했다. 학교 평가 전용과 최소1초 클릭 규칙을 유지했다.
''')

write('docs/README.md', '''# 문서 안내

최종 검토: 2026-10-26 (Asia/Pyongyang)

프로젝트가 직접 관리하는 Markdown 전체13개입니다. 작업 전후 아래 모든 본문을 읽고 실제 코드·측정·요구사항과 대조해 갱신합니다.

| 문서 | 용도 |
|---|---|
| [AGENTS.md](../AGENTS.md) | 최신 범위·작업 규칙·학교 격리·현재 PC 사양 |
| [README.md](../README.md) | 인간/봇 주소·경기·모델·확인 범위 |
| [docs/README.md](README.md) | 관리 문서 전체 색인 |
| [docs/SETUP.md](SETUP.md) | PC/Pi·웹·운영자·선택 나무 모델 설치와 실행 |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | 픽셀 ML·D1/R2·비공개 채점·봇 입력 구조 |
| [docs/DATASET.md](DATASET.md) | 기존134장·로컬34장·라벨/관계 그룹·학교 최종 전용 |
| [docs/DATASET_CANDIDATES.md](DATASET_CANDIDATES.md) | Kaggle 출처/이용 조건·새 독립 자료 계획 |
| [docs/INTEGRATION.md](INTEGRATION.md) | 4종 대결 API·공통 시계·한 판 규칙·화면 좌표 계약 |
| [docs/EXECUTION_PLAN.md](EXECUTION_PLAN.md) | 웹·실제 입력·평가·ONNX·Pi 실행 순서 |
| [docs/ROADMAP.md](ROADMAP.md) | 남은 작업과10/28 내부 임시 목표 |
| [docs/STATUS.md](STATUS.md) | 실제 배포/검증·ML 실패·미완료·재현 명령의 정본 |
| [docs/CHANGELOG.md](CHANGELOG.md) | 작업 이력·검증·전체 문서 검토 기록 |
| [web/alpha-arena/README.md](../web/alpha-arena/README.md) | 새 인간·봇·사진관리 웹 소스와 운영 방법 |

최신 상태는 README → STATUS → SETUP → INTEGRATION 순서로 읽습니다. 기존8조건4P5N 평가·v1 test 수치는 이력이며 현재4종·가변 정답수·나무 계수의 정확도 보증이 아닙니다. 목표40%는 미달성이고 학교/Pi/OS 입력도 실제 검증을 구분합니다.

`python scripts/check_docs.py --date 2026-10-26`은 검토 표식·날짜·색인 누락을 검사합니다. 내용 정확성은 직접 검토합니다. 검사기가 제외하는 data/models/runs/logs까지 별도 전체 목록과 대조해 자체 문서를 누락하지 않습니다. 가상환경·node_modules·Git·생성된 프레임워크 상태와 vendor 외부 라이선스는 관리 문서에서 제외하며 외부 문서를 임의 갱신하지 않습니다.

이번 작업 검토: 웹소스 안내를 새로 색인에 포함해13개를 검토했다. 기존 웹사이트 제외/5유형 계획을 새 승인 범위와4종 대결로 교체한 문서 위치, 실제 배포/ML/화면 입력 결과의 정본과 이력 구분을 확인했다. 외부 의존성 제외 및 수동 전체 목록 대조 의무를 유지했다.
''')

agents = read('AGENTS.md')
agents = agents.replace('전체 버전은 requirements/windows-py312.lock.txt, 실제 점검은 logs/environment-check.json을 참고한다.', '초기 설치 스냅샷은 requirements/windows-py312.lock.txt, 실제 점검은 logs/environment-check.json을 참고한다. 10/26 선택 나무 모델의 transformers4.57.3/safetensors0.7.0 등 추가는 requirements/booth-tree.txt를 함께 확인한다. 기존 CUDA torch/torchvision은 변경하지 않았다.')
agents = agents.replace('이번 작업 검토: 사용자 확정인 4정답 격자·유형별 약 40% 목표와 8개 조건별 검증 기준을 반영했다.', '이전 작업 검토(40%): 사용자 확정인 4정답 격자·유형별 약 40% 목표와 8개 조건별 검증 기준을 반영했다.')
agents += '\n이번 작업 검토: 2026-10-26 웹 제작 승인으로 범위를 확장하고4종·가변 정답 수·한 참가자 한 판·첫 완벽정답 즉시 종료·오답 재제출을 반영했다. 공유 D1/R2·소유자 인증·사진 등록과 공개 빈 은행, 저장RGB4문제의 실제 ML 선택/실패·별도 고정 나무 사전학습 후보를 확인했다. 도구의 URL 검증 실패에 따른 화면 제어 중단·OS0회와 목표40%/ONNX/Pi/학교 평가 미완료를 유지했다. 새 웹README를 포함해 관리Markdown13개를 검토하며 실제 배포·테스트 결과는 STATUS/CHANGELOG에 기록한다.\n'
write('AGENTS.md', agents)

status = read('docs/STATUS.md')
status = status.replace('최종 검토: 2026-10-22', '최종 검토: 2026-10-26', 1)
status = status.replace('## 최신 확정 목표와 이번 작업', '## 10/22 이력: 40% 목표와 평가 준비', 1)
status = status.replace('이번 작업 검토: 4정답 격자', '이전 작업 검토(40%): 4정답 격자')
marker = '**두 제한 학습 기준 모델의 RTX'
pos = status.index(marker)
historical = status[pos:]
header = '''# 현재 진행 상황

최종 검토: 2026-10-26 (Asia/Pyongyang)

## 현재 결론

인간·봇·사진관리 웹사이트와 공유 D1/R2 출제·채점을 구현했고 최신 한 판 규칙을 반영했다. 저장 RGB에서 실제 ML의 타일 선택 경로도 실행했다. **공개 사진은행은 비어 있고 모델3조건 실패·목표40% 미달성·실제 OS 입력0회이므로 부스 전체 완료가 아니다.** 학교 사진은0장, ONNX·Pi도 미완료다. 관리 Markdown은13개다.

## 최신 경기·사진 계약

- 4종 무작위: 사람3명이상(정답2~4), 나무3그루이상(3~4), 건물/연못 존재(각2~4).
- 같은3×3 사진·순서를 제공하고 봇 준비 후 인간 시작으로 약2초 뒤 공통 startAt을 사용한다.
- 한 참가자 한 판. 먼저 완벽한 선택 집합을 제출한 역할이 승리하고 서버는 즉시 종료한다. 오답은 수정·재제출하며 시작 시각/타이머는 그대로다. 동시 정답 요청도 단일 승자로 확정하고 종료 후 요청은409다.
- 화면은500ms 폴링/네트워크 뒤 공통 result.finishedAt/elapsedMs로 정지한다. 다음 참가자는 새 방·새 연결 코드다. 90초 제한은 미확정 운영 가안이다.
- 관리 /admin의 Sites 소유자 로그인 또는 비공개 운영 키로 사진을 등록한다. 정확 수/나무>=3/미확인, 건물·연못·원본 그룹·출처를 기록한다. 사람/건물/연못 최소4P7N, 나무4P6N 독립 그룹이 필요하고 준비 전 시작을 거부한다.
- 정답·실제 정답 수·원본 파일명/ID·라벨은 서버 전용이다. 공개 사진은 불투명 ID이고 시작/만료/현재 라운드/활성 상태를 검사한다. 학교 등록도 학습 허가가 아니며 모델 고정 후 최종 평가 전용이다.

## 배포·도메인

공유 Site ID는 appgprj_6ade37995018819184a42c88bb0fde7c다. [인간](https://human.marulee.dev)·[봇](https://bot.marulee.dev)·[관리](https://human.marulee.dev/admin)와 [기본 게시 주소](https://alpha-captcha-arena.duckbearmadecowpig.chatgpt.site)를 사용한다. Cloudflare에 기존 충돌 없는2CNAME(DNS only)·검증TXT4개를 만들었고 두 도메인은 native status/provider/SSL 모두active다. 기존 marulee 터널/다른 DNS는 변경하지 않았다. 실제 HTTPS/API 응답·최종 게시 버전은 아래 최종 점검 결과로 별도 기록한다.

운영 DB/R2와 로컬 .wrangler/state는 분리된다. 로컬 Kaggle 데모34장(2,921,524bytes)은 실제 업로드34/34 성공했지만 공개 재배포 권한을 일괄 확인하지 않았으므로 운영에는 올리지 않았다. 공개 사이트에 사진이 없다는 것은 오류를 숨겨 데모로 채운 상태가 아니라 실제 등록 대기 상태다. 운영자 브라우저 로그인·사진 등록 UI는 도구 중단 때문에 미검증이다.

## 실제 ML 저장 RGB 연결 검사

v1 사람 검출은 SSDLite320 MobileNetV3 Large, 건물/연못은 MobileNetV3 Small이다. **YOLO는 사용하지 않았다.** 기존 체크포인트/프로필/원본/split은 보존했다. tree 존재로 수를 지어내지 않고 별도 Grounding DINO Tiny 공식 사전학습 후보를 연결했다. 프로젝트 추가 학습은 없고 고정 revision/hash/prompt/임계값은 SETUP/ARCHITECTURE에 있다. 가중치689,359,096bytes, transformers4.57.3/safetensors0.7.0을 .venv에 추가했고 기존 CUDA torch/torchvision은 유지했다. pip check는 충돌 없음이다.

예측 전에 seed20261026으로4개 시연 격자를 고정하고 모델에는 각192px RGB9타일만 전달했다. 정답 은행은 평가기만 읽었고 정답 수로 선택을 채우지 않았다. 보고서는 [실제 결과](../runs/booth-model-smoke-v1/report.json), 격자/사전계획은 같은 폴더다. 모델 로드는8.904초다.

| 조건 | ML 선택(0..8) | 평가 정답 | 전체 일치 | GPU9타일 호출 |
|---|---|---|---|---:|
| 사람3명이상 | [5] | [0,5] | 실패 | 2.227191초 |
| 나무3그루이상 | [] | [0,1,4,6] | 실패 | 3.066073초 |
| 건물 | [4,5] | [4,5] | 성공 | 0.531181초 |
| 연못 | [] | [1,3,6,8] | 실패 | 0.521821초 |

나무 검출 수는 [0,0,0,0,1,0,1,0,0]이었다. 이 실패에 맞춰 임계값/모델을 재튜닝하지 않았다. 이미 본34사진을 재사용한 각1문제의 기능 검사이므로 **정확도25%·40% 달성·학교 성능·Pi속도·전체 경기 시간으로 보고하지 않는다.** 캡처·OS 클릭은 하지 않은 저장이미지 검사다.

## 화면 봇 구현과 실제 미완료

booth_bot.py/run_booth_bot.py는 공개 phase/roundId/startAt/질문 조건만 받아 화면 RGB→9타일→ML→좌표→최소1초 간격 타일 클릭/제출을 연결한다. 타일URL/ID/정답은 풀이에 쓰지 않고 제출 API를 봇이 우회 호출하지 않는다. 기본dry-run이며 configs/booth-bot.example.json은 calibrated=false·물리좌표0 빈 자리다. --execute 전 실제 창·줌·OS배율·격자/제출/보호영역을 보정해야 한다.

현재 봇은 고정 예측으로 한 번 제출하고 오답 후 자동 재추론/재시도는 없다. --rounds는1만 허용하며 같은 문제 재클릭을 막는다. 상대 정답으로 끝나면 남은 타일/제출을 취소한다. 무작위 반전·답안 이용·임의 클릭 누락으로 성능을 조절하지 않는다.

IAB 접근성 상태로 인간 홈과 대기실 생성까지 확인했다. 네이티브 Chrome 도구가 현재 브라우저 URL을 신뢰성 있게 확인하지 못해 이번 턴의 화면 제어를 중단했다. 다른 OS/브라우저 입력 도구로 우회하지 않았다. **실제 OS 캡처·클릭·제출0회, 스크린샷 시각 QA·좌표보정·실제 클릭간격·소유자 로그인은 미완료**다. 모의콜백/저장RGB/API 성공을 실제 입력 성공으로 대체하지 않는다.

## 이번 검증과 남은 작업

- 전체 Python unittest98개 통과(9.396초). 한 판 제한·중복 입력 차단·상대 승리 중단과 기존 데이터/학습/평가 검사를 포함한다.
- 최신 로컬 실제 D1/R2 HTTP 통합1개 통과(본문3.270711초, runner8.976320초). 권한·시작 동시성·같은 사진·오답 재제출·정답 경쟁 단일 승자·공통 종료·재시작 거부·정답 비공개를 검사했다. 이는 권한을 가진 서버 채점 테스트이며 ML 봇의 풀이가 아니다.
- Node 단위/SQLite/소유자 인증18개와 TypeScript, 사이트 빌드의 최종 결과는 아래 최종 점검에 기록한다. 대상UI ESLint 오류/경고0을 확인했다.
- 새 모델 학습 없이 CUDA 저장RGB 연결·고정 나무 가중치 로드/추론을 실행했다. 학교사진0장·v1재튜닝0·전역Python/드라이버/OS 변경0이다.
- 다음: 권한 있는 실제 사진 등록·운영자 UI 확인, PC 물리보정/실제 캡처·ML·1초 클릭/제출, 충분한 새 Kaggle 개발/선택/audit 및4종 성능평가, ONNX동등성, Pi의 시리얼/사양/추론/GUI 개별검증, 모델고정 후 학교 최종평가다.

## 현재 재현 명령

```powershell
.\\.venv\\Scripts\\python.exe -m unittest discover -s tests
.\\.venv\\Scripts\\python.exe -m compileall -q src scripts tests
.\\.venv\\Scripts\\python.exe -m pip check
.\\.venv\\Scripts\\python.exe scripts/verify_booth_models.py --device cuda --output runs/booth-model-smoke-new
.\\.venv\\Scripts\\python.exe scripts/run_booth_bot.py --help
.\\.venv\\Scripts\\python.exe scripts/check_docs.py --date 2026-10-26
# web/alpha-arena에서
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs
node node_modules/typescript/bin/tsc --noEmit
node C:/Users/Administrator/.codex/plugins/cache/openai-curated-remote/sites/1.1.2/scripts/build-site.mjs
```

HTTP 검사는 로컬 미리보기·34장 은행·메모리의 ALPHA_ADMIN_KEY가 있어야 실행하며 명령줄/파일에 키를 쓰지 않는다. 상세는 SETUP이다. 모든 출력은 새 폴더를 쓰고 v1/report를 덮어쓰지 않는다.

이번 작업 검토: 최신 웹 제작 승인·4종·한 참가자 한 판·첫 완벽정답 즉시 종료·오답 재제출을 실제 코드/테스트와 대조했다. 배포·DNS와 실제HTTPS를 분리하고 공개빈은행·모델 실패·실화면0회·40%미달성·ONNX/Pi/학교 미완료를 기록했다. 아래는10/22 이전 결과의 보존 이력이며 당시의 웹사이트 없음·모델2개·문서12개·추가설치없음은 현재 상태를 뜻하지 않는다.

## 이전 ML·40% 준비의 상세 이력 (2026-10-22)

'''
write('docs/STATUS.md', header + historical)
