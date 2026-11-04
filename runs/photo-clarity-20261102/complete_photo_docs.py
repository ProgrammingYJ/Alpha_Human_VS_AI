import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
run=root/'runs/photo-clarity-20261102'
r=json.loads((run/'retry1-production-verification.json').read_text(encoding='utf8'))
c=json.loads((run/'production-bank-combinations.json').read_text(encoding='utf8'))
assert r['passed'] and c['passed'] and r['activePhotoCount']==34
assert r['publicRoundCount']==5
def update(name,old,new):
 p=root/name;s=p.read_text(encoding='utf8');assert old in s,(name,old[:40]);p.write_text(s.replace(old,new,1),encoding='utf8')
update('README.md','**사진 명확성 검토로 기존 46장 중 22장을 출제에서 빼고 새 10장을 추가한 34장 은행**을 준비했습니다.',
 '**사진 명확성 검토로 기존 46장 중 22장을 출제에서 빼고 새 10장을 추가한 34장 은행을 운영에 반영했습니다.** 공개 새 경기 5판에서 네 유형 출제와 교체 전 경기의 사진 보존을 확인했습니다.')
update('AGENTS.md','공개 문제은행46장 등록과 웹 사진 표시는 확인했다.',
 '이전 공개 46장 등록/표시 이력을 보존하며 11/02 명확성 교체 후 활성 34장·퇴역 22장·새 10장과 실제 공개 4종 출제를 확인했다.')
section='''## 최신 작업: 애매한 사진 퇴역·명확한 사진 교체·버전13 (2026-11-02)

사용자의 사진 명확성 요청으로 기존 공개 46장을 전수 시각 검토하고 **22장 퇴역·24장 유지·새 10장 추가, 활성 34장**으로 운영에 반영했다. 현재 정본은 [public-web-v3/bank.json](../data/booth/public-web-v3/bank.json)이며 활성 파일 합계는 9,290,899bytes다. 로컬 Kaggle 시연 34장과 같은 숫자지만 서로 다른 은행이고 Kaggle/학교 사진은 공개하지 않았다. v1/v2의 46장·12,362,595bytes는 이전 이력이다.

야간·원경 인물/나무·가린 수면·자연 수면 경계·고고도 지형·건물처럼 보이는 잔해 등 어려운 장면을 제외했다. 새 사진은 큰 단체/단독 인물, 건물 외관, 분리된 나무 줄기, 경계가 보이는 정원 연못이다. 실제 RGB 및 216px full-frame contain 미리보기를 검토했고 사이트의 타일 CSS도 object-fit:contain으로 이미지를 자르지 않음을 읽었다. 새 사진은 CC0 7장/PD-USGov-NASA 3장이며 원문 파일 revision/wikitext·권리·촬영 그룹·해시를 기록했다. 새 10장은 두 AI의 시각 판단을 대조했고 독립 사람 검수는 미완료다. 모호한 조건은 null로 제외하며 제목만으로 연못을 확정하거나 모델 정오답을 보고 사진을 선택하지 않았다.

### 코드와 배포

- 인증된 `PUT /api/admin/photos`의 `photoIds` 1~128개를 검증한다. UUID/중복/없는 사진·4종 그룹 부족을 거부하고 단일 SQL UPDATE로 전체 활성 집합을 교체한다. 같은 집합 재전송은 멱등이다. 관리자 `?includeInactive=1`·active/SHA 조회를 추가했고 공개 응답에는 라벨/정답을 넣지 않는다.
- 비활성 사진은 다음 추첨에서 제외하지만 이미 생성한 라운드의 사진 ID·픽셀·정답 스냅샷은 유지한다. R2/원본을 삭제하지 않는다. 기존 active 조건이 현재 라운드 사진도 404로 만들던 조회를 교정하고 라운드 소속·만료·준비/공개 시각 검사는 보존했다.
- 버전13 source `2cc72fceeed5cbbd1f44eb63a6f52df7067a8880`, saved `appgprj_6ade37995018819184a42c88bb0fde7c~appgver_dd082b3c37848191b2be432616556827`, deployment `appgdep_6ae897a2e2588191b051f193b217e75a`가 succeeded다. 기존 두 도메인·public audience·D1/R2·소유자 ID는 유지했다. 기존 숨김 키 값을 읽을 수 없어 관리 작업의 ADMIN_KEY만 비밀값으로 갱신했고 환경 revision5에 게시했다. 키는 메모리/호스팅 비밀 환경에만 두고 파일/소스/인자/로그에 저장하지 않았다. [배포 기록](../runs/site-publish/photo-clarity-release.json).
- 모델·가중치·임계값·학습·GPU FIFO·사진 준비/출발·250ms 선택 계획·기존 운영 PC 프로세스는 변경하지 않았다. 이번 사진 교체에 PC 엔진 재시작이나 방 재생성은 필요 없다. 이미 생성한 판은 기존 사진을 유지하며 다음 새 판부터 새 은행을 추첨한다.

### 실제 검사 결과

| 검사 | 확인 결과 |
|---|---|
| 로컬 파일/자료 | 34/34 SHA·완전 RGB 디코딩·원본/해시/선언 그룹 중복 0·EXIF 없음·dHash≤4 후보 0. 유지 24장의 기존 라벨/그룹 불변 |
| 공개 등록/활성 | 새 10/10 업로드·동일 PUT ACK, D1 등록 56장 중 활성34/비활성22, 4종 ready |
| 활성 R2 파일 | 34/34 SHA·RGB 디코딩, 총 9,290,899bytes가 로컬 정본과 일치 |
| 기존 공개 경기 | 교체 전 9장 해시/URL 보존, 그중 퇴역 3장도 교체 뒤 HTTP200 |
| 새 공개 경기 | 실제 5판에서 4종 모두 관측·9개 독립 사진/그룹·허용 정답 수·인간/봇 동일 배열/출발·정답 비노출·퇴역 재출제 0 |
| 전수 추첨 | 실제 운영 사진 UUID/SHA 카탈로그로 11개 유형/정답 수 조합×32회=352회 통과. 반복 추첨이며 독립 정확도 표본 아님 |
| 코드 검사 | 대상 Node 단위33개 통과, TypeScript·production build(6.517초)·diff 통과 |
| 실제 localhost HTTP | 인증/외부 Origin/형식/8192bytes/중복·누락·부족 은행 거부·멱등 교체·active/loading 사진 보존·새 판 퇴역 제외 1개 복합 검사 통과(5.806초, runner5.910초) |

| 주제 | 양성 그룹 | 음성 그룹 | 미확인(제외) |
|---|---:|---:|---:|
| 사람 3명 이상 |14|16|4|
| 나무 3그루 이상 |8|22|4|
| 건물 |9|15|10|
| 연못 |4|30|0|

운영 검증 정본은 [retry1-production-verification.json](../runs/photo-clarity-20261102/retry1-production-verification.json), [운영 카탈로그 전수 추첨](../runs/photo-clarity-20261102/production-bank-combinations.json), [로컬 독립 파일 감사](../runs/photo-clarity-20261102/prepared-final34-independent-files.json)다. 첫 운영 QA는 PC 절대시계로 출발을 기다린 하네스가 playing을 관측하지 못해 업로드/활성화 전에 실패했다. [원본 실패](../runs/photo-clarity-20261102/production-verification.json)를 보존하고 서버 상대시각/유한 상태 관측으로 하네스만 수정한 retry1이 통과했다. 사이트 시간 정책을 바꾸지 않았다. 로컬 첫 실패는 외부 Origin의 비JSON403 파싱, 다음 실패는 예비 그룹 없는 최소 fixture였으며 하네스 파싱 수정·로컬 공개34장 추가 뒤 통과했다. 이를 처음부터 모두 성공한 검사로 보고하지 않는다.

**완료:** 사진 교체·관리 원자 전환·v13 배포·활성 파일/출제/기존 사진 보존 검증. **남음:** 독립 사람 검수와 행사 기기/실제 브라우저 렌더링 리허설, 모델 품질/40%·ONNX·Pi·legacy OS 입력. 이번에는 ML 추론/답안 제출/정확도·승률 측정 0회다. 사진 명확성 개선을 모델 성능 개선이나 무지연 보장으로 쓰지 않는다.

재현은 새 결과 경로를 사용하며 실행형은 관리 키를 숨김 stdin으로만 전달한다. 기존 보고서를 덮어쓰지 않는다.

```powershell
.\\.venv\\Scripts\\python.exe -X utf8 scripts/import_public_booth_bank.py --bank data/booth/public-web-v3/bank.json --base-url https://human.marulee.dev --output runs/photo-clarity-20261102/new-validation-report.json
.\\.venv\\Scripts\\python.exe -X utf8 runs/photo-clarity-20261102/apply_and_verify.py
node runs/photo-clarity-20261102/audit_bank_combinations.mjs runs/photo-clarity-20261102/retry1-active-catalog.json runs/photo-clarity-20261102/new-combinations-report.json
.\\.venv\\Scripts\\python.exe -X utf8 scripts/check_docs.py --date 2026-11-02
.\\.venv\\Scripts\\python.exe -X utf8 runs/site-publish/audit_docs.py --date 2026-11-02 --output runs/site-publish/photo-clarity-document-audit-20261102.json
```

이번 작업 검토: 관리 Markdown 13개 전체 본문을 분담 재독하고 실제 시각 판정·고정 모델/학교 정책·관리 API/현재 라운드 보존·배포/검증과 대조했다. 새 Markdown은 없다. 최종 문서 점검 결과는 전체 갱신 뒤 확정한다.

'''
p=root/'docs/STATUS.md';s=p.read_text(encoding='utf8');s=s.replace('## 최신 검증: GPU 분배와 A/B 동시 추론 후보','## 이전 검증: GPU 분배와 A/B 동시 추론 후보',1)
at=s.index('## 이전 검증: GPU 분배');s=s[:at]+section+s[at:];p.write_text(s,encoding='utf8')
changelog='''## 2026-11-02 사진 명확성 교체·관리 활성 집합·버전13

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

이번 작업 검토: 관리13개 전체 본문과 실제 RGB·그룹/권리·원자 활성 전환·배포/검증을 분담 재검토했다. 새 Markdown은 없으며 전체 문서 검사와 UTF-8/로컬 링크/전수 목록/설정 JSON 감사는 최종 갱신 뒤 실행해 결과를 확정한다.

'''
p=root/'docs/CHANGELOG.md';s=p.read_text(encoding='utf8');at=s.index('## 2026-11-02 GPU');p.write_text(s[:at]+changelog+s[at:],encoding='utf8')
