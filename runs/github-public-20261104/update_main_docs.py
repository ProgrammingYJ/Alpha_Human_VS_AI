from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
names=['AGENTS.md','README.md','docs/README.md','docs/STATUS.md','docs/CHANGELOG.md']
for name in names:
 p=root/name;s=p.read_text(encoding='utf8');s=s.replace('최종 검토: 2026-11-02','최종 검토: 2026-11-04',1)
 # Earlier per-task records remain history; the current review is added below.
 s=re.sub(r'^이번 작업 검토:', '이전 작업 검토(11/02):', s, flags=re.M)
 p.write_text(s,encoding='utf8')
repo='https://github.com/ProgrammingYJ/Alpha_Human_VS_AI'
p=root/'README.md';s=p.read_text(encoding='utf8');mark='송내고등학교 알파 동아리의'
intro=f'''공개 소스 저장소: [{repo}]({repo}) — 저장소 생성 완료, 초기 푸시/원격 검증은 [STATUS](docs/STATUS.md)에 기록합니다.

공개본에는 Python ML/원격 엔진·웹 서버/화면·설정 예시·테스트·문서와 검토된 실험/관리 도구 소스를 담습니다. 실제 가중치·Kaggle/학교/운영 사진·정답은행·JSON 실행 결과·비밀 환경·가상환경·의존성 설치본은 제외합니다. 운영 정답표를 코드에 담은 검토 빌더 2개도 제외합니다. `runs/`에서는 비밀감사를 통과한 `.py/.mjs/.ps1/.cmd/.sh`만 예외로 포함합니다. 기존 Sites Git 기록은 공개하지 않고 웹 소스는 일반 파일로 포함합니다.

```powershell
git clone {repo}.git
cd Alpha_Human_VS_AI
```

새 복제본의 설치는 [SETUP](docs/SETUP.md)을 따릅니다. ML 실행에는 별도 체크포인트가 필요하고 로컬 웹에는 별도 DB·사진 준비가 필요합니다. 문서의 과거 실측은 원래 PC/운영 사이트에서 확인한 이력입니다. 공개본은 제외된 로컬 결과로 향하는 링크를 일반 경로로 표시하며 원래 로컬 문서의 링크는 보존합니다. 코드 파일의 내용을 바꾸는 내보내기는 하지 않습니다.

'''
s=s.replace(mark,intro+mark,1).replace('scripts/check_docs.py --date 2026-11-02','scripts/check_docs.py --date 2026-11-04')
s+='\n이번 작업 검토: 2026-11-04 전체 본문과 공개 범위·복제/설치 흐름을 재검토했다. GitHub public 저장소 생성, 민감/대용량 산출물 제외, 검토한 작성 도구 소스 보존 및 Sites 이력과 분리한 새 공개 소스 내보내기를 반영했다. 실제 초기 푸시/원격 검증·문서 점검은 STATUS/CHANGELOG를 정본으로 삼으며 운영 코드·모델·사진·배포·프로세스는 변경하지 않는다.\n'
p.write_text(s,encoding='utf8')
p=root/'AGENTS.md';s=p.read_text(encoding='utf8');s+='''
## GitHub 공개 소스 관리 (2026-11-04)

사용자는 `ProgrammingYJ/Alpha_Human_VS_AI`라는 새 public GitHub 저장소 생성과 프로젝트 소스 푸시를 명시적으로 승인했다. 실제 URL/브랜치/푸시 확인은 STATUS가 정본이다. 기존 운영 경로와 `web/alpha-arena/.git`의 Sites 기록은 보존하며 별도 `C:\\Users\\Administrator\\Desktop\\Alpha_Human_VS_AI`에 새 Git 소스 스냅샷을 만든다. 웹은 gitlink/서브모듈이 아닌 일반 파일로 포함한다.

Python·웹·설정 예시·테스트·관리 문서·필수 외부 라이선스와 검토된 작성 도구 코드는 보존한다. data/models의 실제 파일, 로그·JSON 실행 결과·사진·은행·키/토큰·.venv/node_modules·생성물과 과거 Git 이력은 공개하지 않는다. runs의 작성 코드 확장자만 비밀검토 뒤 예외로 포함하며, 운영 사진별 정답표를 포함한 build_review_v1.py/finalize_bank.py는 제외한다. 공개본의 제외된 산출물 링크는 exporter에서 일반 경로로 바꾸고 원본 로컬 링크는 유지한다. 내보낸 코드와 원본의 바이트/누락·Git mode를 확인한 뒤 푸시한다.

이번 작업 검토: 2026-11-04 전체 본문을 재검토하고 GitHub 공개 승인·저장소 생성·소스 범위·별도 체크아웃·비밀 및 운영 자료 제외·작성 코드 예외를 반영했다. 모델/학교/사진/40%/Pi/OS 입력·Sites 배포/운영 엔진은 변경하지 않는다. 관리13개 전체 문서 재독·갱신 및 실제 검사/원격 결과는 STATUS/CHANGELOG를 따른다.
''';p.write_text(s,encoding='utf8')
p=root/'docs/README.md';s=p.read_text(encoding='utf8');s=s.replace('`python scripts/check_docs.py --date 2026-11-02`','`python scripts/check_docs.py --date 2026-11-04`')
s+=f'''\n공개 소스는 [{repo}]({repo})에 생성한 저장소를 사용합니다. 실제 푸시/원격 확인은 STATUS를 따릅니다. 관리 Markdown13개는 모두 포함하고 외부 라이선스 문서는 보존하되 관리 문서 갱신 대상에서 구분합니다. 공개 내보내기는 소스에 포함되지 않는 로컬 결과/자료 링크만 일반 경로로 바꿉니다. 새 Markdown은 추가하지 않았습니다.

이번 작업 검토: 2026-11-04 색인과 전체 본문을 재검토하고 public GitHub 소스 범위·실제 운영/평가 산출물 제외·작성 도구 예외·로컬과 공개본 문서 표시를 반영했다. 관리13개 목록은 같으며 실제 게시와 전체 점검 결과는 STATUS/CHANGELOG가 정본이다.
''';p.write_text(s,encoding='utf8')
status=f'''## 최신 작업: GitHub 공개 저장소 준비 (2026-11-04)

사용자 요청으로 [{repo}]({repo})를 `ProgrammingYJ` 계정에 public으로 생성했다. 이 시점 소스 내보내기·초기 푸시·원격 검증은 진행 중이며 완료로 보고하지 않는다. 기존 Sites v13 게시·운영34사진·가중치·임계값·원격 엔진은 이번 작업에서 변경하지 않는다.

원래 프로젝트는 루트 Git 저장소가 없고 web/alpha-arena에 Sites용 Git만 있다. 원본/기존 이력을 보존하고 별도 `C:\\Users\\Administrator\\Desktop\\Alpha_Human_VS_AI`에 새 Git 저장소를 만들어 Python과 웹을 일반 파일로 함께 올린다. 과거 Sites Git 이력이나 gitlink는 공개하지 않는다.

- 포함: Python/웹/설정 예시·요구사항/lockfile·테스트·관리 Markdown13개·빌드 필수 vendor 자산/외부 라이선스·비밀감사를 거친 runs 작성 코드.
- 제외: 실제 사진·Kaggle/학교 자료·학습/운영 manifest/정답은행·모델/가중치·JSON 실행 결과·로그·.env/자격정보·가상환경·node_modules·빌드/런타임 상태·이전 Git 이력. 사진별 정답표를 담은 runs/photo-clarity-20261102/build_review_v1.py 및 finalize_bank.py도 제외한다.
- 공개본의 제외된 로컬 산출물 Markdown 링크는 `scripts/export_public_source.py`로 일반 경로로 표시한다. 원본 로컬 문서·코드 바이트는 유지한다. 새 clone에 실제 모델/은행/실측 파일이 설치돼 있다는 의미가 아니다.

내보내기/민감 패턴·파일 일치·문서/테스트·원격 브랜치 검사 결과는 아래에 실제 수행 후 확정한다. 원본 폴더의 파일을 삭제하거나 Sites를 다시 배포하지 않는다.

이번 작업 검토: 관리13개를 분담해 전체 본문 재독·11/04 갱신 중이며 GitHub public 생성과 소스 내보내기 범위를 확인했다. 초기 푸시·검사 결과는 아직 진행 중이다.

'''
p=root/'docs/STATUS.md';s=p.read_text(encoding='utf8').replace('## 최신 작업: 애매한 사진','## 이전 작업: 애매한 사진',1);at=s.index('## 이전 작업: 애매한 사진');p.write_text(s[:at]+status+s[at:],encoding='utf8')
log=f'''## 2026-11-04 GitHub public 소스 저장소 준비

- 사용자가 새 public 저장소 `Alpha_Human_VS_AI` 생성과 전체 프로젝트 소스 푸시를 요청했다. GitHub CLI의 현재 계정 ProgrammingYJ를 확인하고 {repo} 생성/public 상태를 확인했다. 기존 동일 이름 저장소는 없었으며 기존 원격을 덮어쓰지 않았다.
- 별도 Desktop/Alpha_Human_VS_AI 소스 체크아웃에 Python/웹을 일반 파일로 내보내 기존 Sites Git과 운영 폴더를 보존한다. 원본/모델/사진/정답은행/로그/JSON 결과/자격/의존성·생성물/과거 Git은 제외한다. 작성한 runs 도구 소스는 개별 검사 후 보존하며 원시 운영 정답을 담은 빌더2개는 제외한다.
- .gitignore의 웹·비밀·모델/실행 결과 제외와 작성 코드 예외를 보강하고 scripts/export_public_source.py를 추가했다. 공개 Markdown에서 제외된 로컬 결과 링크만 일반 경로로 표시하며 원본 코드는 바꾸지 않는다.
- 초기 푸시·복제본 검사/원격 확인은 진행 중이고 실제 결과는 완료 후 반영한다. ML·사진·Sites 배포·운영 프로세스 변경은 없다.

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

이번 작업 검토: 관리13개 본문을 분담 재독하고 GitHub 생성·공개 범위·별도 소스 스냅샷 및 기존 운영 보존과 대조했다. 전체 문서 검사·소스 검사·실제 푸시/원격 결과는 완료 후 확정한다.

'''
p=root/'docs/CHANGELOG.md';s=p.read_text(encoding='utf8');at=s.index('## 2026-11-02 사진');p.write_text(s[:at]+log+s[at:],encoding='utf8')
