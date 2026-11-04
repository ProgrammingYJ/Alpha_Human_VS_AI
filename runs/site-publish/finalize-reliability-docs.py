"""Replace pending release notes only after the corresponding evidence passes."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
accept=json.loads((root/'runs/reliability-public-20261101-acceptance.json').read_text(encoding='utf-8'))
surface=json.loads((root/'runs/site-publish/reliability-release-http-20261101.json').read_text(encoding='utf-8'))
engine=json.loads((root/'runs/site-publish/reliability-current-engine.json').read_text(encoding='utf-8-sig'))
assert accept['passed'] and surface['passed'] and engine['startup_verified']
startup=engine['startup_file']
public='''공개검증 결과: [두 호스트/초기 자산 검사](../runs/site-publish/reliability-release-http-20261101.json)에서 human/bot 각각 HTML·health와 초기JS/CSS17개가 모두200이었다. 프로토콜3·사진 준비·250ms 하한·새 schema 접근도 확인했다. [교차호스트 연결](../runs/site-publish/reliability-cross-host-pairing-20261101.json)은 인간 호스트에서 만든 방에 봇 호스트의 표시/실제 EngineRoom을 연결해 같은 코드·B구역·준비/생존을 확인한6개 검사 통과다. ML/경기 시작/운영 방 접근은 없었다.

공개 **CUDA A같은방2판+B1판**에서 모델1회 로드6.547초·합성 예열2.547초, 각 판 예측1회/논리제출1회·서버 제출3회·생존363샘플/준비 후 끊김 관측0을 확인했다. 세 판 모두 사진 캐시 재사용·경기 중 사진 다운로드0·출발 전 실제 문제 추론0·경기 중GPU대기0·계획 전GPU해제였다. A1/A2의연못예측은[]이고B1나무는[1]로서세판모두오답timeout이다. 이 재사용 기능검사를 정확도0%나40%목표 검증으로 해석하지 않는다. [원본 실제 실행](../runs/reliability-public-20261101-v1/verification.json)과 판별 보고서를 보존한다.

원본26개 불리언 중25개가true이고 `slow_human_gate_observed`는false였다. 인간 자신의 디코딩 완료부터3초만 보류한 첫 시험은 다른 두 역할이 준비된 뒤 인간만 미준비인 구간을 관측하지 못했다. **원본passed=false를 그대로 보존했다.** 시험을 다른 두 역할의 준비 확인 뒤3초 보류하도록 고치고 [별도 공개 게이트 검사](../runs/reliability-public-20261101-gate-v2.json)10/10을 통과했다. PC/봇만 준비된loading샘플3개에서 타이머0을 실제 관측했고 보류4.984초 후 인간 준비→공통countdown→출발 전 취소까지 확인했다. 보완 검사는 HTTP/PIL이며 ML/선택/제출0이다. [종합 검증](../runs/reliability-public-20261101-acceptance.json)은 원본의 미관측 사유와 별도 보완 근거를 명시한다.

실제 세 판의9RGB 사전 수신은 A1/A2/B1 각각1.953/1.031/1.328초, 모델 함수는0.094/0.062/1.875초, 계획 ACK왕복은0.344/0.328/0.328초였다. 이것은 각1회 관측이며 평균/p95 또는 모든 행사 네트워크의 속도 보장이 아니다. 선택이0/0/1개여서 공개 다중선택 간격 표본은0이다. SQL/로컬HTTP의250ms 검증과 공개 브라우저/실제 타일 렌더링 실측은 구분한다.

원본의 요청→공통 출발11.570/23.651/20.997초에는 GPU 예약·테스트 역할 준비·공통2초와 통신이 포함된다. 특히 A2는 QA의직렬view/register 관측 공백16.797초가 있었고, 첫loading관측 이후countdown까지3.610초/playing관측까지4.688초였다. PC가 먼저 준비되어도 인간/표시준비false인 동안 서버가 기다린 것은 정상이었다. 원본은 각GET/POST 지연을 분해하지 않아 공백의 세부 네트워크 원인은 미확인이다. 이를 모든 실제 브라우저의 준비 시간이23초라는 주장이나 현장 무지연 증명으로 바꾸지 않는다.

고정 공개9RGB에서 full예측과 질문별 경로의 관련 점수/인원수/선택이 모두 같았고 최대 존재점수 차이는0이었다. full0.360초·건물/연못 각각0.078초·사람0.328초는 같은9장 한 번의 기능 비교다. 새 정확도·배포 장치별 벤치마크/40%달성 측정은 아니다. 가중치/전처리/임계값·추가학습 변경0이다.

운영 엔진은 시작 전0개임을 확인하고 새 콘솔을 켰다. 경로/부모 관계를 검증한 **PowerShell19224→venv12972→base31892**는 CUDA 모델1회 로드6.031초·합성 예열2.469초·총8.5초 초기화와 생존을 확인해 켜 두었다. [가동 기록](../runs/site-publish/reliability-current-engine.json)과 [startup](../'''+startup+''')이 근거다. 에이전트 코드 입력0이며 특정 사용자 방 연결 완료는 아직 아니다. 사용자는 웹을Ctrl+F5로 새로고침하고 최초 새 방으로 PC/표시를 한 번 연결한다. 이후 참가자 교체는 같은 방next를 사용하며 실행기를 중복 실행하지 않는다. 표시 창 두 개는 보이는 상태를 유지한다.

관리13개 Markdown의 전체 본문을 분담 재독·교차검토했고 최신 동작/이력·측정/한계를 갱신했다. `check_docs.py --date 2026-11-01`과 별도 전수 감사에서13개·UTF-8·로컬 링크·색인/목록·설정JSON8개가 통과했다([문서 검사](../runs/site-publish/reliability-document-audit-20261101.json)). 최종 내용 수정 뒤 같은 명령으로 다시 확인한다. 실제 브라우저 동시 렌더링과11/07행사 기기·네트워크 리허설은 사용자의 재검증에 남아 있다.

이번 작업 검토: 11/01에 관리13개를 전수 검토하고 서버/화면/PC의 사진 준비·버전·연결/선택 지연과 복구를 수정했다. 공개v12/HTTPS·실제CUDA3판·미관측 시험의 별도 보완·고정모델 출력 동등성과 운영 엔진 초기화를 구분해 기록했다. 최초 공개 시험passed=false와 타일 간격 표본0·브라우저 미검증을 숨기지 않았다. 학교/학습/임계값·40%/ONNX/Pi/legacy OS 및 현장 검증 경계를 유지한다.'''

p=root/'docs/STATUS.md';t=p.read_text(encoding='utf-8')
t=t.replace('| 공개 CUDA·역할별RGB 준비 |검증 진행 중. 완료 결과는 아래 공개검증 절에 기록 |','| 공개 CUDA·역할별RGB 준비 |A2판+B1판의 실제 추론/서버제출·같은방 교체 확인. 느린 인간 게이트는 별도 공개10개 검사로 보완; 원본 실패 표식 보존 |',1)
old='공개검증 결과: 자체 검사 진행 중. 공개주소/운영엔진최종확인뒤이문장을갱신한다.'
assert t.count(old)==1;t=t.replace(old,public,1);p.write_text(t,encoding='utf-8')

p=root/'docs/CHANGELOG.md';t=p.read_text(encoding='utf-8')
t=t.replace('실제DOM도구연결은불가해우회0이며공개CUDA/HTTPS/운영가동확정결과는STATUS에계속기록한다.','실제DOM도구연결은불가해우회0이며공개CUDA/HTTPS/운영가동확정결과는STATUS에기록했다.',1)
addition='''
- 공개 두호스트 HTML/health/각17개 초기자산200·프로토콜3, 인간호스트생성→봇호스트표시/PC연결6검사 통과다. 실제CUDA A2+B1은 캐시재사용/게임중다운로드0/사전문제추론0/각예측·제출1회/363생존샘플을 확인했다.[]/[]/[1]오답timeout은 기능검사이며 정확도나40%평가가아니다.
- 원본26검사 중25true·느린인간 게이트 미관측1false를 그대로 보존했다. 시험보류기준을 고치고 별도 공개10/10으로4.984초 대기 중 타이머0과 모두준비후출발·출발전취소를 검증해 종합보고서에 연결했다. A2의16.797초 QA직렬관측공백과 공개타일간격표본0·실제DOM미측정을 공개했다. 고정9RGB full/질문별 점수·인원수·선택은동일/점수차0이다.
- 운영엔진0개확인후19224→12972→31892를 새로실행했다. CUDA로드6.031초/합성예열2.469초/총8.5초·생존확인후켜두었고 사용자코드입력0이다. 최초새방연결후일반참가자교체는같은방next다.13개문서의검토표식/날짜/색인·별도전수UTF8/링크/설정JSON8개검사가통과했고최종수정후재실행한다.
'''
anchor='### 이번에 읽고 갱신한 전체 Markdown (13개)'
t=t.replace(anchor,addition+'\n'+anchor,1);p.write_text(t,encoding='utf-8')
print('STATUS and CHANGELOG finalized against successful release, supplemental gate, operator and health evidence.')
