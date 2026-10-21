"""메리츠 연동 탭 값: 원본 머리글, 주식 탭, 메리츠 상세 탭 (모두 그 슬롯의 원본 탭을 읽는 수식). 계좌 슬롯마다 한 벌."""
from layout import MERITZ_SLOTS, Slot, v

HOLD_FIRST, HOLD_LAST = 11, 110      # 메리츠원본 종목 블록 데이터 행
STOCK_FIRST, STOCK_LAST = 16, 115    # 주식 탭 종목 표 데이터 행
STATUS_NAMES = ["총자산", "보유종목", "해외보유", "외화예수금"]
SUMMARY_LABELS = ["총자산", "원화 현금", "유가증권 평가", "외화 예수금(원)", "대출", "자동투자 인출가능", "순자산", "갱신 시각"]
FX_HEADERS = ["통화", "예수금", "환율", "예수금(원)", "해외주식 평가(원)"]
RAW_HOLD_HEADERS = ["구분", "티커", "종목명", "수량", "평단가(원)", "매입금액(원)", "평가금액(원)", "평가손익(원)",
                    "대출(원)", "통화", "평단가(외화)", "현재가(외화)", "매입금액(외화)", "평가금액(외화)"]
STOCK_HEADERS = ["구분", "티커", "종목명", "수량", "평단가(원)", "현재가(원)", "매입금액(원)", "평가금액(원)",
                 "평가손익(원)", "수익률(원)", "통화", "평단가(외화)", "현재가(외화)", "평가금액(외화)", "수익률(외화)", "비중"]


def status_text(raw: str) -> str:
    return (f'=IF(COUNTA({raw}!B2:B5)=0,"아직 갱신 전",'
            f'TEXTJOIN("  ·  ",TRUE,ARRAYFORMULA({raw}!A2:A5&": "&{raw}!B2:B5)))')


def col(c: str, raw: str) -> str:
    """원본 탭 종목 블록의 한 열."""
    return f"{raw}!{c}{HOLD_FIRST}:{c}{HOLD_LAST}"


def _show(expr: str, raw: str) -> str:
    return f'=ARRAYFORMULA(IF({col("A", raw)}="","",{expr}))'


def _copy(c: str, raw: str) -> str:
    return _show(f'IF({col(c, raw)}="","",{col(c, raw)})', raw)


def _num_or_dash(cell: str) -> str:
    return f'=IF(ISNUMBER({cell}),{cell},"-")'


def raw_values(s: Slot) -> list[dict]:
    r = s.raw
    return [v(f"{r}!A1:E1", [["조회", "상태", "코드", "메시지", "마지막 성공"]]),
            v(f"{r}!A2:A5", [[n] for n in STATUS_NAMES]),
            v(f"{r}!G1:G8", [[n] for n in SUMMARY_LABELS]),
            v(f"{r}!J1:N1", [FX_HEADERS]),
            v(f"{r}!A10:N10", [RAW_HOLD_HEADERS])]


def _stock_row(r: str) -> list[str]:
    def c(x):
        return col(x, r)
    return [_copy("A", r), _copy("B", r), _copy("C", r), _copy("D", r), _copy("E", r),
            _show(f'IFERROR({c("G")}/{c("D")},"")', r),
            _copy("F", r), _copy("G", r), _copy("H", r),
            _show(f'IFERROR({c("H")}/{c("F")},"")', r),
            _copy("J", r), _copy("K", r), _copy("L", r), _copy("N", r),
            _show(f'IFERROR(({c("N")}-{c("M")})/{c("M")},"")', r),
            _show(f'IFERROR({c("G")}/SUM({c("G")}),"")', r)]


def stock_values(s: Slot) -> list[dict]:
    r, st = s.raw, s.stock
    summary = [_num_or_dash(f"{r}!H7"), _num_or_dash(f"{r}!H3"), _num_or_dash(f"{r}!H2"), _num_or_dash(f"{r}!H4"),
               f'=IF(COUNTA({col("A", r)})=0,"-",SUM({col("H", r)}))',
               f'=IFERROR(SUM({col("H", r)})/SUM({col("F", r)}),"-")',
               _num_or_dash(f"{r}!H6")]
    return [v(f"{st}!A1", [[f"{s.owner} 메리츠증권 보유 주식"]]),
            v(f"{st}!G1:I1", [["지금 갱신", False, "◀ 체크하면 바로 갱신 (1~2분)"]]),
            v(f"{st}!A2:B2", [["상태", status_text(r)]]),
            v(f"{st}!A3:B3", [["마지막 갱신", f'=IF(ISNUMBER({r}!H8),{r}!H8,"아직 갱신 전")']]),
            v(f"{st}!A5:G5", [["순자산", "유가증권 평가", "원화 현금", "외화 예수금(원)", "평가손익", "수익률", "자동투자 인출가능"]]),
            v(f"{st}!A6:G6", [summary]),
            v(f"{st}!A8:E8", [FX_HEADERS]),
            v(f"{st}!A9", [[f'=ARRAYFORMULA(IF({r}!J2:J6="","",{r}!J2:N6))']]),
            v(f"{st}!A15:P15", [STOCK_HEADERS]),
            v(f"{st}!A16:P16", [_stock_row(r)])]


def meritz_values(s: Slot) -> list[dict]:
    r, m, st = s.raw, s.meritz, s.stock
    def c(x):
        return col(x, r)
    mk, hsum = f"{r}!H3", f'SUM({c("G")})'
    ov, fx = f'SUMIF({c("A")},"해외",{c("G")})', f"SUM({r}!N2:N6)"
    check = (f'=IF(NOT(ISNUMBER({mk})),"-",IF(OR(ABS({hsum}-{mk})>ABS({mk})*0.01,'
             f'ABS({ov}-{fx})>MAX(1,ABS({fx}))*0.01),'
             f'"⚠ 종목 합계가 증권사 평가금액과 1% 넘게 다릅니다 — 조회 시차 또는 데이터 오류","정상"))')
    count = (f'=IF(COUNTIF({c("A")},"?*")=0,"-",COUNTIF({c("A")},"?*")&"개 ("&'
             f'COUNTIF({c("H")},">0")&" / "&COUNTIF({c("H")},"<0")&")")')
    by_kind = [[k, f'=SUMIF({c("A")},"{k}",{c("G")})'] for k in ("국내", "해외", "기타")]
    return [v(f"{m}!A1", [[f"{s.owner} 메리츠증권 상세"]]),
            v(f"{m}!A2:B2", [["상태", status_text(r)]]),
            v(f"{m}!A3:B3", [["검산", check]]),
            v(f"{m}!A5:D5", [["순자산", "평가손익", "수익률", "보유 종목 (수익 / 손실)"]]),
            v(f"{m}!A6:D6", [[f"={st}!A6", f"={st}!E6", f"={st}!F6", count]]),
            v(f"{m}!A9:B12", [["자산 구성", "금액"], ["유가증권", f"=N({r}!H3)"],
                              ["원화 현금", f"=N({r}!H2)"], ["외화 예수금", f"=N({r}!H4)"]]),
            v(f"{m}!D9:E12", [["구분", "평가금액(원)"]] + by_kind)]


def all_values() -> list[dict]:
    return [e for s in MERITZ_SLOTS for e in raw_values(s) + stock_values(s) + meritz_values(s)]
