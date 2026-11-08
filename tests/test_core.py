import json
import subprocess
import sys
from pathlib import Path

import pytest

from office.auction import watch
from office.ledger import ledger
from office.orchestrator import round as rnd
from office.rules import engine

ROOT = Path(__file__).resolve().parents[1]
POLICY = engine.load_policy(ROOT / "config/policy.yaml")


def _summary():
    return ledger.summary(ledger.load(ROOT / "data/sample/ledger_sample.csv"), monthly_expense=8_150_000)


def test_ledger_net_worth_and_redact():
    s = _summary()
    assert abs(s["abs_net_worth"] - 2_356_000_000) < 1
    assert s["drawdown"] == 0
    assert abs(sum(s["bucket_weights"].values()) - 1) < 1e-3
    red = ledger.redact(s)
    assert not any(k.startswith("abs_") for k in red), "AI 패킷에 금액이 남으면 안 됨"


def test_drawdown_triggers(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("date,item,bucket,owner,share,value,liability,monthly_income,note\n"
                 "2026-01-31,a,B2_equity,본인,1,100,0,0,\n"
                 "2026-02-28,a,B2_equity,본인,1,84,0,0,\n", encoding="utf-8")
    s = ledger.summary(ledger.load(p))
    f = engine.portfolio_findings(s, POLICY)
    assert f[0].level == "block"
    v = engine.evaluate_proposal({"bucket": "B2_equity", "weight": 0.01}, s, POLICY)
    assert engine.verdict(v) == "보류"


def test_risk_budget_block_and_pass():
    s = _summary()
    ok = engine.evaluate_proposal({"bucket": "B3_auction", "weight": 0.016, "worst_case": 0.30}, s, POLICY)
    assert engine.verdict(ok) == "오너 승인 대기"
    big = engine.evaluate_proposal({"bucket": "B3_auction", "weight": 0.20, "worst_case": 0.30}, s, POLICY)
    assert engine.verdict(big) == "보류"


def test_conflict_ticker_blocked():
    s = _summary()
    f = engine.evaluate_proposal({"bucket": "B2_equity", "weight": 0.001, "ticker": "005930"}, s, POLICY)
    assert any(x.rule == "conflict" for x in f)


def test_auction_filter():
    w = watch.load_watch(ROOT / "config/auction_watch.yaml")
    res = {r.case_no: r for r in watch.scan(ROOT / "data/sample/auction_sample.csv", w)}
    assert res["2026타경10001"].passed
    assert res["2026타경10007"].passed
    assert not res["2026타경10003"].passed      # 1층
    assert not res["2026타경10004"].passed      # 엘리베이터
    assert not res["2026타경10005"].passed      # 대항력 임차인
    assert not res["2026타경10006"].passed      # 지역 밖
    assert all(r.total_cost <= w["max_total_cost"] for r in res.values() if r.passed)


def test_verify_claim_declarative_only():
    pkt = {"facts": {"summary": {"drawdown": 0.05}}}
    ok = {"evidence": {"check": {"path": "facts.summary.drawdown", "op": "<", "value": 0.1}}}
    bad = {"evidence": {"check": {"path": "facts.summary.drawdown", "op": ">", "value": 0.1}}}
    code = {"evidence": {"check": "__import__('os').system('rm -rf /')"}}
    assert rnd.verify_claim(ok, pkt) == "재현됨"
    assert rnd.verify_claim(bad, pkt) == "재현 실패"
    assert rnd.verify_claim(code, pkt) == "확인 방법 없음"


def test_round_mock_and_anonymity():
    s = _summary()
    pkt = rnd.build_packet("q", {"summary": ledger.redact(s)}, "a", goals_path="none")
    assert "abs_net_worth" not in json.dumps(pkt)
    res = rnd.run_round(pkt, "오너 승인 대기", mock=True, seed=1)
    assert sorted(res.mapping.values()) == ["claude", "gemini", "gpt"]
    assert res.decision == "오너 승인 대기"


def test_judge_critical_objection_holds():
    res = rnd.RoundResult("R", "h", {"A": "gpt", "B": "claude", "C": "gemini"})
    res.reviews = {"gpt": {"claims": [{"id": "C1", "severity": "critical"}]}, "claude": {}, "gemini": {}}
    res.cross = {"claude": {"objections_to_others": [{"target": "A.C1", "verdict": "반박"}]}, "gpt": {}, "gemini": {}}
    d, reasons = rnd.judge(res, "오너 승인 대기")
    assert d == "보류" and "critical" in reasons[0]


@pytest.mark.parametrize("author,files,code", [
    ("re-bot-gpt[bot]", ["config/policy.yaml"], 1),
    ("re-bot-claude[bot]", ["src/office/auction/watch.py"], 0),
    ("edward", ["config/policy.yaml"], 0),
    ("edward", ["keys/app.pem"], 1),
])
def test_guard(author, files, code):
    r = subprocess.run([sys.executable, str(ROOT / "scripts/guard_forbidden.py"), author, *files], check=False)
    assert r.returncode == code
