"""경공매 감시: 물건 목록 CSV를 감시 조건으로 걸러 후보와 탈락 사유를 낸다.

데이터 입력은 CSV다. 법원경매·온비드 자료를 이용 약관을 지키는 방식(수동 내보내기,
유료 데이터 제공사 API 등)으로 받아 data/private/auctions.csv에 두면 된다.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _b(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "y", "yes", "예")


@dataclass
class Result:
    case_no: str
    address: str
    passed: bool
    reasons: list[str] = field(default_factory=list)
    expected_bid: float = 0.0
    total_cost: float = 0.0
    discount_vs_appraisal: float = 0.0
    row: dict = field(default_factory=dict)


def load_watch(path: str | Path = "config/auction_watch.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def evaluate(row: dict, w: dict) -> Result:
    r = Result(case_no=row["case_no"], address=row["address"], passed=True, row=row)
    fail = r.reasons.append
    if not any(reg in row["address"] for reg in w["regions"]):
        fail("감시 지역 밖")
    if row["use"] not in w["uses"]:
        fail(f"용도 불일치({row['use']})")
    if int(row["floor"]) not in w["floors"]:
        fail(f"층 조건 불일치({row['floor']}층)")
    a = float(row["area_pyeong"])
    if not (w["area_pyeong"]["min"] <= a <= w["area_pyeong"]["max"]):
        fail(f"면적 {a}평 범위 밖")
    if int(row["failed_bids"]) > w["max_failed_bids"]:
        fail(f"유찰 {row['failed_bids']}회 초과")
    req = w.get("require", {})
    if req.get("elevator") and not _b(row["elevator"]):
        fail("엘리베이터 없음")
    if req.get("no_illegal_building") and _b(row["illegal_building"]):
        fail("위반건축물")
    if req.get("no_senior_tenant") and _b(row["senior_tenant"]):
        fail("대항력 있는 임차인")
    appraisal = float(row["appraisal"])
    min_bid = float(row["min_bid"])
    r.expected_bid = max(min_bid, appraisal * w["expected_bid_ratio"])
    r.total_cost = r.expected_bid * (1 + w["acquisition_tax_rate"]) + a * w["repair_cost_per_pyeong"]
    r.discount_vs_appraisal = 1 - r.expected_bid / appraisal
    if r.total_cost > w["max_total_cost"]:
        fail(f"총비용 {r.total_cost/1e8:.2f}억 > 상한 {w['max_total_cost']/1e8:.1f}억")
    r.passed = not r.reasons
    return r


def scan(csv_path: str | Path, w: dict) -> list[Result]:
    with open(csv_path, encoding="utf-8-sig") as f:
        results = [evaluate(row, w) for row in csv.DictReader(f)]
    results.sort(key=lambda x: (not x.passed, x.total_cost))
    return results
