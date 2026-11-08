"""주간 보고서(마크다운, 로컬 전용 — 금액 포함). 카톡에는 비율만 담은 요약을 보낸다."""
from __future__ import annotations

from ..rules.engine import Finding

ICON = {"ok": "통과", "warn": "경고", "block": "차단"}


def _eok(v: float) -> str:
    return f"{v / 1e8:,.1f}억"


def render(summary: dict, findings: list[Finding], risk_used: dict, policy: dict, auctions: list, round_res=None) -> str:
    L = [f"# 주간 보고 · {summary['date']}", ""]
    L += ["## 포트폴리오", "",
          f"- 순자산: {_eok(summary['abs_net_worth'])} (고점 {_eok(summary['abs_peak'])})",
          f"- 고점 대비 낙폭: {summary['drawdown']:.1%} / 한도 {policy['drawdown']['limit']:.0%}",
          f"- 월 투자현금흐름: {summary['abs_monthly_income'] / 1e4:,.0f}만 원 / 목표 {policy['cashflow_target_monthly'] / 1e4:,.0f}만 원", ""]
    L += ["| 버킷 | 비중 | 사용 위험 | 위험 예산 |", "|---|---|---|---|"]
    scope = policy.get("budget_scope", list(risk_used))
    for b, w in summary["bucket_weights"].items():
        if b in scope or b == "B0_safety":
            L.append(f"| {b} | {w:.1%} | {risk_used[b]:.2%} | {policy['risk_budget'][b]:.0%} |")
        else:
            L.append(f"| {b} | {w:.1%} | (최악 {risk_used[b]:.1%}) | 실제 낙폭으로 관리 |")
    L += ["", "## 규칙 점검", ""] + [f"- [{ICON[f.level]}] {f.rule}: {f.message}" for f in findings]
    L += ["", "## 석촌호수 1호 경매 후보", ""]
    passed = [a for a in auctions if a.passed]
    if passed:
        L += ["| 사건번호 | 주소 | 예상 낙찰가 | 총비용 | 감정가 대비 할인 |", "|---|---|---|---|---|"]
        L += [f"| {a.case_no} | {a.address} | {_eok(a.expected_bid)} | {_eok(a.total_cost)} | {a.discount_vs_appraisal:.0%} |" for a in passed]
    else:
        L.append("- 이번 주 조건을 통과한 물건이 없습니다.")
    L += ["", f"<details><summary>탈락 {len(auctions) - len(passed)}건 사유</summary>", ""]
    L += [f"- {a.case_no}: {', '.join(a.reasons)}" for a in auctions if not a.passed]
    L += ["", "</details>"]
    if round_res:
        L += ["", "## 3 AI 검토 라운드", "",
              f"- 라운드 {round_res.round_id} · 판정 **{round_res.decision}**",
              "- 라벨 매핑(오너 전용): " + ", ".join(f"{k}={v}" for k, v in round_res.mapping.items())]
        L += [f"- 사유: {r}" for r in round_res.reasons] or ["- 사유 없음"]
        ok = sum(v == "재현됨" for v in round_res.verification.values())
        L.append(f"- 근거 재현: {ok}/{len(round_res.verification)}")
    return "\n".join(L) + "\n"
