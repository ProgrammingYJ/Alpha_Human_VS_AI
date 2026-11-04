# 현재 진행 상황

최종 검토: 2026-11-04 (Asia/Pyongyang)

## 최신 작업: GitHub public 저장소 생성·소스 푸시 (2026-11-04)

사용자 요청으로 [ProgrammingYJ/Alpha_Human_VS_AI](https://github.com/ProgrammingYJ/Alpha_Human_VS_AI)를 `ProgrammingYJ` 계정에 **PUBLIC으로 생성하고 main에 초기 소스333파일을 푸시했다.** 첫 소스 커밋 `1bd9efbdc15ad9b36cdea129d7cbdaa55e3ab30d`가 로컬 HEAD·git ls-remote·GitHub API에서 일치했다. GitHub 기본 브랜치 main·isEmpty=false·visibility=PUBLIC·tree truncated=false 및 333개 일반 파일(mode100644)/gitlink0을 확인했다. 이후 문서 결과 갱신도 같은 main에 동기화한다. 기존 Sites v13 게시·운영34사진·가중치·임계값·원격 엔진은 이번 작업에서 변경하지 않았다.

원래 프로젝트는 루트 Git 저장소가 없고 web/alpha-arena에 Sites용 Git만 있다. 원본/기존 이력을 보존하고 별도 `C:\Users\Administrator\Desktop\Alpha_Human_VS_AI`에 새 Git 저장소를 만들어 Python과 웹을 일반 파일로 함께 올린다. 과거 Sites Git 이력이나 gitlink는 공개하지 않는다.

- 포함: Python/웹/설정 예시·요구사항/lockfile·테스트·관리 Markdown13개·빌드 필수 vendor 자산/외부 라이선스·비밀감사를 거친 runs 작성 코드.
- 제외: 실제 사진·Kaggle/학교 자료·학습/운영 manifest/정답은행·모델/가중치·JSON 실행 결과·로그·.env/자격정보·가상환경·node_modules·빌드/런타임 상태·이전 Git 이력. 사진별 정답표를 담은 runs/photo-clarity-20261102/build_review_v1.py 및 finalize_bank.py도 제외한다.
- 공개본의 제외된 로컬 산출물 Markdown 링크는 `scripts/export_public_source.py`로 일반 경로로 표시한다. 원본 로컬 문서·코드 바이트는 유지한다. 새 clone에 실제 모델/은행/실측 파일이 설치돼 있다는 의미가 아니다.

### 실제 공개 준비 검사

| 검사 | 관측 결과 |
|---|---|
| 최초 공개 복사본 |333파일·3,000,355bytes. 원본/복사본 SHA 일치, 비Markdown 코드 바이트 변경0, 공개 문서의 제외된 산출물 링크114개만 일반 경로로 표시 |
| 독립 비밀/자료 감사 |실제 키/토큰/개인키 패턴0, 실제 사진/은행/운영JSON/모델/과거Git/심볼릭링크 제외 확인. 테스트용 자격 포함 URL2개는 고정 거부 fixture로 분류 |
| 작성 도구 감사 |기존 runs 코드51개 중 정답표 내장2개 제외·나머지49개 공개 가능 확인. 이후 내보내기/문서 도구도 비밀 검사. 과거 고정PID PowerShell은 보관용이며 현재 운영 실행기로 안내하지 않음 |
| 공개본 Python |원래 PC의 설치된 .venv와 공개본 src를 사용해179개 통과12.565초. 새 PC 의존성 재설치/실제 ML 모델·사진 운영 검증은 아님 |
| 공개본 Node |HTTP 통합검사를 제외한 단위110개 통과. 새 npm 의존성 재설치·브라우저 QA·재배포는 수행하지 않음 |
| 문서 |원본/공개본 각각 관리13개 날짜/색인·UTF-8/로컬 링크/목록/설정JSON8개 감사 통과. 외부 vendor 라이선스 보존 |
| Git |export inventory333개와 staging333개 완전 일치·누락/초과0·gitlink0. Windows CRLF와 기존3파일 EOF 빈줄을 보존하고 나머지 whitespace 검사 통과 |

최초 독립 감사는 로컬 `runs/github-public-20261104/independent-source-audit.json`, `independent-run-source-audit.json`, `independent-export-audit.json`에 보존했다. 실제 모델/사진을 올려 링크를 복구하지 않았으며 원본 파일 삭제·Sites 재배포·운영 프로세스 조작은 없다. 공개 Git 복사본은 원래 작업 폴더와 분리되어 이후 수정 시 원본에서 내보내기/refresh 후 같은 main으로 갱신한다. refresh는 이전 export SHA와 같은 소유 파일만 덮어써 공개 복사본의 수동 수정을 보호한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/export_public_source.py --report runs/github-public-20261104/preflight-new.json
.\.venv\Scripts\python.exe -X utf8 scripts/check_docs.py --date 2026-11-04
.\.venv\Scripts\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-04 --output runs/github-public-20261104/document-audit-new.json
gh repo view ProgrammingYJ/Alpha_Human_VS_AI --json url,visibility,defaultBranchRef
git -C C:/Users/Administrator/Desktop/Alpha_Human_VS_AI ls-remote origin refs/heads/main
```

이번 작업 검토: 관리13개를 분담해 전체 본문 재독·11/04 갱신하고 실제 public 생성·초기 푸시·원격 일치·일반 웹 파일/제외 범위·독립 감사 및 공개본 Python179/Node110·원본/공개본 문서13개 통과를 확인했다. 모델/사진/학교/40%/Pi/OS 입력·Sites 배포/운영 프로세스 경계는 유지한다. 최종 문서 동기화의 원격 HEAD 확인 결과는 로컬 release 기록으로 보존한다.

## 이전 작업: 애매한 사진 퇴역·명확한 사진 교체·버전13 (2026-11-02)

사용자의 사진 명확성 요청으로 기존 공개 46장을 전수 시각 검토하고 **22장 퇴역·24장 유지·새 10장 추가, 활성 34장**으로 운영에 반영했다. 현재 정본은 public-web-v3/bank.json (로컬 산출물: `data/booth/public-web-v3/bank.json`)이며 활성 파일 합계는 9,290,899bytes다. 로컬 Kaggle 시연 34장과 같은 숫자지만 서로 다른 은행이고 Kaggle/학교 사진은 공개하지 않았다. v1/v2의 46장·12,362,595bytes는 이전 이력이다.

야간·원경 인물/나무·가린 수면·자연 수면 경계·고고도 지형·건물처럼 보이는 잔해 등 어려운 장면을 제외했다. 새 사진은 큰 단체/단독 인물, 건물 외관, 분리된 나무 줄기, 경계가 보이는 정원 연못이다. 실제 RGB 및 216px full-frame contain 미리보기를 검토했고 사이트의 타일 CSS도 object-fit:contain으로 이미지를 자르지 않음을 읽었다. 새 사진은 CC0 7장/PD-USGov-NASA 3장이며 원문 파일 revision/wikitext·권리·촬영 그룹·해시를 기록했다. 새 10장은 두 AI의 시각 판단을 대조했고 독립 사람 검수는 미완료다. 모호한 조건은 null로 제외하며 제목만으로 연못을 확정하거나 모델 정오답을 보고 사진을 선택하지 않았다.

### 코드와 배포

- 인증된 `PUT /api/admin/photos`의 `photoIds` 1~128개를 검증한다. UUID/중복/없는 사진·4종 그룹 부족을 거부하고 단일 SQL UPDATE로 전체 활성 집합을 교체한다. 같은 집합 재전송은 멱등이다. 관리자 `?includeInactive=1`·active/SHA 조회를 추가했고 공개 응답에는 라벨/정답을 넣지 않는다.
- 비활성 사진은 다음 추첨에서 제외하지만 이미 생성한 라운드의 사진 ID·픽셀·정답 스냅샷은 유지한다. R2/원본을 삭제하지 않는다. 기존 active 조건이 현재 라운드 사진도 404로 만들던 조회를 교정하고 라운드 소속·만료·준비/공개 시각 검사는 보존했다.
- 버전13 source `2cc72fceeed5cbbd1f44eb63a6f52df7067a8880`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_dd082b3c37848191b2be432616556827`, deployment `appgdep_6ae897a2e2588191b051f193b217e75a`가 succeeded다. 기존 두 도메인·public audience·D1/R2·소유자 ID는 유지했다. 기존 숨김 키 값을 읽을 수 없어 관리 작업의 ADMIN_KEY만 비밀값으로 갱신했고 환경 revision5에 게시했다. 키는 메모리/호스팅 비밀 환경에만 두고 파일/소스/인자/로그에 저장하지 않았다. 배포 기록 (로컬 산출물: `runs/site-publish/photo-clarity-release.json`).
- 모델·가중치·임계값·학습·GPU FIFO·사진 준비/출발·250ms 선택 계획·기존 운영 PC 프로세스는 변경하지 않았다. 이번 사진 교체에 PC 엔진 재시작이나 방 재생성은 필요 없다. 이미 생성한 판은 기존 사진을 유지하며 다음 새 판부터 새 은행을 추첨한다.

### 실제 검사 결과

| 검사 | 확인 결과 |
|---|---|
| 로컬 파일/자료 | 34/34 SHA·완전 RGB 디코딩·원본/해시/선언 그룹 중복 0·EXIF 없음·dHash≤4 후보 0. 유지 24장의 기존 라벨/그룹 불변 |
| 공개 등록/활성 | 새 10/10 업로드·동일 PUT ACK, D1 등록 56장 중 활성34/비활성22, 4종 ready |
| 활성 R2 파일 | 34/34 SHA·RGB 디코딩, 총 9,290,899bytes가 로컬 정본과 일치 |
| 기존 공개 경기 | 교체 전 9장 해시/URL 보존, 그중 퇴역 3장도 교체 뒤 HTTP200 |
| 새 공개 경기 | 실제 5판에서 4종 모두 관측·9개 독립 사진/그룹·허용 정답 수·인간/봇 동일 배열/출발·정답 비노출·퇴역 재출제 0 |
| 허용 정답 수별 반복 추첨 | 실제 운영 사진 UUID/SHA 카탈로그로 11개 유형/정답 수 조합×32회=352회 통과. 모든 가능한 사진 격자의 전수 검사가 아니며 독립 정확도 표본도 아님 |
| 코드 검사 | 대상 Node 단위33개 통과, TypeScript·production build(6.517초)·diff 통과 |
| 실제 localhost HTTP | 인증/외부 Origin/형식/8192bytes/중복·누락·부족 은행 거부·멱등 교체·active/loading 사진 보존·새 판 퇴역 제외 1개 복합 검사 통과(5.806초, runner5.910초) |

| 주제 | 양성 그룹 | 음성 그룹 | 미확인(제외) |
|---|---:|---:|---:|
| 사람 3명 이상 |14|16|4|
| 나무 3그루 이상 |8|22|4|
| 건물 |9|15|10|
| 연못 |4|30|0|

운영 검증 정본은 retry1-production-verification.json (로컬 산출물: `runs/photo-clarity-20261102/retry1-production-verification.json`), 운영 카탈로그 전수 추첨 (로컬 산출물: `runs/photo-clarity-20261102/production-bank-combinations.json`), 로컬 독립 파일 감사 (로컬 산출물: `runs/photo-clarity-20261102/prepared-final34-independent-files.json`)다. 첫 운영 QA는 PC 절대시계로 출발을 기다린 하네스가 playing을 관측하지 못해 업로드/활성화 전에 실패했다. 원본 실패 (로컬 산출물: `runs/photo-clarity-20261102/production-verification.json`)를 보존하고 서버 상대시각/유한 상태 관측으로 하네스만 수정한 retry1이 통과했다. 사이트 시간 정책을 바꾸지 않았다. 로컬 첫 실패는 외부 Origin의 비JSON403 파싱, 다음 실패는 예비 그룹 없는 최소 fixture였으며 하네스 파싱 수정·로컬 공개34장 추가 뒤 통과했다. 이를 처음부터 모두 성공한 검사로 보고하지 않는다.

**완료:** 사진 교체·관리 원자 전환·v13 배포·활성 파일/출제/기존 사진 보존 검증. **남음:** 독립 사람 검수와 행사 기기/실제 브라우저 렌더링 리허설, 모델 품질/40%·ONNX·Pi·legacy OS 입력. 이번에는 ML 추론/답안 제출/정확도·승률 측정 0회다. 사진 명확성 개선을 모델 성능 개선이나 무지연 보장으로 쓰지 않는다.

재현은 새 결과 경로를 사용하며 실행형은 관리 키를 숨김 stdin으로만 전달한다. 기존 보고서를 덮어쓰지 않는다.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/import_public_booth_bank.py --bank data/booth/public-web-v3/bank.json --base-url https://human.marulee.dev --output runs/photo-clarity-20261102/new-validation-report.json
.\.venv\Scripts\python.exe -X utf8 runs/photo-clarity-20261102/apply_and_verify.py
node runs/photo-clarity-20261102/audit_bank_combinations.mjs runs/photo-clarity-20261102/retry1-active-catalog.json runs/photo-clarity-20261102/new-combinations-report.json
.\.venv\Scripts\python.exe -X utf8 scripts/check_docs.py --date 2026-11-02
.\.venv\Scripts\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-02 --output runs/site-publish/photo-clarity-document-audit-20261102.json
```

이전 작업 검토(11/02): 관리 Markdown 13개 전체 본문을 분담 재독하고 실제 시각 판정·고정 모델/학교 정책·관리 API/현재 라운드 보존·배포/검증과 대조했다. 새 Markdown은 없다. `check_docs.py --date 2026-11-02`에서 13개 모두 통과했고 별도 전수 감사도 UTF-8·로컬 링크·13개 목록·설정 JSON 8개 모두 통과했다. 감사 기록은 photo-clarity-document-audit-20261102.json (로컬 산출물: `runs/site-publish/photo-clarity-document-audit-20261102.json`)이다. 이번 작업이 띄운 로컬 검증 미리보기는 종료했고 운영 PC 엔진은 조작하지 않았다.

## 이전 검증: GPU 분배와 A/B 동시 추론 후보 (2026-11-02)

현재 운영은 단일 모델 가중치 공유와 FIFO GPU 예약을 유지한다. 두 CUDA 스트림에 추론 요청을 함께 보내는 것은 가능하지만 고정 50% 자원 분배와는 다르다. 스트림 실행은 하드웨어 자원에 따라 겹칠 수 있으며 보장되지 않는다([NVIDIA CUDA](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/asynchronous-execution.html)). RTX 4070 Laptop은 MIG 지원 목록에 없고, 설치된 PyTorch의 Green Context는 Windows를 명시적으로 거부한다([MIG 지원 GPU](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/supported-gpus.html), [PyTorch 소스](https://github.com/pytorch/pytorch/blob/v2.14.0/torch/cuda/green_contexts.py)). 메모리 비율 제한은 연산 성능 비율을 배분하는 기능이 아니다([PyTorch 메모리 제한](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.memory.set_per_process_memory_fraction.html)). 드라이버·의존성·운영체제를 변경하지 않았다.

운영 엔진 0개를 확인하고 별도 프로세스에서 기존 세 모델을 한 벌 로드했다(4.736초). 고정 공개 RGB 9장을 각 레인의 독립 입력으로 사용해 매 조합 18타일을 처리했다. 모드별 예열 뒤 직렬/2스트림을 각각 3회 비교했다. private 라벨·정답·정답 개수·사이트 내부 데이터는 읽지 않았다. 가중치는 공유하고 레인별 PIL 입력·나무 processor/진단 상태를 분리했으며 동시 실행 함수에서 반복적인 model.to/eval 변경을 제거한 실험 전용 래퍼를 사용했다. 운영 함수와 래퍼의 출력 차이는 세 모델 모두 0이었다.

| 두 작업 조합 | 직렬 중앙값 | CUDA 2스트림 중앙값 | 이 표본에서 관측한 결과 |
|---|---:|---:|---|
| 존재 판별 + 사람 검출 | 0.386초 | 0.299초 | 약 23% 단축 |
| 나무 계수 + 존재 판별 | 1.171초 | 1.847초 | 약 58% 증가 |
| 나무 계수 + 나무 계수 | 2.238초 | 3.033초 | 약 36% 증가 |

모든 반복의 출력이 직렬 기준과 일치했고 OOM은 0회다. PyTorch 최고 할당/예약은 약 1,539/2,350MiB다. 완료 직전 nvidia-smi의 장치 전체 사용량은 3,036/8,188MiB이며 이는 전체 시간의 피크 계측이 아니다. 프로세스 종료 후 501MiB로 돌아왔다. 호스트 호출 구간 겹침은 확인했지만 GPU 타임라인을 수집하지 않아 실제 커널 동시 실행은 미검증이다. CPU 전처리·후처리·동기화를 포함한 두 작업 완료 시간이며 순수 GPU 커널 시간·HTTP·출발/사진 준비·화면 렌더링 측정이 아니다. 한 사진 집합/각 3회 결과를 p95·장시간 안정성·정확도·모든 조합 성능으로 일반화하지 않는다.

실험은 [probe.py](../runs/gpu-concurrency-20261102/probe.py)와 report.json (로컬 산출물: `runs/gpu-concurrency-20261102/report.json`)에 보존했다. 최초 재현 명령은 `.\.venv\Scripts\python.exe -X utf8 runs/gpu-concurrency-20261102/probe.py`다. 기존 보고서가 있거나 운영 엔진이 켜져 있으면 즉시 거부한다. 기존 보고서를 지우지 말고 새 날짜의 실험 복사본/출력 경로를 준비해야 재실행할 수 있다. 운영 스케줄러·API·공개 방·서버 배포·운영 프로세스 시작/종료는 변경하지 않았다. 아래 11/01 PID 가동 기록은 과거 관측이며 이번 조회의 엔진 0개와 구분한다.

**완료:** 실제 오프라인 비교·출력 일치·메모리 관측·전체 문서 검토. **미완료:** 운영 동시 추론 도입·실제 커널 타임라인·새 배칭/사진 준비 병행·실제 A/B 현장 장시간 리허설. 나무 조합이 느려져 무조건 병렬화는 채택하지 않았다. FIFO는 사진 준비/카운트다운까지 보유하므로 그 대기는 모델 동시 실행과 별도 과제다. 학습·가중치·임계값·46장 문제은행·학교 미사용·250ms 선택·40%/ONNX/Pi/OS 입력 상태는 유지한다.

문서 검증은 전체 13개 갱신 후 아래 명령을 실행했다. 검토 표식/날짜/색인 13개 모두 통과했고 별도 전수 감사도 Markdown 13개·UTF-8·로컬 링크·목록 및 설정 JSON 8개 모두 통과했다. 감사 보고서는 gpu-concurrency-document-audit-20261102.json (로컬 산출물: `runs/site-publish/gpu-concurrency-document-audit-20261102.json`)에 보존한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/check_docs.py --date 2026-11-02
.\.venv\Scripts\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-02 --output runs/site-publish/gpu-concurrency-document-audit-20261102.json
```

이전 작업 검토(11/02): GPU 할당과 동시 요청, 실제 실험·운영 미채택·메모리 수치와 측정 한계를 전체 본문 및 이전 공개 검증 이력과 대조했다. 관리 Markdown 13개를 분담 재독·갱신했고 새 Markdown은 없다. 최종 문서 검사는 13개 모두 통과했고 별도 전수 감사의 UTF-8/로컬 링크/목록/설정 JSON 8개도 통과했다.

## 이전 상담: A/B 동시 운영·GPU 처리와 대기 구간 (2026-11-01)

**A/B 두 경기를 함께 운영할 수 있다.** 한 실행기가 세 모델을 한 번 로드해 공유하고, GPU 예약/추론을 FIFO 순서로 처리한다. A 추론이 반환되면 GPU를 해제하므로 A의 서버 선택 표시·인간 풀이가 계속되는 동안 B도 준비와 추론을 진행할 수 있다. 모델을 방마다 두 벌 올리는 구조가 아니다. 실행기는 하나만 켜고 같은 콘솔에 A/B를 연결한다.

두 레인의 시작 요청이 겹치면 B는 경기 시작 전에 대기할 수 있다. A/B의 절대 출발 시각은 달라질 수 있고, 각 방의 인간·AI 쌍은 그 방의9장 준비 후 공통 출발한다. 대기를 타이머 앞으로 옮긴 것은 처리 가능성과 공정성 조건이며 전체 부스의 지연0 보장은 아니다.

이번 문의에서는 기존 공개 A1 (로컬 산출물: `runs/reliability-public-20261101-v1/lane-A-game-1.json`)·B1 (로컬 산출물: `runs/reliability-public-20261101-v1/lane-B-game-1.json`)과 종합 검증 (로컬 산출물: `runs/reliability-public-20261101-acceptance.json`)을 읽었다. A1/B1 예약 전 대기는 각각0.375/10.438초, 모델 함수는연못0.094초/나무1.875초, 경기 중 GPU 대기는 둘 모두0초였다. 예약 전 값에는 앞 방의 준비·카운트다운과 상태 확인 HTTP가 포함되므로 순수 GPU 계산시간이 아니다. 서로 다른 두 문제의1회 관측이며 모든 유형 조합·최대 VRAM·장시간 발열/행사 네트워크·브라우저 표시 지연을 보장하지 않는다.

이번은 설명과 관리 Markdown 갱신뿐이다. 새 코드·배포·ML 추론/성능시험·하드웨어 조회·운영 프로세스 조작0이며 아래 버전12 검증/가동 기록을 새 측정으로 보고하지 않는다. 기존 경기별 사진 준비·250ms 선택·같은 방 다음 참가자·고정 모델/학교 미사용·미완료 품질/실기기 경계는 유지한다. 문서 점검 명령은 `scripts/check_docs.py --date 2026-11-01` 및 `runs/site-publish/audit_docs.py --date 2026-11-01`이며 전체 갱신 후13개 모두 통과했고 별도 전수 감사의 UTF-8·로컬 링크·색인/목록·설정JSON8개도 통과했다.

이전 작업 검토(11/02): A/B 병행 가능성, 한 번 로드한 모델 공유와 직렬 GPU 예약, 추론 후 자원 해제, 경기 시작 전 대기와 경기 중 GPU 대기를 기존 보고서로 대조했다. 기존 수치를 새로운 성능 측정이나 무지연 보장으로 사용하지 않고 두 레인 출발과 방 안의 공통 출발을 구분했다. 관리13개 본문은 분담 재검토하고 실제 문서 점검은13개 모두 통과했다.

## 최신 작업: 사진 준비 후 공통 출발·통신/복구 수정·버전12 (2026-11-01)

11/01 재개 요청으로 지난 행사에서 제보된 사진 로딩/출발 차이, 서버·PC 버전 오류, 선택 지연과 A/B·같은 방 반복을 우선 수정했다. 다음 행사 목표는11/07(토)다. 재개 시 실제 공개 버전은11이고10/28 사진 준비 코드는 로컬 부분 구현 상태였음을 확인했다. 현재는 아래 버전12 게시가 완료됐으며 과거 v11 지표는 새 버전 측정으로 재사용하지 않는다.

### 현재 동작과 수정

- **시작 요청→GPU FIFO 예약→loading→인간 화면/AI 표시/PC의9장 준비→약2초 공통 출발→보관 RGB 추론→GPU 해제→선택 계획1회**다. loading은 startAt/deadlineAt/topic=null·tiles=[]·타이머0이며 불투명 preloadTiles만 전달한다. 브라우저는 숨긴 실제9img의decode/크기를 확인하고 PC는RGB9장을 미리 받는다. 실제 문제 추론은 공통 출발 후에만 수행하고 경기 중 재다운로드하지 않는다.
- 브라우저는 같은key/img/src를 출발 때 공개하고 준비한 질문을 시계로 표시한다. 출발 직후 추가GET을 기다리지 않는다. 페이지가 숨겨지면 출발 전 준비를 철회하고 보이는 페이지에서만 다시 준비한다. **인간·AI 표시를 각각 보이는 창/모니터에 둔다.** 같은 브라우저의 숨은 두 탭으로 동시 운영하지 않는다.
- 프로토콜3·round/request/imageLoadId로 준비/회차를 확인한다. 출발 전 재로드는 준비epoch/3역할을 초기화하고 이전ACK를 거부한다. PC는같은회차/같은사진순서만재사용한다. 취소·사진실패·준비60초/엔진15초 만료는 같은 방 lobby로 돌아가 수동 시작한다. 출발 후 재로드는 경기를 소급 정지하지 않는다. GPU대기120초·사진60초·경기90초는 운영 가안이다.
- v11에imageBarrierSupported필드가 아예 없을 때만 PC가protocol2를 협상한다. 새 서버는protocol3 준비를 우회한 출발을 거부한다. lobby중 배포가 바뀌면 같은PC권한으로3을 다시 알린다. 준비ACK의응답이유실되어이미playing이면 같은round/request/epoch·3ready와RGB캐시를새상태에서확인한경우만복구한다. 임의바이패스/재추론은없다.
- 마지막준비ACK와새heartbeat가겹쳐SQLrelease가거부된경우, 저장된3ready/loading을다음상태조회에서원자적으로재정산한다. 재정산은기존countdown시각을바꾸지않는다. 합성SQLite에서HB+1ms→옛시계release0→freshretry1을재현했다(독립경합검사 (로컬 산출물: `runs/image-barrier-audit-20261101/heartbeat-release-race.json`)).
- 화면시계는performance.now/최저RTT표본을사용하며확정카운트다운에서는기준을고정한다. 늦은응답이출발선을흔들던문제를줄였다. 요청은10초제한으로무한hang을해제하고정상회차409를끊김으로표시하지않는다. 사람의로컬선택은상태조회실패/제출왕복동안에도편집할수있다. 서버만채점/단일승자를확정한다.
- PC는스레드별HTTPS연결과최대3사진다운로드pool을재사용한다. 새barrier+plan경로의추론/선택stage동기heartbeat2개와중복guard1개를제거하되주기heartbeat와실제모델전검사/서버plan검사를유지했다. 읽기GET은유한재시도하고멱등사진준비ACK/선택계획은같은요청의재전송으로복구한다. 일반POST를무조건재전송하지않고오류·경합의원자성/정답비공개조건을유지한다.
- PC는ready전에합성RGB로3모델을예열한다. 실제질문은건물/연못이면기존존재모델,사람이면기존검출모델,나무이면기존나무모델만실행한다. 미실행출력은None이고가중치·임계값·전처리/후처리는동일하다. 원래full예측API는보존한다. 합성예열과실제문제의사전추론을구분한다.
- 500ms표시여유/250ms서버선택일정·계획1회·단일승자·같은방next는유지한다. 네트워크/브라우저/모델지연이0이라는주장이나실제250ms렌더링보장은하지않는다.

### 실제 자체 검사

| 검사 | 실제 결과 |
|---|---|
| Python 전체 |179개 통과7.846초; 연결재사용/프로토콜업그레이드/준비ACK유실/캐시·출발경계 포함 |
| Node 단위 |105개 통과0.915초; SQL/회차/3역할/시계/경합 회귀 포함 |
| TypeScript·diff·변경Python컴파일 |통과; production build/source push/package/save/publish 통과 |
| 실제 localhost HTTP |6종 모두 통과20.935초; 느린human2.5초 동안loading/시각null,epoch/reset/사진실패/같은방복구,기존권한/채점/선택/next 포함 |
| 마지막 heartbeat경합 수정 후 HTTP |배리어 재검사1개 통과3.614초(runner),case3.518초 |
| 공개 CUDA·역할별RGB 준비 |A2판+B1판의 실제 추론/서버제출·같은방 교체 확인. 느린 인간 게이트는 별도 공개10개 검사로 보완; 원본 실패 표식 보존 |
| 실제 브라우저 DOM/동시렌더 |미수행. CUA가browser access host unavailable을반환했고다른UI도구로우회하지않음 |

로컬HTTP의준비메시지는테스트클라이언트이며브라우저decode/실제ML검사가아니다. 로컬검증기록 (로컬 산출물: `runs/site-publish/reliability-local-http-20261101.json`)을보존한다. 전체문서의이전일정/성능수치를이번결과로바꾸지않는다.

운영사진46장·12,362,595bytes의로컬정본SHA/디코딩과v1두체크포인트의고정SHA일치를별도로확인했다(보존검사 (로컬 산출물: `runs/image-barrier-audit-20261101/data-preservation.json`)). 학교사진/새학습/임계값조절/임의오답주입0이며ML풀이의관리/정답데이터접근0이다. 은행보존검사와격리서버채점QA의기대정답은ML에전달하지않는다. 이는공개R2전체재검사나사진품질/40%달성평가가아니다. 목표40%·ONNX/Pi·legacy OS 입력·현장컴퓨터/네트워크리허설은미완료다.

### 배포·공개검증·운영

버전12 게시 **succeeded**, commit `6ac76b5b4364ccfaa75b8907052aa9757dfc54cb`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_e3a88ddc0574819199ce873e6c599611`, deployment `appgdep_6ae705508ea4819187390ffbdbe500a2`, 환경revision4다. 기존owner/공개범위/두도메인/비밀환경/D1/R2/사진은행은유지했다. archive해시는배포기록 (로컬 산출물: `runs/site-publish/reliability-release.json`)에있다. migration0004_amazing_namora.sql은사진준비5열추가이며로컬5명령을한번적용했다. 기존0000~0003SQL불변,운영migration은Sites게시절차로적용됐다.

공개검증 결과: 두 호스트/초기 자산 검사 (로컬 산출물: `runs/site-publish/reliability-release-http-20261101.json`)에서 human/bot 각각 HTML·health와 초기JS/CSS17개가 모두200이었다. 프로토콜3·사진 준비·250ms 하한·새 schema 접근도 확인했다. 교차호스트 연결 (로컬 산출물: `runs/site-publish/reliability-cross-host-pairing-20261101.json`)은 인간 호스트에서 만든 방에 봇 호스트의 표시/실제 EngineRoom을 연결해 같은 코드·B구역·준비/생존을 확인한6개 검사 통과다. ML/경기 시작/운영 방 접근은 없었다.

공개 **CUDA A같은방2판+B1판**에서 모델1회 로드6.547초·합성 예열2.547초, 각 판 예측1회/논리제출1회·서버 제출3회·생존363샘플/준비 후 끊김 관측0을 확인했다. 세 판 모두 사진 캐시 재사용·경기 중 사진 다운로드0·출발 전 실제 문제 추론0·경기 중GPU대기0·계획 전GPU해제였다. A1/A2의연못예측은[]이고B1나무는[1]로서세판모두오답timeout이다. 이 재사용 기능검사를 정확도0%나40%목표 검증으로 해석하지 않는다. 원본 실제 실행 (로컬 산출물: `runs/reliability-public-20261101-v1/verification.json`)과 판별 보고서를 보존한다.

원본26개 불리언 중25개가true이고 `slow_human_gate_observed`는false였다. 인간 자신의 디코딩 완료부터3초만 보류한 첫 시험은 다른 두 역할이 준비된 뒤 인간만 미준비인 구간을 관측하지 못했다. **원본passed=false를 그대로 보존했다.** 시험을 다른 두 역할의 준비 확인 뒤3초 보류하도록 고치고 별도 공개 게이트 검사 (로컬 산출물: `runs/reliability-public-20261101-gate-v2.json`)10/10을 통과했다. PC/봇만 준비된loading샘플3개에서 타이머0을 실제 관측했고 보류4.984초 후 인간 준비→공통countdown→출발 전 취소까지 확인했다. 보완 검사는 HTTP/PIL이며 ML/선택/제출0이다. 종합 검증 (로컬 산출물: `runs/reliability-public-20261101-acceptance.json`)은 원본의 미관측 사유와 별도 보완 근거를 명시한다.

실제 세 판의9RGB 사전 수신은 A1/A2/B1 각각1.953/1.031/1.328초, 모델 함수는0.094/0.062/1.875초, 계획 ACK왕복은0.344/0.328/0.328초였다. 이것은 각1회 관측이며 평균/p95 또는 모든 행사 네트워크의 속도 보장이 아니다. 선택이0/0/1개여서 공개 다중선택 간격 표본은0이다. SQL/로컬HTTP의250ms 검증과 공개 브라우저/실제 타일 렌더링 실측은 구분한다.

원본의 요청→공통 출발11.570/23.651/20.997초에는 GPU 예약·테스트 역할 준비·공통2초와 통신이 포함된다. 특히 A2는 QA의직렬view/register 관측 공백16.797초가 있었고, 첫loading관측 이후countdown까지3.610초/playing관측까지4.688초였다. PC가 먼저 준비되어도 인간/표시준비false인 동안 서버가 기다린 것은 정상이었다. 원본은 각GET/POST 지연을 분해하지 않아 공백의 세부 네트워크 원인은 미확인이다. 이를 모든 실제 브라우저의 준비 시간이23초라는 주장이나 현장 무지연 증명으로 바꾸지 않는다.

고정 공개9RGB에서 full예측과 질문별 경로의 관련 점수/인원수/선택이 모두 같았고 최대 존재점수 차이는0이었다. full0.360초·건물/연못 각각0.078초·사람0.328초는 같은9장 한 번의 기능 비교다. 새 정확도·배포 장치별 벤치마크/40%달성 측정은 아니다. 가중치/전처리/임계값·추가학습 변경0이다.

운영 엔진은 시작 전0개임을 확인하고 새 콘솔을 켰다. 경로/부모 관계를 검증한 **PowerShell19224→venv12972→base31892**는 CUDA 모델1회 로드6.031초·합성 예열2.469초·총8.5초 초기화와 생존을 확인해 켜 두었다. 가동 기록 (로컬 산출물: `runs/site-publish/reliability-current-engine.json`)과 startup (로컬 산출물: `runs/remote-engine/20261101-182934-4bd3ee13/startup.json`)이 근거다. 에이전트 코드 입력0이며 특정 사용자 방 연결 완료는 아직 아니다. 사용자는 웹을Ctrl+F5로 새로고침하고 최초 새 방으로 PC/표시를 한 번 연결한다. 이후 참가자 교체는 같은 방next를 사용하며 실행기를 중복 실행하지 않는다. 표시 창 두 개는 보이는 상태를 유지한다.

관리13개 Markdown의 전체 본문을 분담 재독·교차검토했고 최신 동작/이력·측정/한계를 갱신했다. `check_docs.py --date 2026-11-01`과 별도 전수 감사에서13개·UTF-8·로컬 링크·색인/목록·설정JSON8개가 통과했다(문서 검사 (로컬 산출물: `runs/site-publish/reliability-document-audit-20261101.json`)). 최종 내용 수정 뒤 같은 명령을 재실행해13개 모두 통과했다. 실제 브라우저 동시 렌더링과11/07행사 기기·네트워크 리허설은 사용자의 재검증에 남아 있다.

이전 작업 검토(11/02): 11/01에 관리13개를 전수 검토하고 서버/화면/PC의 사진 준비·버전·연결/선택 지연과 복구를 수정했다. 공개v12/HTTPS·실제CUDA3판·미관측 시험의 별도 보완·고정모델 출력 동등성과 운영 엔진 초기화를 구분해 기록했다. 최초 공개 시험passed=false와 타일 간격 표본0·브라우저 미검증을 숨기지 않았다. 학교/학습/임계값·40%/ONNX/Pi/legacy OS 및 현장 검증 경계를 유지한다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --device cuda --execute --output runs/reliability-public-new
.\.venv\Scripts\python.exe runs/site-publish/verify_reliability_surface.py --output runs/site-publish/reliability-http-new.json
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-11-01
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py --date 2026-11-01 --output runs/site-publish/reliability-document-audit-new.json
```

Node단위명령은웹폴더에서 `node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs server/gpu-start.test.mjs server/selection-plan.test.mjs server/image-barrier.test.mjs components/arena-state.test.mjs components/engine-status.test.mjs components/server-clock.test.mjs`다. 실제localhost6종은미리보기5186에숨김stdin의로컬QA키로실행한다. 공개ML명령은새QA방과실제선택/제출을만들며비공개정답을읽지않는다. 기존기록을덮지않도록새출력경로를사용한다.

이후절은이전버전이력이다. 당시학교평가/출발/타일별통신/PID/날짜는현재정책을뜻하지않는다.


## 이전 작업: 선택 통신 최적화·공개 사진22장 추가·버전11 (2026-10-27)

**현재 운영 사진은46장이고 학교 사진은 이번 행사에서 사용하지 않는다.** 학교 촬영·문제·학교 최종 평가는 현재 범위에서 제외했다. 기존 모델/전처리/임계값·학교 자료의 개발 학습 차단·40% 미달성·ONNX/Pi/legacy OS 미검증은 유지한다.

### 통신과 서버 일정

- 기존에는 각 타일마다 상태 GET→선택 POST→ACK후250ms가 필요했다. 최신 PC는 공개 RGB를 ML에 넣어 한 번 정한 목록을 `plan {roundId,selectedIndices}` 한 요청으로 보낸다. 타일별 select/submit HTTP는0이며 서버 생존/상태 조회는 계속한다. 공개 RGB9장은 최대3개 병렬 다운로드하며 `map`으로 타일 순서를 보존하고 실패 시 작업을 정리한다.
- 서버는 같은 round의 목록을 한 번만 수락한다. 같은 순서의 재전송은 동일 ACK, 다른 목록/기존 개별 선택과 혼용은 거부한다. **접수 후500ms 표시 버퍼→250ms 서버 일정→마지막 선택 시 제출**이다.0개 선택도500ms 뒤 그대로 제출하며 9개이면 버퍼 포함2.5초 일정이다. 선택 수/정답 수를 강제로 맞추거나 임의 오답을 넣지 않는다.
- 원격 계획 수락 뒤에는 PC가 끊겨도 이미 받은 결과로 재생을 완료한다. 인간 선승이면 정해진 종료 시각으로 남은 선택을 자른다. 미래 선택은 bot 표시 역할에만 주고 human/모델 입력에 노출하지 않는다. 예정 정오답은 서버 전용이다. due 정산과 인간 채점의 D1 batch/SQL 보호로 한 승자를 유지하며 예정 제출 시각과 같은 시각의 인간 요청은 이미 도래한 bot 제출이 우선한다.
- 계획을 받은 봇 표시는 기존50ms 시계로 체크하고 상태 조회는500ms다. 계획 없는 진행 중 봇 fallback만125ms이며 인간·대기·결과도500ms다. 늦게 받은 화면은 진행 시각까지 따라잡는다. **서버 일정250ms와 실제 화면/OS 클릭 간격은 다른 지표**이며 실제250ms 렌더링을 측정했다고 주장하지 않는다.
- migration `0003_colorful_cassandra_nova.sql`은 round의 nullable 계획4컬럼만 추가했다. 로컬4명령을 한번 적용했고 기존0000~0002는 변경하지 않았다. 구형 개별 API와 GPU 예약 출발/같은 방 next/프로토콜2는 유지한다.

### 새 공개 사진과 학교 범위

- 새 은행 정본 (로컬 산출물: `data/booth/public-web-v2/bank.json`)은 **22장·6,299,046bytes·CC0 15/PD7**이다. 사람 단체·명확한 나무 줄기/군락·건물 외관·돌 경계 정원/잉어 연못을 선정했다. 강/호수처럼 보이는 수면·눈녹은 웅덩이 같은 후보·같은 날 근접 촬영 가능 숲·조형물/그림/합성·사진권리 혼합은 제외하고 모르는 조건은 null로 남겼다. 선별에 모델 예측을 사용하지 않았다.
- 두 AI가 실제 RGB를 대조하고 일부 인원수는 큰 원본으로 다시 셌다. 파일별 Commons 원문 revision/권리·원본 SHA1·전송 SHA256·그룹을 보존했다. 독립 사람 검수는 미완료다. 기존 은행과 원본ID/SHA1·사진 바이트 중복0 및 dHash거리≤4 의심쌍0은 중복 검사 근거이지 세상 모든 유사 촬영이 없다는 증명은 아니다.
- importer dry-run22/22 뒤 운영 **22/22 신규 업로드·기존중복0**을 확인했다(업로드 기록 (로컬 산출물: `runs/site-publish/public-bank-v2-upload.json`)). 기존24장과 합쳐 **46장·12,362,595bytes(CC0 26/PD20)**다. 새 사진은 운영 문제용으로만 사용하며 추가 학습·개발val/audit 편입·승률 튜닝0이다.
- 운영46개 파일의 해시·디코딩이 두 로컬 은행과 일치했고 네 유형 각9독립그룹/사진·같은 인간/봇 배열과 출발·정답수 범위·정답 비노출을 검사했다. 그 중 신규 사진12개를 실제 공개 타일로 관측했다. 관리자 권한의 별도 SERVER 사진 검사이며 ML 풀이기와 분리하고 선택/제출하지 않았다(공개은행 검증 (로컬 산출물: `runs/site-publish/expanded-photo-bank-verification.json`)).

| 운영46장 조건 | 양성 그룹 | 음성 그룹 | 미확인 | 출제 준비 |
|---|---:|---:|---:|---|
| 사람≥3 |14|24|8|ready|
| 나무≥3 |16|22|8|ready|
| 건물 |13|25|8|ready|
| 연못 |11|34|1|ready|

### 실제 검사

| 검사 | 관측 결과 |
|---|---|
| Python 전체 |165개 통과14.515초; 계획 ACK/호환/목록·측정 분리·3다운로드 순서/실패 포함 |
| Node 서버/UI |89개 통과1.217초(서버65/UI24); 계획13·UI3 추가 |
| TypeScript·대상 ESLint·컴파일·diff |통과 |
| 실제 localhost HTTP |5종 통과: 기존채점6.340초·지속방9.065초·GPU대기18.186초·원격20.487초·계획13.005초; runner20.659초 |
| 실제 공개 PC CUDA |A같은방2판+B1판, 모델1회로드8.844초·18검사 passed=true·생존216샘플·준비후끊김 관측0 |
| 로컬 브라우저 |격리된 고정API계획으로9이미지 로드·4체크·전부읽기전용·가로넘침0을 DOM으로 확인. 실제ML/물리OS/정확한250ms렌더링 검사는 아님 |

공개 CUDA의 사람 문제 A1은 `[0,8]` 두 선택으로 정답 종료, A2 연못/B1 나무는 `[]` 그대로 오답 제출 뒤90초 timeout이었다. **세 판 재사용 기능검사를 정확도1/3이나40% 달성으로 해석하지 않는다.** 실제 CUDA 보고서 (로컬 산출물: `runs/scheduled-booth-public-v1/verification.json`)에 예측1회·논리제출1회·서버 제출 관측3·모델/표시 일치·경기중GPU대기0·계획 이전GPU해제와 같은 방/코드/권한 유지가 있다. 관리 정답/학교/OS입력/튜닝 접근0이다.

세 계획의 실제 업로드→ACK는 **0.360/0.375/0.469초**,9사진 다운로드는 **1.500/2.797/1.937초**였다. 서버 예정 간격 표본은 A1의250ms 1개이며 실제 타일별 HTTP 간격 표본은0이다. 고정API UI 시연의4체크는 별도이며 이를 실제 모델 클릭 속도로 바꾸지 않는다. 과거v10의762~957ms 실제 API 간격과 새 서버 예정250ms는 다른 측정이다. 같은 사진·네트워크로 짝지은 전체 경기 속도 비교를 수행한 것은 아니다.

브라우저 첫 고정 하네스가 이전 heartbeat와 출발 전환의409를 치명 오류로 처리해 종료했다. 서버의 옛 요청 거부는 정상이었고 하네스를 상태 재조회로 고친 새 QA방에서 queued→countdown→playing→계획 수락/표시→result를 확인했다. DOM 감시 생성자는 read-only 검사 범위에서 지원되지 않아 정확한 렌더링 간격을 측정하지 못했다. 영역 스크린샷은 캡처 좌표가 잘리지 않아 연결 코드를 포함한 임시 파일을 즉시 제거했으며 부정확한 이미지를 증거로 보존하지 않았다. 실제 DOM 관측과 서버 일정을 근거로 삼는다.

### 배포와 재현

버전11 production build/source push/package/save/publish **succeeded**, commit `8755f3c852c555ac2637c47a85bd4e3cedac8d0e`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_0ef517f5604c8191b1e96654ef95eea5`, deployment `appgdep_6ae065686ac88191a8ea3c01f755ce6a`, 환경revision4다. 사진 등록용 기존 관리자 비밀값은 조회 시 가려져 같은 권한으로 갱신했고 메모리/stdin/서버 비밀 환경만 사용했다. owner·도메인·공개범위·기존사진/모델은 유지했다. 배포 기록 (로컬 산출물: `runs/site-publish/scheduled-release.json`)과 두 호스트 HTTPS200 검사 (로컬 산출물: `runs/site-publish/scheduled-release-http.json`)가 근거다.

운영 중이던6916→49352→16984의 경로·부모 관계를 검사한 뒤 해당 체인만 업데이트를 위해 종료했다. 최신 **PowerShell45960→venv7608→base39488**은 모델1회 CUDA 로드 **6.891초**, 계획 우선/최소0.25초/사진3병렬 초기화와 생존을 확인하고 켜 두었다(가동 기록 (로컬 산출물: `runs/site-publish/scheduled-current-engine.json`), startup (로컬 산출물: `runs/remote-engine/20261027-175954-8c140d26/startup.json`)). 운영 콘솔 코드 입력은0이며 특정 방의 준비 완료는 미확인이다. 이번 업데이트 후 사이트를 새로고침하고 새 방으로 PC/표시를 한번만 다시 연결하며 정상 참가자 교체에는 같은 방 next를 유지한다. QA 모델/하네스와 사용자용 실행기를 구분한다. 로컬 브라우저 DOM 관측은 별도 기록 (로컬 산출물: `runs/scheduled-browser-qa/verification.json`)에 있다.

관리13개 Markdown 전체를 분담해 다시 읽고 현재 정책/수치와 과거 이력을 갱신했다. 최종 `scripts/check_docs.py --date 2026-10-27`은13개 모두 통과했고 전수 감사도13개·UTF-8·로컬 링크·색인/전체목록·설정JSON8개 통과다. 내용은 직접 교차 검토했으며 기계 검사를 내용 검증으로 대체하지 않았다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --device cuda --execute --output runs/scheduled-booth-public-new
.\.venv\Scripts\python.exe scripts/import_public_booth_bank.py --bank data/booth/public-web-v2/bank.json --base-url https://human.marulee.dev --output runs/site-publish/public-bank-v2-dry-new.json
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-27
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py
```

웹 단위검사는 기존8파일에 `server/selection-plan.test.mjs`를 추가한다. 실제 localhost5종은 새 migration 후5186 미리보기·숨김stdin QA키와 `run-local-audits.mjs`로 실행한다. 관리자 사진 검증은 `with_booth_secret.mjs`의 숨김stdin으로 `verify_expanded_photo_bank.py`를 실행했으며 ML 경로에 키/라벨을 넘기지 않았다. 새 실행 출력 경로를 써서 과거 기록을 보존한다. 실제 물리부스 배치/장시간 네트워크·독립 품질·40%·ONNX/Pi/legacy OS 입력은 미완료이며 학교 최종 평가는 현재 행사 범위에서 제외했다.

이후 절은 이전 버전 이력이며 옛 학교 최종평가 계획/타일별 ACK 지연/PID는 현재 운영을 뜻하지 않는다.


## 이전 작업: 선택 간격0.25초 (2026-10-27)

사용자 후속 요청으로 이전1초 제한을 **기본·최소0.25초(250ms)**로 변경했다. GPU 예약을 확보한 뒤 인간/AI가 공통 출발하는 버전9의 흐름은 유지한다. 새 제한은 타일 사이 대기이며 모델 정확도·추론 시간 변경이 아니다.

- Python `MIN_TILE_INTERVAL_SECONDS=0.25`를 remote ACK후 대기·legacy 콜백/설정 검증·CLI·보정기·PC/Pi 예시·저장 이미지 계획에 함께 사용한다. 부동소수점 반올림으로 짧아지지 않도록 다음 표현값으로 올린다. 첫 선택 대기0·제출 간격 제외는 기존 운영 가안이다.
- 서버 `TILE_INTERVAL_MS=250`를 사전 검사와 SQL CAS에 함께 사용한다. 249ms는 거부하고250ms는 허용하며 sequence 재전송 ACK·중복 타일/옛 회차 거부·단일 승자 조건을 유지한다.
- remote AI 표시의 playing 상태만125ms로 조회하고 인간/대기/결과는500ms다. 요청 중복을 막는다. 실제 간격에는 선택/상태 HTTP 왕복과 렌더링이 더해지며 정확히 초당4개 표시를 보장하지 않는다.

| 새 검증 | 실제 결과 |
|---|---|
| Python 전체 |155개 통과,11.072초;0.25 허용·0.249 거부·명시적 느린1.0 설정·ACK후 대기 경계 |
| Node 서버/UI |73개 통과,1.270초(서버52/UI21);249/250ms SQL·순서·상태·폴링 회귀 |
| TypeScript·대상 ESLint·Python 변경 파일 컴파일·diff |통과 |
| 실제 localhost HTTP |4종 통과: 기존채점5.402초·지속방8.004초·GPU대기17.730초·원격권한/250ms선택20.037초; runner20.192초 |

### 배포·공개 검증·PC 가동 확정

- **버전10 게시 succeeded**: commit `44a78ce020602d86c248bcbf9f3da7658f3087a5`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_975ee4e587448191b06c0e3516b3c9c1`, deployment `appgdep_6ae05d76f7b4819186719d3ef1e280f4`, 환경revision3이다. 배포 기록 (로컬 산출물: `runs/site-publish/quarter-release.json`)에 archive 해시가 있다. 도메인/공개범위/D1/R2/기존0000~0002 migration·사진은행은 유지하며 새 migration은 없다. 두 호스트 HTTPS200과 기존 컴퓨터 운영 안내를 확인했다(HTTP 기록 (로컬 산출물: `runs/site-publish/quarter-release-http.json`)).
- 별도 격리 QA방의 **고정 타일0/1/2 API 검사**에서 로컬 서버 선택 간격307/315ms, 공개957/762ms(각2표본)로250ms 제한·중복 ACK·표시 상태 일치가 통과했다. 공개의 마지막 간격762ms는 기존1초 하한보다 짧게 허용됐음을 확인한다. 첫 간격은 중복ACK 검사 왕복도 포함한다. 이 검사는 모델/이미지/정답/제출을 사용하지 않으며 실제 ML 선택 속도·브라우저 렌더링·정확도 측정이 아니다. 근거: 로컬 (로컬 산출물: `runs/site-publish/quarter-interval-local-v1.json`), 공개 (로컬 산출물: `runs/site-publish/quarter-interval-public-v1.json`).
- 이전에 가동 중이던44388→39712→39120의 실행 경로·부모 관계를 검사한 뒤 해당 체인만 종료하고 최신 실행기를 시작했다. **PowerShell49376→venv39132→base15816**, CUDA 세 모델1회 로드 **9.734초**와 생존을 확인하고 켜 두었다. 시작 기록은 startup.json (로컬 산출물: `runs/remote-engine/20261027-171544-882cae21/startup.json`), 최신 PID/확인 시각은 가동 기록 (로컬 산출물: `runs/site-publish/quarter-current-engine.json`)이다. 에이전트의 운영 콘솔 코드 입력0이며 특정 사용자 방의 준비 완료를 주장하지 않는다.
- 이번 업데이트 재시작으로 메모리의 연결 토큰을 잃으므로 **사이트를 새로고침하고 새 방으로 한 번만 PC/AI 표시를 다시 연결**한다. 그 뒤 일반 참가자 교체는 같은 방의 다음 참가자 준비를 사용한다. 참가자마다 실행기 재시작/새 방을 요구하지 않는다.
- 관리13개 Markdown을 전부 읽고 최신 본문/이력·검토 기록을 갱신했다. `check_docs.py --date 2026-10-27`은13개 모두 통과했고 별도 전수 감사도13개·UTF-8·로컬 링크·색인/전체목록·설정 JSON8개 통과다. 실제 브라우저 시각 검증은 이번에도 수행하지 않았으며 직전 도구 연결 종료를 다른 GUI/입력 방식으로 우회하지 않았다.

### 재현 명령

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-27
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py
.\.venv\Scripts\python.exe runs/site-publish/verify_quarter_interval.py --execute --output runs/site-publish/quarter-interval-public-new.json
```

웹 폴더에서 `node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs server/gpu-start.test.mjs components/arena-state.test.mjs components/engine-status.test.mjs`와 `npx tsc --noEmit`을 실행한다. 실제 HTTP4종은 로컬5186 미리보기에만 `run-local-audits.mjs`의 숨김 stdin으로 QA키를 넘겨 실행했다. 키·토큰·방코드는 파일/로그에 쓰지 않았다.

마지막 API 명령은 격리 QA방과 고정 타일 선택을 만들며 모델 추론 명령이 아니다. 기존 보고서를 덮지 않도록 새 출력 경로를 사용한다. 모델/임계값/학교 사용·새 학습은 변경0이다. 이번 선택 제한 수정으로40% 달성·학교 성능·ONNX/Pi·기존 OS 실클릭을 확인한 것은 아니다. 실제 브라우저의125ms 갱신과 물리 부스 기기/네트워크 리허설은 미검증이다.

## 구현 완료 이력: GPU 예약 후 공통 출발·버전9 (2026-10-27)

이 절은 이번 선택 간격 변경 직전에 완료한 버전9 기록이다. **여기의1초 정책과 측정은 당시 이력이며 현재 제한은 위0.25초가 우선한다.**

- 시작 요청은 `queued` 티켓으로 전환하고 round/질문/사진/startAt을 공개하지 않으며 타이머0이다. PC가 관측 등록순 FIFO로 공유 GPU 예약을 얻은 뒤 `begin`이 약2초 뒤 공통 출발을 확정한다. 추론 함수가 반환하면 선택/제출 전에 예약을 해제해 다음 방 준비와 겹친다. 단일 실행기의 등록순이며 서버 전역 공정성이나 모든 지연의 동일함을 보장하지 않는다.
- requestId·roundId·roundNumber 프로토콜2 heartbeat와 revision/티켓 CAS를 구현했다. 취소·오류·15초 생존 만료·120초 대기 상한은 lobby로 되돌리고 수동 재시작한다. 첫 신규 엔진의 명시적 지원false lobby만 부트스트랩하고 첫2 heartbeat로 지원을 확정한다. 구형 엔진은 기존 판을 마칠 수 있지만 새 예약 출발은 거부한다.
- `0002_mysterious_ravenous.sql`5개 컬럼을 추가하고 기존0000/0001을 유지했다. 로컬0002는한번 적용했고 운영 API와 실제 CUDA로 새 schema를 확인했다. Python154개·Node72개·localhost HTTP4종·타입/구문 검사가 통과했다.
- 실제 CUDA의 로컬/공개 각각A두판+B한판은 모두17항목 passed=true다. 대기 중 무문제/타이머0·경기중 GPU 대기0·추론후 예약해제·같은 방/코드/표시 권한·새 참가자 재준비·라운드별 예측/제출1회·표시/모델 일치를 확인했다. 로컬 모델1회 로드14.922초·생존866샘플, 공개18.047초·351샘플이며 준비후 끊김 관측0이다.
- 공개B1은 예약 대기13.250초(상태 HTTP10.843초 포함), 요청→공통 시작19.663초(공통2초 포함), 모델 함수0.907초였다. schema2는 모델 함수와 상태HTTP를 분리하며 기존v8 지표와 속도를 직접 비교하지 않는다. 대기를 타이머 앞으로 옮긴 결과이며 부스 전체 대기 단축 보장이 아니다.
- 로컬/공개 각3판 모두오답·90초 timeout으로 정상 종료했다. 이24사진 재사용 기능검사를 일반 정확도0%로 해석하지 않는다. 로컬1선택·공개2선택으로 연속 선택 간격 표본0이며 이 실행으로1초 실측을 주장하지 않는다.
- 로컬 CUDA 보고서 (로컬 산출물: `runs/gpu-start-local-v1/verification.json`), 공개 CUDA 보고서 (로컬 산출물: `runs/gpu-start-public-v1/verification.json`), 버전9 배포 기록 (로컬 산출물: `runs/site-publish/gpu-start-release.json`), 두 호스트 HTTPS 검사 (로컬 산출물: `runs/site-publish/gpu-start-release-http.json`)가 근거다. v9 commit `774cf6edfc54469253f2fbb343176fdf2d123581`, deployment `appgdep_6ae02fab01508191ba469fa974db7b53`, 환경revision3, succeeded다.
- 당시 운영 엔진49404→52164→51904는 CUDA 로드11.812초에 완료했다. 이PID는 과거 기록이며 재사용될 수 있어 현재 생존 근거로 쓰지 않는다. 운영 엔진은 아래 최신 가동 기록을 따른다. 재시작은 메모리 토큰을 잃으므로 업데이트 때 새 방으로 한 번 연결하고 정상 참가자 교체는 같은 방을 유지한다.
- queued UI의 실제 렌더링/취소는 브라우저 도구 연결 종료로 확인하지 못했다. 다른 입력도구로 우회하지 않았다. 서버 취소·UI 논리 테스트와 실제 화면 검증을 구분한다.

이후 절은 이전 작업 이력이다. 버전·미구현 제안·1초 정책·기기/PID 설명은 해당 당시를 기준으로 읽는다.


## 이전 상담: 공유 GPU 대기와 대결 공정성 (2026-10-27)

- 사용자의 지적은 현재 구조에서 타당하다. `run_one_room`은 playing과 공통 startAt 이후9사진을 받아 `SharedModels.infer`의 단일 잠금을 기다린다. 따라서 한 방 AI의 자원 대기가 그 방 타이머에 포함된다. 그 방 인간은 상대 AI가 늦어지는 이점을 받을 수 있다. A/B 동시 동작 통과를 동일 응답시간/공정성 보장으로 해석하지 않는다.
- 과거 공개v8 A1/B1의 gpu_queue_seconds는0.391/2.250초였다. 단, 타이머는 잠금 획득 후 active() HTTP까지 포함하고 inference_seconds도 predict 뒤 active() HTTP를 포함한다. 정확한 순수 잠금 대기/ML 계산을 분리 측정한 값은 아니며 이번에는 새 측정0이다. 이후 분리 측정이 필요하면 잠금 획득 직후·모델 반환 직후·상태 확인을 각각 기록해야 한다.
- 미구현 제안: 인간의 시작 요청→GPU 예약 대기 표시→차례가 오면 해당 방의 인간/AI에 공통 카운트다운/시작 시각 확정→공개 후 사진 추론→GPU 해제다. 기존 방의1초 간격 선택/제출과 다음 방의 준비/추론은 독립적으로 겹칠 수 있다. GPU 경합 대기를 타이머 전에 옮기는 방안이며 현장 전체 지연을 같게 보장하는 것은 아니다.
- 이 제안은 구현·배포·검증하지 않았다. 현재 버전8의 타이머/시작/API/잠금은 그대로다. 미리 답을 추론하거나 사후에 경기 시간을 고쳐 공정성을 주장하지 않는다. 학교·가중치·임계값·1초·40%·Pi 정책도 바꾸지 않는다.

읽기 전용 재현은 `SharedModels.infer`의 잠금/시간 기록과 `run_one_room`의 playing 이후 호출 순서를 대조한다. 과거 실행 근거는 runs/desktop-liveness-public-v1의 lane-A-game-1.json/lane-B-game-1.json이다. 이번 코드·새 추론/성능시험·배포·운영 프로세스 조작은0이다.

이전 작업 검토(11/02): 관리13개 전체를 분담 재독·갱신해 실행 가능성과 공정성 한계를 구분했다. 미구현 GPU 예약 출발과 현재 버전8 동작·과거 측정 구간의 HTTP 포함을 명확히 기록했다. `check_docs.py --date 2026-10-27`과 별도 전수 감사에서 관리13개·UTF-8·로컬 링크·문서 목록·설정 JSON8개가 통과했다.

## 이번 확인: HTTPS 통신과 두 세션 용량 문의 (2026-10-27)

- 이번은 설명·문서 갱신과 읽기 전용 HTTPS 확인이다. 사이트/코드/모델/추론/배포·운영 프로세스 조작은0이며 아래 버전8 검사 수치를 새 측정이라고 쓰지 않는다.
- 실제 구조는 브라우저 및 PC 엔진→Cloudflare Worker의 HTTPS API와 상태 폴링이다. PC끼리 raw TCP 소켓으로 직접 연결하거나 WebSocket을 상시 여는 코드는 없다. 웹 폴링 기본500ms·엔진 heartbeat3초·유효15초는 유지된다.
- 같은 프로젝트 Python의 urllib로 `https://bot.marulee.dev/?lane=A`를 읽기 전용 조회해 HTTPS200·response.version=11(HTTP/1.1)을 확인했다. Python 경로는 TLS/TCP다. 브라우저의 실제 HTTP버전·도메인의 HTTP/3 협상은 측정하지 않았다. Cloudflare가 HTTP/3/QUIC을 지원한다는 사실만으로 이 사이트의 모든 브라우저가 HTTP/3이라고 단정하지 않는다. [공식 HTTP/3 안내](https://developers.cloudflare.com/speed/optimization/protocol/http3/).
- 같은 엔진은 모델3개를 한 번 로드해 공유하고 A/B 작업을 독립 관리한다. GPU 추론만 단일 잠금으로 직렬화해 모델을 방마다 중복 적재하지 않는다. 다운로드·선택/제출·생존 알림은 방별로 진행한다. 실행기는 하나만 켜고 A/B를 그 콘솔에 연결한다.
- 기존 공개 버전8의 동시 A1/B1 결과가 현재 PC의 두 세션 실행 근거다. A1의 기록된 대기 구간0.391초/추론 구간1.547초, B1 대기 구간2.250초/추론 구간0.844초였다. 두 지표는 잠금 안의 서버 상태 확인 HTTP도 포함하며 순수 GPU 대기/ML 계산 시간은 아니다. 시작~제출은12.156/15.977초로 네트워크·타일 대기를 포함한다. 겹친 추론은 기다릴 수 있으며 모든 유형 조합·현장 장시간 부하/온도·네트워크 성능 보장은 미완료다.

읽기 전용 응답 버전 재현:

```powershell
.\.venv\Scripts\python.exe -c "from urllib.request import Request,urlopen; r=urlopen(Request('https://bot.marulee.dev/?lane=A',headers={'User-Agent':'AlphaCaptchaProtocolCheck/1.0'}),timeout=15); print(r.status,r.version); r.close()"
# 이번 확인 결과: 200 11 (HTTP/1.1)
```

이전 작업 검토(11/02): 관리13개를 분담 재독·갱신하고 HTTPS/폴링과 TCP 계층을 구분했다. Python 응답 버전만 새로 확인했으며 기존 모델 공유·동시 실행 기록으로 용량 질문을 설명했다. 학교/가중치/임계값·40%·Pi/ONNX·기존 OS 입력 상태는 그대로다. `check_docs.py --date 2026-10-27`과 별도 전수 감사에서 관리13개·UTF-8·로컬 링크·문서 목록·설정 JSON8개가 통과했다.

## 현재 결론 (2026-10-27, 버전8)

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
| 로컬 실제 CUDA | 947개 생존 관측, 준비 후 끊김0·새 플래그 확인·same A두판+B한판 passed=true. 모델1회 로드8.766초 |
| 공개 실제 CUDA | 69개 생존 관측, 준비 후 끊김0·모델/표시 일치·same A두판+B한판 passed=true. 모델1회 로드7.063초 |
| 공개 선택·간격 | 선택11회, ACK뒤 다음 전송 간격8개, 최소1.375초. A1/A2/B1 선택(0부터)=[[0, 1, 2], [1, 3, 5, 7], [2, 4, 5, 6]] |
| 브라우저 | localhost 인간1920×1080·AI표시1280×720의 대기 화면 문구/가로 넘침0 확인. 실제 행사 기기/네트워크·새 live격자 크기 재측정 아님 |
| 공개 HTTP | human/bot HTTPS200·컴퓨터 표시 안내·구역 선택·패드 전용 문구 없음 확인 |

로컬 세 문제는 모두 나무≥3,0개 예측·오답·90초 timeout이었다. 따라서 로컬 이번 GPU 검사에는 실제 선택 간격 표본이0개이며 1초 실측 근거로 쓰지 않는다. 공개 세 문제는 모두 사람≥3이었고 선택/제출이 정답으로 종료됐다(A1 12.156초,A2 13.474초,B1 15.977초). 이는 같은24장 공개 시연 은행의 기능 검사이며 정확도100%·유형별40% 달성·학교 성능의 근거가 아니다. 다운로드·GPU 대기/추론·전송/타일 대기·서버 제출 시각을 추론 속도와 구분한다. 생존 관측은 반복 조회 사이0.25초 대기와 HTTP 왕복을 포함한 폴링 샘플이며 실제 관측 간격은 더 길 수 있다. 전체 시간의 무중단 보증이 아니다.

근거: 로컬 생존/모델 보고서 (로컬 산출물: `runs/desktop-liveness-local-v1/verification.json`), 공개 생존/모델 보고서 (로컬 산출물: `runs/desktop-liveness-public-v1/verification.json`), 브라우저 배치 (로컬 산출물: `runs/desktop-browser-qa/layout.json`), 인간 화면 (로컬 산출물: `runs/desktop-browser-qa/human-desktop.png`), AI 표시 화면 (로컬 산출물: `runs/desktop-browser-qa/bot-desktop.png`), 공개 HTTP (로컬 산출물: `runs/site-publish/desktop-release-http.json`). 실제 ML 엔진은 관리자/정답 접근0·OS입력0·학교/학습/튜닝0이다. localhost 서버 채점용 별도 테스트 프로세스만 테스트 관리자 답안을 사용한다.

## 이번 배포·현재 PC 실행기

사이트버전8 **succeeded**: commit `5e05f47c23d13156b28315574b275c09b03277e6`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_358046f965d4819198953a2e3041518f`, deployment `appgdep_6adffa6ea6808191aaaa17cb30798839`, 환경revision3. production build·source push·package·save·publish를 확인했다. 기존 공개 범위·human/bot 도메인·D1/R2·키·0000/0001 migration을 유지한다. 배포 기록 (로컬 산출물: `runs/site-publish/desktop-release.json`)의 URL은 `https://alpha-captcha-arena.duckbearmadecowpig.chatgpt.site`다.

운영용 기존 프로세스는 이번 재조회에서0이었으므로 강제 종료 없이 최신 CLI 안내로 새 콘솔을 시작했다. PowerShell17448→venv11832→base19656의 한 Windows 실행 체인과 CUDA 모델1회 로드8.937초를 확인해 켜 두었다. 시작 기록 (로컬 산출물: `runs/remote-engine/20261027-101330-0bae9e9c/startup.json`), 생존 조회 (로컬 산출물: `runs/site-publish/desktop-current-engine.json`)를 남겼다. 운영 콘솔에 에이전트가 입력한 A/B 코드는0이며 특정 사용자 방 준비/경기 시작은 확인하지 않았다. 위 실제 GPU3라운드는 별도 QA 엔진이며 검증 후 종료한다. 실행기 창을 닫거나 재부팅하면 종료된다.

## 컴퓨터 운영·재현·남은 작업

인간 `https://human.marulee.dev/?lane=A`와 AI표시 `https://bot.marulee.dev/?lane=A`를 컴퓨터 브라우저에 연다. B도 lane=B다. 모델 PC에서 `Start-Alpha-Remote.cmd`를 한 번 켜고 처음에만 인간 방→AI표시 코드→PC 숨김 입력 A/B코드를 연결한다. 이후 결과에서 **다음 참가자 준비 → PC 준비 확인 → 사람이 시작**을 반복한다. AI 표시 화면이 전면에 없어도 OS 커서를 쓰지 않아 인간 마우스를 방해하지 않는다. 기존 열린 화면은 새로고침해 최신 안내를 받는다. 상세 정본은 SETUP이다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
# web/alpha-arena에서:
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs server/state-projection.test.mjs components/arena-state.test.mjs components/engine-status.test.mjs
# 실제 공개 QA 생성·추론·제출; 출력은 새 폴더:
.\.venv\Scripts\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --execute --device cuda --output runs/desktop-liveness-check-new
.\.venv\Scripts\python.exe runs/site-publish/verify_desktop_release.py
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-27
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py
```

이전 작업 검토(11/02): 컴퓨터 브라우저 운영·첫 생존 알림 대기·D1 읽기 시각 경합을 수정해 실제 코드/비동기 회귀/HTTP/로컬·공개 CUDA/브라우저로 검증하고 버전8을 게시했다. 학교 최종 평가 전용·고정 모델·목표40% 미달성·Pi/ONNX/기존 OS 입력 경계를 유지한다. 현장 컴퓨터·모니터 배치/네트워크 리허설과 독립 품질 평가가 남았다. 관리13개 전체를 분담 재독·갱신했다. 문서 최종 점검: `check_docs.py --date 2026-10-27`은13개 모두 통과했고 별도 전수 감사도13개·UTF-8·로컬 링크·최신 CHANGELOG 문서 목록·설정 JSON8개 모두 통과했다.

## 이전 버전7 결론

**사이트버전7을 배포했고 remote A/B는 같은 방에서 다음 참가자를 계속 받는다.** 처음에만 각 인간 방·봇 표시 패드·PC 엔진을 연결한다. 한 판 종료 후 인간이 ‘다음 참가자 준비’를 누르고 PC 준비가 표시되면 다음 사람이 ‘대결 시작하기’를 누른다. 같은 방·코드·engine/viewer 연결과 모델을 유지한다. 한 참가자당 한 라운드이며 자동 연속 시작은 아니다. legacy OS 경로는 기존 새 방 방식이다.

**최신 코드의 사용자용 PC 봇도 켜 두었다.** 표시되는 PowerShell PID38476 → venv Python44732 → base Python42276 체인과 CUDA 모델 1회 로드6.250초를 확인했다. 이는 Windows 가상환경의 한 실행 체인이다. 에이전트는 이 운영용 콘솔에 A/B 코드를 입력하지 않았으며 방별 준비/경기 시작은 아직 확인하지 않았다. 아래 QA의 실제 사진 추론은 별도 검증 프로세스에서 실행했다.

**공개 사이트에서도 재연결 없이 A방 두 판과 독립 B방 한 판을 실제 PC CUDA로 검증했다.** 방/코드/표시 권한 유지·선택 초기화·자동 재준비·라운드별 예측/제출1회·표시 선택 일치·최소1초 선택 간격이 모두 통과했다. 기존 공개 사진24장으로 수행한 연결 검사이며 모델 정확도·40% 달성·학교 성능 검증이 아니다. 물리 Android 태블릿4대 리허설·ONNX/Pi·기존 OS 실제 입력은 미완료다.

## 이전 버전7 변경과 검증 (2026-10-27, 지속 방)

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
| 공개 실제 CUDA | passed=true | 모델 한 번 로드8.594초, A1=[], A2=[5], B1=[]; B1: timeout/winner=None, A1: timeout/winner=None, A2: timeout/winner=None |
| 공개 HTTP | human/bot HTTPS200·원격 안내 통과 | SSR HTML 확인이며 새 브라우저/물리 패드 실측은 아님 |

로컬 근거는 연속 검증 (로컬 산출물: `runs/continuous-booth-local-v1/verification.json`)과 기록된 표시/모델 비교 (로컬 산출물: `runs/continuous-booth-local-v1/viewer-match.json`)다. 공개 근거는 연속 검증 (로컬 산출물: `runs/continuous-booth-public-v1/verification.json`)과 같은 폴더의 세 lane 보고서다. 공개 풀이기는 관리자·정답 데이터 접근0·OS입력0·물리패드0·학교/학습/튜닝0이다. Node의 별도 localhost 서버 채점 검사는 관리자 답안을 사용하는 테스트 전용이며 실제 ML 검증/엔진에는 전달하지 않는다.

## 이전 버전7 배포

사이트버전7은 **succeeded**다. source `483d473ef9d5532303216b1ddfdeda179fe7354a`, saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_42c2bde8e68c81919c4fadbaf152c471`, deployment `appgdep_6adfec3d93d88191842861ff8dc66136`, 환경revision3이다. production build·정확한 source push·package·save·publish와 두 호스트 HTTPS200을 확인했다. 배포 기록 (로컬 산출물: `runs/site-publish/continuous-release.json`), HTTP 확인 (로컬 산출물: `runs/site-publish/continuous-release-http.json`)에 근거를 남겼다. 기존 공개 범위·도메인·D1/R2·키·0000/0001 migration을 유지했다. 아래 버전6과 새 방 운영은 이전 이력이다.

## 이전 버전7 당시 가동 기록과 부스 운영

| 항목 | 확인한 결과 |
|---|---|
| 실행기 | 표시되는 PowerShell에서 최신 `scripts/start_remote_engine.ps1` 실행, 계속 켜 둠 |
| 프로세스 | PID38476 →44732 →42276. 한 Windows venv 실행 체인 |
| 시작 기록 | startup.json (로컬 산출물: `runs/remote-engine/20261027-091218-5af7e178/startup.json`), UTC2026-10-27T00:12:25.5182856Z |
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
.\.venv\Scripts\python.exe -m unittest discover -s tests
# web/alpha-arena에서:
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs server/remote.test.mjs components/arena-state.test.mjs
# 프로젝트 루트에서, 실제 공개 QA방·추론·제출 생성:
.\.venv\Scripts\python.exe scripts/verify_continuous_booth.py --base-url https://bot.marulee.dev --execute --device cuda --output runs/continuous-booth-check-new
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-27
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py
```

이전 작업 검토(GPU 공정성 상담): 같은 방 다음 참가자 요청에 맞춰 서버/UI/PC 지속 세션을 구현·배포하고 로컬 및 공개 CUDA의 A두판+B한판을 확인했다. 운영용 최신 PC 콘솔을 따로 켜 두었고 A/B 코드 자동 입력은 하지 않았다. 관리13개 본문을 분담 재검토·갱신했으며 최종 문서 점검 결과는 아래 기록을 따른다. 목표40%·Android 실4대·학교 최종 평가·ONNX/Pi·OS 입력은 미완료다.

문서 최종 점검: `check_docs.py --date 2026-10-27`은 관리13개 모두 통과했다. 별도 전수 감사도13개로 일치하며 UTF-8·로컬 링크·최신 CHANGELOG 전체 문서 목록·설정 JSON8개가 통과했다. 내용은 팀이 전체 본문을 대조했고 legacy 인간 URL 누락도 교정했다. QA용 로컬 미리보기와 공개 검증 프로세스는 종료했으며 운영용 PC 엔진은 유지한다.

## 이전 후속 정보: Android 태블릿4대 (2026-10-27)

- 사용자 확인값은 **Android 태블릿 네 대**다. 인간A·봇표시A·인간B·봇표시B의 배치와 PC의 `Start-Alpha-Remote.cmd`는 기존 승인 경로를 따른다. 태블릿에서 ML을 실행하거나 물리 터치를 주입하지 않는다. 인간은 직접 화면을 누르고 봇 패드는 PC 모델이 서버에 보낸 실제 선택을 읽기 전용으로 표시한다.
- 운영 브라우저는 Chrome으로 통일하는 것을 권장 기준으로 둔다. 네 대의 실제 Chrome 설치·버전, 기종·Android 버전·해상도·화면 방향은 아직 미확인이다. 앞선 PC 브라우저 viewport 확인을 이 기기들의 실측으로 대체하지 않는다.
- 원격 경로에는 좌표 보정·F8·PC 브라우저 전면 유지가 필요하지 않다. PC ML 엔진을 켜고 각 A/B 방에 연결해야 하며, 패드에서 사이트만 여는 것으로 AI 추론이 시작되지는 않는다. 실제 네 대에서 사진 로딩·인간 제출버튼/봇 상태 표시·방별 선택 동기화·네트워크와 동시 종료를 확인하는 현장 리허설은 남았다.
- 이 Android 기기 확인 작업 당시에는 Markdown만 갱신했다. 당시 새 코드·GUI 조작·배포·추론·정확도/속도 측정은0이었으며, 아래의 CUDA·HTTP·브라우저·게시 결과는 앞선 개발 작업의 보존 이력이다. 이후 사용자 요청으로 원격 엔진을 켠 현재 상태는 위 가동 기록을 따른다. 학교 최종 평가 전용·고정 가중치/임계값·목표40% 미달성·ONNX/Pi 미완료는 그대로다.
- 문서 점검: 이번 갱신 후 `check_docs.py --date 2026-10-27`은 관리13개 통과다. data/models/runs/logs를 포함한 전수 목록도13개로 일치하고 UTF-8·로컬 링크·최신 CHANGELOG 전체 목록·설정 JSON8개 점검도 통과했다.

이전 작업 검토(Android 기기): Android 태블릿4대라는 사용자 답변과 Chrome 권장 기준을 반영했다. 실제 설치·기종·OS·화면·네 대 동시 동작은 미확인이고 PC ML→서버 선택→읽기 전용 패드 구조는 유지한다. 당시 문서 전용 변경을 이전 실측·배포와 구분했으며 관리13개 문서 검사와 별도 감사가 통과했다.

## 이전 버전6 원격 A/B 구현과 검증 (2026-10-27)

- `remote_engine.py`·`run_remote_engine.py`·`Start-Alpha-Remote.cmd`는 PC에 세 모델을 한 번 로드하고 방별 작업 스레드와 하나의 GPU 잠금을 사용한다. A/B의 선택·제출·종료와 새 참가자 코드는 독립이다. 기본 dry-run에서는 모델·방 참가·준비·선택·제출을 실행하지 않는다. 실제 원격 운영에는 `--execute`가 필요하다.
- 인간이 `{mode:remote,lane:A/B}` 방을 만들고 봇 표시 패드와 PC 엔진을 별도 토큰으로 연결한다. 엔진만 선택·제출·생존 알림을 보낼 수 있고 표시 토큰의 쓰기는403이다. 잘못된 레인은 참가 전에409다. 표시 패드의 연결 등록은 실제 화면 로딩·지속 생존을 보장하지 않는다.
- 엔진은 공통 시작 후 공개된9사진을 같은 호스트의 불투명 `/api/photos/UUID` 경로로만 받아 RGB로 디코딩한다. 전송 계층과 모델 입력을 분리해 URL·ID·이름·정답·실제 정답 수·관리 API를 모델에 전달하지 않는다. 이미지 전체를 보여 주도록 원격 화면은 contain 배치다. 기존 OS 화면 캡처 경로와 별개의 승인된 입력 어댑터다.
- 선택 sequence의 재전송은 같은 ACK를 반환하고 변경·중복 타일·1000ms 미만 선택을 거부한다. 제출은 서버에 저장된 선택 집합으로 기존 원자 채점을 호출하며 선택과 제출의 경합도 snapshot CAS로 막는다. 엔진 heartbeat3초/유효15초, 준비 후 시작·상대 정답 즉시 종료·새 참가자 새 방은 유지한다.
- DB는 `arena_remote_rooms` 추가뿐인 `0001_past_rocket_racer.sql`과 새 스냅샷/저널을 추가했다. 기존0000/기존 데이터는 수정하지 않았다. 로컬0001 적용1회 성공, 운영 적용은 Sites 배포가 담당한다. 원격 입력은 사용자 후속 승인 범위이며 legacy의 HTTP 제출 금지는 기존 OS 경로에만 유지한다.

### 실제 로컬 검증

| 검사 | 실제 결과 | 범위 |
|---|---|---|
| Python 전체 | 131개 통과,12.237초 | 원격13개·기존118개. 학습 fixture는 합성 검사이며 새 학습 아님 |
| Node 서버 | 30개 통과,0.790초 | 권한·CAS·1초·생존·기존 채점 회귀 |
| 원격 HTTP | 1개 통과,본문19.126717초/runner19.236777초 | 실제 localhost D1/R2·15초 stale/recover·403/409/429·선택 표시·두 역할 |
| 기존 HTTP | 1개 통과,본문3.088683초/runner8.198929초 | 기존 인간/봇 채점·단일 승자·공유시각 회귀 |
| 정적/환경 | TypeScript·대상UI ESLint·compileall·pip check·Python/PS 구문 통과 | PS1 BOM/CMD ASCII,실제 OS 클릭 아님 |

실제 CUDA 두 방은 검증 보고서 (로컬 산출물: `runs/remote-booth-local-v2/verification.json`), 각 lane 보고서에 있다. 모델은 한 번 로드6.453초, 서버 startAt 차이26ms다. A 건물은 `[0,2,3]`을 선택했고 ACK 뒤 다음 전송까지1.094/1.110초였다(GPU 대기0.109초·추론1.719초). B 나무는0개 선택이었다(대기1.781초·추론4.469초). 두 방 모두 예측1회/제출1회·오답·90초 timeout으로 정상 종료했고 HTTP 표시 상태와 실제 모델 선택이 같았다. 이는 재사용 시연 은행의 연결 검사이며 정확도·40%·학교/Pi 성능으로 일반화하지 않는다.

첫 검사 도구 실행은 제한된 풀이기 transport로 참가자용 방 생성 요청을 보내 거부됐다. 참가자 QA 요청과 풀이기를 분리해 수정한 뒤 위 v2를 통과했다. 실제 풀이기의 허용 경로를 넓히거나 답안 접근을 추가하지 않았다.

별도 실제 CLI+IAB 경기에서는 사람3명이상 모델이 `[7,8]`을 선택했고 브라우저의 체크 두 개와 일치했다.9사진 로딩·모든 봇 타일 disabled·제출 후 오답 안내·시간 종료를 확인했다. CLI 결과 (로컬 산출물: `runs/remote-booth-browser-v1/lane-A-game-1.json`), 1024×768 화면 (로컬 산출물: `runs/remote-browser-qa/bot-landscape.png`), 768×1024 화면 (로컬 산출물: `runs/remote-browser-qa/bot-portrait.png`), DOM 크기 확인 (로컬 산출물: `runs/remote-browser-qa/layout.json`)에 있다.1024×768에서 인간 제출버튼 bottom735·봇 상태 bottom743,768×1024 봇 상태 bottom999,1280×800 봇 상태 bottom775였고 각 scrollHeight는 viewport 높이와 같았다.1280×720의 초기 넘침을 확인해 짧은 화면에도 compact 레이아웃을 적용했다. 브라우저 viewport 검증이며 물리 패드 테스트가 아니다.

### 원격 재현과 운영

```powershell
# 패드4대는 README의 인간A/봇A·인간B/봇B 주소로 접속
.\Start-Alpha-Remote.cmd
# PC 콘솔에 A 코드8자리 또는 B 코드8자리 입력(숨김)
.\.venv\Scripts\python.exe scripts/run_remote_engine.py --help
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/verify_remote_booth.py --execute --device cuda --output runs/remote-booth-check-new
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-27
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py
```

검사 스크립트는 새 QA방 두 개를 만들고 실제 모델로 한 번씩 제출하며, 정답/관리자 데이터는 읽지 않는다. 출력 폴더는 새 경로만 허용한다. 기본 주소는 localhost, 공개 호스트 검사는 `--base-url https://bot.marulee.dev`로 명시한다. 원격 실행은 OS 좌표 보정·F8·전면창이 필요 없으며 기존 OS 실행기와 혼용하지 않는다. 물리 패드4대의 실제 브라우저·네트워크·연결 끊김 복구와 행사 전 운영 리허설은 남았다. 학교·모델·임계값·40%·ONNX/Pi 상태는 그대로다.

### 공개 배포와 실제 PC 연동 결과

사이트버전6은 **succeeded**다. source commit `fb1a661b3258c2cd0e8839bbbd23347201a6b877`, saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_cd2e38219d908191ae59bc2536bfe449`, deployment `appgdep_6adfe389628481919f008ac502f7491b`, 환경revision3이다. production build·push/package/save/publish와 운영 migration이 통과했고 기존 두 도메인·공개 범위·D1/R2·키는 유지했다. 게시 기록 (로컬 산출물: `runs/site-publish/remote-release.json`), 두 호스트 HTTPS200·원격 안내 확인 (로컬 산출물: `runs/site-publish/remote-release-http.json`), 공개 인간 화면 (로컬 산출물: `runs/remote-browser-qa/public-human.png`)을 남겼다.

공개 `bot.marulee.dev`에서도 실제 PC CUDA 두 방 검사를 수행해 공개 연동 보고서 (로컬 산출물: `runs/remote-booth-public-v1/verification.json`)가 **passed=true**다. 모델 한 번 로드7.516초,startAt 차이50ms였다. A 사람3명이상은 `[3,6]`을 선택해12.809초에 정답으로 종료됐고 B 나무는0개 오답을8.679초에 제출한 뒤90초 timeout까지 독립적으로 진행됐다. A 선택 ACK 뒤 다음 전송 간격은1.375초였고 두 표시 클라이언트가 모델 선택과 같았다. GPU 대기/추론은 A3.812/0.828초,B0.437/3.250초다. 실제 처리·다운로드·대기·네트워크를 포함한 서버 제출 시각이며 추론만의 속도와 구분한다.

공개 검사는 원격 코드와24장 문제은행 연결을 확인한 두 문제뿐이며 성공률50%나 목표40% 달성의 근거가 아니다. 당시 학습·임계값/전처리 튜닝·학교·관리자/정답 데이터 접근·OS 입력은0이었고 물리 패드4대는 사용하지 않았다. 그 검증용 PC 엔진과 로컬 미리보기는 종료했으며 공개 배포는 유지했다. 이후 사용자가 켜 달라고 요청한 현재 운영용 엔진은 위 가동 기록처럼 별도로 실행해 유지한다.

관리 Markdown13개를 전부 재검토·갱신했고 `check_docs.py --date 2026-10-27`은13개 통과했다. data/models/runs/logs를 포함한 전수 목록도13개,UTF-8·로컬 링크·최신 CHANGELOG 전체 문서 목록·설정 JSON8개 구문 검사도 통과했다.

## 이전 운영안 상담 기록 (구현 전)

| 자리 | 인간 패드 | 봇 패드 | AI 실행 제안 |
|---|---|---|---|
| A | A방 생성·시작·직접 선택 | A방 모델의 선택 과정 표시 | 이 PC의 A 경기 세션 |
| B | B방 생성·시작·직접 선택 | B방 모델의 선택 과정 표시 | 이 PC의 B 경기 세션 |

- 서버는 roomId별 경기이므로 별도 A/B 방을 만들 수 있는 구조다. 다만 `arena.tsx`의 selected는 탭 안의 Set이며 제출할 때만 tileIds를 보낸다. 공개 상태에 선택 집합은 없으므로 현재 다른 패드에는 선택 과정이 복제되지 않는다.
- `joinRoom`은 방당 bot 최초 참가만 허용한다. PC 실행기와 봇 패드가 각각 새 참가 요청을 보내면 두 번째는409다. 엔진 연결과 읽기 전용 표시 연결을 분리하는 설계가 필요하다. 역할 토큰 단순 공유를 운영 해결책으로 채택하지 않았다.
- 현재 PyAutoGuiScreen은 전면창·OS 스크린샷·전역 마우스를 쓴다. 같은 PC에서 runner 두 개를 켜면 커서와 전면창을 공유하므로 독립 병렬 운영이 보장되지 않는다. PC 모델 공유·방별 독립 화면/입력과 실제 선택 이벤트 표시를 제안했으나 입력 어댑터 변경은 미확정이다.
- 기존 최소1초 선택 간격·RGB만 ML 입력·정답 비공개·경기별 첫 완벽 정답 종료는 유지할 제안이다. 모델은 PC에 두고 패드는 웹 표시를 맡길 수 있으나 현재 원격 선택/제출 경로는 없으며 기존 OS 입력을 HTTP 제출로 바꾸지 않았다.
- 구현 후 먼저 한 쌍, 다음 실제 패드4대에서 동시 출발·서로 다른 방·상대 종료·연결 끊김·선택 간격·GPU 대기/네트워크 시간을 확인해야 한다. 두 경기 처리 성능은 미측정이다. 사용자의 내일은 클라이언트 날짜 기준10/28 운영 계획으로 해석했다.

이번 검토는 읽기 전용 소스 조사와 문서 변경뿐이다. 기존 Python118개·게시버전5는 이전 결과이며 이번에 재실행하거나 새 게시하지 않았다. 재현은 `rg -n 'selected|setSelected' web/alpha-arena/components/arena.tsx`, `rg -n 'bot_token_hash|bot_already_connected' web/alpha-arena/server/service.ts`, `rg -n 'class PyAutoGuiScreen|screenshot|api.click' src/alpha_captcha/booth_bot.py` 및 아래 문서 점검 명령이다. `check_docs.py --date 2026-10-27`은13개 통과했고 별도 전수 목록13개·로컬 링크·UTF-8·최신 CHANGELOG 목록·설정 JSON8개도 통과했다.

## 이전 클릭불가 진단·로컬 실행 경로

- 조사시점 로컬봇0·실측config0이었고 웹ready는역할의수동버튼상태뿐이었다. 기존인간화면은이미인간승리56.92초인완료상태여서동일방재시작이아닌새방이필요하다. 이는AI실행/속도측정결과가아니다.
- `Start-Alpha-Bot.cmd` → `scripts/start_booth_bot.ps1`로사용자가실행한다. 최초에는 `calibrate_booth_bot.py`가F8로격자좌상/우하·제출중심·정적질문영역좌상/우하5점을직접기록한다. 주모니터·봇전면·F11전체화면·OS/Chrome100%·제출까지보임이기준이다. 자동클릭/키주입/캡처가없는사용자조작보정이며Esc/실패시기존설정을보존한다. 명시교체는백업후저장한다. 아직실제 `.local.json`을작성하지않았다.
- 실행기는새인간방코드를받고CUDA3모델을로드한뒤직접봇참가·봇화면열기·보정전면창/화면범위확인후 `--ready`를전송한다. 웹봇에서먼저참가하면409중복이므로새방에서실행한다. 한참가자한판이며다음참가자는새방/실행이다. 실제모델출력만쓰고최소1초타일규칙·첫정답즉시종료·학교정책은그대로다.
- Python은미보정실행을모델/GUI초기화전에거부하고 모델실패/중복참가/전면창실패를단계별한국어안내와비밀값없는보고서로정리한다. 자동ready는지속heartbeat가아니며실제9사진로딩/클릭성공을보증하지않는다. 실행후에도봇창전면이필요하며인간은패드에서시작하는운영을기준으로한다.
- 웹UI는 '봇화면준비/진행중'으로바꾸고 '이 화면만 열어서는 AI가 클릭하지 않습니다. PC에서 로컬 봇 프로그램을 실행하세요.'를표시한다. API/schema·채점·사진·격자/질문/제출배치는바꾸지않았다.
- Chrome확장DOM에서 viewport1920×855/DPR1,격자(660,268,600,600),제출버튼top-left(1110,883.5)/150×44를읽었다. 제출중심(1185,905.5)이현재viewport밖이므로물리좌표로가정해실행하지않았다. 이는CSS측정이며OS좌표보정이아니다. 이후네이티브Chrome의URL확인을도구가하지못해ComputerUse가중단됐다. 그뒤다른UI/입력도구나PyAutoGUI로우회하지않았다.
- 합성startup7개·보정6개를추가해 **전체Python118개22.359초통과**, compileall·pipcheck·두CLI help통과다. WindowsPowerShell5.1 Parser구문검사만통과했고PS1은UTF-8BOM으로저장했다. 모델실GPU실행·새네트워크ready·실보정·OS클릭/제출은0회이며코드/합성검증과실제완료를분리한다. 웹TypeScript검사도통과했다.

사용자실행: 루트 `Start-Alpha-Bot.cmd` 더블클릭 → 봇URL을주모니터에서직접열고F11/F8보정 → 인간새방코드를실행기에입력 → 모델/화면검사후준비 → 인간시작. 수동보정·실제입력결과를확인하기전에는자동클릭완료로보고하지않는다. 상세절차는 [SETUP](SETUP.md)에있다.

### 이번 게시와 문서 점검 결과 (2026-10-27)

- 준비 상태 안내를 포함한 사이트버전4의 TypeScript·production build·push/package/save/publish가 통과했다. 문서 검토일을 10/27로 갱신한 최종 소스는 commit `14c0859f81e1e5dd8d2a8de1645cd4a1572e42b1`이며, 버전5는 README만 추가 변경하여 동일한 빌드 산출물을 재포장했다. 런타임 산출물 SHA는 두 버전이 같다.
- 최종 saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_1803ff5ca7d48191a17995f70b72e28c`, deployment `appgdep_6adf6c79cd8c819187567cbc7458539f`는 **succeeded**, 환경 revision3이다. 기존 공개 범위·두 도메인·D1/R2·비밀값은 그대로다. 게시 기록 (로컬 산출물: `runs/booth-click-diagnosis/release.json`)을 남겼다.
- 최종 게시 뒤 human/bot 두 호스트 모두 HTTPS200이며 HTML에 로컬 봇 프로그램 실행 안내가 있음을 확인했다. HTTP 확인 (로컬 산출물: `runs/booth-click-diagnosis/release-http.json`)은 읽기 전용 GET 검사다. 도구 중단 후 브라우저 재확인·실보정·ML 실행·타일 선택·제출은 하지 않았다.
- `scripts/check_docs.py --date 2026-10-27`은 **관리13개 통과**다. 별도 전수 목록도13개로 일치하고 로컬 링크·UTF-8·최신 CHANGELOG 전체 문서 목록·설정 JSON8개 구문 검사도 통과했다. 새 Markdown은 없고 문서 본문은 팀이 직접 재검토했다.

## 이전 후속 작업: 공개 웹사진 적용

사용자 요청으로 Commons 공개API에서44개 후보를 내려받아 RGB를 검토하고24개를 확정했다. **24장·6,063,549bytes·24원본그룹/해시, CC0 11장·Public domain13장**이다. API표시뿐 아니라 사진 설명 원문/revision/권리템플릿을 두 에이전트가 나눠 확인했다. 건축물만PD이고 사진은CC-BY-SA인 혼합사례는 제외했다. 출처/저자/사용근거/원본ID/변환/SHA와 라벨은 `data/booth/public-web-v1/bank.json`, `provenance.json`, `license-review-summary.json`에 있다. JPEG전체프레임 재인코딩으로EXIF/GPS/comment를 제거했고 원본/연속촬영의 중복후보는 제외했다. 단일 AI시각라벨 검토이며 독립 사람 검수를 완료한 것은 아니다.

| 웹 조건 | 양성그룹 | 음성그룹 | 미확인 | 운영 출제 준비 |
|---|---:|---:|---:|---|
| 사람3명이상 | 8 | 11 | 5 | ready |
| 나무3그루이상 | 9 | 11 | 4 | ready |
| 건물 존재 | 8 | 9 | 7 | ready |
| 연못 존재 | 7 | 17 | 0 | ready |

- 공개은행용 `scripts/import_public_booth_bank.py`를 추가했다. 공개승인·비학교·CC0/PD·파일경계/SHA/Pillow/라벨을 검사하고 기본dry-run·실행시stdin키·관리자헤더redirect금지다. 관계그룹은 보존하고 은행 전체에서 같은 그룹을 무조건 거부하지 않는다. 기존 로컬Kaggle importer는 운영업로드를 계속 금지한다.
- 실제 등록 (로컬 산출물: `runs/site-publish/public-bank-upload.json`)은 **verified24/uploaded24/alreadyPresent0/completedtrue**다. 새학습0·모델튜닝0·학교0이며 원본Kaggle134장/v1/test/나무모델프로필은 변경하지 않았다. 새사진을 목표40%나독립정확도 근거로 쓰지 않는다.
- 운영 서버 출제 검사 (로컬 산출물: `runs/site-publish/public-photo-rounds-verification.json`)는 격리QA방7개 요청 중 네 유형을 모두 확인했다. 유형당9사진이 실제HTTP/디코드/SHA·원본그룹9개를 만족하고 양호스트의 startAt/tiles가 같으며 정답개수 범위·비공개필드 경계를 통과했다. 정답제출·모델·마우스는 실행하지 않은 서버검사다.
- Chrome 확장으로 별도QA방을 생성·시작해 실제 사진9장이 모두 loadedtrue/자연크기>0이고 타이머가 흐름을 확인했다. 브라우저 검사 (로컬 산출물: `runs/site-publish/public-photo-browser-verification.json`)와 전체 화면 (로컬 산출물: `runs/site-publish/public-photo-browser-full.png`)을 저장했다. **답안선택0·제출0·ML봇실행0**이며 기존 사용자대기실은 시작하지 않았다. 과거URL검증실패를 우회한 것이 아니라 이번 턴의 정상 Chrome확장 연결이다.
- 공개사진 importer 경계테스트6개를 추가해 **전체Python105개 통과(12.020초)**, compileall·pipcheck 충돌없음을 확인했다. 데이터등록·사진표시 성공을 모델정확도/실클릭 완료로 합치지 않는다.
- 기존 ADMIN_KEY를 동등한 새 비밀값으로 갱신해 native환경revision3에만 보관하고 기존 소유자설정은 유지했다. 이전값을 파일에서 복구하거나 새키를 인자/로그에 쓰지 않았다. 기존 사이트버전2의 환경재적용 배포 `appgdep_6adf5a88c27c8191b17bb2f16bc4c575`는 succeeded였다. 사진은 R2/D1에 있으므로 원본이미지/정답은행을 소스/빌드압축에 넣지 않는다.
- 최종 문서소스동기화 **사이트버전3 게시 succeeded**: commit `f4898b7f0f046bd8a4b45eca22bed1d2c62d8461`, saved version `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_edbeb4b24f5081918f58c6e2831a1f0d`, deployment `appgdep_6adf5dd1e40c8191a061386f6a722977`, 환경revision3. 웹변경은 README뿐이고 런타임/출제규칙은 이전버전과 같다. production build·push/package/save/publish가통과했으며 ML calibration v2와는무관하다.
- 버전3 배포후 인간/봇HTTPS200·관리자status200/photoCount24/4종ready를 재확인해 D1/R2사진 유지까지 확인했다. 기록은 최종 게시 확인 (로컬 산출물: `runs/site-publish/public-photo-release.json`)이다. 검증용 브라우저탭은 닫았고 원래 사용자 대기실은 미시작 상태로 남겼다.

## 이전 웹 초기 경기·사진 계약

- 4종 무작위: 사람3명이상(정답2~4), 나무3그루이상(3~4), 건물/연못 존재(각2~4).
- 같은3×3 사진·순서를 제공하고 봇 준비 후 인간 시작으로 약2초 뒤 공통 startAt을 사용한다.
- 한 참가자 한 판. 먼저 완벽한 선택 집합을 제출한 역할이 승리하고 서버는 즉시 종료한다. 오답은 수정·재제출하며 시작 시각/타이머는 그대로다. 동시 정답 요청도 단일 승자로 확정하고 종료 후 요청은409다.
- 화면은500ms 폴링/네트워크 뒤 공통 result.finishedAt/elapsedMs로 정지한다. 다음 참가자는 새 방·새 연결 코드다. 90초 제한은 미확정 운영 가안이다.
- 관리 /admin의 Sites 소유자 로그인 또는 비공개 운영 키로 사진을 등록한다. 정확 수/나무>=3/미확인, 건물·연못·원본 그룹·출처를 기록한다. 사람/건물/연못 최소4P7N, 나무4P6N 독립 그룹이 필요하고 준비 전 시작을 거부한다.
- 정답·실제 정답 수·원본 파일명/ID·라벨은 서버 전용이다. 공개 사진은 불투명 ID이고 시작/만료/현재 라운드/활성 상태를 검사한다. 학교 등록도 학습 허가가 아니며 모델 고정 후 최종 평가 전용이다.

## 배포·도메인

공유 Site ID는 appgprj_6ade37995018819184a42c88bb0fde7c다. [인간](https://human.marulee.dev)·[봇](https://bot.marulee.dev)·[관리](https://human.marulee.dev/admin)와 [기본 게시 주소](https://alpha-captcha-arena.duckbearmadecowpig.chatgpt.site)를 사용한다. Cloudflare에 기존 충돌 없는2CNAME(DNS only)·검증TXT4개를 만들었고 두 도메인은 native status/provider/SSL 모두active다. 기존 marulee 터널/다른 DNS는 변경하지 않았다. 실제 HTTPS/API 응답·최종 게시 버전은 아래 최종 점검 결과로 별도 기록한다.

이전 사이트 게시 버전2가 succeeded였다(ML calibration v2와 별개). source commit은 `53040210b7570695eacbaa996a182e4ef19aee7d`, saved version은 `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_0be4bc30f4588191af8c7976d4dcc8a8`, deployment는 `appgdep_6ade402240008191a656805b9ba2fcef`다. 당시 source helper로 Node18개·TypeScript·production build를 순차 통과한 뒤 push/package/save/publish했다. 현재 공개사진은 위 후속 등록과 환경revision3을 따른다.

사진등록 전 버전2의 공개 HTTPS/API8검사 (로컬 산출물: `runs/site-publish/public-http-verification.json`)는 당시 모두 통과했다. 인간/봇/기본 주소 GET200, human 방생성201→bot호스트 참가200→준비200→human공유상태GET200, 당시 빈은행 시작409 `bank_not_ready`다. 현재는24장등록/ready/사진출제를 위 보고서로 확인한다. 토큰·방코드/ID는 메모리에서만 쓰고 보고서에 저장하지 않았으며 기본PythonUA403과 명시UA200 차이도 기록했다.

실제 Python `PublicRoomSession`도 정직한 식별값 `AlphaCaptchaBoothBot/1.0`을 명시하도록 수정하고 공개 bot 호스트의 참가·상태 조회를 통과했다. 봇 연결 기록 (로컬 산출물: `runs/site-publish/python-bot-http-verification.json`)은 인간 방생성201·같은 방 참가·공개 상태3필드(`phase/roundId/startAt`)만 보존함을 확인한다. 준비/사진/정답/제출/관리 API·모델·OS 입력은 실행하지 않았다. 이 수정은 루트 Python만 바꾸므로 웹 게시 버전2와 동일하게 연동된다. 요청 헤더·토큰 범위의 합성 테스트1개를 추가했다. 브라우저 UI/운영 사진 경기 성공은 이 네트워크 검사의 범위가 아니다.

운영 DB/R2와 로컬 .wrangler/state는 분리된다. 로컬Kaggle34장(2,921,524bytes)은 운영에 올리지 않고 별도 공개24장만등록했다. 운영자 소유자로그인·수동사진등록UI는 아직미검증이며 이번관리자API24/24 등록과 구분한다.

## 실제 ML 저장 RGB 연결 검사

v1 사람 검출은 SSDLite320 MobileNetV3 Large, 건물/연못은 MobileNetV3 Small이다. **YOLO는 사용하지 않았다.** 기존 체크포인트/프로필/원본/split은 보존했다. tree 존재로 수를 지어내지 않고 별도 Grounding DINO Tiny 공식 사전학습 후보를 연결했다. 프로젝트 추가 학습은 없고 고정 revision/hash/prompt/임계값은 SETUP/ARCHITECTURE에 있다. 가중치689,359,096bytes, transformers4.57.3/safetensors0.7.0을 .venv에 추가했고 기존 CUDA torch/torchvision은 유지했다. pip check는 충돌 없음이다.

예측 전에 seed20261026으로4개 시연 격자를 고정하고 모델에는 각192px RGB9타일만 전달했다. 정답 은행은 평가기만 읽었고 정답 수로 선택을 채우지 않았다. 보고서는 실제 결과 (로컬 산출물: `runs/booth-model-smoke-v1/report.json`), 격자/사전계획은 같은 폴더다. 모델 로드는8.904초다.

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

이전 웹게시 단계의 ChromeURL확인실패는 당시중단이력이며 같은턴에우회하지않았다. 이번에는 Chrome확장으로 정상연결해 실제사진9장과브라우저스크린샷을 확인했다. **ML봇의OS캡처·타일클릭·제출0회, 물리좌표보정·실제클릭간격·소유자로그인은 미완료**다. 브라우저렌더/모의콜백/저장RGB/API 성공을 ML실제입력 성공으로 대체하지 않는다.

## 현재 검증과 남은 작업

- 클릭 불가 진단 후 전체 Python118개가 통과했다(22.359초). 이전105개에 시작 절차7개와 사용자 보정6개를 추가했다. 모델·화면은 합성 어댑터로 검증했으며 실제 OS 입력 성공을 뜻하지 않는다.
- 이전 웹게시때 로컬D1/R2 HTTP통합1개가 통과했다(본문3.270711초/runner8.976320초). 권한·동시성·오답재제출·단일승자·공통종료·재시작거부를 확인한 서버채점검사다. 이번 원격4유형/사진검사는 위 별도보고서이며 ML풀이가 아니다.
- 이전 웹소스 Node18개·대상UI ESLint0/0은 보존했다. 이번에는 준비 상태 문구 수정 후 TypeScript와 production build를 통과했고 compileall·pip check·두 CLI help·WindowsPowerShell5.1 구문 검사를 확인했다. 의존성과 데이터·모델은 변경하지 않았다.
- 이전 웹작업 때 CUDA 저장 RGB·고정 나무 가중치 추론을 실행했다. 이번 클릭 불가 진단에서는 실제 모델 추론·학습·튜닝과 OS 클릭을 실행하지 않았다. 학교0·v1 재튜닝0·전역 Python/드라이버/OS 변경0이다.
- 관리 Markdown13개를 다시 읽고 검토일과 이번 진단 결과를 갱신했다. `check_docs.py --date 2026-10-27`은13개 통과했고, data/models/runs/logs를 포함한 전수 목록·UTF-8·로컬 링크·최신 CHANGELOG 전체 목록·설정 JSON8개도 통과했다. 기계적 점검은 본문 직접 검토를 대신하지 않는다.
- 다음: 운영자 소유자로그인/수동업로드UI 확인, PC 물리보정/실제캡처·ML·1초클릭/제출, 충분한 새Kaggle 개발/선택/audit·4종성능, ONNX동등성, Pi의시리얼/사양/추론/GUI 개별검증, 모델고정 후학교최종평가다. 공개사진등록·9사진표시는 완료했다.

## 현재 재현 명령

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/verify_booth_models.py --device cuda --output runs/booth-model-smoke-new
.\.venv\Scripts\python.exe scripts/run_booth_bot.py --help
.\.venv\Scripts\python.exe scripts/calibrate_booth_bot.py --help
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-27
.\.venv\Scripts\python.exe runs/site-publish/audit_docs.py
# web/alpha-arena에서
node --test server/logic.test.mjs server/storage.test.mjs server/authorization.test.mjs
node node_modules/typescript/bin/tsc --noEmit
node C:/Users/Administrator/.codex/plugins/cache/openai-curated-remote/sites/1.1.2/scripts/build-site.mjs
```

HTTP 검사는 로컬 미리보기·34장 은행·메모리의 ALPHA_ADMIN_KEY가 있어야 실행하며 명령줄/파일에 키를 쓰지 않는다. 상세는 SETUP이다. 모든 출력은 새 폴더를 쓰고 v1/report를 덮어쓰지 않는다.

이전 작업 검토(원격 구현): 2026-10-27 개발 승인 후 원격 A/B·읽기 전용 표시·서버 선택·공유 PC 모델을 구현하고 로컬 HTTP·실CUDA 두 방·실제 브라우저 체크와 화면 크기를 검증했다. 원격 선택과 물리 터치/OS 클릭을 구분하고 모델 실패·목표40%·학교·Pi/ONNX 미완료를 보존했다. 관리13개를 다시 읽고 실제 변경·재현·한계를 갱신했다. 아래는 이전 결과의 보존 이력이다.

## 이전 ML·40% 준비의 상세 이력 (2026-10-22)

**두 제한 학습 기준 모델의 RTX 4070 Laptop GPU 학습·평가와 저장 3×3 격자 ML dry-run을 마쳤다.** 다만 v1은 나무를 과선택하고 연못을 전부 놓친다. 부스용 완료 모델이 아니며 ONNX·Pi·화면 캡처·OS 클릭은 아직 없다. 관리 Markdown은 12개다.

## 10/22 이력: 40% 목표와 평가 준비

사용자는 **정답 4칸·오답 5칸인 3×3 평가에서 유형마다 각각 약 40%의 문제 성공률**을 원한다고 확정했다. 성공은 정답 4칸 선택과 오답 5칸 제외를 모두 만족하는 선택 집합 완전 일치다. 나무·건물·연못·사람 존재와 사람이 2/3/4/5명 이상인 **8개 조건을 따로 보고**하며 실패 조건을 평균으로 숨기지 않는다. 4칸은 난이도 평가 기준이고 실제 부스의 모든 문항이 4정답이라는 확정은 아니다. 약40%의 구체 허용오차는 미정이다.

- [목표 설정](../configs/calibration-target-v2.json)을 추가했다. 현재 상태는 `target_confirmed_not_achieved`다. 목표 설정과 실제 모델 달성은 구분한다.
- `grid_evaluation.py`와 `scripts/evaluate_grids.py`로 기존 RGB 추론 캐시를 검증하고, 고정 seed로 4정답·5오답 격자를 구성해 실제 선택 집합을 채점한다. 정답/모델 예측을 분리하며 상위4개 강제 선택은 없다.
- 캐시는 manifest·이미지 신원/해시·분할/관계그룹·원본 report/체크포인트 해시에 연결한다. 로컬 해시는 일관성 검사이며 서명 없는 캐시가 실제 ML에서 생성됐음을 독립적으로 증명하지 않는다. 이번에는 실제 v1 보고서/예측 파일만 사용했다.
- 두 학습 CLI는 기본적으로 test를 평가하지 않도록 변경했다. `--evaluate-test`를 명시하면 평가한다. API 직접 호출은 기존 v1 호환 기본값 `evaluate_test=True`를 유지하므로 v2 후보 선택에는 반드시 `evaluate_test=False`를 지정한다. 학습 전 프로필·report·체크포인트에 평가 여부를 남긴다.
- 새 데이터 다운로드·라벨 수정·v2 실제 학습·새 GPU 추론·학교 사진 열람·화면 입력은 하지 않았다. v1 체크포인트와 공개 test는 보존했다.

## 실제 검증 자료 점검: 아직 40% 달성 판단 불가

기존 **val 캐시만** 정규화하고 조건별 100개 무재사용 격자를 요청했다(seed 20261022). 모든 조건이 `insufficient_data`, `target_achieved=null`이다. 8개 조건 결과 (로컬 산출물: `runs/calibration-v2/validation-grid-summary.json`)와 자료 충분성 점검 (로컬 산출물: `runs/calibration-v2/data-readiness.json`)에 기록했다. 새 ML 추론이 아니라 기존 픽셀 예측의 재집계다.

| 조건 | val 정답 사진 | val 오답 사진 | 가능한 무재사용 격자 | 이번 채점 |
|---|---:|---:|---:|---|
| 나무 | 8 | 4 | 0 | 분모 0, 성공률 null |
| 건물 | 5 | 9 | 1 | 기존 캐시로 0/1, 일반화 성공률 아님 |
| 연못 | 1 | 7 | 0 | 분모 0, 성공률 null |
| 사람 존재 | 2 | 2 | 0 | 이 중 검출 적격 캐시가 있는 사진은 양성1·음성2; 예측1개 누락 |
| 2명 이상 | 1 | 2 | 0 | 분모 0, 성공률 null |
| 3명 이상 | 0 | 3 | 0 | 분모 0, 성공률 null |
| 4명 이상 | 0 | 3 | 0 | 분모 0, 성공률 null |
| 5명 이상 | 0 | 3 | 0 | 분모 0, 성공률 null |

사람 존재의 알려진 이진 정답은 정확 인원수를 모르는 사진도 포함할 수 있다. 따라서 evaluator의 양성2/음성2와 검출 적격만 집계한 readiness의 양성1/음성2는 기준이 다르다. 캐시 없는 사진은 임의 예측으로 채우지 않는다. 사진/연결 그룹을 반복 조합한 100격자를 독립100문제로 보고하지 않고 재사용 수를 따로 기록한다. 현재 한 개 격자의 0/1도 40% 도달 여부를 판단하기에는 부족하다.

다음은 새 Kaggle 그룹과 양성/음성 주석 보강 → train/선택 val/잠금 audit 분리 → 유한한 학습 예산 후보와 격자 고정 → val에서 40%에 가까운 후보 선택 → 모델 해시 고정 → 미사용 audit 1회 평가다. v1 test·학교 사진·본선 결과로 맞추지 않는다. 조건별 val/test에 양성20·음성25개가 있어야 무재사용5격자부터 만들 수 있지만, 5문제에서2개 성공만으로 실제40%가 검증됐다고 보고하지 않는다. 최종 표본 수·수치 허용오차와 모델 예산은 남은 결정이다.

## ML 단계에서 실제로 한 작업

- Kaggle RGB를 모델 예측 없이 사전 고정 기준으로 AI 시각 검토했다. 원본·기존 split·학교 격리를 보존했다.
- COCO 64장 중 검출 학습/평가 적격 38장을 선정했다. 군중 8장·모호한 18장은 제외했다. 장난감 인물 4→0, 발의 중복 bbox 3→실물 2명 오류를 근거와 함께 정정했다.
- 존재 판별 56장을 검토하고, 기존 heldout의 연못 양성 결핍을 **첫 fitting/모델 예측 전에** 확인해 Places365 14장을 추가했다. 기존 split은 이동하지 않았고 새 14장은 val/test에만 7장씩 배정했다.
- MobileNetV3 Small의 독립 sigmoid 3출력(tree/building/pond), SSDLite320 MobileNetV3 Large의 실제 person 검출·계수를 구현하고 각각 1 epoch 학습했다.
- 모델에는 RGB 픽셀만 입력한다. 조건·n은 결정적 선택 로직에만 사용하며 파일명·정답 manifest·사이트 내부 데이터로 문제를 풀지 않는다.
- 두 체크포인트의 저장 해시와 frozen features/BN 상태 불변을 확인했다. 다시 불러온 두 모델로 저장 격자 9칸을 판별해 좌표/예정 시각까지 출력했다. 실제 마우스는 조작하지 않았다.

## 고정한 제한 학습 v1

| 설정 | 존재 판별 | 사람 검출·계수 |
|---|---|---|
| 구조 | MobileNetV3 Small, 3개 독립 sigmoid | SSDLite320 MobileNetV3 Large, COCO person ID 1 |
| 사전학습 | ImageNet-1K V1 | COCO V1 |
| 실제 train | 41사진·105개 알려진 존재 라벨 | 적격 17사진·37개 사람 box |
| 학습 제한 | 1 epoch·batch 8·최대 train 64·6 step | 1 epoch·batch 2·최대 train 32·9 step |
| 고정/학습 부위 | features와 BN 통계 고정, classifier 학습 | backbone와 BN 통계 고정, detection heads 학습 |
| 학습률 / optimizer | 0.001 / AdamW | 0.0001 / AdamW |
| 입력 | 전체 이미지 letterbox 224, RGB·ImageNet 정규화 | 전체 이미지 letterbox 320, RGB·SSD 내부 정규화 |
| 판정 | sigmoid >= 0.5 | score >= 0.5, 내부 NMS IoU 0.45, 입력 원본좌표 높이 >=8px·면적 >=64px² |
| 모델 선택 | 마지막 epoch 고정, 조기 종료·임계값 검색 없음 | 동일 |
| seed | 42 | 42 |

`configs/limited-baseline-v1.json`과 학습 전 프로필 JSON으로 설정·자료 해시를 기록했다. 현재 v1은 test를 평가했으므로 결과에 맞춰 같은 v1을 재학습하거나 임계값을 바꾸지 않는다. 후속 개선은 별도 버전과 val·미사용 시험 자료를 먼저 정한다. 숨은 지연·임의 오답·선택 누락은 넣지 않는다.

## 검토 데이터와 한계

| 자료 | 전체 기록 | 모델에 사용하는 train / val / test | 상태 |
|---|---:|---|---|
| COCO | 64 | 적격 17 / 3 / 18 | verified 38, 모호 unknown 18, crowd 8 |
| ADE/Places 존재 자료 | 70 | 41 / 14 / 15 | tree P/N/U=44/19/7, building=31/34/5, pond=4/47/19 |
| 통합 검토 manifest | 134 | 원래 split 기준 68 / 19 / 47 | 134 연결 그룹, 중복 SHA 그룹 0·관련 그룹의 분할 교차 0 |

사람 검증 val은 0명 2장·2명 1장뿐이다. 연못 양성은 train 2·val 1·test 1장이다. 모호 라벨은 loss/평가 분모에서 제외했다. 일부 자료의 주석을 음성·0명으로 자동 변환하지 않았다. 단일 AI 시각 검토이며 독립된 사람 검수 완료를 뜻하지 않는다. 유사 장면 검토에서 확실한 교차 중복은 발견하지 못했지만 모든 촬영 계보를 보증하지 않는다.

사전학습 가중치는 이미 대규모 ImageNet/COCO 학습을 거쳤다. 특히 COCO train 자료는 사람 검출기의 사전학습과 겹치므로 처음 보는 사진에 처음부터 조금 배운 AI의 정확도라고 설명하지 않는다. 이 작은 선별 표본의 결과는 학교 사진·부스 전체 성능이 아니다. 학교 사진은 이번에도 열람·학습·개발 평가에 사용하지 않았다.

정본은 `presence-ml-v1.jsonl`, `coco-person-reviewed-split.jsonl`, `development-reviewed-split.jsonl`이며 검토 CSV/근거 JSON도 `data/manifests/`에 있다. 원본 확보 총량은 사진 134장, 선택 원본 502,563,677 bytes(메타데이터/모델 제외)다. 데이터 출처·기준은 [DATASET](DATASET.md)과 [후보 비교](DATASET_CANDIDATES.md)를 따른다.

## 실제 시험 결과: 모델 고정 후 test

| 항목 | 평가 분모 | 결과 | 반드시 같이 볼 오류 |
|---|---|---|---|
| 나무 | 알려진 14사진(양성7·음성7) | accuracy 50.0%, precision 0.50, recall 1.00, F1 0.667 | 14장 전부 양성으로 예측, 음성 7장 전부 오선택 |
| 건물 | 15사진(양성10·음성5) | accuracy 80.0%, precision 1.00, recall 0.70, F1 0.824 | 양성 3장 놓침 |
| 연못 | 알려진 11사진(양성1·음성10) | recall 0/1, F1 0 | 전부 음성 예측. accuracy 90.9%는 음성 편중 결과이며 유효한 연못 인식 성공으로 보고하지 않음 |
| 사람 존재 | 적격 18사진(양성14·음성4) | accuracy 17/18=94.4%, precision 1.00, recall 13/14 | 사람 있는 1장 놓침 |
| 정확 인원 수 | 같은 18사진 | 일치 13/18=72.2%, MAE 0.556명 | 누락·계수 오류 5장 |
| n명 이상 | 같은 18사진 | n=2:17/18, n=3:16/18, n=4:14/18, n=5:16/18 | n별 양성 수가 달라 정확도만으로 비교하지 않음 |

validation 결과도 보고서에 따로 저장했다. 사람 val exact-count 2/3, 존재 val은 나무 F1 0.800·건물 0.889·연못 0이다. 현재 정확도는 인간과의 승률이나 문제 전체 타일 집합 완전 일치율이 아니다. 부스 문제은행 5개·학교 사진·실제 경기 시간은 아직 평가하지 않았다.

## 일부 타일만 정답일 때: 가정상 참고 계산

아래는 목표 확정 전 **2/3/4칸을 가정한 비교 이력**이다. 이후 4정답·5오답을 난이도 평가 기준으로 삼고 유형별 약40%를 목표로 확정했다. 실제 문제은행을 수정하거나 모델에 정답 개수를 제공하지 않았다. 정답 k칸을 모두 선택하고 오답 9-k칸도 모두 제외해야 전체 선택 집합이 맞는다. 단순한 `accuracy^9` 또는 `recall^k`만으로 일반화하지 않는다.

각 타일의 오류가 조건부 독립이고, 현재 Kaggle test의 양성 검출률(TPR)·음성 제외율(TNR)이 새 문제에도 그대로 적용된다고 가정하면 `P(전체 일치 | 정답 k칸) = TPR^k × TNR^(9-k)`다. 아래는 **실제 3×3 평가나 학교 예측 정확도가 아닌 관측 비율 대입값**이다.

| 조건 | test TP / FN / TN / FP | 정답 2칸 | 정답 3칸 | 정답 4칸 |
|---|---|---:|---:|---:|
| 건물 | 7 / 3 / 5 / 0 | 49.0% | 34.3% | 24.0% |
| 사람 있음 | 13 / 1 / 4 / 0 | 86.2% | 80.1% | 74.3% |
| 2명 이상 | 9 / 1 / 8 / 0 | 81.0% | 72.9% | 65.6% |
| 3명 이상 | 4 / 2 / 12 / 0 | 44.4% | 29.6% | 19.8% |
| 나무 | 7 / 0 / 0 / 7 | 0% | 0% | 0% |
| 연못 | 0 / 1 / 10 / 0 | 0% | 0% | 0% |
| 4명 이상 | 0 / 4 / 14 / 0 | 0% | 0% | 0% |
| 5명 이상 | 0 / 2 / 16 / 0 | 0% | 0% | 0% |

인원 조건의 TP/FN/TN/FP는 기존 `person-limited-v1/report.json`의 test `actual_count`·`person_count`를 n별로 비교해 재집계했다. 새 모델 추론·학습·데이터 변경은 없다. 예를 들어 건물 정답 3칸은 `(7/10)^3 × (5/5)^6 = 34.3%`다.

TNR=100%는 건물 음성 5장·사람 존재 음성 4장 등에서 오탐이 없었다는 소표본 관측일 뿐 보장값이 아니다. 이 대입은 낙관적일 수 있으며 0% 역시 향후 모든 사진에서 반드시 실패한다는 뜻이 아니다. 장면·크기·가림에 따라 오류가 함께 발생할 수 있어 독립 가정도 미검증이다. 특히 4/5명 이상은 각각 실제 양성 0/4·0/2로, 전체 사진 accuracy 77.8%·88.9%가 양성 판별 능력을 뜻하지 않는다. 정답/오답 구성과 문항별 출제 비율이 미정이므로 전체 부스 평균 성공률은 계산하지 않는다. 학교 성능과 실제 9칸 성공률은 여전히 미측정이다.

## 체크포인트와 측정 기록

- 존재 판별 모델 보고서 (로컬 산출물: `models/checkpoints/presence-limited-v1/report.json`), 체크포인트 `presence.pt`.
- 사람 검출 모델 보고서 (로컬 산출물: `models/checkpoints/person-limited-v1/report.json`), 체크포인트 `person.pt`.
- 학습 전 프로필: 존재 모델은 `runs/frozen-profiles/`, 사람 모델은 해당 출력 폴더의 `frozen-profile.json`.
- 두 모델 모두 RTX 4070 Laptop GPU에서 실행했다. fit 구간은 존재 0.616초·사람 1.371초이며 프로세스 시작/패키지 import/가중치 다운로드를 포함한 총 작업 시간이 아니다.
- PyTorch peak allocated는 존재 46.69 MiB·사람 58.63 MiB다. GPU 전체 사용량·필요 VRAM 총량으로 해석하지 않는다. 사람 모델 마지막 단독 음성 batch의 loss=0은 표준 SSD의 positive-dependent hard-negative 방식 한계로 남겼다.
- 저장 RGB 격자(`runs/ml-baseline-v1/grid-example.jpg`)를 실제 두 모델로 추론했다. n>=2에서 타일 8 선택·예시 좌표(600,600)·예정 상대시각 0초. GPU 9칸 단일 호출은 0.560초였으며 p50/p95나 Pi 속도 측정이 아니다.
- 격자 ML dry-run 결과 (로컬 산출물: `runs/ml-baseline-v1/grid-inference.json`)는 캡처/마우스/제출을 하지 않았음을 기록한다. 첫 클릭 0초·제출 제외는 여전히 가안/미정이다.

## 검증과 현재 미완료

이전 ML 작업에서 자동 테스트68개와 실제 GPU 학습·평가를 확인했다. 부분 정답 가정 분석 때에는 report 재집계만 수행했다. 이번 목표 반영에서는 격자 평가와 test 평가 분리의 합성 테스트를 추가하고 **전체 82개 테스트를 통과했다(8.165초)**. `compileall` 및 두 학습 CLI의 `--help`도 통과했다. 테스트의 작은 CPU 학습 fixture는 검증용이며 실제 Kaggle v2 학습이 아니다. 이번 실제 자료 실행은 기존 val 예측 캐시의 정규화·8조건 격자 재집계다. 문서 전체 점검 결과는 CHANGELOG에 기록한다. 이전 `pip check` 이후 의존성·패키지 설치는 변경하지 않았다.

다음은 아직 미완료다.

- 연못 미검출·나무 과선택을 해결한 부스 사용 가능 모델. v1은 실제 실패가 드러난 첫 기준 모델이다.
- ONNX 내보내기·PyTorch/ONNX 출력/선택 비교, PC/Pi 공통 Runtime 추론.
- Pi 실제 시리얼 접속·RAM/OS/Python/화면 세션·추론/GUI/입력 성능.
- 화면 캡처·보정·OS 클릭·실제 최소 1초 간격·제출/결과 연동.
- 문제은행 5개 구성·사진 고정/재추첨, 첫 클릭/제출 제한·재시도·승패 등 경기 세부 규칙.
- 목표40% 선택을 위한 충분한 새 Kaggle 자료·고정 v2 후보·수치 허용오차·잠금 audit 격자 평가. 현재 격자 CLI는 val 전용이다.

## 재현 명령

이번 val 캐시 정규화와 건물 격자 점검 명령은 다음과 같다. 출력은 반드시 새 파일명을 사용한다. `runs/calibration-v2/conditions/building_present.json`은 공개 질문만 담으며 채점 정답은 없다. 생성된 기존 결과는 위 링크에서 읽을 수 있다.

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_grids.py adapt-presence --manifest data/manifests/presence-ml-v1.jsonl --report models/checkpoints/presence-limited-v1/report.json --predictions models/checkpoints/presence-limited-v1/predictions-val.json --output runs/calibration-v2/new-val-presence-cache.json
.\.venv\Scripts\python.exe scripts/evaluate_grids.py adapt-person --manifest data/manifests/coco-person-reviewed-split.jsonl --report models/checkpoints/person-limited-v1/report.json --output runs/calibration-v2/new-val-person-cache.json
.\.venv\Scripts\python.exe scripts/evaluate_grids.py evaluate --manifest data/manifests/presence-ml-v1.jsonl --cache runs/calibration-v2/new-val-presence-cache.json --condition runs/calibration-v2/conditions/building_present.json --grids 100 --seed 20261022 --mode disjoint --output runs/calibration-v2/new-building-grid-report.json
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-22
```

새 학습 CLI의 기본값은 test 평가 제외다. 아래 기존 v1 재현 형식에서 test 평가까지 원하면 고정 모델의 명시적 평가에만 `--evaluate-test`를 추가한다. 후보 비교 중에는 이 옵션을 사용하지 않는다.

현재 부분 정답 계산의 예시와 문서 점검은 다음 명령으로 재현한다. 아래 7/10·5/5는 건물 test 보고서에서 관측한 TPR/TNR이며 가정상 계산에만 사용한다.

```powershell
.\.venv\Scripts\python.exe -c "print({k: round(100*(7/10)**k*(5/5)**(9-k), 1) for k in (2,3,4)})"
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-22
```

기존 v1 학습 출력 폴더는 덮어쓰지 않는다. 새 실험 폴더로 실행하더라도 현재 test를 반복 튜닝용으로 사용하지 않는다.

```powershell
.\.venv\Scripts\python.exe scripts/train_presence.py --manifest data/manifests/presence-ml-v1.jsonl --root . --output-dir models/checkpoints/presence-reproduction-new --device cuda --epochs 1 --batch-size 8 --max-train-images 64 --seed 42 --learning-rate 0.001 --threshold 0.5
.\.venv\Scripts\python.exe scripts/train_person.py --manifest data/manifests/coco-person-reviewed-split.jsonl --output models/checkpoints/person-reproduction-new --device cuda
.\.venv\Scripts\python.exe scripts/predict_saved_grid.py --image runs/ml-baseline-v1/grid-example.jpg --device cuda --output runs/ml-baseline-v1/new-grid-result.json
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/check_docs.py --date 2026-10-22
```

전체 설치 버전은 `requirements/windows-py312.lock.txt`, 기존 환경 보고서는 `logs/environment-check.json`이다. 전역 Python·GPU 드라이버·OS·Pi 환경은 변경하지 않았다. 2026-10-28은 임시 개발 목표이며 행사일 확정이 아니다.

ML 단계 검토 기록: 두 실제 1 epoch GPU 학습·평가·체크포인트·격자 픽셀 추론과 68개 테스트를 반영했다. 데이터 검토/모호값 제외, 사전학습·작은 분모, 연못/나무의 실패와 v1 보존을 명확히 하고 ONNX/Pi/OS 입력·학교 평가 미완료를 구분했다.

부분 정답 분석 검토 기록: k=2/3/4 가정 계산과 기존 test 인원 조건 혼동행렬을 추가했다. 소표본의 0/100%·독립/동일분포 가정을 실제 부스·학교 성공률과 구분했다.

이전 작업 검토(40%): 4정답 격자·조건별 약40% 확정 목표, 격자 평가 코드·캐시/출처 일관성 검사와 실제 val 자료 부족 결과를 기록했다. test 자동 평가 제외와 API 호환 기본값, 모델/학교 미변경·목표 미달성을 명시했다. 새 학습이 완료된 것으로 보고하지 않는다.

이전 작업 검토(0.25초 제한): GPU 예약 출발의 구현/버전9·실제CUDA와 최신0.25초 수정의 테스트/게시/가동을 구분해 정리했다. 이전1초/미구현 제안/PID는 역사 기록으로 표시했다. 관리13개 전수 검토와 새 검증 명령을 반영하고 학교/모델/40%/ONNX/Pi·실제화면 미검증 경계를 유지한다.

이전 작업 검토(11/02): 고정 ML 계획1회·서버500ms/250ms 일정·이미지3병렬·신규22/운영46·학교행사제외를 실제배포/HTTP/CUDA/공개사진/DOM 관측과 대조했다. 예정 시각을 실제 HTTP/화면/OS 시간으로 바꾸지 않고 새 정확도를 주장하지 않는다. 관리13개 재독·갱신과 최종 문서/가동 결과를 기록한다.
