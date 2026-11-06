# 작업 이력

최종 검토: 2026-11-06 (Asia/Pyongyang)

## 2026-11-06 A 단일 부스와 협력적 GPU 작업시간 예산30%

- 사용자의 내일11/07 A 하나/CTF 병행 요청이 기존 기본 병렬 정책을 대체한다. 웹 기본 single·A/B UI 제거·B 새 연결409/이전 B410·내부 A/기존 A 인증 유지, PC single worker/stream·8자리코드만 입력·B 사전 차단을 구현했다. dual/parallel은 양쪽 명시적 복구용이다.
- CooperativePacer로 모델 청크 뒤 마지막까지 작업시간2.333배를 취소 가능한 단위로 쉬게 했다. 유휴 크레딧/추가 상태 HTTP0, 자기 stream 동기화/로컬 생존 검사, 작업/실제 휴식/네트워크/선택 시간을 분리한다. SM/순간 GPU/VRAM 하드 quota가 아니며 CPU4/interop1/자체 BelowNormal만 적용했다.
- 첫 존재1장 분할 실험은 선택이 같아도 점수 최대0.000302553 차이로 사전1e-5를 넘겨 false로 보존했다. 허용오차 완화/가중치/임계값 변경 없이 원래 배치8+1/9/1×9를 복구했고 v2 네 조건×두 프로필×3회 출력 차이0/선택 동일/OOM0·작업 비율최대29.999102%를 확인했다. peak PyTorch reserved1154MiB이며 커널 추적/전체 장치 샘플/CTF 부하는 서로 구분했다.
- Python210개10.243초·웹125pass/1skip·TypeScript/build/diff 통과. 공개 single 한 판은 B 차단·3역할9사진/공통 출발·ML1/plan1·250ms·cache/표시 일치·정상 종료가 통과했다. 실제 IAB 기본 인간/봇 UI 및 이전 B 안내/기본 주소 전환도 확인했고 CUA 종료 기록을 남겼다. HTTP/PIL QA와 실제 브라우저/현장 경기·정확도는 섞지 않는다.
- Sites v15/env7·sourcea3f2cb98bf00cef49a09f6131b4162aade64b504·savedappgprj_6ade37995018819184a42c88bb0fde7c~appgver_e5163f09bb3081919b613c64c0adc8ba·deploymentappgdep_6aed90c7e3948191a4880aaaf10755e5 성공. 공개/두 도메인·초기화 경계1793862306432·관리자 비밀 두 키/DB/R2/사진/모델은 보존했다. source credential 만료는 같은 Site 갱신 후 패키징을 재개했다.
- 실행 중 발견한 프로젝트 체인26360→3272→32036을 경로/부모 검증 후 업데이트를 위해 정지했다. 공개 QA 후 새 **32140→41944→17664**를 켜두고 single/.30/CPU4/worker1/stream1·BelowNormal·로드5.375+예열6.563=11.938초와 생존을 확인했다. 사용자 최초 코드는 입력하지 않았다. 현재 가동은 runs/single-resource-20261106/operator-start.json이다.
- 남음: 실제 CTF 동시 부하·사용자 새 최초 연결/행사 한 판·장시간/연속 참가자, 기존40%/ONNX/Pi/legacy OS 입력. 학교 미사용·학습/모델/임계값/사진·protocol3/250ms/500ms/same-room next 경계를 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이번 작업 검토: 단일 저부하 운영 — 13개 전체를 분담 재독하고 변경·실제 검증/실패 이력·한계·남은 작업을 STATUS에 기록했다. 새 Markdown은 없으며 내용 변화 없는 자료 문서도 검토 결과를 남겼다. 실제 문서 점검과 소스 동기화는 최종 완료 기록으로 반영한다.

마무리 점검: 원본/공개본 관리 Markdown13개 및 별도 UTF-8/로컬 링크/전체 목록/설정JSON8개 감사·Git diff가 통과했다. 최종 감사는 runs/single-resource-20261106/document-audit-final.json이다. 공개359파일 코드 바이트/민감 자료 제외 findings0 뒤 구현 커밋9d31c52f2dee3a9e47e5759373763f1ae53d25e3를 기존 PUBLIC main에 푸시했고 결과 문서도 후속 동기화한다. 운영 single/.30 엔진은 사용자 코드 입력용으로 계속 켜 둔다.

## 2026-11-05 운영 연결 init·중복 봇 연결 복구

- 사용자가 PC 재시작 뒤 ‘이미 연결된 봇’과 전체 init을 요청했다. PC 메모리 토큰 소실과 D1의 잔존 bot/engine 해시를 구분하고, 서버 환경 `ARENA_SESSION_RESET_BEFORE_MS`의 생성시각 경계로 옛 방의 모든 역할 조회/참가/행동·공개 현재 사진을410 `room_reset`으로 철회하는 보호를 추가했다. 잘못된/미래 설정은503으로 중단한다.
- 기존 방/라운드·과거 결과·R2/활성34사진·라벨/그룹·모델을 삭제하지 않으며 관리자 비밀값을 새로 읽거나 회전하지 않는다. 경계는 비밀정보가 아닌 운영 설정이고 후속 배포에도 보존한다. 새 방에서 최초 연결한 뒤 정상 참가자는 계속 같은 방 next를 사용한다.
- UI는 현재 연결의 초기화/만료410에서 해당 저장소/선택/사진/시계를 비우고 시작 화면으로 복구한다. 연결 세대/roomId/storageKey로 늦은 옛 응답이 새 연결을 덮지 못하며 `?reset=1`은 열린 origin/탭의 remote 네 키를 값 열람 없이 제거한다. reset/fragment를 URL에서 제거하고 다른 호스트/탭은 각각 열도록 안내한다.
- 서버/UI Node118개·TypeScript·production build/diff, 전체 Python194개15.522초(reset410/503 진단회귀1개 추가)를 통과했다. 첫 공개 QA 도우미 stdin EOF·v2 수동 중단/오류 파싱은 검증 준비 미완료 이력으로 보존하고 제품 성공/실패와 구분했다. 새 public-reset-verification-v3.json은 이전A/B human/viewer/engineGET6개+옛코드join2개 총8개410 room_reset·새A/B 생성/viewer참가/engineheartbeatready/사진없는lobby 모두통과다. 코드/토큰은RAM전용이며보관하지않았다.
- Sites v14·환경revision6 게시 succeeded. 서버시각기준 cutoff1793862306432, source28d18857722ee6cbc2e93ad86c43621a5cfb449b, saved appgprj_6ade37995018819184a42c88bb0fde7c~appgver_03faf9e180ac81919e7e912f4780cda0, deployment appgdep_6aec2b03d760819191da6af1b79b0701. 기존public주소/ADMIN_KEY/OWNER변경0이며 runs/session-reset-20261105/release.json에기록했다. 적용경계는후속배포에도유지하고init때증가만하며감소/삭제로옛토큰재허용하지않는다.
- 두호스트HTML/health/각17자산200·sessionResetSupported=true를 확인했다. IAB humanA/botA reset주소의초기화면(새방만들기/빈코드·타이머0)과queryreset제거를확인했다. 옛세션보유브라우저410자동복구실측이나사용자외부PC저장소삭제와는구분한다. 화면도구의작업종료기록을남겼으며사용자의운영방코드입력0이다.
- 이전operator21536→43456→38212의경로/부모관계확인후해당체인만정지하고새41224→42632→41396을켜두었다. CUDAparallel2slot/2stream/2workerwarm의load6.500초+warm3.672초=10.172초와생존을확인했다. 새정본은 runs/session-reset-20261105/operator-start.json 및 runs/remote-engine/20261105-160822-58d04071/startup.json이다. Windows OS재부팅·특정사용자방준비완료는주장하지않는다.
- 기본parallel2슬롯/2CUDA스트림·공유 가중치·protocol3·500ms/250ms·같은 방 다음 참가자와 RGB 전용 ML·학교 미사용/학습량·가중치/임계값·사진 정책은 유지한다. Windows 자체 재부팅이나 새 ML/정확도 측정으로 보고하지 않는다. 남은 검증은 사용자 외부 A/B 최초 재연결/한 판·연속 운영과 기존40%/ONNX/Pi/legacy OS 입력·현장 리허설이다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이번 작업 검토: 운영 init — 위13개 전체 본문/이력을 재독·갱신하고 연결 철회·브라우저/PC 복구·실물 자료 보존과 대조했다. 새 Markdown은 없으며 변경 없는 데이터/모델 문서에도 검토 결과를 기록했다. 실제 v14/환경6·이전권한8개410/새A/B연결·코드검사·IAB초기화면·새운영가동과남은사용자최초재연결/실제기기검증을구분한다. `check_docs.py --date 2026-11-05`의13개와 별도UTF-8/로컬링크/전체목록/설정JSON8개감사가 모두통과했다. 정본은 runs/session-reset-20261105/document-audit-agent.json이며 기계검사를 본문 직접검토와 구분한다.

마무리 점검: 원본/공개본 관리13개와 UTF-8/로컬 링크/전체 목록/설정JSON8개 전수 감사·Git diff를 통과했다. root 정본은 runs/session-reset-20261105/document-audit-final.json이다. 공개348파일 코드 바이트/민감 자료 제외 감사 findings0 뒤 초기화 구현 커밋bf8a7d2a684b95dc23e76cce41b40432d21c816c를 기존 GitHub PUBLIC main에 푸시했고 결과 문서도 후속 동기화한다. 새 PC 엔진은 사용자 최초 A/B 코드 입력용으로 유지한다.

## 2026-11-05 A/B 실제 병렬 추론과 운영 엔진 업데이트

- 사용자의 FIFO 시험 제보/병렬 요청을 반영해 기본 SharedModels를 독립2슬롯·공유weights·worker별processor/진단·CUDA2stream으로 바꿨다. 준비/카운트다운도 함께 진행하고 자기 stream만 동기화한다. CLI/PS 기본 parallel, explicit serial 복구 및 startup/round 모드 메타데이터를 추가했다.
- 모델 public serial API는 유지하며 fork_for_inference/fork_for_worker와 readonly 예측을 추가했다. 학습/전처리/임계값·모델 선택/학교/사진 변경0이다.
- 전체 Python193개15.955초 통과, 신규병렬9/ML문맥5·이전serial회귀 유지·CLI/PS 검사 통과. 실제GPU16조건쌍×각mode3회 결과차0·OOM0·weights공유, Kineto44969kernel중서로다른2stream실제겹침0.553852초를 확인했다. 일부조합은느려지며 지연0/50%분할/정확도 보장이 아니다.
- 공개 A/B 새 QA방 각1판에서 양lane loading게이트·각표시9사진PILdecode/3역할준비·공통출발후ML1/plan1·250ms·RGB재사용·표시선택일치 모두통과. 실제외부브라우저/현장리허설과구분한다. 산출물정본은 runs/parallel-operating-20261105/cuda-report.json 및 live-v1/verification.json이다.
- 이전운영체인43132→17060→38628을절대경로/부모검사후업데이트용으로종료하고 GPU검사뒤새운영체인21536 → 43456 → 38212을켜뒀다. startup parallel2슬롯/2stream·두worker예열·생존검증완료. 토큰메모리전용이므로 사용자새A/B방최초재연결1회가필요하고이후같은방교체다. 새정본 operator-start.json/STATUS를따른다. 서버v13은재배포하지않았다.
- 남음: 사용자외부컴퓨터 A/B재시험·연속참가자/장시간부하, 기존40%/ONNX/Pi/legacyOS입력. 기존FIFO/11/02후보수치는이력으로보존했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이번 작업 검토: 위13개 전체 본문을 분담 재독·갱신했고 새 Markdown은 없다. 실제 변경/검증/미완료·재현 명령을 STATUS에 기록했다. 원본/공개본 문서13개 점검과 별도 UTF-8/링크/목록/설정JSON8개 감사·Git diff가 통과했으며 최종 감사 정본은 runs/parallel-operating-20261105/document-audit-final.json이다. 공개 내보내기342파일 민감 자료/코드 바이트 검사 findings0, 병렬 구현 커밋9fde9c77a707b4dbe599339e7cd70c8a09f2c3ca를 기존 PUBLIC main에 푸시하고 로컬/원격 SHA 일치를 확인했다. 결과 문서도 후속 동기화한다. 최종 조회에서 새 운영 체인21536→43456→38212가 생존 중이며 종료하지 않았다.

## 2026-11-05 외부 컴퓨터 시험용 서버 확인·PC 엔진 가동

- 기존 공개 Sites active/public·최신v13을 확인하고 human/bot의 A/B 페이지 및 health6개 모두HTTP200·protocol3/barrier/250ms를 확인했다. 서버 재배포·자격/환경·사진·방 변경은 없다.
- 기존 엔진0개 확인 후 정규 start_remote_engine.ps1을 코드 입력용 새 visible 콘솔로 시작했다. 현재 체인43132→17060→38628의 실행경로/부모 관계·생존과 새 startup을 확인했다. CUDA3모델 load15.046초+합성warm3.657초=18.703초 완료, 문제사진0·agent코드입력0이며 계속 켜 둔다. 정본은 runs/server-readiness-20261105/operator-start.json/public-http-check.json과 runs/remote-engine/20261105-153228-f21fc803/startup.json이다.
- 한 콘솔 A/B 최초코드 입력·공개 HTTPS 4주소·PC 준비/AI 표시 연결·세 역할 사진 준비/출발·같은 방 next 순서를 다시 확인했다. 사용자는 단일 엔진 A/B 연결을 이해하고 외부 시험을 진행하기로 했다. 추가 엔진/브라우저 창은 열지 않았고 실제 외부 컴퓨터/한 판 결과는 미수신이다.
- 모델/학습/임계값·운영사진/학교·40%/ONNX/Pi/legacy OS 입력 상태는 그대로다. 새 제품 코드 변경이나 전체 단위 테스트 재실행 없이 실제 기동/합성 예열·HTTP로 확인했다. 11/04 GitHub 공개는 이력으로 보존하고 이번에는 원격 소스를 다시 푸시하지 않았다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이번 작업 검토: 관리13개 전체 본문을 분담 재독·11/05 갱신하고 현재 PC 기동/공개 HTTP와 미확인 외부 시험을 구분했다. 운영 엔진을 사용자 시험용으로 계속 유지한다. `check_docs.py --date 2026-11-05`의13개 및 별도 전수 감사의 UTF-8/로컬 링크/전체 목록/설정JSON8개 모두 통과했다. 기록은 runs/server-readiness-20261105/document-audit.json이다. 마무리 생존 조회에서도 새 운영 프로세스 체인을 확인했고 종료하지 않았다.

## 2026-11-04 GitHub public 소스 저장소 생성·푸시

- 사용자가 새 public 저장소 `Alpha_Human_VS_AI` 생성과 전체 프로젝트 소스 푸시를 요청했다. GitHub CLI의 현재 계정 ProgrammingYJ를 확인하고 https://github.com/ProgrammingYJ/Alpha_Human_VS_AI 생성/public 상태를 확인했다. 기존 동일 이름 저장소는 없었으며 기존 원격을 덮어쓰지 않았다.
- 별도 Desktop/Alpha_Human_VS_AI 소스 체크아웃에 Python/웹을 일반 파일로 내보내 기존 Sites Git과 운영 폴더를 보존한다. 원본/모델/사진/정답은행/로그/JSON 결과/자격/의존성·생성물/과거 Git은 제외한다. 작성한 runs 도구 소스는 개별 검사 후 보존하며 원시 운영 정답을 담은 빌더2개는 제외한다.
- .gitignore의 웹·비밀·모델/실행 결과 제외와 작성 코드 예외를 보강하고 scripts/export_public_source.py를 추가했다. 공개 Markdown에서 제외된 로컬 결과 링크만 일반 경로로 표시하며 원본 코드는 바꾸지 않는다.
- PUBLIC main에 최초333파일을 푸시했고 첫소스SHA1bd9efbdc15ad9b36cdea129d7cbdaa55e3ab30d가 로컬/ls-remote/GitHubtree에서 일치했다. GitHub 기본main·empty=false·333개mode100644·gitlink0을 확인했다. 공개복사본 코드 바이트/필수vendor/비밀·자료 제외 독립 감사 및 Python179(12.565초)/Node110·원본/공개본 문서13개/UTF8/링크/설정JSON8개 검사가 통과했다. 결과 갱신 문서도 같은 main으로 동기화한다. 새 의존성 재설치·ML 운영·Sites 재배포 검사는 수행하지 않았다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이번 작업 검토: 관리13개 전체 본문을 분담 재독·11/04 갱신하고 실제 GitHub public main 푸시·원격 일치·복사본 코드/제외 범위·독립 감사·Python179/Node110 및 원본/공개본 문서13개 통과를 기록했다. 원래 Sites 이력/운영 폴더·모델/사진/배포/프로세스는 보존했다. 최종 문서 동기화의 원격 커밋/공개 상태는 로컬 release 기록으로 확인한다.

## 2026-11-02 사진 명확성 교체·관리 활성 집합·버전13

- 기존 공개 46장 전수 RGB 검토와 216px 타일 검토로 22장을 퇴역하고 24장을 유지했다. 새 CC0 7장/PD 3장을 교차검토·원문 권리/그룹 확인해 총 활성34장·9,290,899bytes로 운영에 반영했다. 정본은 data/booth/public-web-v3/bank.json이다. 모호한 장면을 줄였으며 null을 음성으로 바꾸거나 모델 정오답으로 선별하지 않았다.
- 비공개 관리자 includeInactive/active/SHA 조회 및 PUT photoIds 전체 활성 집합 교체를 추가했다. 4종 그룹 준비를 검증하고 단일 SQL로 교체하며 반복은 멱등이다. 현재 라운드의 퇴역 사진 URL/R2/정답 스냅샷은 보존하고 다음 추첨만 제외한다.
- 버전13 SHA2cc72fceeed5cbbd1f44eb63a6f52df7067a8880·saved appgprj_6ade37995018819184a42c88bb0fde7c~appgver_dd082b3c37848191b2be432616556827·deployment appgdep_6ae897a2e2588191b051f193b217e75a succeeded/환경5다. 소유자 ID·public audience·도메인은 유지했고 숨김 관리 키만 갱신했다. 비밀값은 파일/소스/인자/로그에 저장하지 않았다.
- 새10/10 등록·활성34/퇴역22/등록56·34파일 SHA/RGB·기존 경기9사진 유지(퇴역3 HTTP200)·새 공개5판4유형/9독립그룹/정답수/양역할동일사진·출발/비노출/퇴역재출제0을 확인했다. 실제 운영 카탈로그의 11조합×32=352추첨도 통과했다. 정본은 runs/photo-clarity-20261102/retry1-production-verification.json 및 production-bank-combinations.json이다.
- 대상 Node33개·TypeScript·build·diff 및 실제 localhost HTTP 복합1검사5.806초가 통과했다. 로컬 하네스 비JSON403/최소fixture 실패, 첫 운영 하네스 PC절대시계 대기 실패를 보존하고 파싱·fixture·서버상대시각 검증으로 수정해 통과했다. 실패 전에 운영 업로드/활성화는 0이었다.
- ML 추론·학습·임계값 변경·답안 제출·운영 PC 프로세스 조작은 0이다. 독립 사람 검수·실제 행사 GUI/기기 리허설·40%/ONNX/Pi/legacy 입력은 미완료이며 새 사진을 정확도 표본으로 보고하지 않는다. 다음은 사용자의 실제 화면 검수다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 관리13개 전체 본문과 실제 RGB·그룹/권리·원자 활성 전환·배포/검증을 분담 재검토했다. 새 Markdown은 없다. `check_docs.py --date 2026-11-02`의 13개와 별도 전수 감사의 UTF-8/로컬 링크/13개 목록/설정 JSON 8개가 모두 통과했다. 결과는 runs/site-publish/photo-clarity-document-audit-20261102.json에 보존했다. 검증용 로컬 미리보기는 종료했고 운영 PC 엔진은 조작하지 않았다.

## 2026-11-02 GPU 분배 검토·오프라인 CUDA 2스트림 비교

- 현재 GPU 예약/FIFO·모델의 가변 상태와 공식 NVIDIA/PyTorch 문서를 검토했다. CUDA 스트림의 동시 요청과 고정 50% 분배를 구분하고 MIG 지원 목록·Windows Green Context 거부·메모리 cap의 의미를 기록했다. 설치·운영 정책은 바꾸지 않았다.
- 운영 엔진 0개를 확인한 뒤 기존 모델 한 벌을 로드하고 공개 RGB 9장씩 두 작업을 모드별 3회 비교했다. 직렬→2스트림 중앙값은 존재+사람 0.386→0.299초, 나무+존재 1.171→1.847초, 나무+나무 2.238→3.033초다. 레인별 processor/진단 상태·입력을 분리한 실험 래퍼는 기존 함수와 출력 차이 0이고 모든 반복 출력도 일치했다. 실험/보고서 (로컬 산출물: `runs/gpu-concurrency-20261102/report.json`)를 보존했다.
- OOM 0회, PyTorch 최고 할당/예약 약 1,539/2,350MiB, 완료 직전 장치 전체 관측 3,036/8,188MiB를 구분했다. 호출 구간은 겹쳤으나 GPU 타임라인은 미수집이다. 고정 한 사진 집합/각 3회 결과는 모든 문제·현장·장시간·정확도·무지연 보장이 아니다.
- 나무 조합은 지연이 증가해 운영 동시 추론을 도입하지 않았다. 운영 코드·배포·방·프로세스·사진·가중치·임계값·학습 변경은 0이다. 다음은 준비/카운트다운 예약 구간과 모델 실행 병행을 분리 검토하고 현장 A/B 리허설을 하는 일이다. 학교/40%/ONNX/Pi/legacy OS 입력의 미완료 경계는 유지한다.
- 아래 13개 전체 본문을 분담 재독·갱신했다. 새 Markdown은 없다. 문서 검사 13개 모두 통과했고 별도 전수 감사도 UTF-8·로컬 링크·13개 목록·설정 JSON 8개 모두 통과했다. 감사 결과는 runs/site-publish/gpu-concurrency-document-audit-20261102.json에 보존했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 실제 저장 RGB 동시 요청 비교를 이전 공개 경기 검사와 구분하고 현행 FIFO 유지 및 실측 한계를 반영했다. 전체 문서 검사 명령은 `scripts/check_docs.py --date 2026-11-02`와 `runs/site-publish/audit_docs.py --date 2026-11-02 --output runs/site-publish/gpu-concurrency-document-audit-20261102.json`이다. 최종 결과는 문서 13개·별도 감사·설정 JSON 8개 모두 통과다.

## 2026-11-01 A/B 동시 운영·GPU 대기 설명 재확인

- 사용자 문의에 기존 공개 CUDA 보고서를 읽어 A/B 병행·모델1회 공유·GPU FIFO 예약/추론·모델 반환 후 해제를 확인했다. A 참가자가 푸는 동안 B가 진행할 수 있지만 시작 요청이 겹치면 B는 경기 시작 전에 기다릴 수 있다. 두 레인의 절대 출발 시각과 각 방 인간/AI의 공통 출발을 구분했다.
- 기존 A1/B1의 예약 전0.375/10.438초와 경기 중 GPU 대기0/0초, 모델 함수연못0.094초/나무1.875초를 대조했다. 예약 전 값은 다른 방의 준비·카운트다운/상태 HTTP를 포함하며 순수 GPU 계산시간이 아니다. 모든 유형 조합·장시간·현장 네트워크의 지연0 보장은 미완료다.
- 이번은 설명·문서 갱신뿐이며 새 코드·배포·모델/사진/임계값·추론/성능시험·하드웨어 조회·운영 프로세스 변경0이다. 버전12의 기존 게시와 가동 기록은 보존했다. 다음은 사용자 환경의 A/B 실운영 재검증이며 학교/40%/ONNX/Pi/legacy OS 경계는 유지한다.
- 아래13개 전체 본문을 분담 재독하고 변경 없는 데이터 문서도 검토 결과를 기록한다. 새 Markdown은 없다. 전체 문서 검사13개와 별도 전수 감사의 UTF-8·로컬 링크·색인/목록·설정JSON8개가 모두 통과했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): A/B 두 경기의 처리 가능성과 무지연 보장을 구분해 기존 실행 보고서·공유 GPU 구조 및 관리 문서 전체를 재검토했다. 실제 변경 범위는 Markdown이며 운영 엔진·웹·모델·학교 정책은 유지한다. 최종 기계 점검은 문서13개와 설정JSON8개 모두 통과했다.

## 2026-11-01 사진 준비 동기화·연결/지연 수정·버전12

- 10/28중단된부분구현과공개v11의불일치를확인하고3역할9장준비→공통출발을서버/화면/PC에완성했다. loading동안타이머0/질문숨김,동일DOM/RGB재사용,protocol3/epoch/CAS/숨김페이지철회/60초실패복구를구현했다. v11전용protocol2협상과배포중3업그레이드·ACK유실복구를추가했다.
- 느린HTTP시계변경·무한hang·정상409끊김오표시·사람로컬선택잠금을수정했다. 마지막준비ACK와HB의시각경합으로all3ready가loading에멈추는조건을독립검토에서발견해freshclock+상태조회재정산으로고쳤고재현회귀를추가했다. PC HTTPS/pool재사용·불필요HB/GET제거·합성예열·질문에필요한고정모델만실행하는경로를추가했다.
- Python179개7.846초·Node105개0.915초·tsc/컴파일/diff/productionbuild통과. 실제localhost6종20.935초통과,마지막경합수정후배리어1종3.614초통과다. 실제DOM도구연결은불가해우회0이며공개CUDA/HTTPS/운영가동확정결과는STATUS에기록했다.
- 버전12 commit `6ac76b5b4364ccfaa75b8907052aa9757dfc54cb`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_e3a88ddc0574819199ce873e6c599611`, deployment `appgdep_6ae705508ea4819187390ffbdbe500a2`, 환경revision4게시succeeded다. schema-only0004사진준비5열추가·로컬한번적용·이전migration불변,기존공개범위/도메인/비밀환경/사진/모델을보존했다.
- 로컬공개46장/12,362,595bytesSHA·디코딩과v1두모델고정SHA를재검사했다. 학교/학습/튜닝/임의오답0이며독립품질·40%·Pi/ONNX/legacy OS·현장리허설완료를주장하지않는다.11/07행사전자체검증뒤사용자가실제컴퓨터에서한번더검증한다.


- 공개 두호스트 HTML/health/각17개 초기자산200·프로토콜3, 인간호스트생성→봇호스트표시/PC연결6검사 통과다. 실제CUDA A2+B1은 캐시재사용/게임중다운로드0/사전문제추론0/각예측·제출1회/363생존샘플을 확인했다.[]/[]/[1]오답timeout은 기능검사이며 정확도나40%평가가아니다.
- 원본26검사 중25true·느린인간 게이트 미관측1false를 그대로 보존했다. 시험보류기준을 고치고 별도 공개10/10으로4.984초 대기 중 타이머0과 모두준비후출발·출발전취소를 검증해 종합보고서에 연결했다. A2의16.797초 QA직렬관측공백과 공개타일간격표본0·실제DOM미측정을 공개했다. 고정9RGB full/질문별 점수·인원수·선택은동일/점수차0이다.
- 운영엔진0개확인후19224→12972→31892를 새로실행했다. CUDA로드6.031초/합성예열2.469초/총8.5초·생존확인후켜두었고 사용자코드입력0이다. 최초새방연결후일반참가자교체는같은방next다.13개문서의검토표식/날짜/색인·별도전수UTF8/링크/설정JSON8개검사가통과했고최종수정후재실행해13개모두통과했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 관리13개 전체 본문을 분담 재독하고 최신 코드·실제 검사·배포와 과거 이력을 대조했다. 내용 변화 없는 데이터/평가 문서도 검토 결과를 기록했다. 새 Markdown은 없으며 문서점검 최종결과/공개CUDA/운영가동은 STATUS에 확정 기록한다.


## 2026-10-27 통신 왕복 제거·공개 사진 확대·학교 미사용·버전11

- 사용자 요청으로 타일별 상태GET/선택POST/ACK대기를 고정 ML 선택 계획1회 업로드로 대체했다. 서버500ms표시 버퍼·250ms일정·마지막 선택시 논리제출이며 같은 목록멱등/다른목록거부·human선승중단·due봇과human원자채점·timeout/같은방next/구형API호환을 구현했다. 수락후PC끊김에도서버재생이완료되며 미래정오답은서버만보유한다. 계획받은viewer는50ms시계+500ms상태조회,계획없는진행중bot만125ms다.
- RGB9장최대3병렬/map순서/실패정리를추가했다. 모델·전처리·임계값·학습/고의오답 변경0이다. 새 nullable4컬럼 migration0003생성·로컬한번4명령적용,기존0000~0002불변이다.
- Commons77후보에서명확한22장(6,299,046bytes·CC0 15/PD7)을시각/권리/원본그룹/해시와두AI교차검토후선정했다. 애매한수면/눈웅덩이·동일근접촬영숲·혼합권리·그림/조형물/합성은제외하고카누수면연못조건은null로뒀다. 독립사람검수는미완료다. 사진선정에모델예측을사용하지않았다.
- 신규22/22업로드·기존중복0으로운영46장/12,362,595bytes(CC0 26/PD20)이다. 공개46파일SHA/디코딩·4유형9독립사진·정답수범위·양역할배열/출발동일·비공개답안보호를검사했고신규12개공개타일을관측했다. 관리자SERVER사진검사와실제ML풀이를분리했다. 학교는이번행사촬영/문제/최종평가범위에서제외하며미래개발유입차단은유지한다.
- Python165개14.515초·Node89개1.217초·tsc/대상ESLint/컴파일/diff통과,실제localhostHTTP5종도통과(runner20.659초,계획검사13.005초)다. 실제공개CUDA A2판+B1판은18검사passed=true·모델1회로드8.844초·생존216샘플·준비후끊김관측0·각예측1/계획1/서버제출관측1을확인했다. A1사람[0,8]정답1판·A2연못[]/B1나무[]오답timeout2판은재사용기능검사이며정확도1/3이나40%달성아니다.
- 실제계획ACK0.360/0.375/0.469초,사진9장다운로드1.500/2.797/1.937초다. 예정250ms간격1표본·실제타일HTTP0표본을구분했고과거API762~957ms와예정시각을직접성능비교하지않는다. 로컬고정API브라우저9사진로드/4체크/읽기전용/넘침0은실제ML·OS·250ms렌더링검사가아니다. 첫하네스409회차경합을고친새QA방에서정상완료했으며불완전영역캡처파일은제거했다.
- 버전11 commit `8755f3c852c555ac2637c47a85bd4e3cedac8d0e`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_0ef517f5604c8191b1e96654ef95eea5`, deployment `appgdep_6ae065686ac88191a8ea3c01f755ce6a`, 환경revision4로게시succeeded다. 관리자키만동일권한갱신·메모리/stdin전용,owner/도메인/공개범위/기존사진/모델을유지했다. 두호스트HTTPS200을확인하고기록했다.
- 검증한운영체인6916→49352→16984만업데이트를위해종료하고45960→7608→39488을시작했다. CUDA3모델1회6.891초로드·계획우선/0.25초/사진3병렬·생존을확인해켜두었고코드입력0이다. 업데이트후새방최초한번재연결,이후같은방next를유지한다. 가동정본은scheduled-current-engine.json과STATUS다.
- 다음은실제운영컴퓨터배치/네트워크/장시간반복리허설·충분한독립품질/40%·ONNX/Pi/legacy OS다. 현재학교최종평가계획은제외했다. 아래13개전체본문을분담재독·갱신하고내용변경없는문서에도검토를기록했다. 과거수치와당시정책은이력으로보존하며새Markdown은없다.
- 최종 `check_docs.py --date 2026-10-27`은13개모두통과,별도전수감사도13개·UTF-8·로컬링크·색인/목록·설정JSON8개통과다. 교차검토에서legacy첫대기0범위와stop후서버계획계속설명을교정했고옛실측은보존했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md


## 2026-10-27 선택 간격0.25초 변경

- 사용자 최신 요청으로 이전1초 제한을0.25초/250ms로 대체했다. Python 공유 하한·ACK후 대기·legacy 스케줄러/검증·CLI·보정기·PC/Pi 예시, 서버 사전 검사/SQL CAS와 UI 안내를 함께 교정했다. HTTP재시도1초와 GPU 예약/학습 정책은 유지한다.
- 경기 중 remote AI 표시는125ms 폴링, 그 외500ms이며 중복 요청을 막는다. 통신/렌더링을 포함한 실제250ms 표시 보장으로 설명하지 않는다.
- Python155개11.072초·Node73개1.270초·타입/대상lint/컴파일/diff 통과. 실제 localhost HTTP4종도 모두 통과(runner20.192초)했다. 249ms 거부/250ms 허용과 기존 순서/CAS/생존/참가자 교체/공통 출발을 확인했다.
- 버전10 build/source push/package/save/publish succeeded다. commit `44a78ce020602d86c248bcbf9f3da7658f3087a5`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_975ee4e587448191b06c0e3516b3c9c1`, deployment `appgdep_6ae05d76f7b4819186719d3ef1e280f4`, 환경revision3이다. 도메인/공개범위/D1/R2/기존migration·사진은행은 유지했고 새migration0이다. 두 호스트HTTPS200을 확인했다. 배포/HTTP 기록은 runs/site-publish/quarter-release.json·quarter-release-http.json이다.
- 고정타일0/1/2의 격리API 검사에서 로컬307/315ms·공개957/762ms(각2표본), 중복ACK·viewer선택 일치가 통과했다. 공개762ms로 기존1초보다 짧은 선택이 허용됨을 확인했지만 실제 ML/렌더링 속도 측정은 아니다. 모델/사진/정답/제출을 사용하지 않았으며 첫 간격은 중복ACK 왕복도 포함한다. quarter-interval-local-v1.json·quarter-interval-public-v1.json에 기록했다.
- 검증한 운영체인44388→39712→39120만 종료하고 최신49376→39132→15816을 시작했다. CUDA3모델1회 로드9.734초·생존 확인 후 켜 두었고 운영콘솔코드 입력0이다. 이번 업데이트 뒤 새방으로 한 번 PC/표시를 다시 연결하고 이후 정상 참가자 교체는 같은방을 유지한다. 실제OS/Pi/브라우저 표시 간격·학교/40%·행사장 리허설은 미완료다.
- 아래13개 전체 본문을 이번 제한 변경과 기존 GPU 예약 구현에 맞춰 분담 재검토·갱신했다. 변경 없는 데이터 정책도 검토 결과를 남기고 과거1초 측정값은 보존했다. 새 Markdown은 없다. 최종 `check_docs.py --date 2026-10-27`은13개 통과, 별도 전수 감사도13개·UTF-8·로컬 링크·색인/목록·설정JSON8개 통과다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

## 2026-10-27 GPU 예약 출발 구현·버전9 (직전 작업 확정)

- 사용자 승인으로 queued 무문제/타이머0→PC FIFO예약→begin 공통약2초 출발→모델 반환후 예약해제→방별 선택을 구현했다. 프로토콜2·취소/만료/오류 복구·begin 멱등/옛티켓 거부와 구버전 출발 거부를 추가했다. migration0002는5컬럼 추가이며 기존0000/0001은 유지했다.
- Python154개·Node72개·실제 HTTP4종이 통과했다. 실제 로컬/공개 CUDA 각각A두판+B한판은17검사 통과, 경기중 GPU대기0·선택전해제·같은방/코드/표시·예측/제출1회를 확인했다. 각3판 모두오답timeout은 재사용24사진 기능검사이며 정확도/40% 달성 근거가 아니다. 연속선택 간격 표본은0이다.
- 버전9은 build/source push/package/save/publish succeeded다. commit `774cf6edfc54469253f2fbb343176fdf2d123581`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_9987abc16e84819187520a57980c38b3`, deployment `appgdep_6ae02fab01508191ba469fa974db7b53`, 환경revision3이다. 도메인·공개범위·기존사진·키를 유지했다. 두호스트HTTPS200 확인, 운영엔진 당시11.812초 로드/가동. 최신0.25초가 이 당시1초 정책을 대체한다.
- schema2는 모델함수/상태HTTP를 분리하지만 예약대기는 상태HTTP를 포함한다. 상태HTTP를 포함한 기존v8 지표와 속도를 직접 비교하지 않는다. 실제 queued 렌더링은 브라우저 연결 종료로 미검증이며 입력도구 우회0이다. 학교/모델/40%/ONNX/Pi·부스물리 리허설 경계를 유지했다.
- 다음 작업은 최신사이트·PC 갱신 후 행사 컴퓨터 배치에서 최초연결/공통출발/같은방 다음참가자 반복, 독립 품질평가·학교최종평가·ONNX/Pi다.


## 2026-10-27 GPU 순차 대기의 공정성 검토

- 사용자 지적에 현재 공유 GPU 대기가 타이머 시작 후 발생하며 한쪽 AI 지연이 그 방 인간에게 유리할 수 있음을 확인했다. 기존 동시2세션 실행 성공은 동일 반응시간/공정성 검증이 아니다.
- 시작 요청을 GPU 예약 대기로 받은 뒤 자원 차례에 해당 인간/AI의 공통 출발을 확정하고 추론 후 GPU를 해제하는 방안을 미구현 제안으로 기록했다. 선택/제출은 기존처럼 방별 독립 진행이다. 사전 정답 추론·사후 시간 보정을 하지 않는다.
- 보고서 gpu_queue_seconds/inference_seconds의 active() 상태조회 HTTP 포함을 확인해 ‘순수 GPU 대기/순수 추론’이라는 이전 설명을 교정했다. 기존 측정값은 보존하고 새 순수 측정으로 바꾸지 않았다.
- 이번은 문서 검토만으로 코드·타이머 규칙·추론/성능시험·배포·운영 프로세스 조작0이다. 학교/모델/임계값·1초·40%·Pi/ONNX·현장 리허설 경계를 유지한다. 다음 구현은 별도 작업이며 아직 완료하지 않았다.
- 관리13개 전체를 분담 재독·갱신했다. `check_docs.py --date 2026-10-27`과 별도 전수 감사에서13개·UTF-8·로컬 링크·문서 목록·설정 JSON8개가 통과했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): GPU 경합의 참가자 조건 차이와 보고서 시간 구간을 재검토했다. 현재 구현·과거 측정·미구현 예약 출발 제안을 나눠 기록하고 관리13개 문서를 갱신했다.

## 2026-10-27 통신 계층·A/B 두 세션 설명 확인

- 사용자의 TCP/두 세션 용량 문의에 코드와 기존 보고서를 읽어 답했다. 원격은 Cloudflare HTTPS API/폴링이며 PC간 raw TCP 직결·전용 WebSocket이 아니다. 같은 urllib 경로의 공개 읽기 전용 GET에서 HTTPS200/HTTP1.1을 확인했고 브라우저 HTTP2/3 협상은 미측정으로 남겼다.
- 모델1회 로드 공유·단일 GPU 추론 잠금·독립 A/B를 재확인했다. 과거 버전8 A1/B1의 대기 구간0.391/2.250초·추론 구간1.547/0.844초(상태 확인 HTTP 포함)와 동시 실행 검증을 근거로 삼되 새 성능 측정/장시간 보장으로 쓰지 않았다. 운영 실행기 하나에 A/B를 연결하도록 설명했다.
- 이번 변경은 관리 문서뿐이며 코드·배포·ML추론/성능측정·학교/모델/임계값·운영 프로세스 조작0이다. 버전8을 유지한다. 현장 컴퓨터/네트워크·장시간/유형별 동시 부하·40%·학교 최종 평가·Pi/ONNX·OS 입력 미완료는 유지한다.
- 관리13개 전체를 분담 재독·갱신했다. `check_docs.py --date 2026-10-27`과 별도 전수 감사에서13개·UTF-8·로컬 링크·문서 목록·설정 JSON8개가 통과했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 설명 요청에 맞춰 통신·공유 모델·두 세션 실행 근거와 한계를 갱신했다. 새 HTTP 응답 확인과 과거 GPU 측정을 구분하고 관리13개 전체 검토와 문서 점검 의무를 유지한다.

## 2026-10-27 컴퓨터 화면 운영·초기 생존 상태 수정·버전8

- 최신 사용자 요청으로 Android4대 계획을 컴퓨터 브라우저 인간/AI 표시로 대체했다. 기기/모니터 대수는 미정이며 기존 PC ML·remote 선택·A/B·같은 방 참가자 교체·1초·권한은 유지한다. UI·CLI·PS1·운영 문서를 교정했다.
- 서버가 D1 읽기 전 now와 읽기 도중 새 heartbeat를 비교해 정상 연결을 false로 표시하던 경합을 재현했다. remote 읽기 후 시각으로 serverNow/ready/connected를 함께 투영하도록 고쳤다. engineHeartbeatReceived로 첫 알림 대기와 실제 만료를 구분하고 제출/0개/오류에서도 stale를 표시한다. 3초/15초·진짜 미래값 거부·라운드 CAS·단일승자는 유지하며 schema/migration 변경0이다.
- Python147개10.214초·Node55개1.157초·TypeScript·대상UI ESLint·Python컴파일·PowerShell구문/BOM 통과. 실제 localhost HTTP3종(5.323/7.439/20.859초,runner21.017초)도 통과했다.
- 실제 CUDA 로컬 A두판+B한판: 모델 로드8.766초·생존947샘플·준비후끊김0·passed=true. 세문제 모두나무0개오답timeout으로 실제선택간격표본0이다. 공개검사는 모델 로드7.063초·생존69샘플·준비후끊김0·모델/표시일치·passed=true. 사람3문제에서11선택·간격8개최소1.375초·세정답종료를 확인했다. 같은24장 재사용 연결검사로100%정확도·40%달성·학교 성능으로 일반화하지 않는다.
- localhost 브라우저 인간1920×1080/AI표시1280×720 대기 화면의 문구·가로넘침0과 스크린샷을 기록했다. 실제 행사 기기 배치와 새 live격자 검증이 아니다. 운영 중 사용자 방/답안/OS입력은 조작하지 않았고 QA 엔진의 RGB 추론만 수행했다.
- 버전8 build·source push·package·save·publish succeeded. commit `5e05f47c23d13156b28315574b275c09b03277e6`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_358046f965d4819198953a2e3041518f`, deployment `appgdep_6adffa6ea6808191aaaa17cb30798839`, 환경revision3이다. 기존 도메인/공개범위/D1/R2/키/0000·0001을 유지했다. human/bot HTTPS200과 최신컴퓨터안내를 확인했다. 기록은 runs/site-publish/desktop-release.json·desktop-release-http.json이다.
- 기존 운영 엔진0을 확인한 뒤 최신 콘솔17448→11832→19656을 시작해 CUDA 로드8.937초와 생존을 확인하고 켜 뒀다. 에이전트 운영콘솔 A/B코드입력0·특정사용자방준비미확인이다. QA 엔진은 별도종료이며 실행기와 구분한다.
- 학교/추가학습/가중치·임계값·전처리 변경0. 40%·독립품질/학교평가·Pi/ONNX·기존OS입력·현장컴퓨터/모니터·네트워크 리허설은 미완료다. 다음은 실제 행사 배치에서 최초연결→시작→다음참가자 반복 점검이다.
- 관리13개 전체를 분담해 재독·갱신했다. 문서 최종 점검: `check_docs.py --date 2026-10-27`은13개 모두 통과했고 별도 전수 감사도13개·UTF-8·로컬 링크·최신 문서 목록·설정 JSON8개 모두 통과했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 컴퓨터 화면 전환과 초기 연결 오표시 두 원인을 수정·배포하고 로컬/공개 실제 모델 및 생존 샘플을 검증했다. 정상 연결과 첫 대기·진짜 만료를 구분하며 실제 추론 속도 개선이나 정확도를 보장하지 않는다. 관리13개 전체 검토·검사와 미완료 경계를 기록했다.

## 2026-10-27 같은 방 연속 참가자·PC 지속 엔진·버전7 게시

- 사용자 후속 요청으로 정상 참가자 교체의 새 방/코드 방침을 대체했다. remote 인간 결과의 ‘다음 참가자 준비’가 같은 방/코드/engine·viewer 권한을 유지해 lobby로 원자 초기화하고, 다음 사람이 PC 재준비 후 수동 시작한다. legacy는 기존 한 판/새 방 방식이다.
- 서버 next의 종료 roundId·revision CAS/멱등 ACK, 새 start 허용, heartbeat roundId+roundNumber CAS, 종료 경합409 round_ended를 구현했다. 늦은 옛 요청이 다음 판 선택/준비를 덮지 못하게 했다. schema/migration 추가0이다.
- UI는 다음 참가자 버튼·연결 유지 안내·새 사진/선택/타이머 reset과 revision 기반 늦은 상태 거부를 추가했다. PC 대화형 기본은 지속 세션이며 같은 모델·토큰으로 라운드별 한 번만 새 RGB 추론/제출한다. --once·stop A/B·quit 경계를 유지했다.
- Python141개(11.514초), Node43개(0.737초), TypeScript·대상UI ESLint·compileall·pip check 통과다. 실제 localhost HTTP3종을 통과했고 종료 경합 명시 검사 추가 후 해당1종도5.555초에 통과했다. 테스트용 관리자 답안은 localhost 서버 채점 프로세스에만 있고 실제 ML 엔진에는 전달하지 않았다.
- 로컬 실제 CUDA 연속 검증은 passed=true다. A1/B1 나무0개·A2 건물[2,3,6]을 라운드별1회 제출하고 모두90초 timeout으로 종료했다. 모델 로드9.531초, 방/코드/표시권한 유지·선택초기화·재준비·표시/모델 일치·최소1초를 확인했다. 근거는 runs/continuous-booth-local-v1/이다.
- 버전7 production build·source push·package·save·publish가 succeeded다. commit `483d473ef9d5532303216b1ddfdeda179fe7354a`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_42c2bde8e68c81919c4fadbaf152c471`, deployment `appgdep_6adfec3d93d88191842861ff8dc66136`, 환경revision3이다. 두 기존 도메인 HTTPS200·공개 범위·D1/R2·키·기존 migration을 유지했다. 근거는 runs/site-publish/continuous-release.json과 continuous-release-http.json이다.
- 공개 실제 CUDA 연속 검증 runs/continuous-booth-public-v1/verification.json도 passed=true다. 모델1회 로드8.594초, A1=[], A2=[5], B1=[]; B1: timeout/winner=None, A1: timeout/winner=None, A2: timeout/winner=None. 같은A방 두판과 독립B방, 같은연결/표시권한/코드·새사진추론·1회제출·1초간격을 확인했다. 물리 Android0·정답/관리자 접근0·OS입력0이며 정확도 표본이 아니다.
- 기존 운영용 PID39972/46576/46728은 재조회 시 모두 종료 상태였고 다른 remote 엔진0이었다. 최신 소스로 표시되는 PowerShell38476→venv44732→base42276을 시작해 CUDA 모델1회 로드6.250초와 생존을 확인하고 켜 뒀다. 기록은 runs/remote-engine/20261027-091218-5af7e178/startup.json다. 이 운영 콘솔에는 A/B 코드 입력0이며 QA엔진과 분리한다.
- 학교사진/추가학습/가중치·임계값·전처리 변경0이다. 유형별40%·독립 품질평가·학교최종평가·ONNX/Pi·물리Android4대 리허설·기존 OS입력은 미완료다. 다음은 실제 패드 네 대의 최초페어링→두판 반복·네트워크/화면 점검이다.
- 관리13개를 분담해 전체 본문을 읽고 변경/불변 검토 결과를 갱신했다. 교차 검토에서 legacy 인간 URL 누락을 찾아 README/SETUP에 `human.marulee.dev/?mode=legacy`를 명시했다. `check_docs.py --date 2026-10-27`은13개 모두 통과했고 별도 전수 감사도13개·UTF-8·로컬 링크·최신 문서 목록·설정 JSON8개 통과다. QA용 로컬 미리보기와 공개 검증 프로세스는 종료하고 운영용 PC 엔진은 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 사용자 승인된 같은 방 연속 운영을 서버·화면·PC 지속 세션까지 반영하고 실제 로컬/공개 CUDA 두 회차 및 별도 B방과 버전7 게시를 검증했다. 최신 사용자 PC 콘솔은 켜 둔 상태로 모델 로드와 방 연결을 구분했다. 13개 문서 전체 갱신·최종 검사와 미완료 품질/실기기 경계를 기록했다.

## 2026-10-27 이전 최초 PC 엔진 가동·수정 전 운영안

- 사용자가 내일 운영 순서와 지금 PC 봇 실행을 요청했다. 기존 엔진0을 확인한 뒤 `scripts/start_remote_engine.ps1`을 표시되는 PowerShell 콘솔에서 실행했다. 사용자가 계속 쓸 실행기이므로 종료하지 않고 유지한다.
- 실제 PowerShell PID39972 → venv Python46576 → base Python46728의 부모/자식 체인을 확인했다. Windows 가상환경의 실행 체인이며 두 개의 독립 엔진을 띄운 것으로 해석하지 않는다.
- `runs/remote-engine/20261027-085448-1262f33b/startup.json`의 수정 시각은 UTC `2026-10-26T23:54:55.6974036Z`(사용자10/27 오전)다. remote·CUDA·`models_loaded_once=true`·모델 로드7.297초·GUI/자격증명 기록/튜닝 없음이 확인됐다. GPU 모델 로드가 실제 있었으므로 GPU 실행0으로 쓰지 않는다.
- 조회 시 lane 보고서는0개였다. 에이전트는 A/B 방 코드를 자동 입력하거나 새 경기/사진 추론을 시작하지 않았다. 사용자 직접 입력 여부와 방 연결은 서버 조회하지 않았다. 프로세스/모델 로드 완료와 특정 방의 준비·사진 판별·선택·제출 완료를 구분했다.
- Android4대 주소 배치 → 인간별 새 방 → 각 봇 표시 패드의 같은 레인 코드 → PC 숨김 입력 `A <코드>`/`B <코드>` → 각 인간 화면의 엔진/표시 준비 확인 후 시작 → 완료한 레인만 새 참가자 새 방/코드 순서를 문서에 반영했다. 상세 정본은 SETUP이며 원격 운영에 F8/좌표 보정·PC 전면창은 필요하지 않다.
- 코드·배포·사진/학교·가중치/임계값 변경과 새 성능 측정은0이다. 기존 모델 실패·40% 미달성·물리 Android4대 리허설·ONNX/Pi·기존 OS 입력 미완료를 보존했다. 앞선 '문서 전용'과 '검증용 엔진 종료'는 당시 이력으로 한정했다.
- 이 최초 실행 뒤 같은 방 연속 운영 수정으로 작업 범위가 확장됐다. 당시 문서 점검 대기 상태는 위 후속 수정의 전체 검토·최종 점검으로 통합했다.

### 이번에 읽고 갱신하는 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 최초 실행 검토: 당시 운영용 모델 로드·생존을 확인했고 새 방/코드 운영안을 기록했다. 이후 사용자 요구로 위 지속 방 구현과 최신 엔진 실행이 이를 대체했다. 초기 프로세스는 재조회 시 종료 상태였으며 최종 결과는 위 후속 변경과 STATUS를 따른다.

## 2026-10-27 이전 후속 기기 확인: Android 태블릿4대

- 사용자 후속 답변으로 네 대 모두 Android 태블릿임을 확정했다. 인간A·봇표시A·인간B·봇표시B와 PC ML→서버 선택→읽기 전용 표시 구조를 유지한다. Android에서 AI를 실행하거나 터치를 주입하는 구현으로 바꾸지 않았다.
- 운영 브라우저는 Chrome으로 통일하는 것을 권장 기준으로 기록했다. 실제 Chrome 설치·버전, 태블릿 기종·Android 버전·해상도·화면 방향과 네 대 동시 Wi-Fi/브라우저 동작은 미확인이다. 앞선 PC viewport·CUDA/API 검증을 Android 실기기 검증이라고 보고하지 않는다.
- 원격 경로에는 좌표/F8 보정과 PC 브라우저 전면 유지가 필요하지 않음을 다시 확인했다. 실제 운영은 PC 원격 엔진을 켜고 새 A/B 코드를 연결해야 한다. 다음은 실제 태블릿 네 대의 사진·버튼/상태 표시·동기화·동시 종료·연결 복구 리허설이다.
- 이 기기 확인 작업 당시 변경은 관리 Markdown뿐이었다. 당시 코드·GUI·배포·추론·새 정확도/속도 측정은0이다. 학교 최종 평가 전용·가중치/임계값 불변·40% 미달성·ONNX/Pi 미완료를 유지하며, 아래 원격 구현의 측정·게시 기록은 이전 작업 이력으로 보존했다.
- 관리 대상13개를 팀이 분담해 전체 본문을 재검토하고 갱신했다. 이번 수정 후 `check_docs.py --date 2026-10-27`은13개 통과다. data/models/runs/logs를 포함한 전수 목록도13개로 일치하고 UTF-8·로컬 링크·최신 CHANGELOG 전체 목록·설정 JSON8개 감사도 통과했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): Android 태블릿4대라는 확정 답변과 Chrome 권장 기준·실기기 미확인을 반영했다. PC 추론과 읽기 전용 패드의 역할·원격 F8 불필요를 유지하고 이번 문서 전용 작업을 이전 실측/배포와 구분했다. 관리13개 문서 검사와 별도 전수 감사가 통과했다.

## 2026-10-27 후속 개발: PC ML·A/B 원격 선택·표시 패드

- 사용자 개발 승인으로 패드4대 운영의 기본 입력을 remote 모드로 구현했다. PC는 세 모델을 한 번 로드하고 A/B 작업 스레드와 공유 GPU 잠금으로 추론한다. 인간 패드는 방 생성/시작/답안, 봇 패드는 읽기 전용 표시, PC는 별도 engine 권한으로 선택/제출한다. 기존 OS 경로와 F8 보정은 legacy로 보존했다.
- 서버는 lane 일치·engine/viewer 토큰 분리·3초 heartbeat/15초 유효·서버1000ms 선택 간격·순서 멱등 ACK·선택/제출 snapshot CAS를 추가했다. 새 `arena_remote_rooms` 테이블의0001 migration만 생성했고 기존0000/데이터/사진은 보존했다. 종료·방 혼선·viewer 쓰기를 거부하고 정답·실제 정답 수·원본 정보는 공개하지 않는다.
- PC는 공통 시작 후 공개9사진을 안전한 같은 호스트 경로에서 RGB로 받아 모델에 이미지 픽셀만 전달한다. 조건은 결정적 선택 로직에만 쓰며 URL/ID/파일명/라벨로 판정하지 않는다. 고정 모델 예측1회/제출1회,0개도 그대로 제출하며 자동 재추론·임의 오답·상위k강제선택은 없다. 입력 어댑터는 이번 사용자 승인 범위로 바꿨고 모델·임계값·학교 정책은 변경하지 않았다.
- 새 `Start-Alpha-Remote.cmd`·PowerShell/CLI는 모델 로드 후 숨긴 `A CODE8`/`B CODE8` 입력으로 지속 운영한다. 활성 구역 덮어쓰기를 막고, 종료한 구역은 새 참가자 코드로 바꿀 수 있다. 기존 파일은 덮어쓰지 않고 보고서에 코드/토큰/원본 이름을 기록하지 않는다.
- Python131개12.237초,서버Node30개0.790초,TypeScript·대상UI ESLint·compileall·pip check·Python/PS 구문검사 통과다. 실제 localhost remote HTTP1개19.126717초와 기존 HTTP1개3.088683초를 통과했다. 오류 재현을 고친 뒤 필요한 검사만 재실행했다.
- 실제 CUDA 두 방 검사 `runs/remote-booth-local-v2/verification.json`은 passed=true다. 모델 로드6.453초,startAt 차이26ms,A 건물 선택[0,2,3]·ACK뒤다음전송1.094/1.110초,B 나무0개를 확인했다. 두 답안은 오답으로90초 timeout이며 모델 선택과 HTTP 표시 상태는 일치했다. GPU 대기/추론을 별도로 기록했고 정확도/40%/학교 성능으로 해석하지 않는다. 첫 검증 도구의 방 생성 요청 거부는 참가자 QA와 풀이기 transport를 분리해 수정했으며 풀이기 권한을 넓히지 않았다.
- 별도 실제 CLI/IAB에서 사람 문제의 모델 선택[7,8]이 체크 두 개로 표시되고9사진 로딩·모든 봇 타일 disabled·오답/종료를 확인했다.1024×768에서 인간 제출 bottom735/봇 상태743,768×1024 봇 상태999,1280×800 봇 상태775로 화면 내 배치를 확인했다. 넓고 낮은 초기 넘침을 수정했다. 증거는 `runs/remote-browser-qa/`와 `runs/remote-booth-browser-v1/`이며 물리 패드4대·Wi-Fi 검증이 아니다.
- 사이트버전6의 production build·push/package/save/publish는 succeeded다. source `fb1a661b3258c2cd0e8839bbbd23347201a6b877`, saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_cd2e38219d908191ae59bc2536bfe449`, deployment `appgdep_6adfe389628481919f008ac502f7491b`, 환경revision3이다. 기존 공개 범위·두 도메인·D1/R2·키를 유지하고 빌드에 모델/사진/정답은행을 넣지 않았다. 게시 후 검증의 최종 결과는 STATUS에 기록한다.

- 게시 후 human/bot HTTPS200·원격 안내를 확인하고 IAB에 공개 A 인간 화면을 열었다. 공개 호스트에서도 실제 PC CUDA 두 방을 실행해 `runs/remote-booth-public-v1/verification.json` passed=true다. A 사람3명이상[3,6]은12.809초 정답 종료,B 나무0개는8.679초 오답 제출 후90초 timeout까지 독립 진행됐다. 모델 로드7.516초,startAt 차이50ms,두 선택 사이 ACK후다음전송1.375초였다. 두 HTTP 표시 클라이언트와 모델 선택이 같았으며 물리 패드0·정답/관리자 접근0·학교/튜닝0이다. 이는 두 문제 연결 검사로 성공률50%나40% 달성을 뜻하지 않는다.
- 관리 Markdown13개 본문을 전부 다시 읽고 갱신했다. `check_docs.py --date 2026-10-27`은13개 통과했고 data/models/runs/logs까지 포함한 전수 목록도13개로 일치했다. UTF-8·로컬 링크·최신 CHANGELOG 전체 목록·설정 JSON8개 구문 검사도 통과했다. 당시 검증용 엔진/로컬 미리보기는 종료하고 공개 사이트는 유지했다. 이후 사용자의 실행 요청으로 켠 운영용 엔진은 위 최신 가동 기록을 따른다.

남은 작업은 실제 패드4대의 브라우저/네트워크 동시 리허설, 운영자 UI 확인과 충분한 독립 자료·모델40%·ONNX·Pi·고정 후 학교 최종 평가다. 이번 원격 선택/표시 검증을 물리 터치나 기존 OS 클릭 성공으로 보고하지 않는다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 개발 승인 후 원격 A/B 입력·PC 모델·읽기 전용 표시·서버 생존/선택/CAS와 실행기를 구현하고 실제 CUDA·HTTP·브라우저 결과를 확인했다. 관리13개 본문을 직접 다시 읽고 새 경로와 legacy·미검증 경계를 갱신했다. 학교·가중치·임계값·목표40%·Pi/ONNX 상태는 유지한다.

## 2026-10-27 이전 상담: 패드4대 A/B 부스 운영 가능성 검토

- 사용자가 내일(클라이언트 날짜 기준10/28) 패드4대를 인간A·봇A·인간B·봇B로 운영하는 방안을 제안해 현재 소스와 대조했다. 각 참가자가 독립 방에서 AI와 대결하고 PC가 ML을 맡는 구성을 제안했다. 입력 어댑터 변경과 세부 운영은 아직 확정하지 않았다.
- 현재 selected는 React 탭 로컬이고 제출 전 선택 이벤트는 서버에 없다. 공개 상태도 선택 집합을 반환하지 않아 별도 봇 패드의 실시간 선택 표시는 미구현이다. 방당 최초 bot 참가만 허용해 엔진·표시 패드의 독립 연결 설계가 필요하다.
- OS 전면창·스크린샷·전역 클릭 경로 때문에 같은 PC에서 현재 runner 두 개를 켜면 커서/전면창을 공유한다. PC 모델 공유와 경기별 독립 입력·표시 동기화가 필요하며 두 경기 GPU/네트워크 성능은 미측정이다. 구현 후 한 쌍→패드4대의 동시 경기·중단/재연결을 검증하는 순서를 제안했다.
- 변경은 관리 Markdown13개 상담·검토 기록뿐이다. 기능 코드·데이터·모델·학교·임계값·설정·배포를 변경하거나 새 GUI/추론/실클릭을 실행하지 않았다. 기존118개 테스트와 게시버전5는 이전 검증 이력이다.
- `scripts/check_docs.py --date 2026-10-27`은 관리13개 모두 통과했다. data/models/runs/logs를 포함한 별도 전수 목록도13개로 일치하며 UTF-8·로컬 링크·최신 CHANGELOG 전체 목록·설정 JSON8개 점검도 통과했다. 본문은 각 담당 에이전트가 전체 재검토했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 패드4대 A/B 운영의 구성과 현재 선택 동기화·중복 참가·PC 커서 제약을 코드로 확인했다. 가능성 제안과 미구현/미측정을 구분하고 관리13개를 재검토했다. 이번에는 문서만 변경했으며 실제 입력·성능·배포 완료를 새로 주장하지 않는다.

## 2026-10-27 완료 정리: AI 클릭불가 진단·로컬 실행기와 수동보정

- 사용자제보를조사해 run_booth_bot프로세스0·configs/*.local.json0을확인했다. 웹ready는로컬엔진heartbeat가아니며인간화면의기존대결은이미인간승리56.92초였다. 새방/실행경로가필요하고이를모델정확도나AI속도로설명하지않았다.
- Start-Alpha-Bot.cmd와scripts/start_booth_bot.ps1/.cmd를추가했다. 최초에는사용자가F8로물리좌표5점을측정하고새인간방코드를입력한다. CUDA3모델→직접봇참가→브라우저→보정전면창/화면범위확인후 --ready를전송한다. 미보정실행은모델/GUI초기화전에차단하고모델/409/창실패는한국어단계별안내+비밀값없는보고서로정리한다.
- calibrate_booth_bot.py는사용자F8의위치/키상태조회만하고캡처/클릭/키주입을하지않는다. 주모니터/F11/OS·Chrome100%·제출보임·정적질문ROI조건을명시하고Esc/실패시기존보존·명시교체시백업한다. 실제측정전 calibrated=true파일을임의작성하지않았다.
- 웹arena의수동ready를 '봇화면준비/진행중'으로표현하고PC실행필요안내를추가했다. 격자/질문/제출배치·채점·timer/API/schema·사진/학습/모델/threshold는변경하지않았다. 자동ready도지속heartbeat나실제클릭성공보증이아니다.
- Chrome확장DOM측정에서1920×855/DPR1·격자(660,268,600,600)·제출중심(1185,905.5)을확인했다. 제출은현재viewport밖이므로임의로물리좌표에대입하지않았다. 이어네이티브Chrome주소검증실패로ComputerUse가중단됐으며그뒤모든UI/OS입력과PyAutoGUI우회를하지않았다. 새모델추론/실보정/실클릭/제출0이다.
- startup7+수동보정6합성테스트추가후전체Python118개22.359초통과,compileall/pipcheck·CLI help통과. WindowsPowerShell5.1 Parser구문검사만통과했고한글PS1을UTF-8BOM으로저장했다. 웹TypeScript도통과했다. 실제프로그램을켜둔상태나실제1초간격성공은주장하지않는다.

사이트버전4에서 TypeScript·production build·push/package/save/publish를 통과했다. 10/27 검토일을 웹 README에 반영한 최종 소스 commit `14c0859f81e1e5dd8d2a8de1645cd4a1572e42b1`은 같은 런타임 산출물을 재포장해 버전5로 게시했다. saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_1803ff5ca7d48191a17995f70b72e28c`, deployment `appgdep_6adf6c79cd8c819187567cbc7458539f`는 succeeded/환경revision3이다. 기존 도메인·공개 범위·D1/R2·비밀값을 유지했다. 최종 두 호스트의 HTTPS200 및 HTML 로컬 프로그램 안내를 읽기 전용으로 확인했고 브라우저/ML/OS 입력은 실행하지 않았다. 게시 기록 (로컬 산출물: `runs/booth-click-diagnosis/release.json`), HTTP 검사 (로컬 산출물: `runs/booth-click-diagnosis/release-http.json`).

관리 Markdown13개를 전체 재검토·갱신했다. `check_docs.py --date 2026-10-27`은13개 통과했고, data/models/runs/logs를 포함한 전수 목록13개·UTF-8·로컬 링크·최신 CHANGELOG 전체 목록·설정 JSON8개 구문 검사도 통과했다. 실제 자동 입력은 도구 중단과 사용자 물리 보정이 남아 미완료다. 다음은 사용자 보정 후 새 방에서 실제 캡처·ML·최소1초 타일 간격·제출/종료 확인이며, 학교0·공개24장·Kaggle/v1 보존·40%/ONNX/Pi 미완료를 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 2026-10-27에 AI가 클릭하지 않는 로컬 실행 부재와 웹 ready의 의미를 재검토했다. 실행기·사용자 F8 보정·시작 검사·오류 안내·웹 문구 변경을 반영했다. 합성 검사와 실제 입력 미검증을 구분하며 Chrome URL 확인 실패 후 우회하지 않았다. 13개 문서의 검토일·본문과 새 실행 절차를 다시 확인했다. 아래는 이전 사진 적용 이력이다.

## 2026-10-26 이전 후속: 공개 웹사진24장 운영 적용·브라우저 확인

### 실제 변경과 검증

- 사용자가 웹에서 임의 사진을 내려받아 두 사이트에서 시험하도록 요청했다. 기존 로컬Kaggle34장 대신 Commons의 별도 공개사진24장·6,063,549bytes·24원본그룹을 준비해 운영 D1/R2에24/24 등록했다. CC0 11장·Public domain13장, 학교0·새학습/튜닝0이다.
- `prepare_public_booth_bank.py`로44후보를 확보하고 RGB·원문사진권리/revision/template을 검토했다. 그림·중복Apollo11·연속촬영 후보와 건축물만PD/사진CC-BY-SA인 혼합사례는 제외했다. 전체프레임JPEG로재인코딩해EXIF/GPS/comment제거, 불명확인원/정확나무수는null·명확한>=3만기록했다. 독립 사람검수·모든권리의법률보증·모든촬영계보자동검증을 주장하지 않는다.
- `import_public_booth_bank.py`는 공개승인·비학교CC0/PD·SHA/Pillow/경계/라벨검증, dry-run기본·실행시stdin키·redirect금지·동일SHA409만중복건너뛰기를 구현했다. 은행의관계그룹은보존하고동일그룹다른사진을전체은행에서금지하지않는다. 기존privateKaggle importer 공개금지는유지했다.
- dry-run24장통과후 운영등록 (로컬 산출물: `runs/site-publish/public-bank-upload.json`) verified24/uploaded24/alreadyPresent0/completedtrue확인. 비밀키/역할토큰은파일/인자/로그에쓰지않았다. 기존ADMIN_KEY만동등갱신한환경revision3을기존사이트v2에재적용한배포 appgdep_6adf5a88c27c8191b17bb2f16bc4c575는succeeded. 사진·정답은행은웹소스/빌드자산에포함하지않았다.
- 서버준비성P/N/U는사람8/11/5·나무9/11/4·건물8/9/7·연못7/17/0, 네유형ready다. 서버실검사 (로컬 산출물: `runs/site-publish/public-photo-rounds-verification.json`)는격리방7개에서4유형각9사진HTTP/실디코드/SHA·그룹9·정답개수범위·양호스트동일startAt/tiles·답안필드비공개를통과했다. 평가기만라벨을읽었고정답제출/모델/마우스0이다.
- 이번Chrome확장정상연결로별도QA방생성/시작후9사진loadedtrue/자연크기>0과타이머를직접확인했다. 브라우저검사 (로컬 산출물: `runs/site-publish/public-photo-browser-verification.json`), 전체스크린샷 (로컬 산출물: `runs/site-publish/public-photo-browser-full.png`)을저장했다. 답안선택/제출·ML봇실행은0이며기존사용자방은시작하지않고이전자료부족알림만닫았다. 이전URL확인실패는이전작업이력으로구분한다.
- 공개importer경계테스트6개추가, 전체Python105개12.020초통과·compileall통과·pipcheck충돌없음. 모델학습/새GPU평가/정확도측정은수행하지않았다. 기존v1/test/나무모델임계값·학교정책·40%미달성·ONNX/Pi/ML실OS미검증을유지했다.

### 전체 문서와 남은 일

관리Markdown13개를모두읽고현재본문을갱신했다. 데이터와전달라이선스·등록·브라우저렌더와ML실제입력검증을구분하고, 빈은행/Chrome중단은역사로보존했다. `check_docs.py --date 2026-10-26`은13개통과했고 data/models/runs/logs까지포함한전수목록도13개·로컬링크/UTF-8/최신CHANGELOG전체목록/설정JSON8개구문검사모두통과했다. 소유자로그인/수동업로드UI·실제ML캡처/클릭/제출·모델40%·ONNX·Pi·학교최종평가는남았다. 사용자는현재공개사진으로출제를시험할수있다.

최종문서소스동기화 사이트버전3도production build·push/package/save/publish통과했다. source `f4898b7f0f046bd8a4b45eca22bed1d2c62d8461`, saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_edbeb4b24f5081918f58c6e2831a1f0d`, deployment `appgdep_6adf5dd1e40c8191a061386f6a722977` succeeded/환경revision3이다. 변경은웹README만이며런타임/출제규칙은변경하지않았다. 사진/정답은행/모델/키는빌드에없고R2/D1데이터는유지한다. 검증용브라우저탭은닫고원래사용자대기실을유지했다.

배포후 두호스트HTTPS200·관리자status200/사진24/4종ready를 다시확인했다. 공개자료/R2·D1가유지되며 `runs/site-publish/public-photo-release.json`에비밀값없이기록했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 공개웹사진24장과원문권리/RGB/그룹·운영등록24/24·서버4유형사진검사·Chrome9사진표시를확인했다. 학교/학습/튜닝0·모델성능미변경·정답파일풀이금지·ML실OS미검증을유지하고관리13개를모두갱신했다. 아래는공개사진등록전의이전게시작업이력이다.

## 2026-10-26 이전 작업: 인간·봇 사이트·사진 등록·실제 ML 연결

### 최신 사용자 요구와 구현

- 사용자 요청으로 기존 웹사이트 제외 범위를 대체하고 human.marulee.dev·bot.marulee.dev 두 화면과 관리자 사진 등록을 구현했다. 하나의 Sites/Cloudflare Worker·D1·R2를 공유한다. 새 출제는 사람3명이상(정답2~4), 나무3그루이상(3~4), 위임으로 선정한 건물/연못(각2~4)의4종이다.
- 한 참가자 한 판·첫 완벽정답 즉시 승리/종료를 반영했다. 오답은 수정·재제출하고 타이머가 계속 흐른다. 공통 미래 startAt과 종료 finishedAt/elapsedMs, D1 트랜잭션의 단일 승자, 사용한 방 재시작 거부·새 참가자 새 방/봇 연결을 구현했다. 90초 시간초과와 첫클릭0초/제출간격제외는 운영 가안이다.
- 공개 state에 정답·실제 정답수·원본 신원·라벨을 넣지 않고 불투명 사진ID만 제공한다. 사진은 시작·대기실만료·현재라운드·활성여부를 검사한다. 관리자 공식 Sites 소유자 로그인/환경 키를 분리했으며 비밀값은 소스·인자·로그·파일에 저장하지 않았다. 소유자 브라우저 로그인은 미검증이다.
- 사진 업로드·정확수/나무>=3/unknown·원본 그룹·출처·유형별 준비성 검사를 구현했다. 학교0장, 로컬 Kaggle 데모34장(2,921,524bytes)은 실제 D1/R2에34/34 업로드했으나 공개 재배포 권한을 일괄 확인하지 않아 운영에 올리지 않았다. 공개 문제은행은 비어 있어 시작409 bank_not_ready가 정상이다.
- 화면 픽셀 봇·CLI·모의화면/공개조건 테스트를 추가했다. 최소1초 타일 간격·질문/전면창/round 검사·상대승리 취소·한판만 허용·동일문제 재실행 차단을 구현했다. 현재 고정예측으로 한 번 제출하며 오답 자동재추론/재시도는 없다. 제출API로 실제입력을 대신하지 않는다.

### 실제 모델과 검증

- YOLO는 사용하지 않았다. 기존 MobileNetV3 Small 존재·SSDLite320 MobileNetV3 Large 사람 v1은 보존했다. 나무>=3은 별도 Grounding DINO Tiny 공식 사전학습 후보를 연결했으며 프로젝트 추가학습은 없다. 고정revision a2bb814dd30d776dcf7e30523b00659f4f141c71, 가중치689,359,096bytes/SHA1a2412ef99bd74bcd3c2a246fa1e48581f8889a1300c9051974741314fc042f3, prompt/score/NMS를 예측 전에 고정했다. transformers4.57.3/safetensors0.7.0을 .venv에 추가했고 CUDA torch/torchvision·전역환경은 유지했다.
- seed20261026으로 고정한 저장RGB4문제를 실제GPU에서 실행했다. 사람[5] vs 정답[0,5] 실패2.227191초, 나무[] vs [0,1,4,6] 실패3.066073초, 건물[4,5] 일치0.531181초, 연못[] vs [1,3,6,8] 실패0.521821초다. 모델로드8.904초. report는 runs/booth-model-smoke-v1/report.json이다. 사진 재사용의 각1문제 기능검사이며 정확도25%·목표40%·학교/부스성능으로 확대하지 않는다. 실패에 맞춰 v1/임계값을 다시 조절하지 않았다.
- 최종 전체 Python99개 통과11.136초(앞선98개 이후 HTTP 식별/토큰 범위1개 추가), Node 단위/SQLite/소유자인증18개 통과, TypeScript 통과, 대상UI ESLint 오류/경고0. 최신 로컬 HTTP D1/R2 통합1개 통과(본문3.270711초/runner8.976320초): 오답2회·정답동시경쟁·단일승자·공통종료·같은방재시작거부·비공개/권한/사진을 확인했다. 서버 채점용 비공개 정답 접근과 ML 풀이를 분리했다.
- Sites production build·push·archive·saved version2·공개 게시 succeeded. commit53040210b7570695eacbaa996a182e4ef19aee7d, saved version appgprj_6ade37995018819184a42c88bb0fde7c~appgver_0be4bc30f4588191af8c7976d4dcc8a8, deployment appgdep_6ade402240008191a656805b9ba2fcef. 배포압축에는 모델/사진/정답은행/키가 없고 빌드산출물·storage선언·스키마만 있다.
- Cloudflare 기존없는 이름에2CNAME(DNS only)·4검증TXT 생성, 두 도메인 native/provider/SSL 모두active. 기존 marulee 터널/다른DNS는 수정하지 않았다. 최초 공개 HTTPS/API8검사 통과:3주소200, human생성201→bot참가/준비200→human공유상태200→빈은행start409 bank_not_ready. 기본Python UA403과 명시UA200 차이를 보고서에 기록했으며 최종 사이트버전2에서도8개 모두 재통과했다. 이어 AlphaCaptchaBoothBot/1.0 식별 헤더를 추가한 실제 Python PublicRoomSession도 bot호스트 참가·상태조회를 통과했다. 요청 식별/토큰 범위 합성테스트를 추가했고 정답/준비/제출/관리/UI는 사용하지 않았다. 두 공개검사 JSON에는 토큰·방코드/ID를 저장하지 않았다.
- IAB 접근성 상태로 홈·인간대기실 생성을 확인했다. 네이티브Chrome 도구가 현재URL을 신뢰성 있게 검증하지 못해 이번 턴 화면제어를 중단했다. 다른 입력도구로 우회하지 않았다. 실제OS 캡처/클릭/제출0회·물리보정·실제1초간격·스크린샷QA는 미완료다.

### 한계·다음 작업·문서 점검

공개 사진 등록·소유자 UI확인, PC 실제 화면보정/ML/클릭/제출, 충분한 새 Kaggle 선택val/잠금audit·4종 성능, ONNX동등성, Pi의 사양/시리얼/추론/GUI 개별점검, 모델고정 후 학교최종평가가 남았다. 학교를 개발튜닝에 쓰지 않는다. 목표40%와 부스전체완료는 주장하지 않는다. 날짜26은 사용자 세션의 Asia/Pyongyang 기준이며 배포API UTC시각은25일일 수 있다.

관리 Markdown13개를 팀이 모두 읽고 실제본문을 갱신했다. 새 웹README를 docs색인에 추가했고 vendor 외부라이선스/생성프레임워크상태는 관리대상에서 제외했다. 최종 `scripts/check_docs.py --date 2026-10-26`은13개 모두통과했다. data/models/runs/logs까지 포함한 별도 전수목록도13개로일치하고 로컬링크·UTF-8·최신CHANGELOG 전체목록·설정JSON8개 구문도 통과했다. compileall·pip check 통과, 점검용 로컬미리보기는 종료했고 공개사이트는 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md
- web/alpha-arena/README.md

이전 작업 검토(11/02): 웹제작 승인·최신한판/첫정답규칙·4종과공개빈사진은행·실제GPU선택/실패·별도사전학습후보·새사이트버전과DNS를 검토했다. 저장RGB/API/모의입력과실제OS입력0회를 구분하고 목표40%/ONNX/Pi/학교미완료·v1보존·모든Markdown갱신의무를 유지했다. 아래는 당시사실을 보존한 이전작업 이력이다.

## 2026-10-22 유형별 40% 목표 확정·격자 평가 준비

### 사용자 확정과 실제 변경

- 사용자는 정답4칸인 3×3 문제에서 약40% 성공을 원했고 후속 답변으로 **유형마다 각각 약40%**를 확정했다. 사람 존재와 n=2/3/4/5 이상을 따로 보고해 나무·건물·연못과 합계8조건을 점검한다. 목표는 4정답·5오답의 선택 집합 완전 일치율이다. 부스의 모든 문항을 4정답으로 고정한 것은 아니며 수치 허용오차는 미정이다.
- `configs/calibration-target-v2.json`에 조건·목표0.4·선택seed20261022·v1 test/학교 격리·미달성 상태를 기록했다. 목표 설정 파일이 40% 달성 체크포인트를 뜻하지 않는다.
- `src/alpha_captcha/grid_evaluation.py`, `scripts/evaluate_grids.py`에 val 예측 캐시 정규화와 4P5N 격자 계획/집합 채점을 구현했다. manifest/원본/이미지/체크포인트 해시와 행 신원·분할·관계 그룹을 검사하며 같은 격자에 원본/크롭 계보를 중복 배치하지 않는다. 정답은 구성/채점에만 쓰고 `select_tiles`에는 모델 예측과 공개 조건만 전달한다.
- 모의 재사용 격자는 재사용 사진·그룹과 서로 다른 조합 수를 따로 보고한다. 소수 격자나 재사용100회로 독립100표본 신뢰구간·40% 달성을 주장하지 않는다. 캐시 해시는 일관성 검사이며 서명 없는 캐시의 ML 출처를 독립적으로 보증하지 않는다.
- 두 학습 CLI는 test 평가를 기본 제외하고 `--evaluate-test`로 명시할 때만 평가하도록 변경했다. API 직접 호출은 v1 호환 기본값True를 유지하므로 후보 선택은 반드시 `evaluate_test=False`다. 프로필/report/checkpoint에 평가 여부를 기록한다. 실제 v2 후보 반복 전에 test 자동 평가로 잠금 자료를 노출하는 경로를 분리했다.

### 실제 실행과 검증 결과

- 기존 v1의 val 예측을 `val-presence-cache.json`, `val-person-cache.json`으로 정규화하고 8조건별100개 무재사용 격자를 요청했다. seed20261022에서 건물만1개 가능했고 기존 예측으로 0/1이었다. 나머지7조건은0개다. **8조건 모두 `insufficient_data`, `target_achieved=null`**이며 새 ML 추론은 없다. 결과는 `runs/calibration-v2/validation-grid-summary.json`과 `evaluation/*.json`이다.
- `runs/calibration-v2/data-readiness.json`에 현재 train/val/test의 P/N/unknown·그룹·무재사용 가능 격자를 기록했다. 사람 존재는 이진 정답이 알려진 evaluator 기준val P2/N2, 검출 적격 캐시 기준P1/N2라 한 예측이 부족하다. 정확 인원수 모호값을 음성/0명으로 만들지 않았다.
- 현재 자료는 유형별 약40%를 선택/확인하기에 부족하다. 별도v2는 기존134개 전체 원본/해시/관계그룹을 제외한 새 Kaggle 자료로 준비하는 계획을 기록했다. 조건별각pool 20P25N이면5개 격자부터 가능하지만 실제40% 성능의 충분한 통계적 근거가 된다는 뜻은 아니다.
- 격자 평가 합성 테스트10개, 두 학습기의 test 미평가/잘못된 bool 거부 테스트4개를 추가했다. **전체 unittest 82개 통과(8.165초)**, `compileall`·두 학습 CLI help 확인 통과. 실제 모델 v1 체크포인트·기존 데이터/라벨·패키지/OS는 변경하지 않았다.
- 새 데이터 다운로드·실제 v2 학습·새 GPU 추론·학교 사진 열람·ONNX/Pi/화면 입력은 수행하지 않았다. 이전 68개 테스트와 실제 GPU 학습은 아래 이전 작업 이력이다.
- 관리 Markdown12개 전체 본문·실제 코드/보고서를 읽고 갱신했다. 최종 문서 점검 결과를 여기에 기록한다.

### 한계와 다음 작업

목표40%가 확인됐으며 달성 모델은 아직 없다. 새 그룹 자료/주석 보강, train·선택val·잠금audit 분리, 예측 전 격자 동결과 유한한 학습 예산 후보 확정, val 후보 선택, 모델 해시 고정 후 미사용 audit 평가가 남아 있다. 현 격자 CLI는 val 전용이며 잠금 audit 실행 경로는 후속이다. v1의 공개test나 학교 결과를 보고 학습량·임계값을 맞추지 않는다. 속도 규칙은 실제 연속 타일 클릭 최소1초로 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (12개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

아래는 이전 작업 기록이다. 가정상 성공률과 목표40% 확정 전의 미정 표기를 현재 달성값·최신 목표로 취급하지 않는다.

## 2026-10-22 부분 정답 타일 구성의 성공률 가정 분석

### 수행 작업과 확인 결과

- 사용자가 9칸 중 일부만 정답일 것으로 예상하여 정답 2/3/4칸의 참고 계산을 요청했다. 이 숫자는 분석 가정이며 실제 문제별 정답 개수나 출제 배정의 확정이 아니다.
- 기존 두 `*-limited-v1/report.json`을 읽고 test의 양성 검출률(TPR)·음성 제외율(TNR)을 대조했다. 전체 선택 집합 일치에는 정답 k칸을 모두 선택하고 오답 9-k칸도 모두 제외해야 한다. 조건부 독립·동일 성능 가정에서 `TPR^k × TNR^(9-k)`를 계산하고 별도 수학 검토와 대조했다.
- k=2/3/4 순서의 대입값은 건물 49.0/34.3/24.0%, 사람 있음 86.2/80.1/74.3%, 2명 이상 81.0/72.9/65.6%, 3명 이상 44.4/29.6/19.8%다. 나무·연못·4/5명 이상은 관측 비율을 대입하면 모두 0%다. 미래의 보장값이나 실제 3×3 측정값이 아니다.
- 인원 조건별 test 혼동행렬을 기존 `actual_count`·`person_count`로 재집계했다. TP/FN/TN/FP는 n=2에서 9/1/8/0, n=3에서 4/2/12/0, n=4에서 0/4/14/0, n=5에서 0/2/16/0이다. 높은 전체 accuracy만으로 4/5명 양성 판별 능력을 설명하면 안 됨을 STATUS에 보완했다.
- 작은 음성 표본에서 오탐 0건인 TNR=100%는 새 사진의 보장값이 아니다. 관측치 0/100%, 오류 상관, Kaggle→학교 분포 차이와 미확정 출제 비율 때문에 부스 전체 평균 성공률을 확정하지 않는다. 기존 시험 사진을 복원 없이 9장 재조합해 측정한 성공률도 아니다.
- AGENTS·README·STATUS와 문서별 검토 기록을 갱신했다. 데이터·split·라벨·모델 가중치·코드·설정·패키지·OS 변경, 새 학습/추론·학교 열람·화면 입력은 없다. 이전 68개 소스 테스트를 이번에 재실행했다고 보고하지 않는다.
- 관리 Markdown 전체 12개를 읽고 갱신했다. `scripts/check_docs.py --date 2026-10-22`는 **12개 통과**했다. data/models/runs/logs를 포함한 별도 전체 목록도 12개로 일치하며 로컬 링크·UTF-8·최신 CHANGELOG의 전체 문서 목록 점검을 통과했다. STATUS의 건물 계산 재현 명령은 실제 49.0/34.3/24.0%를 출력했다.

### 한계와 다음 작업

이번 결과는 이전 시험 보고서로 계산한 가정상 참고값이다. 실제 부스 문제의 성공률과 학교 사진 성능은 미측정이다. 다음 실제 평가는 고정 모델로 별도 3×3 문제의 정답 타일 집합과 예측 집합을 비교해야 한다. 정답 개수를 모델에 전달하거나 상위 k개를 강제 선택하지 않는다. 기존 ONNX·PC/Pi 추론·GUI 입력·최소 1초 실클릭 검증은 남아 있으며 v1 test 재튜닝 금지와 학교 최종 평가 전용 정책은 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (12개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

아래는 이전 작업 이력이다. 실제 GPU 학습과 68개 테스트는 해당 ML 작업 당시의 실행 기록이다.

## 2026-10-22 실제 제한 학습 v1·평가·저장 격자 ML 추론

### 승인과 실제 변경

- 사용자의 “이제 머신러닝 들어가자” 요청에 따라 실제 학습을 진행했다. 학교 사진과 참가자 웹사이트는 사용하거나 만들지 않았다.
- Kaggle 사진을 모델 예측 전에 고정 기준으로 시각 검토했다. 단일 AI 검토이며 독립 사람 검수를 완료했다고 주장하지 않는다. COCO 군중 8·모호 18장은 제외하고 38장을 검출 적격으로 선정했다. 장난감 인물 4→0, 발 중복 상자 3→실물 2명 오류를 원본 보존 후 교정했다.
- 존재 후보 56장에 대해 나무·건물·연못의 명시적 양성/음성/모호값을 기록했다. 기존 val/test에 연못 양성이 없음을 첫 fitting/모델 예측 전에 확인하고 Places365 14장을 추가 확보·검토해 7 val/7 test로 배정했다. 기존 split 이동은 없다.
- 현재 사진 134장·134 연결 그룹, 통합 원 split은 train 68/val 19/test 47이다. 존재 모델은 70장(41/14/15), 사람 검출은 적격 38장(17/3/18)을 사용한다. 원본 확보 합계 502,563,677 bytes는 메타데이터·모델을 제외한다. 실제 사진 해시·픽셀·출처·학교 차단·관련 그룹 분할 검사를 통과했다. 완전한 촬영 계보 보증이나 자동 유사도 검색 완료를 뜻하지 않는다.
- `presence_model.py`, `train_presence.py`: MobileNetV3 Small ImageNet V1의 features/BN 고정·classifier 학습, 전체 RGB letterbox 224·독립 sigmoid 3출력·unknown 마스킹을 구현했다.
- `person_model.py`, `train_person.py`: COCO V1 SSDLite320 MobileNetV3 Large의 backbone/BN 고정·head 학습, 전체 RGB letterbox 320·person ID 1 검출·원좌표 복원·계수를 구현했다. verified/완전 box/검토 적격 자료만 사용한다.
- 첫 학습 전에 고정한 제한은 두 모델 각각 1 epoch, seed 42다. 존재는 최대 64장·batch 8·lr 0.001·threshold 0.5, 사람은 최대 32장·batch 2·lr 0.0001·score 0.5·NMS IoU 0.45다. 실제 train은 41장/17장, optimizer step 6/9다. 마지막 epoch를 사용하고 조기 종료·임계값 검색은 하지 않았다.
- `inference.py`, `predict_saved_grid.py`: 재로딩한 두 모델에 저장 3×3의 RGB 타일만 전달해 조건 선택·좌표·예정 상대 시각을 출력한다. 파일명/정답 manifest/사이트 내부 데이터를 읽어 답을 구하지 않는다. 예시 학습/클래스 설정을 실제 v1 프로필·출력 순서로 정정했다.

### 실제 GPU 결과와 검증

- RTX 4070 Laptop GPU에서 두 모델을 실제 학습·평가했다. fit 구간은 존재 0.616초·사람 1.371초이며 import/가중치 다운로드 등을 포함한 총시간이 아니다. PyTorch peak allocated 46.69/58.63 MiB는 전체 필요 VRAM이 아니다.
- 체크포인트와 보고서: `models/checkpoints/presence-limited-v1/`, `models/checkpoints/person-limited-v1/`. features/backbone 및 BN 상태 해시 불변, 실제 손실/gradient 유한성, 모델 재로딩을 확인했다. 사람 마지막 단독 음성 batch loss=0은 표준 SSD negative mining의 한계로 기록했다.
- 존재 체크포인트 SHA-256: `beba9696ed7ea8cbfdb2f8b64f48c988661413c3956caf29d2a4f120f060a9a4`. 사람 체크포인트: `c48d5287fa234bbd2dbeae39dc0d01f03a2f178f007a58aca579d03017fc8cbf`. 저장 보고서와 실제 파일 해시가 일치한다.
- 고정 후 test에서 정확 인원 수 13/18=72.2%, MAE 0.556명, 사람 존재 17/18. n>=2/3/4/5 정확도는 17/18·16/18·14/18·16/18이다. 같은 18장에 대한 서로 다른 조건이며 n별 양성 분모가 다르다.
- 나무는 알려진 14장 전부 양성으로 예측해 정확도 50%, 건물은 15장 정확도 80%(양성 3장 누락), 연못은 양성 1장까지 놓쳐 recall 0/1·F1 0이다. 연못 90.9% accuracy는 음성 편중에 따른 값이며 성공한 연못 모델로 보고하지 않는다. 대상별 precision/recall/F1·분모는 STATUS와 원본 report에 기록했다.
- 저장 예시 격자 한 장의 실제 GPU 9타일 추론 0.560초, n>=2에서 타일 8·예시 좌표(600,600)·예정 0초 출력. 기존 test 사진 조합을 사용한 연결 검증이며 새 독립 정확도·p50/p95·Pi 성능이 아니다. 캡처·마우스·대기·제출은 수행하지 않았다.
- 전체 자동 테스트 **68개 통과**, `compileall` 통과, `pip check` 의존성 충돌 없음. 새 패키지 설치·전역 Python·GPU 드라이버·OS 변경은 없다.
- 관리 Markdown 12개의 본문을 읽고 갱신했다. `scripts/check_docs.py --date 2026-10-22`는 **12개 통과**했다. 검사기 제외 폴더인 data/models/runs/logs까지 포함한 별도 전체 목록도 12개로 일치했다. 로컬 링크·UTF-8·최신 CHANGELOG의 전체 문서 목록·JSON 설정 구문 점검도 통과했다. 본문 정확성은 모델/manifest/소스와 직접 대조했다.

### 한계와 다음 작업

v1은 실제 실패를 확인한 첫 기준 모델이며 부스 사용 가능 상태가 아니다. 연못 train 2/val 1/test 1 양성과 사람 val 3장은 특히 작다. ImageNet/COCO 사전학습 모델이므로 처음부터 소량만 학습한 AI라고 설명하지 않으며 COCO train과 사전학습 자료의 겹침도 기록했다. 학교 성능·부스 문제 전체 타일 집합 일치율·경기 승률은 미측정이다.

현재 test 결과에 맞춰 v1을 다시 튜닝하지 않는다. 후속 개선은 별도 버전·val 기준·미사용 시험 계획을 먼저 마련한다. 다음 배포 단계는 ONNX 내보내기·PyTorch 출력/선택 비교다. Pi 실기기 추론과 GUI 입력은 별개로 점검하고, 화면 캡처/보정·OS 클릭·실제 최소 1초 간격·사이트 제출/결과 연동은 아직 남아 있다. 학교 자료는 모델 고정 후 최종 평가 전용, 10/28은 임시 목표를 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (12개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

아래는 이전 작업의 이력이다. 당시의 데이터 수량·라벨 미검토·ML 미구현 표기는 현재 상태가 아니다.

## 2026-10-22 착수 승인·Kaggle 후보 확보·분할/판정/타이밍 구현

### 승인과 실제 변경

- 사용자가 수정 문서를 바탕으로 “이제 진행하자”라고 하여 구현·데이터 준비 착수를 승인했다. 이전 문서 전용/승인 대기 경계를 종료했다. 후속 답변으로 사람 수 질문의 n은 2~5명으로 확정했다.
- 기존 관리 Markdown 12개 전체와 소스·설정을 읽고 새 대상 존재/사람 계수 요구를 기준으로 구현했다. 패드용 웹사이트는 만들지 않았다.
- `dataset.py`: Kaggle 전용 JSONL 스키마·출처/허용 경로·학교 유입·symlink 탈출·SHA-256·실제 이미지 디코딩·bbox·군중 검증, 계보/동일 원본/해시 통합 그룹 분할과 통계 구현.
- `kaggle_data.py`: 공개 Kaggle의 작은 개별 파일 확보, 응답 형식/전체 HTTP 200/크기/완전 JSON·이미지 검사와 임시 파일 정리 구현. 자격증명을 읽거나 출력하지 않았다.
- `prepare_coco_subset.py`: 실제 COCO 64사진과 train/val 원본 주석을 확보. 인원 구간별 후보와 군중을 구분하고 미확인 box 수를 확정 인원 수로 쓰지 않았다.
- `prepare_presence_candidates.py`: 실제 ADE20K 32사진/32mask와 Places365 24사진, 클래스표 1개를 확보. 마스크 양성만 임시로 쓰고 미주석·연못 장면·인원 수는 자동 확정하지 않았다.
- `tasks.py`: tree/building/pond 점수와 사람 수를 받는 9칸 조건 판정·명시적 eq/gte·n=2~5·unknown 거부 구현. 실제 픽셀에서 점수/검출을 만드는 ML은 아직 없다.
- `timing.py`: 최소 1초 콜백 간격·문제 변경/취소·쿨다운 유지·실패 처리 구현. 실제 마우스 어댑터를 연결하지 않았고 테스트는 모의 시계와 콜백만 사용했다.
- CLI의 `data-check`, `data-split` 및 dry-run 예정 상대 시각을 추가했다. PC/Pi 설정의 1초 규칙·첫 클릭 0초 가안·제출 미정을 명시했다. 학습 설정은 새 과제 후보와 미확정 제한값을 구분했다.
- `review_labels.py`의 빈 CSV 출력/명시적 0·1·인원 수 적용, 신원/해시/경로 대조·원본/annotation_boxes 보존을 구현했다. 원본 JSONL과 사진을 덮어쓰지 않고 새 검토본을 쓰도록 했다.

### 실제 데이터와 검증

- COCO 64장: train 27 / val 5 / test 32. 원본 annotations 489,773,314 bytes, 사진 10,560,523 bytes.
- ADE/Places 56장: train 41 / val 7 / test 8. 사진 56·mask 32·class표 1의 선택 원본 89파일·2,024,475 bytes.
- 합계 **사진 120장·120 연결 그룹**, **train 68 / val 12 / test 40**. 선택 원본 합계 502,358,312 bytes이며 메타데이터/보고서는 제외한 값이다. 대형 원본 전체를 받지 않았다.
- 실제 모든 사진의 해시·픽셀·스키마와 통합 분할 검증 통과. 중복 해시 그룹 0, 관련 그룹/해시의 분할 교차 0. 유사 장면·촬영 묶음을 전부 알아냈다는 의미는 아니다.
- 마스크 임시 양성은 tree 23·building 15. 연못 정답 확정 0, exact person count 검증 0(unknown 112·crowd 8), 존재 음성도 미확정이다. 이 상태를 완성된 학습 세트로 보고하지 않는다.
- `development-candidates-split.jsonl`, `development-validation-report.json`, 120행의 `development-label-review.csv`를 작성했다. 학교 사진은 읽거나 사용하지 않았다.
- COCO 8·ADE 8·Places 12의 축소 contact sheet를 점검해 장면 라벨·작은 배경 인물·물 유형의 경계 문제를 확인했다. 최종 라벨 변경은 0이며 `sample-visual-inspection.json`에 점검 범위·제약을 기록했다.
- `.venv\Scripts\python.exe -m unittest discover -s tests -v`: **52개 통과**. 학교 경로/심볼릭 링크·불완전 다운로드·군중/unknown·분할 누수·조건 경계·시계/취소/콜백·CLI/라벨 검토를 검증했다. `compileall`도 통과.
- PC/Pi 예시 dry-run을 Windows에서 실행해 좌표와 예정 0/1/2초 확인. `pip check` 통과. 실클릭·실제 경과시간·Pi 성능 검증이 아니다. GPU 연산은 이번에 재실행하지 않았다.
- C: 여유 공간은 초반 조회 134.94 GiB. `Win32_SerialPort` 조회에 인식된 포트가 없었지만 Pi 연결 여부를 단정하지 않았다.
- 관리 Markdown 12개는 본문을 직접 검토·갱신했다. `check_docs.py --date 2026-10-22` **12개 통과**. 검사기 제외 폴더를 포함한 별도 전체 파일 목록도 12개로 일치하며 로컬 링크·최신 CHANGELOG의 전체 문서 목록·문자 인코딩 점검도 통과했다.

### 한계와 다음 작업

현재는 데이터 후보·검토 도구·초기 분할과 기반 코드 단계다. 공통 대상/계수 기준·명시적 음성·인원 수/연못 라벨·유사 장면 그룹 검토가 남아 미확인 정답으로 학습하지 않았다. 다음은 이 검토와 제한 학습 프로필 고정, 작은 기준 모델 학습이다. 학습·ML 추론·ONNX·OS 캡처/클릭·Pi 실기기·실제 정확도/속도는 미완료·미측정이다. 학교 자료는 계속 모델 고정 후 최종 평가 전용이다. 10/28은 임시 개발 목표다.

### 이번에 읽고 갱신한 전체 Markdown (12개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

아래는 이전 작업 기록이다. 당시 문서 전용·승인 대기·데이터 없음·n 미정은 현재 상태를 뜻하지 않는다.

## 2026-10-21 문제 범위·경기 제한·Pi 연결 계획 반영

### 사용자 요청과 후속 답변

- 사용자는 AI 정답률을 의도적으로 낮춰 인간과 경쟁시키고, 초당 한 번의 속도 제한을 적용한다고 정정했다. 후속 질문의 답변은 **학습량·모델 성능 제한**과 **타일 클릭을 1초에 한 번씩**이다.
- 대상은 나무·건물·연못·사람·사람이 n명 이상인 사진이다. 문제은행 5개 중 하나, 고정 3×3과 서로 다른 독립 사진 9개를 확정했다.
- 사용자가 Pi를 PC에 시리얼 통신 어댑터로 연결할 예정이라고 밝혔다. 연결 후 콘솔에서 기기 확인·설치·로그 수집을 진행하는 계획으로 갱신했다. 실제 접속과 GUI 입력은 아직 미검증이다.

### 변경 사항

- 단일 대표 장면 분류와 사람 판별 후순위 계획을 대상별 존재 판별·사람 검출/계수 계획으로 대체했다. COCO의 사람 인스턴스 주석을 우선 검토하고 나무·건물·연못에 맞는 Kaggle 자료를 추가 선정하도록 수정했다.
- 학습 표본·epoch·동결 범위·모델 용량으로 정답률을 조절하는 방향을 기록했다. 임의 예측 반전이나 정답 클릭 누락은 도입하지 않는다. 구체 제한 수치와 목표 정답률은 아직 미정이다.
- 실제 연속 타일 클릭 간격은 PC/Pi 모두 최소 1.0초로 명시했다. 추론 주기와 구분하고, 첫 클릭·제출 버튼 적용 여부는 미정으로 남겼다. 제한 대기와 실제 처리 시간은 따로 기록한다.
- 학교 사진의 학습·개발 검증·튜닝 금지는 유지했다. 모델·제한 프로필을 고정한 뒤 학교 문제를 평가하며, 학교/본선 결과에 맞춰 다시 조절하지 않는다.
- 5개 문항을 5유형에 하나씩 배치하는 안, 사진 고정/재추첨, n 범위, 일부 보이는 사람의 계수 기준, 승패·재시도·시간초과는 추가 확정 사항으로 분리했다.
- 같은 문제/사진 배열로 대결하기, 계수 기준을 명시하기, 향후 사진 조합을 늘리기 등의 추가 제안은 미확정으로 표시했다.

### 검증·한계·다음 작업

관리 Markdown 12개를 모두 읽고 갱신했다. 실제 파일 목록·색인·검토일/표식과 새 규칙의 일관성을 대조하고 문서 검사기를 실행했다. 기존 환경 측정은 이전 기록으로 유지했으며 이번에는 GPU·pip·dry-run·Pi·화면을 재검증하지 않았다.

이번 변경은 Markdown뿐이다. 소스·JSON 설정·패키지·데이터·모델은 변경하지 않았다. 다운로드·학습·새 기능 구현의 착수 승인은 기존의 별도 대기 상태를 유지한다. 실제 정확도·사람 수 성능·클릭 간격·기기 속도는 아직 미측정이다. 다음 단계는 구현 착수 후 대상별 데이터/인원수 주석과 학습 제한 수치를 정하고, Pi 연결 시 기기 점검을 병행하는 것이다.

### 이번에 읽고 갱신한 문서 (12개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

아래는 이전 작업 당시의 기록이다. 과거의 대표 장면 단일 분류·사람 후순위·격자 미정 등의 문구는 최신 요구사항이 아니다.

## 2026-10-21 실행 계획서 작성 및 승인 대기

### 수행 작업과 사용자 확정 답변

- AGENTS.md·README.md·docs/ 전체 11개 기존 문서와 소스·설정·환경 로그·실제 데이터/모델 폴더를 읽고 구현 상태를 감사했다. Protocol과 구현을 구분했다.
- 사용자가 학교 사진 전체를 문제·모델 고정 후 최종 평가에만 사용한다고 재확인했다. 이번 본문의 학교 추가 학습 문구를 후속 답변으로 대체했으며 기존 학습/개발 검증/튜닝 금지를 유지했다.
- 첫 CAPTCHA를 대표 장면 분류, 각 타일에 독립 사진으로 확정했다. 최종 클래스·문제 문구·격자 규격은 아직 미정이다.
- docs/EXECUTION_PLAN.md를 추가했다. 데이터 준비·그룹 분할 → 제한 학습 → 평가 → ONNX 출력 비교 → PC/Pi 추론 → 저장 이미지 dry-run → 사이트 준비 후 실클릭의 산출물·통과 조건·한계를 기록했다.
- 초기 학습 가안은 MobileNetV3 Small 특징 추출부 고정·클래스당 최대 200장·1 epoch부터 필요 시 총 3 epoch다. 사전학습 공개·임의 오답/숨은 지연 금지·실제 속도 측정과 최종 평가 누수 방지를 명시했다.
- 후보 4개의 Kaggle 공개 API 버전·totalBytes를 재조회했다: Intel v2 368859597, Human v5 273809455, COCO v2 27603146598, Places v1 25274286325 bytes. 파일 수·라이선스는 기존 조사와 이번 재조회를 구분했다. Intel 우선과 사람 판별 후순위를 반영했다.
- AGENTS 포함 모든 관리 Markdown을 문서별로 갱신하고 새 계획서를 색인에 추가했다. 현재 12개다. 코드·설정·패키지는 수정하지 않았다.

### 이번 검증 결과

- PC/Pi 예시 설정의 dry-run을 Windows에서 재실행: 타일 0/4/8의 예시 좌표 (200,200)/(400,400)/(600,600), 두 명령 모두 성공. Pi 실기기 실행은 아니다.
- `python -m pip check`: 성공, 의존성 충돌 없음.
- C: 여유 138.59 GiB를 조회했다. 기존 PC 사양 표의 설치 전 저장공간 스냅샷과 구분한다.
- 기존 환경 로그에서 CUDA 텐서 연산 통과와 ONNX Runtime CPU 공급자, 캡처/클릭/보정 미검증을 확인했다. GPU 연산은 이번에 재실행하지 않았다.
- `scripts/check_docs.py --date 2026-10-21`: 새 계획서 포함 12개 모두 통과. 별도 전체 Markdown 검색의 12개와 일치하며 docs 색인·검토 표식·날짜를 확인했다.
- 검사기가 data/models/runs/logs 등도 제외하는 한계를 확인했다. 프로젝트 소유 Markdown의 실제 전체 목록을 수동 대조하며 본문은 직접 검토한다.

### 한계와 다음 작업

사용자 요청에 따라 **계획 승인 전**이다. 다운로드·학교 사진 열람·분할/학습/추론/캡처/클릭 새 구현, 실제 학습과 Pi 실기기 검증은 하지 않았다. 정확도·지연시간·인간 승률은 미측정이다. 승인 후 Intel 샘플·라벨 지침·원본 그룹/분할부터 진행하고 Pi 정보 확인을 병행한다. 10/28은 임시 개발 목표로 유지한다.

### 이번에 읽고 갱신한 전체 문서 (12개)

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/DATASET_CANDIDATES.md
- docs/EXECUTION_PLAN.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

아래 항목은 이전 작업 당시의 기록이며 문서 수·추천 우선순위는 당시 기준이다. 현재 상태와 승인 경계는 위 최신 항목 및 STATUS를 따른다.

## 2026-10-21 Kaggle 후보 조사와 학교 사진 정책 확정

- 사용자 정정: 학교 사진은 AI 학습에 일절 반영하지 않고 자체 CAPTCHA 문제로만 사용한다. 문서 전반에 학습·미세조정·개발 검증·모델 선택·임계값 튜닝 제외 및 최종 평가 전용을 반영했다.
- 이전 초기 프롬프트의 학교 사진 추가 학습 제안을 대체했다. 코드·패키지·GPU 설정은 변경하지 않았다.
- Kaggle 공개 API 메타데이터를 조회하여 Intel(약369MB), Human Detection(약274MB), COCO2017(약27.6GB), Places365(약25.3GB)를 비교했다. Human Detection은 파일 목록 921장(사람 없음362/있음559)도 확인했다.
- docs/DATASET_CANDIDATES.md를 추가하고 문서 목록·현재 상태·설계·일정을 갱신했다. 장면 라벨과 대상 존재 라벨의 차이, 미표기를 음성으로 쓰는 오류 및 미러/원저자 이용 조건 차이를 기록했다.
- 이미지는 다운로드하거나 육안 검사하지 않았다. 실제 학습·성능·Pi 실행도 수행하지 않았다. 문서 11개의 검토 표식·목록과 정책 일관성을 확인했다.
- 이번 전체 검토 대상: AGENTS.md, README.md, docs/README.md, docs/SETUP.md, docs/ARCHITECTURE.md, docs/DATASET.md, docs/DATASET_CANDIDATES.md, docs/INTEGRATION.md, docs/ROADMAP.md, docs/STATUS.md, docs/CHANGELOG.md.

## 2026-10-21 환경 및 초기 구조 구성 완료

송내고 알파 동아리 AI vs 인간 CAPTCHA의 ML·컴퓨터 조작 프로젝트를 바탕화면 `Alpha-Captcha-AI`에 생성했다. PC의 OS/CPU/RAM/GPU/저장공간을 직접 조회하고 AGENTS.md에 기록했다. 웹사이트 제작과 실제 모델 학습은 이번 작업 범위 밖이다.

### 변경

- Python 3.12.3 프로젝트 전용 가상환경과 GPU PyTorch 2.14.1+cu126, Torchvision 0.29.1+cu126 설치.
- ONNX Runtime 1.31.0, 모델 내보내기·데이터 도구·화면 제어 라이브러리·Kaggle 도구 설치.
- 공통/학습/GPU 의존성 파일과 Windows 설치 스냅샷, PC/Pi 초기 설정 스크립트 작성.
- 타일 좌표 계산과 dry-run, 학습/추론/화면 조작 Protocol, 예시 설정 및 빈 데이터/모델 폴더 작성.
- 용도별 문서와 문서 목록 검사기 작성. 모든 작업 후 관리 Markdown 전체 갱신 규칙 반영.
- 별도 소스 ZIP에 문서·설정·코드·폴더 자리표시자만 포함. 설치된 `.venv`, 로그, 임시 캐시, 데이터, 모델은 제외한다.

### 확인

CUDA 사용 가능 및 실제 GPU 텐서 연산의 결과 검증 통과. ONNX Runtime CPU 공급자와 필수 모듈 import 확인. `pip check`, Python 코드 구문, PowerShell 설정 스크립트 구문, dry-run과 문서 목록 검사 통과. 수동 지정 타일 0/4/8에서 예시 좌표 (200,200)/(400,400)/(600,600)을 확인했다. 격자 간격 및 잘못된 타일/크기/중복 입력의 거부도 별도 확인했다.

### 남은 조건

데이터셋과 라벨은 미정이다. 학습·추론·캡처·실클릭 구현, Pi 설치·성능·화면 제어는 미완료다. PC 재설치 스크립트는 구문만 확인했고 새 환경 전체 재설치는 실행하지 않았다. Kaggle 인증·데이터 다운로드, 전역 Python 패키지 변경, 시스템 드라이버 변경은 수행하지 않았다. 다음 작업은 라벨/데이터 확정과 Pi 초반 환경 점검이다.

### 전체 Markdown 검토 기록

아래 10개 문서를 모두 읽고 현재 파일·명령·범위와 대조했다. 실제 결과가 바뀐 문서는 본문을 수정하고, 다른 문서도 해당 내용의 유효성을 검토한 결과를 갱신했다.

- AGENTS.md
- README.md
- docs/README.md
- docs/SETUP.md
- docs/ARCHITECTURE.md
- docs/DATASET.md
- docs/INTEGRATION.md
- docs/ROADMAP.md
- docs/STATUS.md
- docs/CHANGELOG.md

ML 단계 검토 기록: 실제 시각 라벨 검토·134장 자료·두 1 epoch GPU 학습·체크포인트·test 결과와 저장 격자 픽셀 추론을 기록했다. 68개 테스트, 나무/연못 실패와 작은 표본·사전학습 한계, v1 보존·남은 ONNX/Pi/OS 입력을 구분하고 관리 Markdown 12개 전체를 갱신했다. 기존 이력은 당시 사실로 보존했다.

부분 정답 분석 검토 기록: 정답2/3/4칸 가정 분석·기존 인원 조건 재집계·수학 검토 결과와 소표본/독립 가정 한계를 기록했다. 새 성능 측정 없이 문서12개를 갱신했다.

이전 작업 검토(GPU 공정성 상담): 사용자 확정40% 목표·설정·실제 격자 평가 준비와 val 자료 부족, test 자동 평가 제외 및 82개 테스트를 기록했다. 목표 달성/새 학습을 주장하지 않고 기존 이력·학교 격리·전체 Markdown 검토 원칙을 유지했다.

이전 작업 검토(0.25초 제한): 누락된 직전 GPU 예약 구현의 실제v9 게시/CUDA 결과와 최신0.25초 선택 요청을 별도 이력으로 기록했다. 관리13개 전체 본문을 재검토했고 이전1초 실측은 보존했다. 최신 검사/배포/가동 정본은 STATUS이며 학교/모델/40%/실기기 한계를 유지한다.

이전 작업 검토(11/02): 통신최적화의일정/측정·사진22추가/46운영·학교행사제외·v11배포/실제CUDA/서버사진검사를구분해기록했다. 관리13개전체본문을재독갱신했으며모델/정답률조작0과미완료실기기/품질경계를유지한다. 최종문서명령과운영PC가동은STATUS정본이다.
