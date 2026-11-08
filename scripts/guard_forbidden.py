"""헌장 7장 금지 구역 검사. PR 작성자가 봇(re-bot-*)이면 금지 경로 수정 시 실패한다.

사용: python scripts/guard_forbidden.py <author> <changed_file>...
"""
import sys

FORBIDDEN = (
    "AI_COLLABORATION_CHARTER.md",
    "INVESTMENT_POLICY.md",
    "goals.yaml",
    "config/policy.yaml",
    ".github/",
    "data/raw/",
    "scripts/guard_forbidden.py",
)
SECRET_HINTS = (".pem", ".env", "secret", "credential")


def main() -> int:
    author, files = sys.argv[1], sys.argv[2:]
    is_bot = author.startswith("re-bot-") or author.endswith("[bot]")
    bad = []
    for f in files:
        if any(h in f.lower() for h in SECRET_HINTS):
            bad.append(f"비밀 정보 의심 파일: {f}")
        if is_bot and any(f == p or f.startswith(p) for p in FORBIDDEN):
            bad.append(f"AI 금지 구역 수정: {f}")
    for b in bad:
        print("::error::" + b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
