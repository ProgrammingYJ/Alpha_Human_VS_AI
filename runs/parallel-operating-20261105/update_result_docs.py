"""Record only completed verification and the newly verified operator startup."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/parallel-operating-20261105"
gpu = json.loads((RUN / "cuda-report.json").read_text(encoding="utf-8"))
live = json.loads((RUN / "live-v1/verification.json").read_text(encoding="utf-8"))
operator = json.loads((RUN / "operator-start.json").read_text(encoding="utf-8-sig"))
if not (gpu["passed"] and live["passed"] and operator["startup_verified"]):
    raise RuntimeError("Do not document incomplete verification as passed")
startup_path = operator["startup_path"]
startup = json.loads((ROOT / startup_path).read_text(encoding="utf-8"))
if startup.get("inference_mode") != "parallel" or startup.get("cuda_stream_count") != 2:
    raise RuntimeError("Parallel CUDA operator not verified")
kernel = gpu["cuda_kernel_profile"]
peak_alloc = max(row["peak_allocated_bytes"] for case in gpu["cases"] for mode in ("serial", "parallel") for row in case[mode]) / 1048576
peak_reserve = max(row["peak_reserved_bytes"] for case in gpu["cases"] for mode in ("serial", "parallel") for row in case[mode]) / 1048576
names = {"building_present": "건물", "pond_present": "연못", "person_count": "사람", "tree_count": "나무"}
table = "\n".join(f"|{' + '.join(names[c['task_type']] for c in case['conditions'])}|{case['serial_median_wall_seconds']:.3f}|{case['parallel_median_wall_seconds']:.3f}|" for case in gpu["cases"])
chain = " → ".join(str(pid) for pid in operator["process_chain"])
section = f"""## 최신 작업: A/B 실제 병렬 추론 적용 (2026-11-05)

사용자가 외부 시험에서 기존 FIFO를 확인하고 병렬 연산을 명시적으로 요청했다. 기존 한 개 GPU 잠금을 기본 경로에서 제거하고 **parallel 독립 슬롯2개·CUDA 스트림2개**로 바꿨다. A/B 각각 사진 준비·카운트다운·추론을 진행하며 다른 레인의 완료를 기다리지 않는다. 모델 가중치 한 세트는 공유하고 processor/tokenizer·입력·진단 상태는 worker별로 분리한다. 읽기 전용 예측에서는 model.to/eval을 반복하지 않으며 해당 CUDA 스트림만 동기화한다. `--inference-mode serial` / PowerShell `-InferenceMode serial`만 이전 FIFO 비교/복구 경로다.

### 실제 검증

- 전체 Python **193개 통과, 15.955초**. 새 병렬 회귀9개와 ML 문맥5개를 포함한다. 두 레인의 begin/사진/RGB 재사용/카운트다운/모델 동시 진입·회차 변경 차단·한쪽 취소/예외 독립·슬롯 반환·250ms·명시적 serial 직렬 검사를 확인했다. CLI 구문/도움말과 PowerShell 파서도 통과했다.
- RTX 4070 Laptop에서 실제 운영 SharedModels의 serial/parallel을 공개 저장 RGB9장씩 두 세트로 비교했다. 사전 고정 네 조건의 **16쌍×각 모드3회**, 합96회 두 작업 실행에서 선택 및 보고 예측 최대 차이0, weights 동일 객체, OOM0이었다. 정답은행·학습·임계값 변경·학교 사진·실제 브라우저/OS 입력0이다. [CUDA 보고서](../runs/parallel-operating-20261105/cuda-report.json).
- 별도 tree/tree Kineto 추적은 **{kernel['kernel_count']:,}개 CUDA 커널, 서로 다른 stream17/21의 실제 커널 겹침 {kernel['distinct_stream_kernel_overlap_seconds']:.6f}초**를 기록했다. CPU 호출 시간만으로 병렬을 추정하지 않았다. 이 한 추적의 GPU busy 합집합은 {kernel['gpu_busy_union_seconds']:.6f}초다. 프로파일러 부하가 있는 추적을 아래 속도 중앙값과 섞지 않는다. GPU50% 고정 분할·모든 커널 동시 실행·모든 조합 단축·지연0 보장은 아니다. [커널 추적](../runs/parallel-operating-20261105/cuda-report-tree-tree-trace.json).
- 전체 비교에서 PyTorch 최대 allocated {peak_alloc:.2f}MiB / reserved {peak_reserve:.0f}MiB. 이는 PyTorch 관측값이며 OS/다른 앱 포함 전체 VRAM이나 장시간 한계 측정이 아니다.
- 공개 human/bot 서로 다른 호스트에서 새 QA A/B 두 방을 만들고 production PC 엔진으로 각 한 판을 실행했다. **A/B가 모두 loading에 도달하기 전 어느 HTTP 표시 역할도 사진 준비 ACK를 하지 않는 게이트를 통과**하여 기존 단일 FIFO의 준비 직렬화가 없음을 확인했다. 각 역할9장 실제 PIL 디코딩·세 역할 준비 뒤 공통 출발·출발 후 모델1회·고정 계획1회·250ms 일정·경기 중 사진 다운로드0·RGB 캐시 재사용·표시 선택과 모델 결과 일치가 두 방 모두 통과했다. 코드는 RAM에서만 처리하며 정답/관리 데이터·URL/토큰 로그0이다. [공개 두 방 보고서](../runs/parallel-operating-20261105/live-v1/verification.json).
- 공개 QA는 A 건물/B 연못이었고 두 방의 startAt 차이255ms, 짧은 모델 호출의 실제 겹침은0초였다. 이 QA는 독립 준비/출발/선택 연결의 증거이며 실제 GPU 동시 실행의 증거는 위 별도 저장 RGB Kineto 추적이다.
- 공개 QA의 표시 역할은 **HTTP/PIL 대역**이다. 실제 외부 Chrome 렌더링/기기·네트워크 리허설·장시간 부하·정확도/40%를 검증했다고 확대하지 않는다. 두 방의 절대 출발은 같을 필요가 없고 각 레인 안의 인간/AI는 공통 startAt을 사용한다. 원격 프로토콜3·500ms 표시 여유·250ms 선택·90초 가안과 같은 방 참가자 교체는 그대로다.

두 작업 합계 벽시계 시간 중앙값(초, 각3회; 전처리/후처리 포함, 네트워크·사진 준비 제외):

|A 조건 + B 조건|serial|parallel|
|---|---:|---:|
{table}

나무+사람 등 일부 조합은 느려졌으며 시간은 입력 사진·GPU 상태에 의존한다. 이번 변경의 확정 결과는 A/B 독립 입장과 실제 동시 연산이다. 11/02 별도 후보 실험 및 11/01의 B10.438초 예약 전 대기는 이전 FIFO 이력으로 보존한다.

### 현재 운영 엔진

수정 적용을 위해 이전 운영 체인43132→17060→38628의 절대 경로/부모 관계를 다시 검사한 뒤 해당 체인만 종료했다. 토큰을 디스크/프로세스 메모리 덤프로 추출하지 않았다. GPU 검사 후 정규 실행기를 새 interactive 콘솔로 다시 켜 두었다. 새 체인은 **{chain}**이며 두 Python PID는 가상환경 실행 체인이다. [새 가동 기록](../runs/parallel-operating-20261105/operator-start.json), [startup]({('../' + startup_path)}).

실제 startup: device=cuda, inference_mode=parallel, 동시 슬롯2, CUDA stream2, 가중치 한 세트 공유, 두 worker 합성 예열 완료. 모델 로드 {startup['model_loading_seconds']:.3f}초 + 예열 {startup['synthetic_warmup']['seconds']:.3f}초 = 전체 {startup['startup_total_seconds']:.3f}초다. 시작 후 경로/부모 관계·생존을 확인했고 계속 켜 둔다. 공개 서버는 기존 v13으로 두 방 병렬을 허용해 재배포/DB/사진/환경 변경이 필요하지 않았다.

**사용자 재시험:** 재시작으로 메모리 토큰이 없어졌으므로 인간 A/B에서 새 방을 한 번씩 만들고 각 AI 표시 창에도 새 코드를 연결한다. 지금 켜 둔 한 콘솔에 `A 실제8자리코드`, `B 실제8자리코드`를 숨겨 입력한다. 에이전트는 사용자 방 코드를 입력하지 않았다. 두 인간 화면에서 함께 시작해 더 이상 앞 레인의 준비/경기 종료를 기다리지 않는지 확인한다. 이후 참가자 교체는 기존과 같이 같은 방에서 다음 참가자 준비를 사용한다. 추가 엔진을 켜지 않는다.

재현(운영 엔진과 동시에 CUDA 검증기를 실행하지 않는다):

```powershell
.\\.venv\\Scripts\\python.exe -X utf8 -m unittest discover -s tests
# 아래 검증은 엔진이 꺼져 있을 때 새 결과 경로로 실행한다.
.\\.venv\\Scripts\\python.exe -X utf8 runs/parallel-operating-20261105/verify_cuda.py --execute --profile --repetitions 3 --output runs/parallel-operating-20261105/cuda-recheck.json
.\\.venv\\Scripts\\python.exe -X utf8 runs/parallel-operating-20261105/verify_live.py --execute --output runs/parallel-operating-20261105/live-recheck
.\\.venv\\Scripts\\python.exe -X utf8 scripts/check_docs.py --date 2026-11-05
.\\.venv\\Scripts\\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-05 --output runs/parallel-operating-20261105/document-audit.json
```

이번 작업 검토: 관리 Markdown13개 전체를 분담 재독하고 최신 parallel 정책·실제 CPU/CUDA/공개 두 방 결과·새 가동을 반영했다. 기존 FIFO 측정은 이력으로 보존한다. 가중치/임계값·사진·학교 미사용·40%/ONNX/Pi/legacy OS 입력 상태는 바꾸지 않았다. 남은 작업은 사용자 실제 외부 컴퓨터 A/B 재시험·연속 참가자/장시간 리허설과 기존 미완료 항목이다. 전체 문서 점검 결과는 아래 완료 기록과 CHANGELOG를 따른다.

"""
status = ROOT / "docs/STATUS.md"
body = status.read_text(encoding="utf-8")
body = body.replace("## 최신 작업: 외부 컴퓨터 시험용 PC 엔진 가동 (2026-11-05)", "## 이전 작업: 외부 컴퓨터 시험용 FIFO PC 엔진 가동 (2026-11-05)\n\n이 절의 PID와 기동은 병렬 업데이트 전 이력이다. 현재 엔진은 최상단의 새 가동 기록을 따른다.", 1)
heading_end = body.index("\n\n", body.index("최종 검토:")) + 2
if "## 최신 작업: A/B 실제 병렬" in body: raise RuntimeError("preserve documented result")
status.write_text(body[:heading_end] + section + body[heading_end:], encoding="utf-8")

docs = ["AGENTS.md", "README.md", "docs/README.md", "docs/SETUP.md", "docs/ARCHITECTURE.md", "docs/DATASET.md", "docs/DATASET_CANDIDATES.md", "docs/EXECUTION_PLAN.md", "docs/INTEGRATION.md", "docs/ROADMAP.md", "docs/STATUS.md", "docs/CHANGELOG.md", "web/alpha-arena/README.md"]
changelog = ROOT / "docs/CHANGELOG.md"
body = changelog.read_text(encoding="utf-8")
heading_end = body.index("\n\n", body.index("최종 검토:")) + 2
entry = f"""## 2026-11-05 A/B 실제 병렬 추론과 운영 엔진 업데이트

- 사용자의 FIFO 시험 제보/병렬 요청을 반영해 기본 SharedModels를 독립2슬롯·공유weights·worker별processor/진단·CUDA2stream으로 바꿨다. 준비/카운트다운도 함께 진행하고 자기 stream만 동기화한다. CLI/PS 기본 parallel, explicit serial 복구 및 startup/round 모드 메타데이터를 추가했다.
- 모델 public serial API는 유지하며 fork_for_inference/fork_for_worker와 readonly 예측을 추가했다. 학습/전처리/임계값·모델 선택/학교/사진 변경0이다.
- 전체 Python193개15.955초 통과, 신규병렬9/ML문맥5·이전serial회귀 유지·CLI/PS 검사 통과. 실제GPU16조건쌍×각mode3회 결과차0·OOM0·weights공유, Kineto44969kernel중서로다른2stream실제겹침0.553852초를 확인했다. 일부조합은느려지며 지연0/50%분할/정확도 보장이 아니다.
- 공개 A/B 새 QA방 각1판에서 양lane loading게이트·각표시9사진PILdecode/3역할준비·공통출발후ML1/plan1·250ms·RGB재사용·표시선택일치 모두통과. 실제외부브라우저/현장리허설과구분한다. 산출물정본은 runs/parallel-operating-20261105/cuda-report.json 및 live-v1/verification.json이다.
- 이전운영체인43132→17060→38628을절대경로/부모검사후업데이트용으로종료하고 GPU검사뒤새운영체인{chain}을켜뒀다. startup parallel2슬롯/2stream·두worker예열·생존검증완료. 토큰메모리전용이므로 사용자새A/B방최초재연결1회가필요하고이후같은방교체다. 새정본 operator-start.json/STATUS를따른다. 서버v13은재배포하지않았다.
- 남음: 사용자외부컴퓨터 A/B재시험·연속참가자/장시간부하, 기존40%/ONNX/Pi/legacyOS입력. 기존FIFO/11/02후보수치는이력으로보존했다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

""" + "\n".join("- " + path for path in docs) + "\n\n이번 작업 검토: 위13개 전체 본문을 분담 재독·갱신했고 새 Markdown은 없다. 실제 변경/검증/미완료·재현 명령을 STATUS에 기록했다. 문서 점검은 최종 완료 기록에 실제 결과로 남긴다.\n\n"
changelog.write_text(body[:heading_end] + entry + body[heading_end:], encoding="utf-8")
print("Recorded completed parallel results in STATUS and CHANGELOG")
