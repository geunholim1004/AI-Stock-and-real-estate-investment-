"""자산 원장: 스냅샷 CSV → 순자산, 버킷 비율, 고점 대비 낙폭, 월 투자현금흐름.

원장 실제 파일(data/private/)은 .gitignore로 저장소에 올리지 않는다.
AI에게는 summary()의 비율 값만 전달한다(헌장 원칙 4).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

BUCKETS = ["B0_safety", "B1_income", "B2_equity", "B3_auction", "B4_realestate"]


@dataclass
class Snapshot:
    date: str
    assets: float = 0.0
    liabilities: float = 0.0
    monthly_income: float = 0.0
    by_bucket: dict[str, float] = field(default_factory=lambda: {b: 0.0 for b in BUCKETS})

    @property
    def net_worth(self) -> float:
        return self.assets - self.liabilities


def load(path: str | Path) -> list[Snapshot]:
    snaps: dict[str, Snapshot] = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = row["date"]
            s = snaps.setdefault(d, Snapshot(date=d))
            share = float(row.get("share") or 1)
            value = float(row["value"]) * share
            bucket = row["bucket"]
            if bucket not in s.by_bucket:
                raise ValueError(f"알 수 없는 버킷: {bucket} ({row['item']})")
            s.assets += value
            s.by_bucket[bucket] += value
            s.liabilities += float(row.get("liability") or 0) * share
            s.monthly_income += float(row.get("monthly_income") or 0) * share
    return [snaps[k] for k in sorted(snaps)]


def summary(snaps: list[Snapshot], monthly_expense: float | None = None) -> dict:
    """최신 스냅샷 기준 비율 요약. 금액(abs_*)은 로컬 보고서에만 쓰고 AI 패킷에서는 제거한다."""
    if not snaps:
        raise ValueError("원장이 비어 있습니다.")
    cur = snaps[-1]
    peak = max(s.net_worth for s in snaps)
    nw = cur.net_worth
    out = {
        "date": cur.date,
        "drawdown": round(0.0 if peak <= 0 else max(0.0, (peak - nw) / peak), 4),
        "bucket_weights": {b: round(v / cur.assets, 4) if cur.assets else 0.0 for b, v in cur.by_bucket.items()},
        "abs_net_worth": nw,
        "abs_peak": peak,
        "abs_monthly_income": cur.monthly_income,
        "abs_by_bucket": dict(cur.by_bucket),
    }
    if monthly_expense:
        out["safety_months"] = round(cur.by_bucket["B0_safety"] / monthly_expense, 1)
    return out


def redact(summary_dict: dict) -> dict:
    """AI에게 보낼 버전: abs_ 로 시작하는 금액 키를 모두 제거."""
    return {k: v for k, v in summary_dict.items() if not k.startswith("abs_")}
