"""사용법:
  python -m office weekly                 # 예시 데이터, 모의 AI
  python -m office weekly --ledger data/private/ledger.csv --auctions data/private/auctions.csv --expense 8150000 --live --send
  python -m office check --bucket B3_auction --weight 0.016 --worst 0.30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .auction import watch
from .ledger import ledger
from .orchestrator import round as rnd
from .report import kakao, weekly
from .rules import engine


def _summary(args):
    snaps = ledger.load(args.ledger)
    return ledger.summary(snaps, monthly_expense=args.expense)


def cmd_weekly(args) -> int:
    policy = engine.load_policy(args.policy)
    s = _summary(args)
    findings = engine.portfolio_findings(s, policy)
    risk = engine.current_risk_used(s, policy)
    auctions = watch.scan(args.auctions, watch.load_watch(args.watch))
    facts = {"summary": ledger.redact(s), "risk_used": risk,
             "auction_candidates": [{"case_no": a.case_no, "discount": round(a.discount_vs_appraisal, 3),
                                     "cost_to_assets": round(a.total_cost / s["abs_net_worth"], 4)}
                                    for a in auctions if a.passed]}
    packet = rnd.build_packet("이번 주 포트폴리오 상태와 경매 후보에 대한 위험·기회·반례를 검토하라.",
                              facts, "투자정책서 v0.2 한도 준수, 근거는 facts 경로로 재현 가능해야 함")
    res = rnd.run_round(packet, engine.verdict(findings), mock=not args.live)
    rnd.save(res, args.logs)
    md = weekly.render(s, findings, risk, policy, auctions, res)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    passed = sum(a.passed for a in auctions)
    lines = [f"낙폭 {s['drawdown']:.1%} / 한도 15%",
             f"경고·차단 {sum(f.level != 'ok' for f in findings)}건",
             f"경매 후보 {passed}건",
             f"AI 판정: {res.decision}"]
    text = kakao.card_text("AI 투자 1인 기업 주간 보고", lines, packet["packet_hash"])
    result = kakao.send(text, args.link) if args.send else {"sent": False, "text": text}
    print(md)
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_check(args) -> int:
    policy = engine.load_policy(args.policy)
    s = _summary(args)
    f = engine.evaluate_proposal({"bucket": args.bucket, "weight": args.weight,
                                  "worst_case": args.worst, "ticker": args.ticker}, s, policy)
    for x in f:
        print(f"[{x.level}] {x.rule}: {x.message}")
    v = engine.verdict(f)
    print("판정:", v)
    return 0 if v != "보류" else 2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="office")
    p.add_argument("--policy", default="config/policy.yaml")
    p.add_argument("--ledger", default="data/sample/ledger_sample.csv")
    p.add_argument("--expense", type=float, default=8_150_000, help="월 생활비(원)")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("weekly")
    w.add_argument("--auctions", default="data/sample/auction_sample.csv")
    w.add_argument("--watch", default="config/auction_watch.yaml")
    w.add_argument("--out", default="reports/weekly.md")
    w.add_argument("--logs", default="logs")
    w.add_argument("--live", action="store_true", help="실제 AI API 호출")
    w.add_argument("--send", action="store_true", help="카카오톡 전송")
    w.add_argument("--link", default="")
    w.set_defaults(fn=cmd_weekly)
    c = sub.add_parser("check")
    c.add_argument("--bucket", required=True)
    c.add_argument("--weight", type=float, required=True)
    c.add_argument("--worst", type=float)
    c.add_argument("--ticker")
    c.set_defaults(fn=cmd_check)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
