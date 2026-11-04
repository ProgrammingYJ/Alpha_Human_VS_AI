from pathlib import Path
import re

root=Path(__file__).resolve().parents[2]
def review(text, label, latest):
    head,tail=text.rsplit('\n이번 작업 검토:',1)
    return (head+'\n이전 작업 검토('+label+'):'+tail).rstrip()+'\n\n이번 작업 검토: '+latest+'\n'
path=root/'AGENTS.md'; text=path.read_text(encoding='utf-8')
anchor='| 운영 화면 |'
assert anchor in text
text=text.replace(anchor,'| 출발 | remote 시작 요청→GPU 예약 대기(타이머0·문제 비공개)→PC 예약 획득 뒤 약2초 공통 출발. 추론 반환 뒤 GPU 해제, 선택은 방별 진행 |\n'+anchor,1)
text=text.replace('인간 시작 후 서버 공통 startAt은 약2초 뒤다.','remote는 인간 요청 뒤 GPU 예약을 기다리고 PC begin 수락 시 약2초 뒤 공통 startAt을 확정한다. queued에는 round·질문·사진·시작 시각이 없고 타이머0이다.',1)
text=text.replace('제출 버튼의1초 제외는 운영 가안','제출 버튼의1초 제외·GPU 대기120초 상한은 운영 가안',1)
text=text.replace('추론은 공유 잠금으로 직렬화하고 GPU 대기와 추론 시간을 따로 기록한다.','queued 관측 등록순 FIFO로 예약을 받고 begin·카운트다운·공개 RGB 추론까지 보유한 뒤 선택 전에 해제한다. 단일 실행기의 등록순이며 서버 전역 순서/동일 네트워크 지연 보장은 아니다. 예약 대기·모델 함수·상태 HTTP를 schema2로 분리하고 v8 시간과 직접 속도 비교하지 않는다.',1)
new='- 사용자 요청의 수정 적용을 위해 기존 운영용 체인을 검증한 뒤 재시작했다. 최신 PC 콘솔은 CUDA 세 모델을 한 번 로드11.812초에 완료했고 켜 두었다. 운영 콘솔 A/B 코드 입력은0이며 특정 방의 준비와 모델 로드를 구분한다. 업데이트 재시작은 메모리 토큰을 잃어 최초 새 방 연결이 한 번 필요하고, 정상 참가자 교체에는 같은 방을 유지한다. PID·시작 기록·실제 QA 결과는 STATUS가 정본이다.'
text,n=re.subn(r'^- 사용자가 후속으로 “지금 PC 봇을 켜 달라”고 요청해.*$',new,text,count=1,flags=re.M);assert n==1
text=text.replace('## 현재 구현 경계 (2026-10-27)','프로토콜2 heartbeat는 requestId·roundId·roundNumber를 묶고 begin/cancel은 요청ID·revision을 검사한다. 구형 엔진은 기존 진행 판을 마칠 수 있으나 새 예약 출발은 거부한다. 첫 신규 참가의 명시적 지원false lobby만 부트스트랩해 첫 protocol2 알림으로 지원을 확정한다. 취소·오류·15초 생존 만료·대기120초 만료는 lobby로 돌아가 수동 시작을 요구한다.\n\n## 현재 구현 경계 (2026-10-27)',1)
text=review(text,'공정성 상담','사용자 승인으로 GPU 예약 후 공통 출발·취소/만료/구버전 보호·모델 반환 후 해제를 구현하고 버전9에 반영했다. 관리13개 전체를 분담 재검토했으며 실제 검사/게시/운영용 재시작은 STATUS에 기록한다. 모델/학교/1초/40%/Pi 경계를 유지하고 새 대기 화면의 실제 렌더링은 브라우저 도구 연결 종료로 미검증이다.')
path.write_text(text,encoding='utf-8')
path=root/'README.md';text=path.read_text(encoding='utf-8')
text=text.replace('봇 준비 후 인간이 시작하면 약2초 뒤 공통 서버 시각부터 타이머가 흐릅니다.','인간 시작 요청 뒤 GPU 차례를 기다리고 PC가 예약을 확보하면 약2초 공통 카운트다운으로 출발합니다. 예약 대기에는 문제/사진이 공개되지 않고 타이머0이며 대기를 취소할 수 있습니다.',1)
text=text.replace('각 인간 화면에서 PC 준비와 AI 표시 연결을 확인한 뒤 참가자가 시작합니다. 약2초 공통 출발 후','각 인간 화면에서 PC 준비와 AI 표시 연결을 확인한 뒤 참가자가 시작을 요청합니다. GPU 대기 화면 뒤 약2초 공통 출발 후',1)
text,n=re.subn(r'^현재는 타이머가 시작된 뒤 GPU 차례를 기다리므로.*$','**시작 요청→GPU 예약 대기→해당 인간/AI 공통 출발→추론 후 GPU 해제**를 구현했습니다. 한 실행기의 FIFO 예약 대기를 경기 타이머 전에 처리하고, 이미 분석한 방의 최소1초 간격 선택/제출과 다음 방의 준비/추론을 겹칠 수 있습니다. 대기 취소·연결 만료·오류는 대기실로 돌아갑니다. GPU 대기120초 상한은 운영 가안입니다. 새 출발에는 최신 프로토콜2 PC 실행기가 필요합니다. 이번 업데이트 재시작 후에는 새 방으로 한 번 연결하고 이후 참가자 교체는 같은 방을 유지합니다. 사전 문제 풀이·사후 시간 보정은 하지 않습니다. 네트워크/질문별 모든 지연을 같게 보장하는 것은 아닙니다.',text,count=1,flags=re.M);assert n==1
text=review(text,'공정성 상담','GPU 예약 출발 승인에 따라 실제 서버/PC/UI 계약과 운영 순서를 교정했다. queued의 타이머0·무문제·취소와 프로토콜2 업데이트를 반영하고 같은 방/1초/고정 모델을 유지했다. 실제 검사와 버전9 게시/엔진 가동은 STATUS가 정본이며 브라우저 연결 종료로 새 대기 화면 실제 렌더링은 미검증이다. 학교/40%/Pi/현장 리허설 한계를 유지한다.')
path.write_text(text,encoding='utf-8')
path=root/'docs/README.md';text=path.read_text(encoding='utf-8')
text=text.replace('4종·공통 시계·원격 선택/회차 생존·다음 참가자 API·기존 OS','4종·GPU 예약 출발/취소·공통 시계·회차 생존·다음 참가자·기존 OS',1)
text=review(text,'공정성 상담','관리13개 색인과 전체 본문을 GPU 예약 출발 구현에 맞춰 대조했다. queued/프로토콜2·begin/cancel·0002 migration·실제 QA·업데이트 최초 재연결 위치를 확인했다. 새 Markdown은 없고 게시/검사/가동과 브라우저 미검증 정본은 STATUS다. 모델/학교/1초/40%/Pi·현장 리허설 경계를 유지한다.')
path.write_text(text,encoding='utf-8')
print('Updated AGENTS, root README and documentation index for GPU reservation starts.')
