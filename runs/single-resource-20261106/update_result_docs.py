"""Record completed single-mode work; never turn a pending check into success."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "runs/single-resource-20261106"
gpu = json.loads((RUN / "cuda-budget-v2.json").read_text(encoding="utf-8"))
live = json.loads((RUN / "live-v1/verification.json").read_text(encoding="utf-8"))
release = json.loads((RUN / "release.json").read_text(encoding="utf-8"))
operator = json.loads((RUN / "operator-start.json").read_text(encoding="utf-8-sig"))
startup = json.loads((ROOT / operator["startup_path"]).read_text(encoding="utf-8"))
if not (gpu["passed"] and live["passed"] and operator["startup_verified"] and release["status"] == "succeeded"):
    raise RuntimeError("Incomplete verification must not be documented as complete")
if startup["inference_mode"] != "single" or startup["target_gpu_duty_cycle"] != .3:
    raise RuntimeError("Unexpected operator settings")
profile = gpu["profile"]
names = {"building_present": "건물", "pond_present": "연못", "person_count": "사람3명 이상", "tree_count": "나무3그루 이상"}
rows = "\n".join(f"|{names[c['condition']['task_type']]}|{c['unlimited_median_seconds']:.3f}|{c['budget_median_seconds']:.3f}|{c['budget_observed_fraction_max'] * 100:.4f}%|" for c in gpu["cases"])
managed = ["AGENTS.md", "README.md", "docs/README.md", "docs/SETUP.md", "docs/ARCHITECTURE.md", "docs/DATASET.md", "docs/DATASET_CANDIDATES.md", "docs/EXECUTION_PLAN.md", "docs/INTEGRATION.md", "docs/ROADMAP.md", "docs/STATUS.md", "docs/CHANGELOG.md", "web/alpha-arena/README.md"]
section = f"""## 최신 작업: A 단일 운영·협력적 GPU 시간 예산30% (2026-11-06)

사용자는 내일 **11/07(토) A 하나만 운영**하고 CTF/Codex 작업과 PC를 함께 사용하기 위해 A/B 분할 제거와 GPU30%를 요청했다. 이 요구가11/05 병렬 기본값을 대체한다. 현재 웹 기본 주소는 구역 선택 없이 인간/AI 표시 두 역할만 제공하고 내부 A를 유지한다. B 생성·참가는409, 이전 B 조회·행동/현재 사진은410 `lane_disabled`로 차단한다. 기존 A 방/인증·same-room next·사진 준비 프로토콜3과250ms 선택/500ms 여유는 유지했다.

### 적용한 자원 제한과 한계

- 실행기 기본은 `--inference-mode single --gpu-duty-cycle 0.30 --cpu-threads 4`이며 한 작업/한 CUDA stream·모델 weights 한 세트를 사용한다. 8자리코드만 입력하면 내부 A에 붙고 `A CODE8`도 호환한다. single에서 B args/stdin은 모델 로드/HTTP 이전에, 대화형 B 입력은 예열 뒤 방 참가 HTTP 이전에 거부한다.
- 각 모델 청크의 전처리/추론/후처리와 해당 stream 동기화까지의 벽시계 작업시간을 측정하고 `t × (1/0.30 - 1)`을 쉰다. 마지막 청크 뒤에도 쉬고 과거 유휴시간의 버스트 크레딧을 쌓지 않는다. 로컬 취소/heartbeat 상태로 대기를 중단하며 매50ms 대기에 HTTP를 추가하지 않는다. 작업/계획 휴식/실제 휴식·전체 추론/네트워크/서버 선택을 분리 기록한다.
- 수치 보존을 위해 기존 배치인 **존재8+1·사람9·나무1×9**를 유지했다. 가중치·학습량·임계값·전처리·사진/라벨·학교 사용을 바꾸거나 예측/클릭을 조작하지 않았다. SharedModels 직접 API의 parallel/1.0 기본은 기존 호출/테스트 호환용이며 운영 CLI가 single/.30을 전달한다. parallel과 낮은 duty cycle의 혼용은 합산30%가 아니므로 거부한다.
- 이 제한은 **협력적 모델 작업시간 예산**이다. Windows WDDM·RTX4070Laptop에 하드웨어 SM30% 고정 할당을 적용한 것이 아니며 순간 GPU/전체 장치 사용률30% 상한, VRAM 상한, CTF70% 예약을 보장하지 않는다. 개별 청크 처리 중 순간 부하는 높을 수 있다. 전역 전력/클럭/드라이버 및 다른 프로세스는 변경하지 않았다.
- CPU는 해당 Python의 OMP/MKL/intraop4·interop1과 Windows **BelowNormal(16384)** 실제 적용을 확인했다. CPU 코어/전체 CPU 사용률 할당이나 CTF 성능 보장은 아니다. 운영 가동 후 같은 프로세스의 working set은 약1.66GiB라는 한 번의 관측이었으며 RAM 상한이 아니다.

공식 지원 근거: 설치된 torch/cuda/green_contexts.py는 Windows에서 Green Context를 거부한다. [NVIDIA MPS](https://docs.nvidia.com/deploy/mps/when-to-use-mps.html)는 Linux/QNX용이고 [MIG 지원 목록](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html)에 RTX4070Laptop은 없다. [PyTorch memory fraction](https://docs.pytorch.org/docs/2.14/generated/torch.cuda.memory.set_per_process_memory_fraction.html)은 allocator VRAM 제한으로 연산 비율과 다르다. [NVIDIA GPU utilization](https://docs.nvidia.com/deploy/nvidia-smi/index.html)은 별도 샘플 구간/장치 전체 지표다.

### 실제 검사와 GPU 측정

- 최종 전체 Python **210개 통과10.243초**. 신규 예산8개·단일 실행기5개·worker 연결3개와 기존 회귀를 포함한다. 마지막 청크 휴식/유휴 크레딧 없음/취소/예외 동기화·원래 배치 순서/추가 HTTP 없음/슬롯 반환·B 입력 거부/코드 숨김을 확인했다. 기존 dual 입력 테스트는 명시적 parallel/GPU1로 보존했다. 웹 Node **125개 통과·1개 건너뜀(1.683초)**, TypeScript·production build·diff도 통과했다. 별도 전체 HTTP 스위트는 이번에 재실행하지 않았고 아래 실제 single 공개 API 경로로 검증했다.
- 첫 1장씩 분할 실험은 선택4유형이 같았지만 분류 점수가 최대0.000302553 달라 사전 허용오차1e-5를 넘었다. [첫 결과](../runs/single-resource-20261106/cuda-budget.json)는 `passed=false`로 보존했다. 허용오차를 완화하거나 모델을 튜닝하지 않고 원래 배치 크기를 복구했다. 재실행 직전 사용자 실행기 체인26360→3272→32036을 발견해 경로/부모 관계 검증 뒤 업데이트용으로 정지했고, 중복 GPU 실행이 없는 상태에서 재측정했다.
- [최종 CUDA v2](../runs/single-resource-20261106/cuda-budget-v2.json): 사전 고정 공개 RGB9장과 네 조건으로 각 프로필3회, 총24 grid 실행(예산 프로필12회)을 비교했다. **선택 및 보고 점수 최대 차이0·OOM0**, 관측 작업시간 비율 최대29.999102%다. 예산 프로필의 PyTorch allocated 최고1075.72MiB/reserved 최고1154MiB는 해당 실험값이며 하드 VRAM 제한이 아니다.

저장 RGB9장 한 문제의 벽시계 중앙값(초, 각3회; 네트워크/사진 준비/클릭 제외):

|조건|자원 휴식 없음|30% 작업시간 예산|예산 프로필 최대 작업시간 비율|
|---|---:|---:|---:|
{rows}

- 별도 tree Kineto 추적은 {profile['kernel_count']:,}개 커널의 GPU busy 합집합{profile['busy_kernel_union_seconds']:.6f}초/프로파일링 벽시계{profile['profiled_infer_wall_seconds']:.6f}초, 약{profile['kernel_busy_fraction_in_profiled_call'] * 100:.3f}%를 관측했다. 그 호출의 전후처리 포함 작업시간 비율은{profile['cooperative_metrics']['resource_work_fraction_observed'] * 100:.4f}%다. 이 추적의 계측 부하는 위 중앙값에 섞지 않는다. [추적](../runs/single-resource-20261106/cuda-budget-v2-tree-trace.json).
- NVIDIA 전체 장치 샘플273개는 평균23.773%/최고80%, 장치 메모리 최고2125MiB였다. 데스크톱/다른 앱과 휴식 없는 비교도 섞인 값이며 봇30% 하드 제한이나 실제 CTF 동시 부하 검증의 증거로 쓰지 않는다. 실제 CTF 프로그램을 함께 실행한 리허설은 미수행이다.

### 사이트 게시·공개 한 판·운영 엔진

**Sites v15·환경 revision7 게시 succeeded**. source `{release['source_commit']}`, saved `{release['version_id']}`, deployment `{release['deployment_id']}`다. `ARENA_OPERATION_MODE=single`만 추가했고 관리자 두 비밀값 및 `ARENA_SESSION_RESET_BEFORE_MS=1793862306432`를 보존했다. public audience·두 custom domain·D1/R2/활성34사진·과거 경기 데이터 변경0이다. [배포 기록](../runs/single-resource-20261106/release.json). 패키징 전 짧은 소스 credential 만료는 같은 Site의 credential을 갱신해 해결했으며 새 Site/다른 권한을 만들지 않았다.

[공개 single QA](../runs/single-resource-20261106/live-v1/verification.json)는 두 health의 single·B 생성/표시 및 엔진 참가 거부·lane 생략 시 내부 A를 확인하고 새 A 한 방을 실제 PC CUDA/협력적 .30으로 실행했다. 인간/표시 각9장의 실제 PIL 디코딩과 PC RGB 준비·loading 타이머0/문제 숨김·세 역할 준비 후 공통 출발·출발 후 모델1회/계획1회·250ms 일정·RGB 재사용/경기 중 다운로드0·표시 선택과 모델 동일·정상 종료 모두 통과했다. 해당 랜덤 문제의 작업시간 비율은{live['model_budget_metrics']['resource_work_fraction_observed'] * 100:.4f}%였다. bot이 정답으로 끝났지만 **한 판은 정확도나40% 달성 표본이 아니다.** 화면 역할은 HTTP/PIL 대역이며 실제 브라우저 한 판/외부 PC/네트워크 성능과 구분한다. 토큰·코드 기록0이며 원본 파일명/정답·관리 데이터 접근0이다.

[공개 surface](../runs/single-resource-20261106/public-surface.json)는 두 호스트 HTML/health와 각각17개 초기 자산HTTP200, single/protocol3/barrier/250ms를 확인했다. IAB 실제 기본 인간/AI 표시에서 A/B 선택·구역명 제거, 인간 새 방 버튼 활성/AI 빈 코드 입력을 확인했다. 이전 `?lane=B`는 B 종료 안내와 빈 준비실로 전환하고 lane query를 제거했다. GUI에서 답안/시작은 누르지 않았다. [브라우저 기록](../runs/single-resource-20261106/browser-verification.json).

정규 실행기를 새 interactive 콘솔로 시작해 **32140→41944→17664**의 절대 경로/부모 관계·생존을 확인하고 켜 뒀다. [현재 가동](../runs/single-resource-20261106/operator-start.json), [startup](../{operator['startup_path']})은 single/A only·GPU 시간 예산.30·worker1/stream1·CPU4/interop1/BelowNormal·모델 한 세트/한 worker 예열을 확인한다. 로드{startup['model_loading_seconds']:.3f}초+예열{startup['synthetic_warmup']['seconds']:.3f}초=전체{startup['startup_total_seconds']:.3f}초다. 에이전트의 사용자 방 코드 입력0이며 사용자 특정 방 연결 완료를 주장하지 않는다. 과거 PID는 이력이다.

사용자는 인간/AI 표시 **기본 주소**를 새로고침하고 인간에서 만든8자리코드를 AI 표시와 지금 켠 PC 콘솔에 한 번 입력한다. 업데이트 재시작으로 메모리 권한을 잃은 이전 방은 새 방으로 최초 연결해야 한다. 이후 같은 방 next로 계속 운영한다. 단일에서는 B를 연결하지 않는다. dual 복구에는 웹 env=dual과 PC `--inference-mode parallel --gpu-duty-cycle 1` 양쪽 명시가 필요하다.

**완료:** 단일 UI/API/CLI·협력적 예산/CPU 설정·고정 모델 출력 비교·공개 한 판·v15 게시·운영 가동. **남음:** 사용자 실제 행사 기기와 CTF 동시 부하·장시간/연속 운영 리허설, 기존40%/ONNX/Pi/legacy OS 입력. 실제 모델/사진 정확도를 새로 측정한 작업이 아니다.

재현(운영 엔진과 CUDA 검증기를 동시에 실행하지 않고 새 결과 경로를 사용한다):

```powershell
.\\.venv\\Scripts\\python.exe -X utf8 -m unittest discover -s tests
.\\.venv\\Scripts\\python.exe -X utf8 runs/single-resource-20261106/verify_cuda_budget.py --execute --profile --output runs/single-resource-20261106/cuda-recheck.json
.\\.venv\\Scripts\\python.exe -X utf8 runs/single-resource-20261106/verify_live_single.py --execute --output runs/single-resource-20261106/live-recheck
.\\.venv\\Scripts\\python.exe -X utf8 scripts/check_docs.py --date 2026-11-06
.\\.venv\\Scripts\\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-06 --output runs/single-resource-20261106/document-audit.json
```

이번 작업 검토: 단일 저부하 운영 — 2026-11-06 관리 Markdown13개 전체 본문/이력을 분담 재독하고 실제 구현·v1 미통과/원래 배치 복구·v2 측정·공개 한 판·사이트 게시·새 가동을 대조했다. 변경 없는 데이터/모델 문서도 보존 정책과 이번 검토 결과를 기록했다. 새 Markdown은 없다. 전체 문서 점검·최종 소스 동기화는 아래 마무리 기록/CHANGELOG를 따른다.

"""

status = ROOT / "docs/STATUS.md"
body = status.read_text(encoding="utf-8").replace("최종 검토: 2026-11-05", "최종 검토: 2026-11-06", 1)
body = body.replace("## 최신 작업: 운영 연결 init·중복 봇 연결 복구", "## 이전 작업: 운영 연결 init·중복 봇 연결 복구", 1)
at = body.index("\n\n", body.index("최종 검토:")) + 2
if "## 최신 작업: A 단일" in body: raise RuntimeError("Preserve documented results")
status.write_text(body[:at] + section + body[at:], encoding="utf-8")

entry = f"""## 2026-11-06 A 단일 부스와 협력적 GPU 작업시간 예산30%

- 사용자의 내일11/07 A 하나/CTF 병행 요청이 기존 기본 병렬 정책을 대체한다. 웹 기본 single·A/B UI 제거·B 새 연결409/이전 B410·내부 A/기존 A 인증 유지, PC single worker/stream·8자리코드만 입력·B 사전 차단을 구현했다. dual/parallel은 양쪽 명시적 복구용이다.
- CooperativePacer로 모델 청크 뒤 마지막까지 작업시간2.333배를 취소 가능한 단위로 쉬게 했다. 유휴 크레딧/추가 상태 HTTP0, 자기 stream 동기화/로컬 생존 검사, 작업/실제 휴식/네트워크/선택 시간을 분리한다. SM/순간 GPU/VRAM 하드 quota가 아니며 CPU4/interop1/자체 BelowNormal만 적용했다.
- 첫 존재1장 분할 실험은 선택이 같아도 점수 최대0.000302553 차이로 사전1e-5를 넘겨 false로 보존했다. 허용오차 완화/가중치/임계값 변경 없이 원래 배치8+1/9/1×9를 복구했고 v2 네 조건×두 프로필×3회 출력 차이0/선택 동일/OOM0·작업 비율최대29.999102%를 확인했다. peak PyTorch reserved1154MiB이며 커널 추적/전체 장치 샘플/CTF 부하는 서로 구분했다.
- Python210개10.243초·웹125pass/1skip·TypeScript/build/diff 통과. 공개 single 한 판은 B 차단·3역할9사진/공통 출발·ML1/plan1·250ms·cache/표시 일치·정상 종료가 통과했다. 실제 IAB 기본 인간/봇 UI 및 이전 B 안내/기본 주소 전환도 확인했고 CUA 종료 기록을 남겼다. HTTP/PIL QA와 실제 브라우저/현장 경기·정확도는 섞지 않는다.
- Sites v15/env7·source{release['source_commit']}·saved{release['version_id']}·deployment{release['deployment_id']} 성공. 공개/두 도메인·초기화 경계1793862306432·관리자 비밀 두 키/DB/R2/사진/모델은 보존했다. source credential 만료는 같은 Site 갱신 후 패키징을 재개했다.
- 실행 중 발견한 프로젝트 체인26360→3272→32036을 경로/부모 검증 후 업데이트를 위해 정지했다. 공개 QA 후 새 **32140→41944→17664**를 켜두고 single/.30/CPU4/worker1/stream1·BelowNormal·로드5.375+예열6.563=11.938초와 생존을 확인했다. 사용자 최초 코드는 입력하지 않았다. 현재 가동은 runs/single-resource-20261106/operator-start.json이다.
- 남음: 실제 CTF 동시 부하·사용자 새 최초 연결/행사 한 판·장시간/연속 참가자, 기존40%/ONNX/Pi/legacy OS 입력. 학교 미사용·학습/모델/임계값/사진·protocol3/250ms/500ms/same-room next 경계를 유지한다.

### 이번에 읽고 갱신한 전체 Markdown (13개)

""" + "\n".join("- " + name for name in managed) + "\n\n이번 작업 검토: 단일 저부하 운영 — 13개 전체를 분담 재독하고 변경·실제 검증/실패 이력·한계·남은 작업을 STATUS에 기록했다. 새 Markdown은 없으며 내용 변화 없는 자료 문서도 검토 결과를 남겼다. 실제 문서 점검과 소스 동기화는 최종 완료 기록으로 반영한다.\n\n"
path = ROOT / "docs/CHANGELOG.md"
body = path.read_text(encoding="utf-8").replace("최종 검토: 2026-11-05", "최종 검토: 2026-11-06", 1)
at = body.index("\n\n", body.index("최종 검토:")) + 2
path.write_text(body[:at] + entry + body[at:], encoding="utf-8")
print("Completed single-mode measurements/publication/operator recorded")
