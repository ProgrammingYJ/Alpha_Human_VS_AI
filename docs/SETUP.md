# 개발·부스 웹사이트·실행 환경

최종 검토: 2026-11-05 (Asia/Pyongyang)

## A/B 병렬 모드로 실행하기 (2026-11-05)

사용자의 A/B 실제 병렬 추론 요청으로 이전 단일 FIFO 운영 기본값을 대체했다. 원격 실행기 하나가 존재·사람·나무 가중치 한 벌을 공유하며 `SharedModels(..., execution_mode="parallel")`의 독립 작업 슬롯2개와 CUDA stream2개를 사용한다. A/B는 각자 슬롯을 확보해 사진 준비·카운트다운·출발 뒤 추론을 진행하므로 한 레인이 다른 레인의 준비/추론 완료를 기다리는 단일 큐를 사용하지 않는다. 각 방의 인간/AI 공통 출발은 유지하며 서로 다른 방의 절대 출발 시각을 강제로 맞추지 않는다.

각 작업은 `fork_for_inference()`(`fork_for_worker()` 별칭)로 만든 predictor 문맥을 사용한다. 두 제한 모델과 나무 모델의 가중치는 동일 객체이고, 나무 processor/tokenizer·`last_detections`와 메타데이터는 작업별로 분리한다. fork는 모델의 eval·장치 준비 상태를 확인하고 병렬 예측 중 `model.to()`·`eval()`을 반복하지 않는다. 작업 스레드는 자기 CUDA stream과 `torch.inference_mode()` 안에서 실행하고 자기 stream 완료만 동기화한 뒤 결과를 반환한다. 합성 RGB 예열은 방 연결 전에 두 문맥 모두 수행한다.

기본 실행은 `Start-Alpha-Remote.cmd`이며 명시적 직렬 복구는 `Start-Alpha-Remote.cmd -InferenceMode serial`, Python 직접 실행은 `--inference-mode parallel|serial`이다. `serial`은1슬롯 FIFO로 복구하며 실행기를 레인마다 두 개 켜지 않는다. 시작/라운드 보고서의 `inference_mode`, `max_concurrent_inferences`, `cuda_stream_count`, `model_weights_shared`로 실제 설정을 확인한다. 50:50 하드웨어 할당이나 모든 주제의 속도 향상·통신/화면 지연0을 보장하지 않는다. 최신 CUDA 출력/시간/VRAM 검증과 운영 프로세스는 STATUS가 정본이다.

프로토콜3·각 방의 세 역할9사진 준비·출발 전 문제 추론 금지·같은 방 다음 참가자·500ms 전달 여유/250ms 선택 계획은 유지한다. 취소·만료·오류는 해당 슬롯과 라운드에 한정하고 다른 레인의 작업을 해제하거나 중단하지 않는다. 가중치·전처리·임계값·학교 미사용·임의 오답 금지와40%/ONNX/Pi/legacy OS 입력 미완료도 유지한다.

11/05 실제 운영 `SharedModels`를 고정 공개 RGB 두 묶음으로 검사했다. 4유형의16개 순서 있는 조건쌍을 serial/parallel 각각3회 실행했으며 선택 번호·보고 예측의 최대 차이는0, 공유 가중치 객체 동일, OOM0이었다. 두 작업 전체 소요의 중앙값(serial→parallel)은 사람+사람0.534→0.376초, 나무+나무3.504→2.948초였지만 나무+사람은1.553→2.206초로 느려졌다. 모든 조합이 빨라진다는 근거로 쓰지 않는다. 최대 PyTorch 할당1522.18MiB·예약3226MiB는 이 표본의 관측값이다.

나무+나무 별도 Kineto 추적에서44,969개 CUDA kernel·두 stream17/21과 서로 다른 stream의 실제 kernel 겹침0.553852초를 확인했다(GPU 활성 구간 합집합2.857961초). 호스트 호출 겹침을 넘어 GPU 실행이 실제 겹친 이 사례의 근거이며50:50 자원 분할·행사장 무지연 보장은 아니다. 원본은 `runs/parallel-operating-20261105/cuda-report.json`이다. 이 저장 RGB 검사는 HTTP/브라우저·정확도·장시간 부하 검증과 별개이며 공개 두 방 검사·최신 운영 재시작/PID는 STATUS를 따른다.

## 병렬 수정 전 외부 컴퓨터 시험 준비 이력 (2026-11-05)

공개 사이트는 기존 v13을 유지한다. 11/05 인간·봇의 A/B 주소와 두 호스트의 `/api/health` 총6요청이 HTTP200이었고 프로토콜3·사진 준비 배리어·250ms 하한을 확인했다. 새 배포 없이 정규 `Start-Alpha-Remote.cmd`로 이 PC의 운영 콘솔을 켜 두었다. CUDA3모델 로드15.046초·합성 예열3.657초·총18.703초 성공 후 숨김 코드 입력을 기다린다. 이는 문제 사진 추론·방 연결·실제 외부 경기 성공을 뜻하지 않는다. 현재 프로세스와 재현 근거는 [STATUS.md](STATUS.md)가 정본이다.

| 역할 | A 레인 | B 레인 |
|---|---|---|
| 참가자 | [인간 A](https://human.marulee.dev/?lane=A) | [인간 B](https://human.marulee.dev/?lane=B) |
| AI 선택 표시 | [봇 A](https://bot.marulee.dev/?lane=A) | [봇 B](https://bot.marulee.dev/?lane=B) |

1. 외부 컴퓨터의 Chrome에서 위 공개 HTTPS 주소를 연다. 인터넷 접속이 필요하며 같은 Wi-Fi·로컬IP·포트5186 접속이나 외부 컴퓨터의 Python/모델 설치는 필요 없다.
2. 최초에 인간 화면에서 레인별 방을 만들고 그 코드를 같은 레인의 봇 표시 화면과 모델 PC 콘솔에 한 번씩 연결한다. PC 콘솔 하나에 `A CODE8`, `B CODE8`을 차례로 입력해 두 레인을 처리한다. 입력 글자가 숨겨지는 것은 정상이며 실제 코드·토큰을 문서/로그에 남기지 않는다. 이미 켜 둔 실행기를 레인마다 중복 실행하지 않는다.
3. 인간과 AI 표시를 각각 보이는 창/모니터에 둔다. 숨긴 탭은 사진 준비가 완료되지 않을 수 있다. 첫 heartbeat와 PC 준비를 확인한 뒤 시작하면 GPU 예약→세 역할9장 준비→공통 출발 순서로 진행한다.
4. 한 판 뒤 인간 화면의 **다음 참가자 준비 → PC 준비 확인 → 대결 시작하기**를 반복한다. 정상 교체 때 새 방·코드 재입력·모델 재로드는 필요 없다. 운영 PC의 전원·인터넷·콘솔을 유지한다.

위 준비 검사는 병렬 수정 전 FIFO 실행기의 기록이다. 모델 로드/HTTP 성공과 실제 방 연결·병렬 문제 추론·외부 선택/승패는 별도이며 최신 운영 모드·측정·프로세스는 STATUS를 따른다.

## 공개 GitHub 소스에서 시작하기 (2026-11-04)

[ProgrammingYJ/Alpha_Human_VS_AI](https://github.com/ProgrammingYJ/Alpha_Human_VS_AI)의 공개 `main` 첫 푸시와 원격 확인을 완료했다. 최초 소스 커밋은 `1bd9efbdc15ad9b36cdea129d7cbdaa55e3ab30d`이며 로컬 HEAD·ls-remote·GitHub tree가 일치했다. 333개 일반 파일과 gitlink 0개를 확인했고 후속 문서 동기화의 최신 커밋은 STATUS를 따른다. 별도 `C:\Users\Administrator\Desktop\Alpha_Human_VS_AI`에서 공개 소스를 관리하며, 기존 `Alpha-Captcha-AI`의 파일을 이동하거나 Sites Git 이력을 복사하지 않았다.

사용자 요청으로 `Alpha_Human_VS_AI` 공개 저장소에 Python·웹 소스·예시 설정·의존성 목록·문서를 함께 올렸다. 저장소 생성/푸시 결과와 주소는 [STATUS.md](STATUS.md)가 정본이다. 원래 작업 폴더와 Sites 배포용 `web/alpha-arena/.git`는 보존하고, 공개 복제본에서는 웹 파일을 일반 소스로 포함해 서브모듈 초기화가 필요 없도록 했다. GitHub 공개는 기존 인간/봇 사이트의 재배포나 PC 엔진 재시작을 뜻하지 않는다.

공개 복제본에는 `.venv`·`node_modules`·빌드/캐시·`.env`·운영자 키/토큰·기기별 `.local.json`·사진/정답은행·Kaggle/학교 원본·모델 가중치·실행 로그가 없다. 아래 이력의 `data/`, `models/`, `runs/`, `logs/` 경로는 이 PC에서 확인한 별도 산출물이다. 복제만으로 기존 두 v1 체크포인트나 운영34장 은행이 생기지 않으며, 데이터·라벨·고정 모델을 별도 준비해야 실제 추론/학습/사진 가져오기를 실행할 수 있다. 나무 모델은 `scripts/fetch_tree_model.py`로 고정 revision을 다시 받을 수 있지만, 두 제한 학습 v1 체크포인트의 공개 다운로드를 제공한 상태는 아니다.

`runs/` 아래의 관리 QA·실험·문서 도구 중 민감정보 검사를 통과한 스크립트 소스는 원래 경로로 공개하는 예외 대상이다. 같은 폴더의 JSON 결과·카탈로그·로그·사진·실측 산출물은 제외한다. 도구 소스가 있어도 해당 입력 사진/모델·관리 권한·과거 결과 파일이 함께 제공되는 것은 아니다.

과거 게시/재시작용 PowerShell 도구에는 당시의 고정 PID나 경로가 남아 있다. 이는 이력 재현용 보관 소스이며 현재 실행기가 아니므로 그대로 실행하지 않는다. 현재 부스 시작은 아래의 `Start-Alpha-Remote.cmd` 절차를 따른다.

소스 폴더에서 PC 의존성은 아래의 `setup_pc.ps1` 절차를 따른다. 웹만 확인하려면 Node22.13 이상에서 다음 형식으로 의존성을 설치한다. 빈 D1/R2의 출제는 사진 부족으로 거부되며, 기존 운영 사이트의 사진/정답·소유자 권한을 자동 복사하지 않는다. 이 명령 안내와 실제 깨끗한 기기 설치 검증은 구분한다.

```powershell
cd web/alpha-arena
npm ci
npm run dev -- --hostname 127.0.0.1 --port 5186
```

`.sites-runtime/execution-profile.json`이 없는 새 복제본은 코드상 `portable` 프로필을 사용한다. 데이터 저장소를 준비할 때에는 아래 마이그레이션 절차를 따르고, 게시에는 본인 소유 Sites 프로젝트와 비밀 환경을 별도 구성한다. 기존 `.openai/hosting.json`의 식별자만으로 운영 권한이 생기지는 않는다.

선택 간격 정책(2026-10-27, 현재 유지): AI 선택 간격은 **0.25초(250ms)**다. 최신 remote 실행기는 ML 결과를 불변 선택 계획으로 한 번 전달해 타일별 상태조회·선택·ACK 왕복을 없앤다. 서버 수락 뒤500ms 전달 여유를 두고250ms 간격으로 선택한 뒤 마지막 선택 시각에 한 번 제출한다. legacy PC/Pi 클릭 정책의 최소0.25초는 유지한다. 실제 HTTP·화면 속도와 게시/PC 가동은 STATUS가 정본이며 예정 시각을 실측으로 보고하지 않는다. 사용자는 학교 사진을 이번 행사에 넣지 않기로 했다. 운영 사진은 공개 사용 조건과 시각 라벨을 검토한 인터넷 자료로 준비하고 학교 최종 평가는 현재 행사 범위에서 제외한다.

## 명확한 사진으로 문제은행 교체 (2026-11-02)

사용자 요청으로 기존46장의 실제 RGB와 작은 타일 판독성을 다시 검토했다. 작은 사람·가려진 건물·맨가지·원경 수관·경계가 불분명한 물 등22장을 제외하고24장을 유지하며, 명확한 CC0/PD 사진10장을 더한 **34장 교체 은행**을 선정했다. 로컬 정본은 `data/booth/public-web-v3/bank.json`이다. 실제 운영 업로드·활성 전환·배포와 최종 수량/검사 결과는 [STATUS.md](STATUS.md)가 정본이다. 아래의 v1/v2 업로드 수치는 당시 이력이며 로컬 선정을 운영 적용 완료로 해석하지 않는다.

새 사진의 원문 이용 조건·저자·촬영일·SHA·촬영 그룹과 실제 RGB를 검토했다. 모르는 정확한 나무 수는 null로 두고 명확한3그루 이상만 기록한다. 같은 촬영·연속 촬영 관계를 묶으며 학교 사진·모델 예측·학습/임계값 조절은 사용하지 않았다. 이 AI 시각 검토와 사진 교체는 독립 사람 검수·정확도/40% 측정이 아니다.

관리자 조회 `GET /api/admin/photos?includeInactive=1`은 비활성 사진도 `active`·`sha256`과 함께 제공한다. 인증된 `PUT /api/admin/photos`의 `{photoIds:[...]}`는 기존1~128개 고유 사진 ID와 네 유형 준비성을 검증하고 활성 집합 전체를 한 SQL로 교체한다. 원본 라벨·R2 바이트는 삭제하거나 덮어쓰지 않는다. 새 문제에는 활성 사진만 뽑고 이미 생성한 현재 라운드 사진은 보존해 도중에 이미지가 깨지지 않게 한다. 정상 참가자 교체는 계속 같은 방의 다음 참가자 준비를 사용한다.

```powershell
# 34장 로컬 교체 은행 검증. 운영 활성 변경은 하지 않는다.
.\.venv\Scripts\python.exe scripts/import_public_booth_bank.py --bank data/booth/public-web-v3/bank.json --base-url https://human.marulee.dev --output runs/public-v3-import-dryrun-new.json
```

11/02 운영 적용 확인: 사이트 v13·환경 revision5가 게시 성공했다(commit `2cc72fceeed5cbbd1f44eb63a6f52df7067a8880`). 새10장 업로드10/10 후 **활성34장·비활성22장·전체 등록56장**을 확인했고 활성34파일의 SHA/RGB와 합계9,290,899bytes가 로컬 정본과 일치했다. 은행 교체 전 만든 현재 라운드9장 해시는 유지됐으며 그중 퇴역한3장의 URL도 HTTP200이었다. 공개5판에서 네 유형·9개 서로 다른 선언 그룹·정답 수 범위·양 역할의 같은 사진/출발·정답 비공개와 퇴역 재등장0을 확인했다. 운영 카탈로그로 허용된 유형/정답 수11조합을 각각32회, 총352회 추첨해 통과했다. 이는 가능한 모든 격자의 전수 시험이나 독립 정확도352문제가 아니다.

근거는 `runs/photo-clarity-20261102/retry1-production-verification.json`과 `production-bank-combinations.json`이다. 이번 사진 교체 대상 Node33개·실제 localhost HTTP1개(5.806초)·TypeScript·production build·diff 점검이 통과했다. 이 공개 검사는 모델 추론/답안 제출0이며 실제 브라우저 GUI·행사장 리허설·독립 사람 검수를 대신하지 않는다. 최종 전체 문서 점검과 재현/배포 상세는 STATUS/CHANGELOG를 따른다.

## 이전 GPU 동시 추론 후보 검토 (2026-11-02 이력)

11/02 당시 운영 실행기는 공유 모델 한 벌과 FIFO 예약을 유지했고 예약에 사진 준비·공통 카운트다운·모델 반환까지 포함했다. 아래 검토/측정은 당시 이력이며11/05 기본 모드는 상단의 독립2슬롯 병렬로 대체했다. 실행기는 계속 하나만 켠다.

검토 후보는 한 프로세스에서 A/B별 CUDA stream에 독립 추론을 올리거나 적합한 같은 모델 입력을 묶는 방식이다. GPU 자원이 허용하면 작업이 겹칠 수 있으나 두 레인에 계산 자원을 정확히 50%씩 보장하는 설정은 아니다. 메모리 한도를 나누는 것만으로 계산 시간이나 출발 시각이 나뉘지도 않는다. RTX 4070 Laptop은 NVIDIA의 MIG 지원 GPU 목록에 없으며, 현재 설치된 PyTorch의 Green Context 경로는 Windows를 거부한다. 자세한 근거와 공유 모델의 상태 변경 주의점은 [ARCHITECTURE.md](ARCHITECTURE.md)를 따른다.

운영 채택 전에는 같은 RGB의 출력 동등성, 레인별 처리 시간, 전체 소요 시간, 피크 VRAM과 모든 문제 조합을 별도로 측정해야 한다. 이번 오프라인 비교의 실제 결과·한계는 [STATUS.md](STATUS.md)가 정본이다. 웹의 세 역할 사진 준비·출발 뒤 실제 추론·250ms 선택 간격과 같은 방 반복은 유지하며, 동시 추론이 지연 0을 보장한다고 안내하지 않는다.

11/02 저장 RGB 9장·모델 한 벌·조합별 3회 비교에서 두 작업이 모두 끝나는 시간의 중앙값은 직렬→두 stream 순으로 존재+사람 0.386→0.299초, 나무+존재 1.171→1.847초, 나무+나무 2.238→3.033초였다. 출력은 이 표본에서 같았고 메모리 부족 오류는 없었으나 나무 조합은 느려졌다. HTTP·사진 준비·화면이 없는 작은 비교이고 실제 GPU 커널의 동시 실행은 추적하지 않았다. 원본은 `runs/gpu-concurrency-20261102/report.json`이며 이11/02 검토 당시 운영은 FIFO였으며11/05 기본값은 병렬로 대체했다.

## 이전 A/B 직렬 예약의 기다리는 구간 (2026-11-01 이력)

11/01에는 A의 모델 반환 뒤에야 B가 준비·공통 출발·추론할 수 있는 직렬 예약을 사용했다. 모델 한 벌과 경기 진행 겹침은 유지하되 이 예약 정책은11/05 독립2슬롯 병렬로 대체한다. 각 방의 인간/AI 공통 출발은 유지하고 A/B 두 방의 절대 출발 시각을 강제로 일치시키지 않는다.

11/01 공개 CUDA 기록에서 A1의 시작 전 예약 대기는0.375초, B1은10.438초였고 두 판 모두 경기 중 GPU 대기는0초였다. B의 시작 전 대기는 먼저 예약한 A의 사진 준비·카운트다운·추론과 상태 HTTP/문맥 확인의 영향을 받으며 순수 GPU 연산 시간이나 모든 경기의 고정 대기값이 아니다. 두 세션 실행은 확인했지만 통신·화면 지연0, 모든 주제 조합과 장시간 부하까지 보장한 검사는 아니다. 측정 정본은 STATUS와 `runs/reliability-public-20261101-v1/`이다.

## 사진 준비 후 공통 출발과 PC 지연 수정 (2026-11-01)

현재 remote 출발 순서는 **인간 시작 요청 → GPU 예약 대기 → loading에서 인간 화면·AI 표시 화면·PC의 사진9장 준비 → 세 역할의 준비 확인 → 약2초 공통 카운트다운 → 실제 문제 판별**이다. loading의 질문·시작 시각은 비공개이고 타이머는0이다. 브라우저는 숨긴 동일9개 이미지 노드를 실제로 디코딩하고 PC는9개 RGB를 최대3개 병렬로 받아 준비한다. 인간과 AI 표시 창은 공통 출발까지 둘 다 앞에 보이는 상태로 두며, 같은 창의 배경 탭은 준비 완료를 보류한다. 사진 URL은 loading부터 불투명 라운드 경로로 사용할 수 있지만 정답·원본 파일명·실제 정답 수는 제공하지 않는다. 시작 때 같은 브라우저 이미지와 PC의 같은 RGB 캐시를 재사용하고 실제 문제의 ML 판별은 playing 뒤에만 수행한다. 이전의 begin 즉시2초 출발·출발 후 사진 다운로드 설명은 아래에 남은 당시 이력이다.

`imageLoad`의 공통 준비 번호와 humanReady/botReady/engineReady를 사용한다. PC의 `images_ready`는 roundId·roundNumber·requestId·imageLoadId에 묶인다. 시작 전 페이지를 새로 열거나 새로고침하면 준비 번호와 세 플래그를 다시 확인하며, 이미 디코딩한 동일 라운드/동일 순서의 RGB는 재사용한다. 준비 번호가 달라진 옛 ACK나 다음 판 사진에는 캐시를 전용하지 않는다. 준비 ACK가 유실되고 재전송 때 이미 출발한 경우는 새 서버 조회에서 같은 라운드·요청·준비 번호와 세 플래그의 완료를 증명한 때만 복구한다. 경기 시작 뒤의 새로고침은 이미 시작한 타이머를 되돌리지 않으므로 참가자 교체에는 새로고침 대신 같은 방의 다음 참가자 준비를 사용한다.

사진 준비60초·GPU 대기120초·경기90초는 운영 가안이다. 준비 실패·취소·만료는 대기실로 복귀하고 인간이 다시 시작한다. 기존15초 엔진 생존 검사는 유지한다. 단순 viewer 참가나 모델 로드만으로 사진 로딩 완료를 표시하지 않는다. 새 서버에는 protocol3가 필요하고 과거 v11처럼 사진 준비 지원 필드가 없는 서버만 protocol2로 협상한다. 새 서버가 지원false를 알리는 경우는 준비 전 상태이므로 배리어를 우회하지 않는다. 대기실에서 새 서버 배포를 관측하면 같은 엔진 토큰으로 다음 생존 알림을3으로 올리며 이미 진행 중인 구형 판은 기존 계약으로 끝낸다.

PC는 방 연결을 허용하기 전에 합성 회색 RGB9장으로 존재·사람·나무 세 고정 모델을 예열한다. 실제 문제·학교 사진·정답은 예열에 사용하지 않고 startup에 모델 로드/예열/전체 시간을 나눠 기록한다. 건물·연못에는 기존 존재 모델만, 사람 문제에는 기존 사람 검출 모델만 실행해 질문과 무관한 연산을 생략한다. 가중치·전처리·임계값·NMS·계수·타일 선택 규칙은 유지하며 미실행 항목은 None으로 남긴다. 전체 예측 API는 보존하고 같은 공개 RGB9장에서 전체 실행과 대상별 점수/계수·선택 동등성을 별도 검사한다.

Python 기본 통신은 origin에 묶인 표준 http.client의 HTTP/1.1 연결을 호출 스레드별로 재사용한다. 리다이렉트·관리 API·외부 호스트는 허용하지 않으며 엔진 토큰은 방 API에만 전달한다. 읽기 GET은 일시 연결 오류에 한 번만 재시도한다. begin·사진 준비·불변 plan·개별 sequence는 기존 멱등 본문을 그대로 제한 재전송하며 일반 POST를 무조건 재전송하지 않는다. 새 배리어+plan 경로의 추론/선택 stage 표시는 주기 heartbeat로 전송해 경기 안의 동기 왕복을 줄인다. GPU 예약/사진 준비의 서버 확인과 모델 직전 상태 확인, 서버의 계획/승패 검증은 유지한다. 사진3개 worker와 연결은 종료 시 정리한다.

사진 준비에는 추가 migration `0004_amazing_namora.sql`이 round의 준비 번호/만료 시각/세 역할 준비 플래그5열을 더한다. 기존0000~0003은 변경하거나 다시 적용하지 않는다. 실제 로컬/운영 적용은 STATUS를 확인한다.

검증 스크립트 `scripts/verify_continuous_booth.py`는 실제 PC 모델을 한 번 로드해 A두판+B한판을 진행하고, 인간/봇 역할도 각각9개 공개 RGB를 실제 다운로드·PIL 디코딩한 뒤 준비를 알린다. A첫판 인간 준비를3초 보류해 PC/봇 준비 뒤에도 타이머0·사전 추론0인지 검사한다. 이 보류는 시험 조건이며 운영 지연 설정이 아니다. HTTP/PIL 시험은 실제 브라우저 렌더링 시험과 별개다. 같은 RGB의 출력 동등성과 준비/모델/HTTP 시간, 경기 중 사진 다운로드0을 기록하며 독립 정확도·목표40% 달성이나 지연0을 주장하지 않는다. 실제 게시/실측·현장 기기/네트워크의 미확인 범위는 STATUS가 정본이다.


## 선택 계획으로 통신 대기 줄이기

PC는 loading에서9사진을 **최대3개 병렬 다운로드**하고 결과를 원래 타일 순서로 유지한다. 각 사진은 기존의 통제된 공개 경로·바이트/픽셀 크기·RGB 디코딩 경계를 그대로 통과한다. 한 장이라도 실패하면 시작한 다운로드 작업을 정리한 뒤 해당 추론을 중단하며 부족한 사진을 다른 타일로 메우지 않는다. 선택 전송 방식만 서버의 `selectionPlanSupported=true`에 따라 결정한다.

GPU 예약 뒤 세 역할의9사진 준비를 확인하고 인간/AI가 공통 출발한다. 캐시 RGB의 추론 함수가 반환하면 먼저 GPU를 해제한다. 그 뒤 `plan` 요청 하나에 실제 모델의 선택 번호만 보내고 서버가 정한 첫 시각과250ms 간격을 사용한다. 9개 선택의 계획은500ms 여유+2초 재생으로 수락부터 최종 제출까지 최대2.5초다. 0개 예측도 그대로500ms 뒤 한 번 제출하며 정답 수에 맞춰 채우지 않는다. 첫500ms는 전달/표시 여유이며 legacy의 첫 클릭0초 가안과 구분한다. 이 예정 길이는 네트워크·모델 추론·실제 브라우저 표시 시간을 포함한 경기 속도 보장이 아니다.

계획은 라운드마다 하나로 고정하고 응답 유실 시 같은 순서/같은 번호의 재전송만 기존 계획으로 ACK한다. 다른 계획·기존 개별 선택과의 혼용은 거부한다. 서버가 계획을 수락한 뒤 PC 연결이 끊겨도 이미 맡긴 재생/최종 제출은 서버가 처리하며, 인간이 먼저 완벽 정답을 제출하면 남은 선택을 종료 시각에서 중단한다. PC는 이후 heartbeat와 상태 관측만 수행한다. 지원 필드가 없는 이전 서버에서는 기존 개별 선택/제출 경로를 유지한다.

보고서의 `selection_transport=scheduled_plan`, `planned_selection_events`, `plan_upload_*`는 예정 시각과 업로드 왕복이다. `selection_events`는 실제 개별 전송 기록에만 사용하므로 계획 경로에서는 빈 배열이다. `submit_sent=false`는 별도 submit HTTP를 보내지 않았다는 뜻이며 `logical_submission_count=1`과 `server_submission_observed`로 계획 수락과 실제 서버 시도를 구분한다. 모델 함수/상태 HTTP의 기존 schema2 시간과 선택 계획의 schema3 기록도 구분한다. 계획 수신 전 봇125ms·수신 후500ms 상태조회와 서버시계 재생을 사용하고 인간/그 외 단계는500ms다. 실제 네트워크·렌더링 지연 때문에 정확250ms 화면 전환을 보장하지 않는다.

계획 저장에는 추가 전용 `0003_colorful_cassandra_nova.sql`의 round nullable4열이 필요하다. 기존0000~0002를 수정하거나 다시 적용하지 않는다. 실제 migration 적용·서버 채점 경합/계획 UI·공개 속도·CUDA·배포 결과는 STATUS에서 확인한다.

## 이 PC

프로젝트 위치는 `C:\Users\Administrator\Desktop\Alpha-Captcha-AI`입니다. Python 3.12.3 기반의 `.venv`를 프로젝트 내부에 만들었습니다. 하드웨어 실측값은 [AGENTS.md](../AGENTS.md)에 있습니다. 전역 Python 패키지, GPU 드라이버, 시스템 실행 정책은 변경하지 않습니다.

설치 완료 여부와 실제 버전은 [STATUS.md](STATUS.md), `requirements/windows-py312.lock.txt`, `logs/environment-check.json`에서 확인합니다. 기존 Windows 잠금 파일·환경 로그는 초기 설치 스냅샷이며 10/26 선택 패키지 추가는 `requirements/booth-tree.txt`와 STATUS를 함께 확인합니다. Windows 스냅샷은 Pi의 잠금 파일로 사용하지 않습니다.

## 2026-10-26 승인된 웹사이트 범위와 현재 확인

사용자가 사람·AI 부스 웹사이트 제작을 명시적으로 승인하여 이전의 웹사이트 별도 제작/범위 제외 조건을 대체했습니다. `web/alpha-arena/`에 Vinext 기반 전체 스택 앱을 만들었습니다. 사람용 `human.marulee.dev`, AI용 `bot.marulee.dev`는 같은 백엔드와 대기실을 사용하는 배포 대상 주소입니다. **실제 원격 배포·DNS·도메인 연결 완료 여부는 [STATUS](STATUS.md)를 기준으로 확인**하며 로컬 성공만으로 연결됐다고 보고하지 않습니다.

현재 웹 문제는 사람 3명 이상·나무 3그루 이상·건물 존재·연못 존재의 4개 테마입니다. 정답 수는 사람/건물/연못 2~4개, 나무 3~4개를 무작위로 고릅니다. 같은 원본/촬영 그룹·동일 바이트 사진은 한 문제에 중복 배치하지 않습니다. 이전 4P/5N·8조건별 40%는 모델 난이도 평가 목표이며 현재 모든 웹 문항의 정답 수를 4개로 강제하는 규칙이 아닙니다. 목표 달성 모델은 아직 없습니다.

사람 화면에서 대기실을 만들고 AI 표시 화면과 PC 엔진이 코드로 참가·준비합니다. 원격 화면에서 시작을 누르면 먼저 **경기 전 GPU 예약 대기**가 되고 PC가 자원을 확보하면 세 역할의9사진 준비를 기다리고, 모두 완료한 뒤 서버가 **2초 뒤 공통 startAt**을 양쪽에 동일하게 제공합니다. GPU 대기에는 질문·사진이 없고 타이머는0이며, loading에는 사진만 숨겨 미리 받고 질문·타이머는 공개하지 않습니다. **한 참가자는 한 라운드만 진행하며 먼저 완벽한 선택 집합을 제출한 쪽이 승리하고 양쪽 경기가 즉시 종료**됩니다. 오답은 같은 문제·시작 시각에서 수정·재제출할 수 있습니다. 원격 A/B는 같은 방·코드·연결을 유지하며 결과에서 ‘다음 참가자 준비’ 후 다음 사람이 시작합니다. 자동 연속 시작은 아닙니다. 기존 OS/legacy만 새 참가자마다 새 방이며 기존 직접 시작을 유지합니다. **90초 제한은 운영 가안**입니다. 실제 게시·PC 가동은 STATUS를 따릅니다.

로컬 `http://127.0.0.1:5186`에서 페이지 HTTP 응답, D1 마이그레이션, R2 데모34장과 API를 점검했습니다. 오답 재제출·타이머 유지·단일 승자는 유지하고, 같은 방 재시작 거부는 legacy에만 남겼습니다. 원격 방은 종료 라운드의 원자 초기화·같은 코드로 두 라운드 진행·이전 요청 거부를 추가 검증했습니다. 제출과 경기 종료는 D1 트랜잭션으로 처리하고 공통 `result.finishedAt`·`result.elapsedMs`로 양쪽 타이머를 멈춥니다. 이전 URL 확인 실패 후 PyAutoGUI로 우회하지 않은 이력과 실제 ML·현장 화면·최종 운영 검증은 구분하며 최신 결과는 STATUS를 따릅니다.

사진 등록 전의 게시 버전 2에서 두 사용자 도메인·기본 Sites 주소의 HTTPS 200과 도메인 간 대기실 생성·AI 참가/준비·사람 화면의 공유 상태를 공개 HTTP/API 8개 검사로 확인했습니다. 당시 빈 운영 문제은행의 시작은 HTTP 409 `bank_not_ready`로 중단됐습니다. 식별용 `AlphaCaptchaBoothBot/1.0` 헤더를 추가한 실제 Python PublicRoomSession의 공개 참가·상태 조회도 통과했습니다. 후자는 준비·사진·제출/관리 API나 화면을 사용하지 않았습니다. 기록은 `runs/site-publish/python-bot-http-verification.json`과 `runs/site-publish/public-http-verification.json`이며 역할 토큰·대기실 코드/ID를 보관하지 않았습니다. 이 검사는 실제 정답 경기나 화면 입력 검증이 아니며 새 공개 사진 등록 이후 결과의 정본은 STATUS입니다.

## 웹 저장소·운영자 인증·로컬 명령

`.openai/hosting.json`은 Sites의 `DB`(D1)와 `BUCKET`(R2)를 선언합니다. 사진 정답/출처는 서버 전용 D1, 실제 사진은 R2에 저장하고 메모리 대체 저장소는 사용하지 않습니다. 바인딩이 없으면 요청을 실패시키며 로컬 `.wrangler/state`와 원격 저장소는 별개입니다. 기존 `drizzle/0000_living_ma_gnuci.sql`은 변경하지 않았습니다. 10/27 원격 엔진용 테이블만 추가하는 `drizzle/0001_past_rocket_racer.sql`을 새로 생성해 로컬에1회 적용했습니다. 이미 적용한 마이그레이션은 다시 실행하지 않으며 운영 적용·게시 버전은 STATUS를 따릅니다.

GPU 예약 시작에는 `drizzle/0002_mysterious_ravenous.sql`이 필요합니다. `npm run db:generate`1회로 만든 추가 전용 migration이며 room의 요청ID/요청·만료시각/취소사유4열과 remote의 `engine_protocol DEFAULT1 NOT NULL`1열만 추가합니다. 과거0000/0001은 수정하지 않았고 데이터·토큰을 초기화하지 않습니다. 새0002의 실제 로컬/운영 적용 여부는 STATUS를 확인하고 이미 적용된 SQL을 반복하지 않습니다.

공개 대기실 응답은 질문 조건·불투명한 라운드별 사진 URL·서버 시각·제출 결과만 제공하고 정답 개수·라벨·원본 ID·파일명은 제공하지 않습니다. 시작 전 사진은 화면에서 숨기되 loading부터 준비용 바이트 요청을 허용합니다. 새 출제는 활성 사진만 쓰지만, 은행 교체로 비활성화해도 이미 생성한 현재 라운드의 사진은 보존합니다. 현재 결과 화면의 사진은 대기실 만료 전까지 표시할 수 있고, 과거 데이터에 다음 라운드가 있더라도 이전 URL을 차단합니다. 역할 토큰은 서버에 SHA-256으로 저장합니다. 관리자 목록과 정답은 일반 참가자에게 열리지 않습니다.

운영자는 `/admin`에서 **Sites 소유자로 로그인**해 키를 입력하지 않고 사용할 수 있습니다. 서버의 `ADMIN_OWNER_ID`와 Sites dispatch가 인증한 `oai-authenticated-user-id`가 정확히 일치할 때만 허용합니다. 방문자·다른 계정·소유자 ID 미설정은 권한을 얻지 못합니다. 로그인은 공식 `/signin-with-chatgpt?return_to=/admin`의 최상위 이동을 사용하며 브라우저 코드가 사용자 ID 헤더를 만들어 보내지 않습니다. 로컬 portable 미리보기의 `local_seedy` 모의 로그인은 개발 전용이며 운영 배포 인증을 대신하지 않습니다. 실제 소유자 로그인 UI 검증은 아직 남았습니다.

자동화/CLI용 `ADMIN_KEY` 인증도 유지합니다. 값은 서버 환경 또는 실행 중 메모리에만 두고 소스·명령 인자·Git·로그·hosting manifest에 기록하지 않습니다. `scripts/with_booth_secret.mjs`는 숨긴 stdin에서 키를 받아 자식 프로세스 환경/stdin으로만 전달하는 로컬 QA 도구입니다. 키 원문 보관 파일이나 사용자에게 전달할 공용 기본 키는 만들지 않았습니다.

프로젝트 루트에서 다음과 같이 웹 점검을 실행합니다. 의존성은 Node 22 환경에 설치했습니다. 패키지 입력이 바뀌지 않았다면 설치를 반복할 필요는 없습니다.

```powershell
cd web/alpha-arena
npm run dev -- --hostname 127.0.0.1 --port 5186
```

별도 터미널에서 다음을 실행합니다. `db:generate`는 스키마 변경 후 새 마이그레이션을 만들 때만 사용합니다. HTTP 통합 검사는 로컬 데모 은행·메모리 운영자 키가 있을 때만 실행되며 환경이 없으면 생략됩니다.

```powershell
cd web/alpha-arena
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs server/gpu-start.test.mjs
npx tsc --noEmit
node --test server/http.test.mjs
$env:ALPHA_BASE_URL = 'http://127.0.0.1:5186'
node --test server/remote.http.test.mjs
node --test server/gpu-start.http.test.mjs
# 아래 특권 localhost 서버 채점 감사는 메모리의 ALPHA_ADMIN_KEY도 필요하다.
node --test server/remote-rounds.http.test.mjs
```

로컬 전용 Kaggle 데모는 `data/booth/demo-bank.json`과 `demo-images/`의 **34장·2,921,524 bytes**입니다. 학교 사진은 0장이며 이 데모의 공개 재배포 허가를 확인한 상태가 아니므로 원격 사이트에 자동 게시하지 않습니다. 실제 사진·정답 파일은 웹 `public/`에 넣지 않았습니다. `scripts/import_booth_demo.py`는 localhost만 허용하며 `--execute --admin-key-stdin`을 명시해야 업로드합니다. 운영자용 채점 통합 테스트가 비공개 정답을 읽는 것과 ML 풀이기가 정답을 읽는 것은 분리했습니다. ML runner는 관리자 목록·정답 파일을 읽지 않습니다. 기존 OS runner는 화면 RGB·화면 제출을 유지하고, 사용자 승인된 새 remote 엔진은 공개 사진 URL을 RGB 전송에만 쓰고 엔진 API로 실제 모델 선택·제출을 처리합니다.

운영자 업로드는 JPEG/PNG/WebP의 용량·서명·SHA와 라벨 형식을 검사합니다. API의 바이트 서명 검사가 완전한 이미지 디코딩이나 주석 정확도를 보장하지는 않습니다. 파일 원래 이름은 공개 URL에 쓰지 않습니다. 정확한 나무 총수가 불명확한 숲은 `treeCount=3`으로 만들어 넣지 않고 `treeAtLeast3` 또는 검토한 하한을 사용합니다. 하한 0/1/2만으로 3그루 미만이라고 판정하지 않습니다. 최신 사용자 결정으로 학교 사진은 이번 운영에 등록하지 않습니다. 향후 학교 자료를 별도 취급하더라도 학습·개발 검증·모델/전처리/임계값 튜닝에 자동 편입하지 않는 기존 안전 경계를 유지합니다.

## 공개 웹 테스트 사진 가져오기

사용자가 웹 사진을 내려받아 운영 사이트에서 테스트하도록 명시적으로 요청했습니다. 기존 Kaggle 데모를 공개 허가 자료로 바꾸지 않고 별도 `data/booth/public-web-v1/bank.json`을 사용합니다. Wikimedia의 Public domain13장·CC0 11장을 새로 확보해 **24장·24원본 그룹·6,063,549bytes**를 준비했습니다. 원본 출처·저자·이용 조건과 다운로드 SHA를 기록하고 RGB를 검토해 문제용 라벨을 붙였습니다. 학교 사진·개발 train/val/test·모델 가중치와 분리하며 이 시험 사진으로 모델을 학습하거나 40%에 맞춰 튜닝하지 않습니다. 원격 등록/출제 결과는 STATUS를 따릅니다.

`scripts/import_public_booth_bank.py`는 이 별도 공개 은행을 검증하는 기본 dry-run입니다. `publicDeploymentCleared=true`, `schoolPhotosUsed=false`, 사진별 `source=other`, Public domain/CC0의 provenance·HTTPS 출처·다운로드 SHA가 필요합니다. 실제 파일 경계·중복 ID/바이트·원본 그룹 기록·Pillow 디코딩·8MiB 상한과 모순 없는 라벨을 검사합니다. 정확한 나무 수가 불명확하면 null과 명시적 >=3 판정을 보존합니다.

실제24장에 대한 dry-run은 통과했고 기록은 `runs/public-booth-import-dryrun-reviewed-v1.json`입니다. 이어 운영 human.marulee.dev의 관리자 API에 **검증24장·업로드24장·이미 등록0장·완료true**로 등록했습니다. 실제 운영 결과는 `runs/site-publish/public-bank-upload.json`에 있으며 운영자 키 저장/로그는 없고 학교 사진·학습·모델 튜닝도0입니다. 각 provenance JSON은 최대1127자로 서버4000자 상한보다 작았습니다. 문제용 라벨의 시각 검토는 단일 AI 검토이며 독립 사람 검수를 대체하지 않습니다. 사진 등록은 확인했지만 소유자 브라우저의 수동 업로드 UI·실제 ML 화면 클릭은 별도 미검증이며 최종 원격 준비성·사진 표시·경기 결과는 STATUS를 따릅니다.

```powershell
.\.venv\Scripts\python.exe scripts/import_public_booth_bank.py --bank data/booth/public-web-v1/bank.json --base-url https://human.marulee.dev --output runs/public-booth-import-dryrun-new.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_public_booth_import.py -v
```

실제 업로드는 `--execute --admin-key-stdin`을 명시하고 숨긴 stdin 도우미로 운영자 키를 메모리에 전달합니다. 키를 인자·파일·문서에 쓰지 않습니다. 공개 대상은 HTTPS 기본 포트의 human.marulee.dev/bot.marulee.dev로 제한하고 개발 localhost도 허용합니다. HTTP 리다이렉트에는 키를 전달하지 않습니다. 동일 SHA에 대한 서버의 `409 duplicate_photo`만 이미 등록된 사진으로 건너뛰며 다른 오류는 중단합니다. 기존 사진의 라벨을 덮어쓰지 않습니다. 행마다 비밀값 없는 결과를 checkpoint하고 다시 실행할 때는 새 출력 파일을 사용합니다. 원본 그룹과 출처 검사가 수동 라벨의 사실 여부를 자동 보증하지는 않습니다.

## 화면 기반 AI runner와 나무 검출 선택 기능

### 기존 OS 입력 경로: 자동 클릭이 없었던 원인과 Windows 실행기

이전 자동 클릭 문의 당시 로컬 `run_booth_bot.py` 프로세스와 `configs/*.local.json` 실측 설정이 없었고, 예시는 `calibrated=false`와 좌표0인 상태였다. 기존 웹의 봇 참가/준비 버튼은 서버의 참가 상태만 바꾸므로 모델 실행이나 마우스 제어를 시작하지 않는다. 사이트만 열어서는 로컬 AI가 동작하지 않는다. 현재 별도 원격 엔진의 가동은 아래 원격 운영 항목과 STATUS를 따른다.

프로젝트 루트의 **`Start-Alpha-Bot.cmd`**를 사용자가 직접 실행하는 경로를 추가했다. 이 파일은 `scripts/start_booth_bot.ps1`을 프로세스 한정 `ExecutionPolicy Bypass`로 호출하며 시스템 실행 정책은 변경하지 않는다. PS1은 Windows PowerShell5.1의 한글 처리를 위해 UTF-8 BOM으로 저장했고 실제5.1 파서로 구문만 검사했다. 설정이 없으면 사용자 수동 F8 보정기를 호출하고, 실측 후에는 [legacy 인간 화면](https://human.marulee.dev/?mode=legacy)에서 **새 방**을 만들어 연결 코드를 입력한다. 기본 remote 방은 이 실행기의 준비 API와 호환되지 않는다. 기존 미보정 설정을 다시 만들 때는 `Start-Alpha-Bot.cmd -Calibrate`를 명시한다. 기존 설정의 자동 교체는 하지 않는다.

보정할 때는 주 모니터의 봇 페이지를 열고 사용자가 F11 전체화면과 OS/Chrome100%를 직접 맞춘다. 사진9칸과 제출 버튼이 동시에 보여야 하며 창·스크롤·줌을 바꾸지 않는다. 타일 간격의 기본8은 물리픽셀이므로 다른 배율은 실제 간격을 별도로 측정한다. F8은 격자 좌상단/우하단·제출중심·질문 보호영역 두 모서리를 기록하며 타이머/선택개수/움직이는 부분은 보호영역에서 제외한다. Esc·실패는 기존 설정을 보존하고 교체는 성공 시에만 백업 후 수행한다. 이 도구는 사용자의 위치·키 상태를 읽으며 클릭·키입력·화면캡처를 자동으로 수행하지 않는다.

```powershell
# 프로젝트 루트에서 사용자가 직접 실행한다.
.\Start-Alpha-Bot.cmd
# 보정 다시 하기. 원래 설정은 보정기의 백업 정책을 따른다.
.\Start-Alpha-Bot.cmd -Calibrate
# 이미 실측한 설정으로 모델·캡처만 검사하고 실제 클릭/자동 ready는 하지 않기.
.\Start-Alpha-Bot.cmd -DryRun
```

실행기는 기본 CUDA·고정 나무 모델·한 판만 사용하고 `runs/booth-live/<시각-고유값>/`에 새 보고서를 만든다. 웹 봇 화면에서 먼저 코드로 참가하면 역할이 이미 소비되어 실행기의 참가가409로 거절된다. 이때 기존 토큰을 가져오거나 덮어쓰지 않고 `human.marulee.dev/?mode=legacy`에서 새 방을 만든다. 실행기는 모델3개를 불러오고, 직접 봇 역할로 참가한 뒤 브라우저를 연다. 명시적 `--execute --ready` 경로는 **보정된 전면 ALPHA BOT 창·캡처 범위의 격자/질문 보호영역/제출 좌표를 확인한 후에만** 서버에 준비를 알린다. 이것이 사진9장 로딩이나 실제 클릭 성공까지 보증하는 heartbeat는 아니다.

실행 중 봇 창이 전면에 있어야 한다. 인간은 패드 등 별도 기기에서 시작한다. 같은 PC에서 인간 화면으로 전환해 시작했다면 봇 창으로 돌아와야 하며, 다른 창이 전면이면 봇은 안전하게 중단한다. 한 판이 끝나면 실행기가 종료되므로 다음 참가자는 새 방·새 코드로 다시 실행한다. 예시 좌표를 `calibrated=true`로 임의 변경하거나 이미 선택한 같은 문제에 재실행해 토글하지 않는다.

### 컴퓨터 브라우저·A/B 원격 운영 (2026-10-27 후속 변경)

사용자가 승인한 원격 선택·HTTP 엔진 제출 경로를 유지하며 인간·AI 표시 화면을 컴퓨터 브라우저로 운영합니다. 기존 PyAutoGUI 경로는 보존하고 `remote` 방에서 이 PC의 고정 모델을 공유합니다. 봇 화면은 읽기 전용으로 서버가 수락한 선택을 표시하며 PC가 두 방의 RGB를 판별합니다. 전면창·물리 마우스·F8 보정에 의존하지 않습니다. 최신 원격 게시·실제 GPU·화면 검증 결과는 STATUS를 기준으로 확인합니다.

이전 Android 태블릿4대 계획은 사용자의 컴퓨터 브라우저 운영 요청으로 대체됐습니다. A/B별 인간 화면과 읽기 전용 AI 표시 화면, 총4개 화면 역할은 유지합니다. 물리 컴퓨터 대수·각 화면의 OS/브라우저 버전·해상도·배율·현장 성능은 확정하거나 실측하지 않았습니다. 추론은 이 PC에서 실행하므로 표시용 브라우저에는 Python·모델·PyAutoGUI를 설치하지 않습니다.

통신은 각 브라우저와 PC 엔진이 공개 서버에 보내는 **HTTPS API 요청**입니다. 컴퓨터끼리 raw TCP로 직접 연결하거나 전용 소켓을 계속 열어 동기화하지 않습니다. remote AI 표시는 진행 중 계획 수신 전125ms, 수신 후500ms 상태조회와 서버시계 재생을 사용합니다. 인간 화면과 그 외 단계는500ms이며 이전 요청이 끝나지 않았으면 겹쳐 보내지 않습니다. PC 엔진은 약3초 주기의 heartbeat로 생존을 알립니다. 이전 urllib 읽기 확인은 HTTP/1.1이었으며 현재 PC는 표준 http.client의 HTTP/1.1 연결을 재사용하지만 브라우저의 실제 HTTP/2·HTTP/3 협상은 측정하지 않았으므로 전체 통신을 모두 TCP라고 단정하지 않습니다. 같은 방·토큰을 유지한다는 뜻은 애플리케이션 세션이 유지된다는 뜻이며 하나의 TCP 연결을 계속 유지한다는 뜻이 아닙니다.

같은 Python 환경에서 공개 봇 홈을 읽기 전용 HTTPS GET으로 조회해 HTTP200과 `response.version=11`(HTTP/1.1)을 실제 확인했습니다. 이는 해당 요청의 결과이며 브라우저 협상·추론·GPU 속도 측정이 아닙니다.

이 PC의 원격 실행기 하나가 존재·사람·나무 가중치를 한 번 불러 공유하고 기본 parallel2슬롯·CUDA2stream에서 A/B를 독립 처리합니다. 각 레인의 사진 준비·카운트다운·출발 뒤 추론이 다른 레인의 완료를 기다리지 않습니다. 방·라운드·heartbeat·선택·제출과 작업별 processor/진단은 분리합니다. 필요할 때만 `-InferenceMode serial`로1슬롯 FIFO를 명시합니다. 이전 v8의 A1 추론1.547초/대기0.391초·B1 추론0.844초/대기2.250초는 상태조회 HTTP가 포함된 직렬 이력이며 현재 병렬 속도로 쓰지 않습니다. 최신 출력/시간/VRAM·가동은 STATUS를 따릅니다.

이전v8은 공통 startAt 이후 GPU 잠금을 기다려 다른 방 때문에 AI가 늦고 그 참가자가 상대적으로 유리할 수 있었습니다. 위 A1/B1은 그때의 상태조회 포함 샘플이며 순수 GPU 대기 차이·모든 경기의 공정성 검증값이 아닙니다.

후속 승인으로 **시작 요청→경기 전 작업 슬롯 확보→해당 방의 세 역할9사진 준비→공통 카운트다운→사람·AI 동시 시작→캐시 RGB 추론→GPU 해제**를 구현했습니다. 추론을 마친 방의 최소0.25초 선택은 다음 방의 추론과 겹칠 수 있습니다. queued에는 round를 만들지 않아 누적 번호도 그대로이고 사진/문제/시작시각은 비공개·타이머0입니다. 사진 사전 풀이·타이머 사후 보정·추가 임의 지연은 없습니다. 현재 parallel은 두 방의 슬롯을 독립 확보하며 각 방의 출발 전 준비를 지키는 구현입니다. 실제 GPU/HTTP/UI·배포와 남은 네트워크 차이는 별도 검증이고 정본은 STATUS입니다.

시작 대기 중에는 인간 화면에서 취소할 수 있습니다. 대기 만료120초는 운영 가안이며 엔진15초 끊김·error도 현재 요청을 취소하고 준비를 해제합니다. 같은 방/코드를 유지해 PC 재준비 뒤 사람이 다시 시작하며 자동 재시작하지 않습니다. 시작 요청ID를 새로 만들기 때문에 취소한 옛 begin/heartbeat가 새 요청을 시작하거나 바꾸지 못합니다. `protocolVersion:3`를 알리지 않는 구 실행기는 이전 진행 중 판을 마칠 수 있지만 새 GPU 예약 시작은 거부되므로 최신 PC 실행기가 필요합니다. 현재 운영 중 엔진의 교체/가동 여부는 STATUS를 따르며 담당자가 임의 종료하지 않습니다.

현장에서는 다음 순서로 운영합니다. 현재 PC에 실행해 둔 엔진의 실제 모델 로드/입력 대기 상태는 STATUS의 이번 가동 기록을 따르며, 이미 정상 대기 중이면 같은 실행기를 추가로 켜지 않습니다.

앞선 단일 라운드 실행기의10/27 가동에서는 CUDA3모델 로드7.297초와 코드 자동 입력·경기 시작0회를 `runs/remote-engine/20261027-085448-1262f33b/startup.json`으로 확인했습니다. 이는 당시 기록이며 지속 라운드 버전으로의 게시/재시작·현재 입력 대기는 STATUS를 따릅니다. **PC 모델 로드 완료와 특정 방의 서버 준비 완료는 다릅니다.** 실제 방 코드·봇 표시 참가·엔진 ready가 갖춰지기 전에는 해당 방의 준비 완료로 해석하지 않습니다.

1. 추론 PC와 표시용 컴퓨터의 전원을 켜고 추론 PC 전원 어댑터를 연결합니다. 각 브라우저의 인터넷 접속을 확인하고 운영자가 행사 동안 PC 절전 진입과 화면 꺼짐을 방지하도록 전원 설정을 확인합니다. 이 문서 작업에서 OS 설정을 자동 변경하지 않았습니다.
2. 컴퓨터 브라우저에서 아래4개 주소를 각각 열고 A/B·인간/AI 표시 역할을 맞춥니다. 같은 Wi-Fi가 필수인 구조는 아니며 각 화면에서 공개 HTTPS 사이트로 인터넷 접속이 가능해야 합니다.
3. 추론 PC에서 **`Start-Alpha-Remote.cmd`**를 한 번 실행하고 존재·사람·나무 모델3개 로드와 합성 RGB 예열이 끝나 콘솔의 `레인과 새 연결 코드 (입력 숨김)>`가 나올 때까지 기다립니다. 이미 정상 대기 중인 엔진은 유지합니다. F8 좌표 보정은 필요 없으며 표시용 브라우저에는 모델을 설치하지 않습니다.
4. A/B 인간 화면에서 각각 ‘새 대결 만들기’를 누릅니다. 각 인간 화면에 표시된 서로 다른8자리 코드를 해당 A/B 봇 표시 화면에 입력해 연결합니다. 봇 화면의 역할은 읽기 전용입니다.
5. PC 콘솔에 `A`·공백·A방8자리 코드를 입력하고 Enter를 누른 뒤 `B`·공백·B방8자리 코드도 입력하고 Enter를 누릅니다. **입력 중 글자가 보이지 않는 것이 정상**입니다. 각 레인의 모델 준비 안내를 확인합니다. 코드나 토큰을 채팅/로그에 옮기지 않습니다.
6. 각 인간 화면에서 같은 레인의 봇 표시·최신 PC 준비가 확인되면 ‘대결 시작하기’를 누릅니다. GPU 대기와 세 역할의 사진9장 준비 동안 타이머0으로 기다리고 모두 준비되면 약2초 공통 카운트다운 뒤 시작합니다. 인간/AI 두 화면을 앞에 두어 숨겨진 탭 때문에 준비가 보류되지 않는지 확인합니다. 대기는 취소할 수 있으며 끊김/오류/만료 뒤에는 재준비 후 직접 다시 시작합니다. AI는 실제 모델의 불변 계획을 한 번 보내고 서버가500ms 전달 여유 뒤250ms 간격으로 재생/제출합니다. A/B의 방·승패와 작업 슬롯은 독립적이며 가중치 한 벌만 공유합니다. 한 레인의 사진 준비/카운트다운이 다른 레인을 단일 큐에 묶지 않습니다.
7. 먼저 완벽한 선택을 제출한 쪽이 승리하면 즉시 종료합니다. 현재 기본90초 안에 정답이 없으면 승자 없이 끝납니다. 이90초는 운영 가안입니다. 인간은 틀렸을 때 같은 문제에서 수정할 수 있고 AI는 예측1회·제출1회 후 다시 추론하지 않습니다.
8. 결과 화면에서 해당 인간 화면의 **‘다음 참가자 준비’**를 누릅니다. 같은 방·8자리 코드·봇 화면/PC 연결을 유지하며 이전 사진·선택·타이머를 비우고 PC가 다음 라운드를 준비합니다. 다음 사람이 자리에 오고 PC 준비가 표시되면 ‘대결 시작하기’를 누릅니다. 새 코드 입력·재참가·모델 다시 로드는 필요 없고 다른 레인은 그대로 진행합니다. 준비 버튼만으로 새 경기가 자동 시작되지는 않습니다.
9. 부스 운영을 마칠 때 PC 입력란에 `quit`을 입력하고 Enter를 누릅니다. 창을 닫아도 엔진이 종료되므로 운영 중에는 창과 표시 탭을 유지합니다. 엔진을 완전히 종료해 메모리 연결을 잃었거나 방이 만료된 경우는 예외 복구로 새 방·최초 페어링이 필요합니다.

| 컴퓨터 브라우저 역할 | 열 주소 |
|---|---|
| A 인간 | `https://human.marulee.dev/?lane=A` |
| A AI 표시 | `https://bot.marulee.dev/?lane=A` |
| B 인간 | `https://human.marulee.dev/?lane=B` |
| B AI 표시 | `https://bot.marulee.dev/?lane=B` |

AI가0개를 선택하면 모델의 양성 예측이 없었다는 뜻입니다. 현재 출제는 정답2~4개(나무3~4개)이므로0개 제출은 오답이며 자동 재추론하지 않고 사람의 정답 또는90초 종료를 기다립니다. ‘레인 사용 중/busy’는 이미 그 레인의 지속 세션이 연결돼 있다는 뜻일 수 있습니다. 정상 참가자 교체에는 PC 콘솔을 다시 입력하지 않고 인간 결과 화면의 ‘다음 참가자 준비’를 사용합니다. 코드 오류·연결 유실·방 만료처럼 세션을 유지할 수 없는 예외에만 새 방으로 복구합니다. 살아 있는 레인에 다른 코드를 덮어쓰거나 다른 레인의 엔진을 함께 재시작하지 않습니다.

```powershell
# 모델/네트워크/GUI를 실행하지 않는 기본 명령 점검
.\Start-Alpha-Remote.cmd -DryRun
# 실제 원격 운영 기본값: parallel2슬롯. 코드·토큰은 콘솔 숨김 입력 사용
.\Start-Alpha-Remote.cmd
# 명시적인1슬롯 FIFO 복구가 필요한 경우에만 실행
.\Start-Alpha-Remote.cmd -InferenceMode serial
# Python 직접 실행 시 --execute를 명시한다. 출력은 새 경로여야 한다.
.\.venv\Scripts\python.exe scripts/run_remote_engine.py --execute --base-url https://bot.marulee.dev --device cuda --inference-mode parallel --output runs/remote-engine/new-session
```

원격 시작은 봇 표시 참가·엔진 ready·최근15초 heartbeat와 GPU 예약 지원이 필요합니다. `gpuReservationSupported`와 `imageBarrierSupported`는 지원 규약 보고이며 물리 자원 검증이나 화면9장 로딩의 보증이 아닙니다. 새 출발은 protocol3와 세 역할의 실제 사진 준비가 필요합니다. viewerConnected도 참가 기록입니다. 엔진은 lobby의 ready→queued의waiting_gpu/reserved→begin 후loading_images/images_ready, 출발 후inferencing/selecting/submitted로 전환합니다. heartbeat의 roundId/roundNumber/requestId CAS와 시작의 expectedRevision이 늦은 옛 요청을 거부합니다. ticket은 active/result까지 보존하고 next/cancel에서 비웁니다. 진행 중 error 재무장 금지와 결과의 다음 참가자 준비는 유지합니다.

초기 연결 표시는 최초 생존 확인과 실제 끊김을 구분합니다. `engineHeartbeatReceived=false`이면 아직 heartbeat가 도착하지 않은 상태이고 ready를 허용하지 않습니다. heartbeat가 한 번 도착한 뒤15초를 넘겨 갱신되지 않으면 실제 끊김입니다. 서버는 D1 상태 읽기 후의 시각으로 `serverNow`·생존·준비를 함께 계산합니다. 읽기 전에 잡은 시각보다 새 heartbeat 시각이 늦어 살아 있는 엔진이 잠깐 끊김으로 보이던 경합을 수정했으며15초 제한을 늘리거나 실제 끊김을 숨기지 않습니다.

지속 라운드 변경 뒤 서버36개+UI7개 총Node43개(0.736924초)·TypeScript를 통과했습니다. 실제 localhost HTTP는 같은 방2라운드 감사7.1024613초·기존 legacy4.757811초·원격 권한/간격20.1666424초를 모두 통과했습니다(전체 runner20.287487초). 새 schema나 migration은 추가하지 않았습니다. 앞선 Python131개 및 `runs/remote-booth-local-v2/verification.json`의 CUDA2방 검사는 이전 단일 라운드 경로의 기록이며 새 지속 세션 GPU/게시 검증과 구분합니다. 가중치·임계값·학습량·OS 클릭은 변경하지 않았고 최종 실제 측정/배포/PC 재시작은 STATUS를 따릅니다.

앞선 초기 상태 수정의 서버42개/tsc에 이어 GPU 예약 SQL·queue 무문제 공개·cancel/begin 경합·재요청 격리·끊김/error·구프로토콜 경계를 추가해 서버52개(1.1270847초)와tsc를 통과했습니다. HTTP 검사도 queued→begin·취소/회복·동일 방2라운드로 갱신했습니다. 최종 실제 HTTP·GPU·UI·게시·PC 가동 수치는 STATUS를 따릅니다. 담당자는 운영 중 엔진·사용자 방·GUI·실제 모델을 조작하지 않았습니다.

기존 브라우저의1024×768·768×1024·1280×800 viewport 검사는 화면 크기를 바꾼 시뮬레이션입니다. Android 실물 검사나 새 컴퓨터 표시 환경 전체의 동작 보증이 아닙니다. 위 운영 순서의 URL·레인·숨김 코드 입력·새 참가자 절차를 실행기 소스와 대조했으며, 현장에서는 각 실제 브라우저와 네트워크에서9사진·인간 제출 버튼·봇 상태·A/B 동시 진행을 확인해야 합니다. 원격 게시·현재 PC 가동 상태·전체 검증 기록의 정본은 STATUS입니다.

### 기존 OS 실행기의 직접 명령 (legacy)

직접 Python을 실행할 때의 형식은 다음과 같다. `--ready`는 `--execute`, `--room`, `--tree-model grounding-dino`를 모두 요구한다. 준비를 기다리는 중 프로세스가 실패하면 가능한 경우 로비의 ready를 해제한다. 모델 불러오기·409 중복 참가·창 확인 실패는 한국어 안내와 `aborted.json`에 단계를 기록하며 응답 본문/역할 토큰을 남기지 않는다.

```powershell
.\.venv\Scripts\python.exe scripts/run_booth_bot.py --config configs/booth-bot.local.json --room ABCD2345 --base-url https://bot.marulee.dev --open-browser --execute --ready --rounds 1 --tree-model grounding-dino --device cuda --render-wait-seconds 1.0 --timeout-seconds 900 --output runs/booth-live-new
```

이 실행 경로는 코드와 합성 테스트/구문 검사로 확인했으며 이번 도구의 실제 GUI/ML 클릭 시험 완료를 뜻하지 않는다. CLI 실행 전 `calibrated=true` 검사는 이제 모델/화면 초기화 전에 수행한다. 새 startup 테스트7개와 기존 봇 테스트15개가 통과했고 PowerShell 구문·compileall도 통과했다. 전체 통합 수량과 실제 화면 검증/도구 중단 상태는 STATUS가 정본이다.

`scripts/run_booth_bot.py`와 `alpha_captcha.booth_bot`은 통제된 로컬 또는 `bot.marulee.dev` 화면의 RGB 캡처 → 9칸 분리 → 실제 ML → 좌표·최소0.25초 간격 클릭/제출 경로를 구현합니다. **기본값은 dry-run**이며 `--execute`가 있어야 OS 입력을 수행합니다. 실제 창 제목·물리 픽셀 격자·제출 좌표·문제 변경 감시 영역을 실측한 `BoothLayout` JSON이 필요합니다. 기존 `pc.example.json`을 그대로 실행용 화면 보정으로 취급하지 않습니다.

방 동기화는 공개 phase/roundId/startAt/질문 조건만 남기고 모델에는 캡처 RGB와 일반 질문만 전달합니다. 토큰은 메모리에 보관하고 토큰이 있는 브라우저 fragment나 관리자 자료를 결과 로그에 남기지 않습니다. 창/문제 변경·시간 초과 시 중단하며, 예측 없는 타일을 정답 개수에 맞춰 채우지 않습니다. 현재 실제 OS QA는 하지 않았으므로 보정 파일을 임의 작성해 실행하지 않습니다. 실행 옵션은 다음 명령으로 확인합니다.

```powershell
.\.venv\Scripts\python.exe scripts/run_booth_bot.py --help
```

나무 3그루 이상은 기존 tree 존재 점수로 대신 세지 않습니다. 선택 기능인 `--tree-model grounding-dino`는 별도 사전학습 **IDEA-Research/grounding-dino-tiny**를 실제 픽셀 검출에 사용합니다. `requirements/booth-tree.txt`의 transformers **4.57.3**, safetensors **0.7.0**을 프로젝트 `.venv`에 추가했고 기존 CUDA torch/torchvision은 바꾸지 않았습니다. 재현 절차는 다음과 같으며 이번 설치·다운로드는 이미 수행했습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/booth-tree.txt
.\.venv\Scripts\python.exe scripts/fetch_tree_model.py
.\.venv\Scripts\python.exe -m pip check
```

다운로드 revision은 `a2bb814dd30d776dcf7e30523b00659f4f141c71`, safetensors는 **689,359,096 bytes**이며 SHA-256은 `1a2412ef99bd74bcd3c2a246fa1e48581f8889a1300c9051974741314fc042f3`입니다. 출처는 `models/pretrained/grounding-dino-tiny/alpha-provenance.json`에 남기고 가중치·캐시는 Git에서 제외합니다. 추론은 로컬 파일만 읽고 원격 코드 실행을 허용하지 않습니다.

PC CUDA에서 가중치 로드 약 11.639초와 단일 데모 추론 약 1.232초를 확인했습니다. 이는 zero-shot 사전학습 후보의 실행 점검이며 추가 학습·나무 전체 정확도·40% 보정·Pi 성능 검증이 아닙니다. 학교 사진을 사용하지 않았고 v1 체크포인트도 변경하지 않았습니다. 전체 의존성의 최종 `pip check` 결과는 STATUS를 따릅니다.

## 이전 ML v1·40% 평가 준비 기록

사용자의 “이제 머신러닝 들어가자” 승인 후 이 PC의 GPU에서 두 제한 모델을 실제 학습하고 v1을 고정했습니다. 존재 판별은 검토 70장 중 train 41장으로 1 epoch·6 step, 사람 검출은 완전 bbox 사용이 허용된 train 17장으로 1 epoch·9 step을 실행했습니다. 두 모델의 고정 features/backbone 및 BN state hash는 학습 전후 같았습니다. 저장 격자의 ML 예측·조건 판정·좌표/예정 시각 출력은 구현했고 ONNX·Pi·화면 캡처·실제 마우스 제어는 아직 없습니다. 전역 패키지·GPU 드라이버·OS 설정은 이번에도 변경하지 않았습니다. 전체 결과와 한계는 [STATUS.md](STATUS.md), 구조는 [ARCHITECTURE.md](ARCHITECTURE.md)를 따릅니다.

기존 환경 로그의 CUDA 텐서 연산 성공과 이번 실제 모델 학습·평가는 서로 다른 확인입니다. 학습된 체크포인트와 `report.json`은 각 `models/checkpoints/*-limited-v1/`에 있습니다. 타이밍 정책은 여전히 모의 콜백으로만 검증했고 PC/Pi 예시를 Windows에서 읽는 것은 Pi 실기기 검증이 아닙니다. 다음은 프로젝트 루트에서 사용할 점검 명령입니다. `check_env.py --report`는 지정 로그를 새로 갱신합니다.

현재 후속 목표는 **4P/5N의 3×3 평가에서 나무·건물·연못·사람 존재와 `count >= 2/3/4/5`의 8조건 각각 약 40% exact-set 성공률**입니다. 허용 오차 수치는 미정이며 아직 달성하거나 v2 모델을 학습하지 않았습니다. 설정은 `configs/calibration-target-v2.json`, 자료 준비성은 `runs/calibration-v2/data-readiness.json`입니다. 4P/5N은 평가 기준이고 실제 문항의 고정 정답 수나 모델 입력이 아닙니다. 현재 val은 건물 한 격자 외에는 양성 4장·음성 5장 조건을 만족하지 못해 신선 자료를 준비해야 합니다. 기존 사진 재사용을 독립 평가 표본 증가로 간주하지 않습니다.

`runs/calibration-v2/validation-grid-summary.json`은 기존 val 예측 cache로 실제 평가 코드를 실행한 기록입니다. 조건당 무재사용 100격자 요청에 8조건 모두 `insufficient_data`였고 건물의 가능한 한 격자만 exact-set 0/1로 점검했습니다. 새 추론·학습은 없으며 목표 달성을 입증한 상태가 아닙니다. 사람 존재의 알려진 val 정답 2P/2N은 검출 적격 1P/2N보다 넓지만 추가 양성의 cache가 한 장 부족합니다. 자료·검출 적격·기존 예측 수량을 구분하고 부족한 예측을 음성으로 채우지 않습니다.

```powershell
cd "$env:USERPROFILE\Desktop\Alpha-Captcha-AI"
.\.venv\Scripts\python.exe -m alpha_captcha dry-run --config configs/pc.example.json --tiles 0,4,8
.\.venv\Scripts\python.exe -m alpha_captcha dry-run --config configs/pi.example.json --tiles 0,4,8
.\.venv\Scripts\python.exe -m alpha_captcha data-check --help
.\.venv\Scripts\python.exe -m alpha_captcha data-split --help
.\.venv\Scripts\python.exe scripts/review_labels.py --help
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_env.py --training --require-cuda --report logs/environment-check.json
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-11-05
```

`data-check`와 `data-split`은 실제 manifest를 대상으로 검사·분할하는 명령입니다. `--help`로 입력·출력 옵션을 확인합니다. CLI dry-run의 예정 상대 시각은 처리 지연·직전 문제 클릭이 없는 계획값이며 실제 sleep·클릭을 실행하지 않습니다. 첫 클릭 대기 기본값 0초는 가안이고 제출 버튼은 타일 스케줄러에 포함하지 않았습니다.

## 현재 학습 명령과 고정 산출물

다음은 이번 v1 학습에 사용한 고정 프로필의 재현 형식입니다. **이미 test를 평가한 v1을 결과에 맞춰 재학습·튜닝하지 않습니다.** 기존 v1 출력은 보존하며 명령을 그대로 다시 실행하면 기존 출력 보호로 중단합니다. 존재 모델의 출력 옵션은 `--output-dir`, 사람 모델은 `--output`입니다.

현재 두 학습 CLI는 기본적으로 **test를 평가하지 않고**, 모델을 고정한 최종 audit에서 명시적인 `--evaluate-test`를 줄 때만 test를 평가합니다. 아래 v1 프로필 재현 형식도 현재 CLI로 실행하면 기본 test 생략 정책을 따릅니다. 직접 Python API를 사용할 경우 기존 호출 호환성 때문에 `evaluate_test=True`가 기본값으로 남아 있으므로 **선택/보정 단계에서는 반드시 `evaluate_test=False`를 명시**합니다. CLI의 안전한 기본값이 API에도 같다고 가정하지 않습니다. 이 문서 갱신을 위해 학습이나 test 평가를 재실행하지 않았습니다.

```powershell
.\.venv\Scripts\python.exe scripts/train_presence.py --manifest data/manifests/presence-ml-v1.jsonl --root . --output-dir models/checkpoints/presence-limited-v1 --device cuda --epochs 1 --batch-size 8 --max-train-images 64 --seed 42 --learning-rate 0.001 --threshold 0.5
.\.venv\Scripts\python.exe scripts/train_person.py --manifest data/manifests/coco-person-reviewed-split.jsonl --root . --output models/checkpoints/person-limited-v1 --device cuda
```

종합 프로필은 `configs/limited-baseline-v1.json`입니다. 공식 사전학습 가중치는 `models/pretrained/`에 저장하고 Git에서 제외합니다. presence의 학습 전 고정 기록은 `runs/frozen-profiles/`, person은 `models/checkpoints/person-limited-v1/frozen-profile.json`입니다. 체크포인트·보고서에는 manifest/가중치/모델 해시, 실제 train 수량·손실·실행 기기·VRAM·시간을 기록합니다.

v2는 기존 원본 SHA·그룹·출처 ID·부모 계보를 제외하는 새 Kaggle 목록과 별도 출력 디렉터리를 사용합니다. train과 선택용 val, 모델 고정 후 1회 audit용 test를 격리하고 후보 예산 목록을 fit 전에 고정합니다. v1 test·학교 사진으로 40%를 맞추거나 상위 4개 강제 선택·예측 반전·클릭 누락을 사용하지 않습니다. 최소 수집·검토안은 [후보 비교](DATASET_CANDIDATES.md), 조건별 부족 수량은 [DATASET.md](DATASET.md)를 따릅니다. 새 수집 스크립트는 제안 단계이며 이번에 사진 확보·v2 fit은 수행하지 않았습니다.

존재 모델은 ImageNet 사전학습 MobileNetV3 Small의 classifier를, 사람 모델은 COCO 사전학습 SSDLite의 head를 학습했습니다. 처음부터 소량 데이터만 학습한 모델이라고 설명하지 않습니다. 존재 판별은 알려진 라벨만 loss/지표에 포함하며 unknown은 음성이 아닙니다. 작은 test에서 tree 전부 양성·pond 전부 음성이었으므로 부스 실사용 완성 모델로 취급하지 않습니다. 사람 test exact 13/18도 작은 COCO 표본·사전학습 이력의 제약이 있습니다. 마지막 사람 없는 단독 batch의 SSD loss 0도 한계로 기록했습니다.

## 저장 격자 ML 추론과 dry-run

다음 명령은 이미 저장된 테두리 없는 3×3 격자에서 두 체크포인트를 읽고 RGB 픽셀만으로 판별합니다. 출력 경로는 새 JSON 파일이어야 하며 기존 파일은 덮어쓰지 않습니다. `configs/task.example.json`은 공개 질문 `person_count`, `gte`, n=2 예시입니다. 정답 정보를 넣지 않습니다.

```powershell
.\.venv\Scripts\python.exe scripts/predict_saved_grid.py --image runs/ml-baseline-v1/grid-example.jpg --condition configs/task.example.json --config configs/pc.example.json --device cuda --output runs/ml-baseline-v1/grid-inference-recheck.json
```

기본 체크포인트는 `models/checkpoints/presence-limited-v1/presence.pt`와 `models/checkpoints/person-limited-v1/person.pt`입니다. 현재 GPU 예시 한 번은 전처리를 포함한 추론 약 0.56초, 선택 타일 `[8]`, 예시 좌표 `(600,600)`, 예정 상대 시각 0초를 출력했습니다. 모델 로딩 시간은 별도이며 실제 대기·캡처·마우스·제출은 실행하지 않습니다. 한 번의 추론 시간은 경기 시간이나 p50/p95가 아닙니다.

9칸 중 일부만 정답이어도 모델은 각 사진을 판별해 선택 집합을 만듭니다. 문제 전체 성공에는 정답 k칸 선택과 나머지 9−k칸 제외가 모두 필요하며, 정답 개수를 입력해 그만큼 강제 선택하는 방식은 아닙니다. [STATUS.md](STATUS.md)의 성공률 분석은 독립·동일 성능 가정의 대입값으로, 실제 학교/부스 성능 측정이나 새 모델 실행 결과가 아닙니다. 이 후속 설명을 위해 학습·추론을 다시 실행하거나 v1을 변경하지 않았습니다.

`--device cpu`로 바꾸고 새 출력 경로를 지정하면 Windows CPU에서도 같은 체크포인트를 읽는 실행 방법을 확인할 수 있습니다. Windows CPU에서 체크포인트를 읽는 것과 Pi에서의 추론·설치·속도 검증은 별개입니다. 현재 ONNX는 없고 PyTorch를 PC에서 실행한 결과를 Pi 완료로 보고하지 않습니다.

## PC 의존성 재설치

의존성을 다시 설치할 때에는 프로젝트 루트에서 다음과 같이 실행합니다. Python 3.12가 필요하며 GPU 묶음은 이 PC의 NVIDIA GPU를 대상으로 합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_pc.ps1
```

`Bypass`는 이 프로세스에만 적용하며 영구적인 실행 정책 변경을 하지 않습니다. 설치는 공식 PyTorch CUDA 12.6 저장소와 PyPI를 구분하여 진행합니다. CUDA Toolkit 전체나 NVIDIA 드라이버를 별도로 설치하지 않았습니다. GPU가 없는 PC에는 이 스크립트를 그대로 사용하지 마세요.

`requirements/runtime.txt`는 기존 ONNX·화면 제어 실행 준비용 묶음이며 현재 PyTorch ML 추론을 위한 torch/torchvision 전체를 포함하지는 않습니다. PC에는 `training.txt`와 별도 `pc-gpu.txt`를 설치해 두었습니다. Kaggle COCO·ADE·Places 사진의 확보와 라벨 검토 후 일부로 v1을 학습했으며 나머지 미확인·군중 라벨은 계속 분리합니다. 최종 확보량·출처·검토 범위는 STATUS와 [후보 비교](DATASET_CANDIDATES.md)를 따릅니다. 인증 정보는 채팅이나 Git에 넣지 않습니다.

## Raspberry Pi 시리얼 연결 후 점검 (미실행)

사용자는 Pi 4B를 시리얼 어댑터로 PC에 연결할 예정입니다. 연결되면 콘솔에서 기기 정보 확인·설치 명령 실행·로그 수집을 빠르게 진행할 수 있습니다. 실제 COM 포트·어댑터·통신 속도·로그인·OS·GUI 상태는 미확인입니다. UART 콘솔을 사용한다면 Pi에 맞는 3.3V 레벨 어댑터와 실제 핀·콘솔 설정을 확인합니다. 비밀번호와 토큰은 문서나 로그에 기록하지 않습니다.

앞선 Windows `Get-CimInstance Win32_SerialPort` 조회에는 인식된 포트 목록이 없었습니다. 조회 결과만으로 실제 연결 여부를 단정하지 않으며, Pi에 접속하거나 OS·세션을 확인한 상태는 아닙니다.

연결 후 다음 읽기 명령으로 점검을 시작합니다.

```bash
uname -m
getconf LONG_BIT
cat /etc/os-release
python3 --version
free -h
echo "$XDG_SESSION_TYPE"
```

시리얼은 셸에 접근하는 경로이며, 브라우저 화면 전송·GUI 캡처·마우스 입력을 자동으로 제공하지는 않습니다. 콘솔의 `DISPLAY`나 세션 값은 GUI 세션 상태와 다를 수 있으므로, 실제로 실행할 그래픽 세션을 별도로 확인합니다. 화면 확인 방법과 큰 모델 파일의 전달 경로는 접속 후 선택합니다. 이번 작업에서는 OS·UART·세션을 변경하지 않았습니다.

1. ARM64 여부·OS·Python·RAM을 확인합니다. 현재 공통 목표는 64비트 ARM과 Python 3.12~3.13입니다.
2. 소스와 향후 모델·metadata를 전달합니다. Windows의 `.venv`와 잠금 파일, 학습 사진 전체는 복사하지 않습니다.
3. `python3-venv`를 준비하고 실행 환경을 만듭니다. 기존 `bash scripts/setup_pi.sh`는 초기 공통 패키지 설치용이며 Pi에서 검증하지 않았습니다. 새 검출·후처리 기능의 추가 의존성은 구현 단계에서 확인합니다.
4. `.venv/bin/python scripts/check_env.py --report logs/environment-check-pi.json`으로 패키지를 점검합니다. Wayland나 headless 환경에서 import를 건너뛴 것은 입력 성공을 의미하지 않습니다.
5. 저장 이미지 추론과 통제된 테스트 화면의 캡처·좌표·클릭을 별도로 검증합니다. 사이트 완성을 기다리지 않고 입력 가능성부터 확인합니다.
6. 같은 모델·전처리·계수·최소0.25초 클릭 간격 규칙으로 PC와 Pi를 비교합니다. 추론 자체가 더 오래 걸리는 경우도 별도로 기록합니다.

## 데이터·화면 규칙

Kaggle 데이터는 `data/raw/kaggle/`, 공개 허가 운영 사진은 별도 `data/booth/public-web-*/`로 분리합니다. 학교 사진은 이번 행사에서 사용하지 않으며 학교 최종 평가도 현재 행사 범위에서 제외했습니다. 향후 학교 자료가 들어오면 기존 `data/raw/school/` 격리 원칙을 유지하고 학습·val·튜닝에 쓰거나 하나의 `ImageFolder`로 섞지 않습니다. 실제 학습 로더는 manifest의 Kaggle 출처·허용 경로·해시·이미지·그룹 분할을 검사하고 train만 최적화합니다. 학교 경로·경로 탈출을 거부하지만 이름을 바꿔 옮긴 사진의 진짜 출처나 시각적 유사 중복까지 자동 판정하지는 않습니다.

확보한 COCO64의 box 후보 수를 곧바로 정답 인원수로 사용하지 않습니다. 검증되지 않은 수는 unknown, 군중은 crowd, 대상 존재의 미주석은 `null`로 관리합니다. 이번 학습은 검토된 존재 라벨과 별도로 검출 학습 가능 여부가 확인된 사람 bbox만 사용했습니다. 학교 사진은 열람·학습하지 않았고 최종 학교 평가도 아직 없습니다.

`scripts/review_labels.py`의 `export`로 실제 manifest에 대응하는 새 검토 CSV를 만듭니다. 존재 여부는 `1`/`0`, 애매하거나 확인하지 않은 값은 빈칸으로 남깁니다. 빈칸은 unknown을 음성·0명으로 바꾸지 않습니다. 명시한 라벨에는 검토자와 검토 기록이 필요합니다. `apply`는 출처/이미지 ID·해시·경로를 대조하고 새 JSONL에만 결과를 쓰므로 원본 이미지와 manifest를 보존합니다. 정확한 인원수만 검토한 경우 기존 bbox는 `annotation_boxes`에 따로 보존하고 검증된 좌표로 취급하지 않습니다. 학교 사진은 이 개발용 검토 절차에 넣지 않습니다.

이전 문제은행 5문제·n=2~5 평가 계획과 이번 웹사이트 4개 테마를 구분합니다. 현재 웹은 위의 사람/나무 3개 이상·건물/연못 조건으로 구현했고, 이전 8조건별 40%는 별도의 난이도 목표입니다. v1 학습·계수 프로필은 보존하며 실제 예측을 그대로 사용합니다. 실제 타일 클릭 간격·Pi와 부스 전체 동작은 아직 측정하지 않았습니다.

3×3 규격은 확정됐지만 ROI·간격·배율·주 모니터는 보정 전입니다. 현재 예시는 `calibrated=false`이므로 실클릭에 쓰지 않습니다. 해상도나 줌이 바뀌면 다시 보정합니다.

## 공식 참고

- [PyTorch 설치](https://pytorch.org/get-started/locally/)
- [ONNX Runtime](https://onnxruntime.ai/docs/install/)
- [PyAutoGUI](https://pyautogui.readthedocs.io/en/latest/)
- [Raspberry Pi 시리얼·UART·화면 설정](https://www.raspberrypi.com/documentation/computers/configuration.html)
- [Kaggle CLI](https://github.com/Kaggle/kaggle-cli)

이전 작업 검토(ML v1): 실제 두 GPU 학습 명령·고정 v1 체크포인트/프로필·저장 격자 ML 추론 명령을 반영했다. CPU 복원 방법·한 번의 GPU 추론·모의 클릭 시각과 미완료 ONNX/Pi/캡처/실마우스를 구분하고, tree/pond 편향·SSD 음성 batch·작은 COCO 표본/사전학습 한계 및 test 후 재학습·튜닝 금지를 기록했다. 기존 설치 정보·전역 환경 무변경·학교 차단과 시리얼 미확인을 유지했다.

이전 작업 검토(부분 정답 설명): 일부 타일 정답 구성에서도 고정 모델의 사진별 판별·선택을 사용하며 정답 선택과 오답 제외가 모두 필요함을 확인했다. STATUS의 가정 분석과 기존 실행 방법·실측 결과를 구분했고 소스·모델·패키지 변경이나 새 학습·추론 실행은 없었다.

이전 작업 검토(40% 검증 준비): 4P/5N 평가의 8조건별 약 40% 목표·허용 오차 미정과 자료 준비성 부족을 반영했다. 학습 CLI의 test 기본 생략/명시적 audit 및 직접 API의 evaluate_test=False 필요를 실제 코드와 대조했다. v1 보존·새 v2 자료 격리 계획만 기록했으며 당시 문서 담당 작업에서 다운로드·학습·모델 실행·패키지/OS 변경은 하지 않았다.

이전 작업 검토(10/27 자동 클릭 진단): 로컬 프로세스/실측 설정 부재와 웹 준비 표시의 차이, Windows 직접 실행기·사용자 수동 보정·모델/전면/화면범위 확인 후 명시적 ready·새 방/한 판 운영을 대조했다. 앞선 startup7개/기존봇15개·PowerShell구문/compileall은 실제 GUI 실행 증거가 아니다. UI 점검은 Chrome URL 확인 실패로 중단됐고 같은 턴 다른 브라우저/OS/PyAutoGUI/보정기로 우회하지 않았다.

이전 작업 검토(10/27 초기 상태): 컴퓨터 브라우저4역할과D1 읽기 뒤 시각 projection·최초 heartbeat 구분을 반영하고15초 제한·서버42개/tsc 결과와 최종 STATUS를 대조했다. 모델/임계값/학교 사용·legacy는 유지했다.

이전 작업 검토(10/27 통신/두 세션): HTTPS API·웹0.5초 폴링·PC 약3초 heartbeat와직접 PC TCP/전용 지속 소켓 부재, Python HTTP200/version11과브라우저 협상 미측정, 모델 공유·GPU 직렬화와공개v8의 기존 샘플을 대조했다.

이전 작업 검토(10/27 공정성 상담): startAt 후 GPU 대기의 불균등과상태조회가 포함된 이전 보고서 구간을 확인하고 경기 전 예약을 미구현 제안으로 기록했다.

이전 작업 검토(GPU 예약 출발): 2026-10-27에 전체 본문을 다시 읽고 사용자 승인된 queued→PC GPU 예약→begin/공통 카운트다운→RGB 추론 후 해제와최소1초 선택 겹침으로 운영/명령을 갱신했다. 무round·타이머0·비공개 사진, expectedRevision/requestId CAS·취소/끊김/error/120초 가안·protocol2 지원/구엔진 호환과0002 추가 열을 반영했다. 서버52개·tsc 통과와HTTP 감사 갱신은 실제 결과이며 최종 HTTP/GPU/UI/배포·가동은 STATUS를 따른다. 기존 모델/학습/임계값·학교 평가 전용·40%·legacy·OS 클릭/Pi/ONNX 경계는 유지했고 운영 엔진/사용자 방/GUI를 담당자가 조작하지 않았다.

이전 작업 검토(0.25초 제한): 2026-10-27에 전체 본문을 다시 읽고0.25초 선택 하한과 진행 중 remote AI 표시125ms/그 외500ms 폴링을 반영했다. 이전1초 실측·테스트는 당시 이력으로 보존했다.

이전 작업 검토(선택 계획): 2026-10-27에 전체 본문을 다시 읽고 타일별 왕복을 없애는 불변 선택 계획·500ms 전달 여유/250ms 서버 일정·0개 제출·인간 선승 시 중단과 예정/실측 보고서 구분을 반영했다.9사진 최대3병렬과 원순서/실패 정리·기존 RGB 경계,0003 추가열·과거 migration 불변을 기록했다. 학교 사진과 학교 최종 평가를 이번 행사 범위에서 제외하고 공개 허가 인터넷 사진의 운영/학습 분리와 향후 학교 개발 사용 금지를 유지한다. 모델/임계값·40%·ONNX/Pi/OS 입력 미완료는 유지하며 최종 테스트·사진확보/업로드·CUDA/게시/가동은 STATUS가 정본이다. 담당자는 운영 엔진/사용자 방/GUI/ML을 실행하지 않았다.

이전 작업 검토(11/01 지연 수정): 2026-11-01에 전체 본문을 다시 읽고 사진3역할 준비·프로토콜2/3 협상/배포 중 업그레이드·동일 RGB 재사용·출발 전 문제 추론 금지·ACK 유실 복구를 반영했다. 스레드별 HTTP 연결 재사용/제한 재시도·경기 안 동기 stage 왕복 축소·세 모델 합성 예열·질문별 불필요 모델 실행 생략과 출력 동등성 검증을 대조했다. 실제 검사/게시/PC 가동 정본은 STATUS이며 이전 수치/정책은 이력으로 보존한다. 학교 사진 미사용·고정 모델/임계값·임의 오답0·40%/ONNX/Pi/legacy OS 입력 및 현장 리허설의 미완료 경계를 유지한다.

이전 작업 검토(11/01 A/B 상담): 2026-11-01 A/B 동시 운영·GPU 수용·무지연 문의에 대해 전체 본문을 다시 읽고 공유 모델1회 로드·경기 전 예약·추론 후 해제와 A/B 진행 겹침을 확인했다. 공개 기록의 B1 10.438초는 상태 HTTP/문맥 확인과 앞선 방의 준비·카운트다운·추론 영향이 있는 시작 전 예약 대기이며 순수 GPU 시간이 아니다. 두 판의 경기 중 GPU 대기0과 각 방의 공통 출발을 두 방의 동일 절대 출발·통신/화면 지연0·장시간 보장과 구분했다. 이번 상담은 문서만 갱신했고 코드·배포·새 추론/성능측정·운영 프로세스/사용자 방/GUI 조작0이다. 학교/고정 모델/40%/ONNX/Pi/legacy 경계를 유지한다.

이전 작업 검토(11/02 GPU 동시 추론 상담): 2026-11-02 GPU 자원 분할·A/B 동시 추론 문의에 전체 본문을 다시 읽고 현재 FIFO가 사진 준비·카운트다운까지 보유하는 구간과 실제 CUDA 계산을 구분했다. 공식 CUDA/MIG/PyTorch 자료와 Windows Green Context 지원 경계, 공유 predictor의 상태 변경을 감사했다. 저장 RGB 9장·모델 한 벌·조합별 3회 오프라인 보고서를 확인했으며 출력 동등·OOM 0과 조합별 속도 차이, 호스트 호출 겹침과 미추적 GPU 커널 동시성을 구분했다. 운영 FIFO·웹/API·배포·사용자 방·운영 프로세스를 변경하지 않았고 학교 미사용·고정 가중치/임계값·250ms 선택·40%/ONNX/Pi/legacy OS 미완료를 유지한다. 전체 문서 점검·실제 측정과 남은 작업의 정본은 STATUS/CHANGELOG다.

이전 작업 검토(11/02 사진 교체): 2026-11-02 전체 본문을 다시 읽고 사용자 요청의 애매한 사진 제외·명확한 사진 교체를 반영했다. 기존46장 중22장 제외/24장 유지와 새10장으로 선정한34장 은행, v3 정본·원문 권리/촬영 그룹·RGB/작은 타일 재검토·모델 예측을 쓰지 않은 선정을 기록했다. 인증된 활성 집합 원자 교체/includeInactive·SHA·현재 생성 라운드 사진 보존/R2 삭제 없음의 코드를 대조하고 과거24/46장 수치와 현재 선정을 구분했다. v13·환경5 게시 성공과 새10/10 업로드·활성34/비활성22/전체56·34파일 SHA/RGB·기존 판9사진 보존·공개5판/4종·허용11조합352추첨 통과를 실제 보고서와 대조했다. Node33개·localhost HTTP1개(5.806초)·TypeScript/build/diff 통과와 모델 추론/답안 제출0·실제 GUI/독립 사람 검수/현장 리허설 미완료를 구분했다. 최종 재현·게시와 전체 문서 점검은 STATUS/CHANGELOG를 따른다. 학교 미사용·고정 모델/임계값·FIFO·250ms 선택·40%/ONNX/Pi/legacy OS 입력 및 현장 리허설 미완료를 유지한다.

이전 작업 검토(11/04 GitHub): 2026-11-04 담당 문서 전체 본문을 다시 읽고 공개 GitHub 소스와 별도 운영 자산의 경계, 일반 웹 파일 포함과 원래 Sites Git 보존, 새 clone의 의존성/데이터/모델 준비를 대조했다. 공개 저장소 https://github.com/ProgrammingYJ/Alpha_Human_VS_AI 의 PUBLIC main 첫 푸시와 로컬/원격/GitHub tree 일치를 확인했다. 공개 소스 경로의 Python179개(12.565초)·Node110개 통과와 문서13개/설정 JSON8개 점검 결과를 확인했으며, 후속 문서 동기화의 최신 커밋/최종 감사는 STATUS를 따른다. 과거 고정 PID의 게시/재시작 PS1은 보관 소스이며 현재 운영 실행기로 쓰지 않음을 명시했다. 이 문서 작업에서 모델/가중치/임계값·학교 사용·사진은행·서버 배포·운영 PC 프로세스·250ms/FIFO/프로토콜을 변경하지 않았다. 미완료 40%/ONNX/Pi/legacy OS 입력·현장 리허설을 유지하며 전체 문서 점검 정본은 STATUS/CHANGELOG다.
이전 작업 검토(11/05 외부 시험 준비): 2026-11-05 담당 문서 전체 본문과 AGENTS.md를 다시 읽고 외부 컴퓨터의 공개 HTTPS 접속·인간/AI 표시 창 유지·PC 콘솔 하나의 A/B 최초 연결·같은 방 다음 참가자 순서를 검토했다. 기존 v13의 공개6요청 HTTP200·프로토콜3/사진 배리어/250ms와 정규 PC 엔진의 CUDA3모델 로드15.046초·합성 예열3.657초·총18.703초 성공/코드 입력 대기를 실제 준비 근거로 반영했다. 새 코드 입력·방 heartbeat·문제 RGB 추론·실제 외부 경기/선택은 검증하지 않았고 사용자의 외부 시험 단계와 구분했다. 이번 작업에서 새 배포·가중치/임계값·사진은행·학교 사용·FIFO/250ms 계약을 변경하지 않았다. 기존40%/ONNX/Pi/legacy OS 입력과 현장 리허설 미완료를 유지하며, 운영 프로세스 생존과 전체 문서 점검 정본은 STATUS/CHANGELOG를 따른다.

이번 작업 검토: 2026-11-05 담당 문서 전체 본문을 다시 읽고 Windows/Python 실행 옵션·시작 보고서 설정 확인·현장 운영 순서를 실제 소스와 대조했다. 사용자 최신 요구에 따라 기본 FIFO를 parallel2슬롯·공유 가중치 한 벌·작업별 processor/진단·CUDA2stream으로 대체하고 명시적 serial 복구와 설정 확인 방법을 반영했다. 이전 FIFO 정책·11/01 및11/02 측정값은 이력으로 보존했다. 모델/전처리/임계값·프로토콜3·세 역할 사진 준비·500ms/250ms·학교 미사용·같은 방 교체는 유지한다. CPU 모델 문맥5개와 기존 ML/격자22개 검사를 통과했고 출력/BN 보존·모드/장치 검사·동시 문맥 분리를 확인했다. 실제16조건쌍 CUDA 출력 동등·OOM0·두 stream kernel 겹침과 조합별 속도 차이를 보고서로 확인했고, 공개 두 방 검사·최신 운영 PID/재시작 및 전체 문서 점검은 STATUS/CHANGELOG를 정본으로 둔다. 독립 정확도40%·ONNX/Pi·legacy 실제 OS 입력·현장 리허설을 새로 완료했다고 보고하지 않는다.
