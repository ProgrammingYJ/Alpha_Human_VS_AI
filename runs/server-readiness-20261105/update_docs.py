from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
op=json.loads((root/'runs/server-readiness-20261105/operator-start.json').read_text(encoding='utf8'))
http=json.loads((root/'runs/server-readiness-20261105/public-http-check.json').read_text(encoding='utf8'))
assert op['startup_verified'] and http['passed'] and len(http['checks'])==6
names=['AGENTS.md','README.md','docs/README.md','docs/STATUS.md','docs/CHANGELOG.md']
for name in names:
 p=root/name;s=p.read_text(encoding='utf8').replace('최종 검토: 2026-11-04','최종 검토: 2026-11-05',1)
 if name in {'AGENTS.md','README.md','docs/README.md'}:
  s=s.replace('이번 작업 검토: 2026-11-04','이전 작업 검토(11/04): 2026-11-04',1)
 p.write_text(s,encoding='utf8')
p=root/'README.md';s=p.read_text(encoding='utf8');mark='## 컴퓨터 브라우저 A/B 운영'
intro='''11/05 외부 컴퓨터 시험 준비: 공개 human/bot A/B 페이지와 health 6요청이 모두 HTTP200이며, 이 PC의 CUDA 3모델 로드·합성 예열 후 운영 콘솔을 켜 두었다. **한 엔진 콘솔에 A/B 두 코드를 각각 입력한다.** 외부 인간 화면에서 만든 코드를 해당 AI 표시 화면에 연결하고 PC 콘솔에 `A 실제8자리코드`/`B 실제8자리코드`로 숨겨 입력한다. 별도 엔진을 두 개 켤 필요가 없다. 준비 확인 뒤 각 인간 화면에서 시작하고 종료 뒤 같은 방의 다음 참가자 준비를 사용한다. 현재 가동/PID·미확인 외부 시험은 [STATUS](docs/STATUS.md)가 정본이다.

'''
s=s.replace(mark,intro+mark,1).replace('scripts/check_docs.py --date 2026-11-04','scripts/check_docs.py --date 2026-11-05')
s+='\n이번 작업 검토: 2026-11-05 전체 본문을 재검토하고 공개 사이트 HTTP 확인·정규 PC CUDA 엔진 기동·한 콘솔 A/B 연결과 외부 컴퓨터 시험 순서를 반영했다. 모델 로드/합성 예열을 실제 외부 방 참가·사진 준비/한 판 완료와 구분했다. 운영 엔진은 계속 켜 두며 모델/사진/학교/40%/Pi/OS 입력 상태와 공개 GitHub 이력은 유지한다. 전체 문서 점검 정본은 STATUS/CHANGELOG다.\n';p.write_text(s,encoding='utf8')
p=root/'AGENTS.md';s=p.read_text(encoding='utf8');s+='''
## 외부 컴퓨터 시험용 가동 (2026-11-05)

서버 기동 요청으로 기존 공개 Sites v13 active/public 상태와 두 도메인의 A/B 페이지·health HTTP6개 성공을 확인했다. 정규 start_remote_engine.ps1로 PC CUDA 엔진 한 개를 띄워 3모델 로드15.046초·합성 예열3.657초·총18.703초 완료와 프로세스 부모 관계/생존을 확인했다. 현재 가동 정본은 runs/server-readiness-20261105/operator-start.json과 STATUS다. 과거 PID를 현재 생존 근거로 사용하지 않는다.

사용자는 한 엔진에서 A/B 모두 연결 가능함을 이해하고 외부 시험을 진행하기로 했다. 추가 엔진/브라우저 창은 열지 않았고 현재 콘솔을 유지한다. 최초 각 방 코드를 동일 콘솔에 A/B로 한 번씩 숨겨 입력한다. 외부 컴퓨터는 공개 HTTPS 화면만 사용하고 Python/로컬5186/LAN 포트 개방이 필요하지 않다. 이번 확인은 모델 준비와 HTTP이며 외부 기기의 실제 참가·사진 디코딩·한 판·동시 부하 결과는 미수신이다.

이번 작업 검토: 2026-11-05 전체 본문을 다시 읽고 정규 운영 엔진 기동·현재 프로세스/신규 startup·HTTP6개와 A/B 한 콘솔 운용을 확인했다. 가중치/임계값/사진/학교/40%/Pi/OS 입력·서버 배포는 변경하지 않았다. 관리13개 문서를 분담 재독·갱신하고 검사/완료·남은 시험을 STATUS/CHANGELOG에 기록한다. 사용자의 시험용 엔진은 정리 대상으로 종료하지 않는다.
''';p.write_text(s,encoding='utf8')
p=root/'docs/README.md';s=p.read_text(encoding='utf8').replace('scripts/check_docs.py --date 2026-11-04','scripts/check_docs.py --date 2026-11-05')
s+='''
외부 컴퓨터 시험의 가동 정본은 STATUS, 접속 주소/방 코드·같은 방 다음 참가자 순서는 SETUP이다. 11/05 공개 HTTP6개와 PC CUDA 3모델 준비를 확인했으며 실제 외부 기기 시험 결과와 구분한다. 엔진은 한 개에 A/B를 함께 연결한다.

이번 작업 검토: 2026-11-05 색인과 전체 본문을 다시 대조하고 공개 사이트·PC 정규 엔진 가동과 외부 시험 안내 위치를 반영했다. 관리 Markdown13개는 그대로이고 새 문서는 없다. 모델/사진/학교 및 공개 GitHub 이력은 유지하며 실제 검사·가동과 미확인 외부 시험은 STATUS/CHANGELOG가 정본이다.
''';p.write_text(s,encoding='utf8')
status='''## 최신 작업: 외부 컴퓨터 시험용 PC 엔진 가동 (2026-11-05)

사용자의 서버 기동/외부 컴퓨터 시험 요청으로 공개 사이트를 확인하고 정규 PC 엔진을 켜 두었다. 추가 창 문의에는 한 엔진이 A/B 모두 연결됨을 설명했고 사용자가 이를 이해하고 시험하러 간다고 답했다. 추가 GPU 엔진이나 브라우저 창은 열지 않았다. 외부 컴퓨터의 실제 시험 결과는 아직 받지 않았다.

### 실제 확인

- Sites 조회: project appgprj_6ade37995018819184a42c88bb0fde7c active/public, 최신 버전13. 기존 공개 사이트를 다시 배포하거나 환경/방/사진을 변경하지 않았다.
- human.marulee.dev / bot.marulee.dev 각각 `/?lane=A`, `/?lane=B`, `/api/health` 6요청 모두 HTTP200. health protocol3·사진 준비 barrier=true·최소250ms를 확인했다. HTML/API 수신 검사이며 외부 기기의 브라우저 렌더링·사진 준비 완료 검사가 아니다. 응답 시간0.081~0.729초는 이 PC의 1회 관측으로 외부 네트워크 성능 보장이 아니다. [HTTP 기록](../runs/server-readiness-20261105/public-http-check.json).
- 시작 전 run_remote_engine.py 엔진0개를 확인하고 `scripts/start_remote_engine.ps1`을 새 코드 입력용 visible 콘솔에서 실행했다. 현재 체인은 **powershell43132 → venv Python17060 → base Python38628**이며 경로/부모 관계·생존을 재확인했다. 두 Python PID는 가상환경 실행 체인이고 독립 GPU 엔진 두 개가 아니다. 기존 프로세스를 종료하지 않았다.
- 새 [startup.json](../runs/remote-engine/20261105-153228-f21fc803/startup.json): device=cuda, 3모델 한 번 로드15.046초·합성 RGB 예열3.657초·총18.703초, 실제 문제 사진0·가중치/임계값 변경0. 준비 완료 뒤 코드 입력을 받는 콘솔을 계속 켜 두었다. [현재 가동 기록](../runs/server-readiness-20261105/operator-start.json).
- 에이전트의 방 코드 입력0·사용자 특정 방 연결/엔진 heartbeat/실제 문제 선택·제출 검증0. 사용자가 이후 입력한 방 연결이나 외부 시험 성공을 추정하지 않는다. 11/01 PID 및 이전 CUDA 경기 결과는 당시 이력이다.

### 외부 컴퓨터 시험 순서

| 역할 | 공개 주소 |
|---|---|
| 인간 A | https://human.marulee.dev/?lane=A |
| AI 표시 A | https://bot.marulee.dev/?lane=A |
| 인간 B | https://human.marulee.dev/?lane=B |
| AI 표시 B | https://bot.marulee.dev/?lane=B |

1. Chrome에서 각 역할 화면을 실제 보이는 창으로 연다. 외부 컴퓨터에는 Python/ML 설치가 필요 없다. 이 PC의 localhost5186이나 LAN 포트 연결을 사용하지 않는다.
2. 인간 A/B 각각 새 remote 방을 만들고 코드를 같은 레인의 AI 표시 화면에 입력한다. 이 PC의 이미 켠 **한 콘솔**에 `A 실제8자리코드`, `B 실제8자리코드`를 각각 숨겨 입력한다. 코드/토큰을 인자·파일·로그로 전달하지 않는다.
3. 각 인간 화면의 PC 준비/AI 표시 연결을 확인하고 시작한다. GPU 대기→세 역할9장 준비→약2초 공통 출발을 확인한다. 양 화면을 숨은 탭으로 두지 않는다. A/B의 절대 출발 시각은 다를 수 있다.
4. 종료 뒤 같은 인간 화면에서 다음 참가자 준비→다시 시작한다. 정상 참가자 교체에는 새 방/코드/모델 재시작이 필요 없다. 시험 동안 PC 콘솔과 전원·네트워크를 유지한다.

**완료:** 공개 접근·프로토콜 HTTP 확인, 정규 CUDA 엔진 기동/합성 예열·생존 및 유지. **남음:** 외부 컴퓨터의 실제 방 참가/사진 디코딩·A/B 동시 한 판/연속 참가자·네트워크/장시간 시험 결과. 모델 품질/40%·ONNX·Pi·legacy OS 입력은 그대로 미완료다. 이번에는 운영 코드/학습/사진/서버 배포/전역 네트워크 설정 변경과 새 실전 정확도 측정이 없다. 코드 변경이 없어 기존 전체 단위 테스트를 다시 실행하지 않았고 실제 기동·공개 HTTP로 확인했다.

재현/문서 점검:

```powershell
# 이미 켜 둔 엔진은 중복 실행하지 않는다. 아래 실행기는 꺼져 있을 때만 쓴다.
.\\Start-Alpha-Remote.cmd
.\\.venv\\Scripts\\python.exe -X utf8 scripts/check_docs.py --date 2026-11-05
.\\.venv\\Scripts\\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-05 --output runs/server-readiness-20261105/document-audit.json
```

이번 작업 검토: 관리13개 전체 본문을 분담 재독하고 현재 HTTP/새 startup·프로세스 체인·A/B 단일 엔진/외부 시험 흐름과 대조했다. 사용자 시험용 콘솔은 유지한다. 문서 검사는 전체 갱신 뒤 결과를 확정한다.

'''
p=root/'docs/STATUS.md';s=p.read_text(encoding='utf8').replace('## 최신 작업: GitHub public','## 이전 작업: GitHub public',1);at=s.index('## 이전 작업: GitHub public');p.write_text(s[:at]+status+s[at:],encoding='utf8')
log='''## 2026-11-05 외부 컴퓨터 시험용 서버 확인·PC 엔진 가동

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

이번 작업 검토: 관리13개 전체 본문을 분담 재독·11/05 갱신하고 현재 PC 기동/공개 HTTP와 미확인 외부 시험을 구분했다. 운영 엔진을 사용자 시험용으로 계속 유지하며 전체 문서 점검 결과는 갱신 후 확정한다.

'''
p=root/'docs/CHANGELOG.md';s=p.read_text(encoding='utf8');at=s.index('## 2026-11-04 GitHub');p.write_text(s[:at]+log+s[at:],encoding='utf8')
