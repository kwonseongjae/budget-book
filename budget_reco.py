"""[설정] 추천 예산 채우기 (2026-10-21 사용성 점검 B5): I12 라벨 + J12 체크박스. 체크하면 스크립트(fillBudgets)가
지난 3개월 평균으로 K:M 빈 예산 칸만 채우고 결과를 I13에 적는다 → I13은 값으로 쓰지 않는다(스크립트가 쓴 결과가 지워지지 않게)."""
from layout import SETTINGS, a1_to_grid, v
from layout import _rule

LABEL = f"{SETTINGS}!I12"
CHECK = f"{SETTINGS}!J12"


def values() -> list[dict]:
    return [v(LABEL, [["추천 예산 채우기 (지난 3개월 평균, 빈 칸만)"]]), v(CHECK, [[False]])]


def validation_requests() -> list[dict]:
    return [{"setDataValidation": {"range": a1_to_grid(CHECK), "rule": _rule("BOOLEAN")}}]
