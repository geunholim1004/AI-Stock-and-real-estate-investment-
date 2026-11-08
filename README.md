# Edward AI 투자 1인 기업 — 자동화 의사결정 시스템

세 AI(ChatGPT·Claude·Gemini)가 같은 자료를 독립적으로 검토하고, Python 규칙 엔진이 판정하며, 오너가 카톡 알림을 받고 승인하는 구조입니다.

```
자산 원장(로컬, 비공개) ─┐
경매 물건 CSV(비공개) ───┼─▶ 규칙 엔진 ─▶ 패킷(비율만, SHA-256)
                         │                   │
                         │       ┌───────────┴───────────┐
                         │   GPT · Claude · Gemini (블라인드 병렬, JSON만)
                         │       └───────────┬───────────┘
                         │          근거 재현(선언형 검사만)
                         │          익명 교차 검토(라벨 매 라운드 섞음)
                         │          판정(다수결 금지, critical 1건이면 보류)
                         └─▶ 주간 보고서(로컬) + 카톡 요약(나에게 보내기)
                                       ▼
                              오너 승인 → 오너가 직접 주문
```

## 문서

| 파일 | 역할 | 수정 권한 |
|---|---|---|
| `AI_COLLABORATION_CHARTER.md` | 세 AI의 최상위 지침 | 오너만 |
| `INVESTMENT_POLICY.md` | 투자정책서 v0.2 | 오너만 |
| `goals.yaml` | 5년 100억 목표와 점검 관문 | 오너만 |
| `config/policy.yaml` | 정책서의 기계 판정 수치 | 오너만 |
| `config/auction_watch.yaml` | 석촌호수 1호 경매 감시 조건 | 오너·AI 제안 |

AI 봇 계정(`re-bot-*`)이 위의 "오너만" 파일을 고치면 CI가 PR을 실패시킵니다(`scripts/guard_forbidden.py`).

## 바로 실행 (예시 데이터, 모의 AI)

```bash
pip install -e ".[dev]"
pytest -q
python -m office weekly                     # reports/weekly.md 생성
python -m office check --bucket B3_auction --weight 0.016 --worst 0.30
```

## 실제 데이터로 실행

1. `data/private/ledger.csv`에 자산 원장을 만듭니다. 형식은 `data/sample/ledger_sample.csv`와 같습니다. 이 폴더는 `.gitignore`로 저장소에 올라가지 않습니다.
2. 경매 물건은 `data/private/auctions.csv`에 둡니다. 법원경매·온비드 자료를 **이용 약관을 지키는 방법**(수동 내보내기, 유료 데이터 제공사 API)으로 받습니다. 사이트 무단 크롤링은 하지 않습니다.
3. 실행:

```bash
python -m office --ledger data/private/ledger.csv --expense 8150000 \
  weekly --auctions data/private/auctions.csv --live --send
```

## GitHub 설정 순서

1. **비공개(private)** 저장소를 만들고 이 폴더를 올립니다.
2. `.github/CODEOWNERS`에 오너 아이디(`@geunholim1004`)가 들어 있습니다.
3. Settings → Rules: `main`에 PR 필수, CI 통과 필수, Code owner 승인 필수, force push 금지를 켭니다.
4. Settings → Secrets and variables → Actions
   - Secrets: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `KAKAO_ACCESS_TOKEN`, `LEDGER_CSV_B64`, `AUCTIONS_CSV_B64`
   - Variables: `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `GEMINI_MODEL` (모델명은 코드에 고정하지 않습니다)
   - 원장 CSV는 `base64 -w0 data/private/ledger.csv`로 인코딩해 넣습니다.
5. 각 API 콘솔에서 **월 지출 한도**를 설정합니다.
6. 세 AI 봇은 GitHub App으로 따로 만들고(Contents·Pull requests 권한만), 각자 `ai/gpt/*`, `ai/claude/*`, `ai/gemini/*` 브랜치에서만 작업합니다.

## 카카오톡 '나에게 보내기'

카카오 개발자 콘솔에서 앱을 만들고, 카카오 로그인과 동의항목 `talk_message`를 켠 뒤, 본인 계정으로 받은 액세스 토큰을 `KAKAO_ACCESS_TOKEN`에 넣습니다. 액세스 토큰은 만료되므로 리프레시 토큰으로 갱신하는 절차가 필요합니다(다음 단계 과제). 토큰이 없으면 전송하지 않고 문구만 출력합니다.

## 안전 원칙

- AI는 JSON만 돌려줍니다. 코드 실행·커밋·주문 권한이 없습니다.
- AI에게 가는 패킷에는 금액이 없습니다(`ledger.redact`). 비율만 전달합니다.
- AI가 보낸 근거 검사는 `{"path","op","value"}` 형태의 선언형만 실행합니다. 코드 문자열은 실행하지 않습니다.
- 전체 자산 낙폭 15%에서 모든 신규 제안이 자동 보류됩니다.

## 다음 과제

- [ ] 대시보드(승인 카드, 버전 해시별 승인 기록)
- [ ] 카카오 토큰 자동 갱신
- [ ] 채권 금리 체크리스트·선행지수 국면 판정 모듈
- [ ] 기존 부동산 AI 프로젝트(ARIMAX, 수집 모듈)와 연결
- [ ] 퇴계원 1구역·서울 B 매도 조건 감시 모듈
