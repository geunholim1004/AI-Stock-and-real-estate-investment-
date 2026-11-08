"""규칙 엔진: 투자정책서 한도를 기계적으로 판정한다. AI 의견은 여기서 무시된다."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Finding:
    level: str   # "block" | "warn" | "ok"
    rule: str
    message: str


def load_policy(path: str | Path = "config/policy.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def portfolio_findings(summary: dict, policy: dict) -> list[Finding]:
    out: list[Finding] = []
    re_w = summary["bucket_weights"].get("B4_realestate", 0)
    re_hit = re_w * policy["worst_case_drawdown"]["B4_realestate"]
    if re_hit >= policy["drawdown"]["warning"]:
        out.append(Finding("warn", "realestate_concentration",
                           f"부동산 비중 {re_w:.0%}: 시세 {policy['worst_case_drawdown']['B4_realestate']:.0%} 하락만으로 "
                           f"전체 낙폭 약 {re_hit:.1%} (한도 {policy['drawdown']['limit']:.0%})"))
    dd = summary["drawdown"]
    lim, warn = policy["drawdown"]["limit"], policy["drawdown"]["warning"]
    if dd >= lim:
        out.append(Finding("block", "drawdown", f"전체 자산 낙폭 {dd:.1%} ≥ 한도 {lim:.0%}: 모든 신규 투입 중단"))
    elif dd >= warn:
        out.append(Finding("warn", "drawdown", f"전체 자산 낙폭 {dd:.1%} ≥ 경고선 {warn:.0%}"))
    else:
        out.append(Finding("ok", "drawdown", f"낙폭 {dd:.1%}, 남은 한도 {lim - dd:.1%}"))
    if "safety_months" in summary:
        need = policy["safety_months"]
        m = summary["safety_months"]
        lvl = "ok" if m >= need else "warn"
        out.append(Finding(lvl, "safety", f"안전판 {m}개월분 (기준 {need}개월)"))
    return out


def current_risk_used(summary: dict, policy: dict) -> dict[str, float]:
    """버킷별 현재 사용 위험 = 버킷 비중 × 최악 하락률."""
    w = summary["bucket_weights"]
    wc = policy["worst_case_drawdown"]
    return {b: round(w.get(b, 0) * wc[b], 4) for b in wc}


def evaluate_proposal(proposal: dict, summary: dict, policy: dict) -> list[Finding]:
    """proposal 예: {"bucket": "B3_auction", "weight": 0.016, "worst_case": 0.30, "ticker": None}
    weight = 전체 자산 대비 투입 비중."""
    out = portfolio_findings(summary, policy)
    if any(f.level == "block" for f in out):
        out.append(Finding("block", "proposal", "낙폭 한도 도달 상태에서는 신규 제안을 받지 않습니다."))
        return out
    b = proposal["bucket"]
    weight = float(proposal["weight"])
    worst = float(proposal.get("worst_case", policy["worst_case_drawdown"][b]))
    add_risk = weight * worst
    used = current_risk_used(summary, policy)
    budget = policy["risk_budget"][b]
    base = used[b] if b in policy.get("budget_scope", list(used)) else 0.0
    if base + add_risk > budget + 1e-9:
        out.append(Finding("block", "risk_budget",
                           f"{b} 위험 예산 초과: 사용 {base:.2%} + 신규 {add_risk:.2%} > 예산 {budget:.0%}"))
    else:
        out.append(Finding("ok", "risk_budget", f"{b} 위험 {base + add_risk:.2%} / 예산 {budget:.0%}"))
    scope = policy.get("budget_scope", list(used))
    total = sum(v for k, v in used.items() if k in scope) + add_risk
    remain = policy["drawdown"]["limit"] - summary["drawdown"]
    if total > remain + 1e-9:
        out.append(Finding("block", "total_risk", f"최악 손실 합계 {total:.2%} > 남은 한도 {remain:.2%}"))
    if b not in ("B0_safety",) and weight > policy["single_position_cap"]:
        out.append(Finding("block", "single_cap", f"단일 비중 {weight:.1%} > 상한 {policy['single_position_cap']:.0%}"))
    t = proposal.get("ticker")
    if t and str(t) in [str(x) for x in policy.get("conflict_tickers", [])]:
        out.append(Finding("block", "conflict", f"이해상충 종목 {t}: 오너 사전 확인 필요"))
    return out


def verdict(findings: list[Finding]) -> str:
    if any(f.level == "block" for f in findings):
        return "보류"
    return "오너 승인 대기"
