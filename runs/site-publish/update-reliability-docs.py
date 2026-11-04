"""Reconcile owned entry documents; release evidence is recorded separately."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
review = ('이번 작업 검토: 2026-11-01 재개 시 실제 공개 서버는v11이고10/28 사진 준비 수정은 중단된 로컬 상태임을 확인했다. '
          '사진9장 사전 디코딩/3역할 준비/공통 출발·서버/PC 프로토콜 호환·불필요 통신과 시계 경합·같은 방 A/B 반복을 재검토했다. '
          '관리13개 전체 본문 검토와 실제 검사/배포/가동 정본은 STATUS/CHANGELOG에 기록한다. '
          '고정 모델·46장 RGB·250ms 선택·학교 미사용·40%/ONNX/Pi/legacy OS 미완료 경계를 유지한다. '
          '사진 수신을 경기 전에 옮기는 것과 네트워크 지연0/실제 동시 렌더링 보장은 구분한다.')

def entry(name):
    text = (root / name).read_text(encoding='utf-8-sig')
    text = re.sub(r'최종 검토: \d{4}-\d{2}-\d{2}', '최종 검토: 2026-11-01', text, count=1)
    text = re.sub(r'^이번 작업 검토:.*$', lambda m: '이전 작업 검토(선택 계획·사진 확대):' + m.group(0).split(':', 1)[1], text, flags=re.M)
    return text

def save(name, text):
    (root / name).write_text(text.rstrip() + '\n\n' + review + '\n', encoding='utf-8')

name = 'AGENTS.md'
t = entry(name)
t = t.replace('## 최신 확정 요구사항 (2026-10-27)', '## 최신 확정 요구사항 (2026-11-01)')
t = re.sub(r'^\| 출발 \|.*$', '| 출발 | remote 요청→GPU 예약→사진 준비 loading→인간/AI 표시/PC의9장 준비 확인→약2초 공통 출발. 대기는 타이머0·사진/질문 숨김, 실제 문제 추론은 출발 후·반환 뒤 GPU 해제 |', t, flags=re.M)
t = t.replace('remote는 인간 요청 뒤 GPU 예약을 기다리고 PC begin 수락 시 약2초 뒤 공통 startAt을 확정한다.', 'remote는 GPU 예약 뒤 loading에서 사진을 미리 받는다. 인간/AI 표시 브라우저9장 디코딩과 PC의 추론용RGB9장 수신이 모두 확인된 뒤 약2초 공통 startAt을 확정한다. loading의 시각은null·타이머0이며 질문/사진은 화면에 숨긴다. 출발 때 같은img/RGB를 재사용하고 문제 추론은 출발 후다.')
t = t.replace('표시 토큰은 준비/선택/제출을 할 수 없다.', '표시 토큰은 자기 화면의 사진 준비/철회만 알릴 수 있고 엔진 준비·타일 선택·답안 제출은 할 수 없다.')
t = t.replace('begin·카운트다운·공개 RGB 추론까지', 'begin·사진 준비·카운트다운·공개 RGB 추론까지')
t = re.sub(r'^프로토콜2 heartbeat는.*$', '새 서버의 출발에는 프로토콜3이 필요하다. heartbeat는 requestId·roundId·roundNumber, 사진 준비는 imageLoadId까지 검사한다. 출발 전 브라우저 재로드/준비 철회는 전역 준비 번호와3개 준비를 갱신하고 이전번호ACK를 거부한다. PC는 같은 회차·같은 순서의RGB만 재사용한다. 출발 후 재로드는 경기를 소급 정지하지 않는다. 구형 진행 판은 끝낼 수 있지만 새 서버의 사진 준비를 우회하는 출발은 거부한다. PC는 사진 준비 필드가 아예 없는v11에만 protocol2 호환을 사용한다. 취소·오류·15초 엔진 생존 만료·GPU대기120초/사진 준비60초 만료는 lobby로 돌아가 수동 시작을 요구한다. 실제 배포/검증 정본은 STATUS다.', t, flags=re.M)
t = t.replace('공개 문제은행24장 등록', '공개 문제은행46장 등록')
t = t.replace('내일 운영 순서는 docs/SETUP.md를 따른다.', '운영 순서는 docs/SETUP.md를 따른다.')
t = t.replace('## 일정\n', '## 일정\n\n2026-11-01 사용자 후속 요청으로 다음 행사는11/07(토)이며 이전 행사에서 겪은 지연/출발/버전 문제를 우선 수정하고 자체 검증→사용자 재검증을 진행한다. 지연0이나 행사장 리허설 완료를 측정 없이 주장하지 않는다.\n')
save(name, t)

name = 'README.md'
t = entry(name)
t = t.replace('인간 시작 요청 뒤 GPU 차례를 기다리고 PC가 예약을 확보하면 약2초 공통 카운트다운으로 출발합니다.', '인간 시작 요청 뒤 GPU 차례를 기다린 다음 사진9장을 미리 준비합니다. 인간 화면·AI 표시 화면의 사진 디코딩과 PC의RGB 수신이 모두 끝나야 약2초 공통 카운트다운으로 출발합니다. 준비 중 사진과 질문은 숨겨 두고 타이머는0입니다. 출발 때 이미 받은 사진을 그대로 표시하며 PC도 보관한RGB로 추론합니다.')
t = t.replace('GPU 대기 화면 뒤 약2초 공통 출발 후 인간은 타일 선택/정답 제출을 하고, AI는 PC에서 공개 RGB 최대3개 병렬 수신→ML 판별→고정 선택 목록 한 번 전송을 수행합니다.', 'GPU 대기→사진 준비 화면에서 인간/AI 표시/PC의9장 준비를 기다립니다. 두 브라우저는 사진9장을 실제 디코딩하고 PC는 최대3개 병렬로RGB를 받습니다. 모두 준비된 뒤 약2초 공통 출발하며 인간은 타일 선택/정답 제출, AI는 보관한RGB의ML 판별→고정 선택 목록 한 번 전송을 수행합니다. 준비 중 한쪽이 느리거나 사진 수신에 실패하면 먼저 출발시키지 않습니다.')
t = t.replace('AI 표시 화면에는 타일 수정·준비·제출 권한이 없습니다.', 'AI 표시 화면은 자기 사진 준비만 알리며 타일 수정·엔진 준비·답안 제출 권한은 없습니다.')
t = t.replace('표시 연결 등록은 실제 화면의 사진 로딩·생존까지 보증하지 않습니다.', '표시 연결 등록과 사진 준비는 별도입니다. 출발에는 해당 화면의9장 디코딩 확인이 필요하며 출발 전 페이지를 다시 열면 준비를 다시 확인합니다. 출발 후 새로고침은 이미 시작한 경기를 정지하지 않습니다.')
t = t.replace('**시작 요청→GPU 예약 대기→해당 인간/AI 공통 출발→추론 후 GPU 해제**', '**시작 요청→GPU 예약 대기→양쪽 화면/PC 사진 준비→공통 출발→추론 후 GPU 해제**')
t = t.replace('최신 프로토콜2 PC 실행기', '사진 준비를 지원하는 프로토콜3 PC 실행기')
t = t.replace('scripts/check_docs.py --date 2026-10-27', 'scripts/check_docs.py --date 2026-11-01')
t = t.replace('## 컴퓨터 브라우저 A/B 운영\n', '## 컴퓨터 브라우저 A/B 운영\n\n11/07(토) 행사 전 이번 배포의 자체 검증 결과를 STATUS에서 확인하고 운영 기기에서 다시 시험합니다. 사진 준비 대기와250ms 선택 간격은 의도된 절차이며 인터넷/브라우저의 모든 지연이0이 된다는 뜻은 아닙니다.\n')
save(name, t)

name = 'docs/README.md'
t = entry(name)
t = t.replace('GPU 예약 출발/취소·공통 시계', 'GPU 예약·3역할 사진 준비/취소·공통 시계')
t = t.replace('남은 작업과10/28 내부 임시 목표', '11/07 행사 전 검증·남은 작업과 과거 일정')
t = t.replace('python scripts/check_docs.py --date 2026-10-27', 'python scripts/check_docs.py --date 2026-11-01')
t += '\n현재 재개 작업은 사진 사전 디코딩/3역할 준비 후 출발과 통신/시계/프로토콜 복구다. 단위 검사, 실제 HTTP/PIL, 실제 브라우저/현장 측정을 구분하고 게시/가동 및 미검증 범위는 STATUS를 따른다.\n'
save(name, t)
print('Entry document bodies reviewed and reconciled: AGENTS.md, README.md, docs/README.md')
