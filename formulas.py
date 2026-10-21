"""핵심 수식: 내역 계산열, 환율, 계산, 자산 잔액, 대시보드."""
from charts import pie_labels
from layout import ASSETS, CALC, DASH, INVEST, INVEST_ACCOUNTS, MONTH_FMT, MONTH_MOVE_HINT, RECUR, SETTINGS, TXN, number_format, v

START = "설정!$J$2"
AMT, YM, TYPE, CAT = "내역!$K:$K", "내역!$L:$L", "내역!$C:$C", "내역!$D:$D"
MAJOR = "내역!$M:$M"
USER, ASSET, TO_ASSET, DATE_COL = "내역!$B:$B", "내역!$F:$F", "내역!$G:$G", "내역!$A:$A"
INC, EXP, TRF = '"수입"', '"지출"', '"이체"'
# 나가는 돈 = 수입·이체가 아닌 모든 구분 (지출 + 설정에서 추가한 저축 등)
OUTFLOW = ((TYPE, '"<>"'), (TYPE, '"<>수입"'), (TYPE, '"<>이체"'))

TABLE_HEAD, UNCAT_ROW, CAT_FIRST, CAT_LAST = 60, 61, 62, 91
SIDE_FIRST, SIDE_LAST = 61, 76  # 사용자·카드 표


def sumifs(*conds: tuple[str, str]) -> str:
    """원화금액 합계. conds = (범위, 조건) 쌍."""
    return "SUMIFS(" + ",".join([AMT] + [f"{rng},{crit}" for rng, crit in conds]) + ")"


def ym_of(expr: str) -> str:
    """날짜 → 월 시작일 기준 귀속월 숫자 키(YYYYMM)."""
    first = f"DATE(YEAR({expr}),MONTH({expr})-(DAY({expr})<{START}),1)"
    return f"YEAR({first})*100+MONTH({first})"


def month_pick(cell: str) -> str:
    """보기 탭 월 선택칸 → 숫자 YYYYMM. 비면 이번 달, 텍스트 '2026-10'·날짜로 들어와도 처리."""
    return (f'LET(pick,{cell},IF(pick="",{CALC}!$C$2,IF(ISTEXT(pick),VALUE(SUBSTITUTE(pick,"-","")),'
            f'IF(pick>=100000,pick,YEAR(pick)*100+MONTH(pick)))))')


def by_major(cols: str = "A") -> str:
    """설정 카테고리(수입 제외)를 대분류 순(고정비 → 변동비 → 빈칸)으로. 같은 대분류 안은 설정 순서 그대로."""
    cond = f'{SETTINGS}!$A$2:$A<>"",{SETTINGS}!$B$2:$B<>"수입"'
    return f'IFERROR(SORT(FILTER({SETTINGS}!$A$2:${cols},{cond}),FILTER({SETTINGS}!$D$2:$D,{cond}),TRUE),"")'


def per_row(rng: str, body: str) -> str:
    """rng 각 칸을 x로 받아 body 계산. 빈 칸은 빈 값."""
    return f'MAP({rng},LAMBDA(x,IF(x="","",{body})))'


def txn_values() -> list[dict]:
    # 외화는 N(적용 환율 = 입력 시점에 스크립트가 고정)을 먼저, 없으면 설정 통화표의 실시간 환율
    rate = 'IFERROR(H:H*IF((I:I="")+(I:I="KRW"),1,IF(ISNUMBER(N:N),N:N,VLOOKUP(I:I,설정!$G:$H,2,FALSE))),"환율오류")'
    krw = f'IF(ISNUMBER(H:H),{rate},"금액오류")'  # 금액이 글자(12,000원 등)면 환율 탓이 아니라 금액 탓
    return [
        v(f"{TXN}!K1", [[f'=ARRAYFORMULA(IF(ROW(H:H)=1,"원화금액",IF(H:H="","",{krw})))']]),
        v(f"{TXN}!L1", [[f'=ARRAYFORMULA(IF(ROW(A:A)=1,"귀속월",IF(A:A="","",IFERROR({ym_of("A:A")},"날짜오류"))))']]),
        v(f"{TXN}!M1", [['=ARRAYFORMULA(IF(ROW(D:D)=1,"대분류",IF(D:D="","",IFERROR(VLOOKUP(D:D,설정!$A:$D,4,FALSE),""))))']]),
    ]


def settings_values() -> list[dict]:
    rate = '=IF(G{r}="","",IF(G{r}="KRW",1,GOOGLEFINANCE("CURRENCY:"&G{r}&"KRW")))'
    # 월 예산 = 사람별 예산(K:M) 합계. 0이면 빈 칸(예산 없음 → 사용률 표시 안 함)
    total = ('=ARRAYFORMULA(IF(ROW(A:A)=1,"월 예산(합계)",IF(A:A="","",'
             'IF(K:K+L:L+M:M=0,"",K:K+L:L+M:M))))')
    return [v(f"{SETTINGS}!H1:H20", [["환율(원)"]] + [[rate.format(r=r)] for r in range(2, 21)]),
            v(f"{SETTINGS}!C1", [[total]])]


def calc_values() -> list[dict]:
    months = '=IFERROR(SORT(UNIQUE(FILTER(내역!L2:L,ISNUMBER(내역!L2:L))),1,FALSE),"")'
    years = '=IFERROR(SORT(UNIQUE(FILTER(INT(내역!L2:L/100),ISNUMBER(내역!L2:L))),1,FALSE),"")'
    # 구분 목록: 수입·지출 + 설정 B열에 사용자가 새로 적은 구분. D는 내역용(이체 포함)
    types = ('=UNIQUE({"수입";"지출";IFERROR(FILTER(설정!B2:B,설정!B2:B<>"",설정!B2:B<>"이체"),"수입")})')
    with_trf = '=UNIQUE({FILTER(E2:E,E2:E<>"");"이체"})'
    return [v(f"{CALC}!A1:C2", [["월목록", "연도목록", "현재월"], [months, years, f"={ym_of('TODAY()')}"]]),
            v(f"{CALC}!D1:E2", [["구분(이체 포함)", "구분"], [with_trf, types]]),
            v(f"{CALC}!C4", [["자동 갱신일 (스크립트가 씀)"]]),  # C5 = dailyJob이 쓴 날짜 → 모든 탭 '업데이트일'. 값은 여기서 쓰지 않는다
            *type_category_lists()]


def type_category_lists() -> list[dict]:
    """계산 G1:P1 = 구분 이름(최대 10개), 그 아래 = 그 구분의 카테고리 목록. 카테고리 드롭다운이 행의 구분별로 참조."""
    head = '=ARRAY_CONSTRAIN(TRANSPOSE(FILTER(E2:E,E2:E<>"")),1,10)'
    cols = [chr(ord("G") + i) for i in range(10)]
    lists = [f'=IF({c}1="","",IFERROR(FILTER(설정!$A$2:$A,설정!$B$2:$B={c}1),""))' for c in cols]
    return [v(f"{CALC}!G1", [[head]]), v(f"{CALC}!G2:P2", [lists])]


A_NAMES, A_KINDS, A_OWNERS, A_TARGETS = "자산!$A$2:$A$50", "자산!$B$2:$B$50", "자산!$I$2:$I$50", "자산!$D$2:$D$50"
# 카드 목록: 같은 이름 카드가 둘 이상이면 '하나카드 (신부)'처럼 소유자를 붙여 구분 (2026-10-14 하나카드 ×2)
CARD_LABELS = (f'=IFERROR(LET(n,FILTER({A_NAMES},{A_KINDS}="카드"),o,FILTER({A_OWNERS},{A_KINDS}="카드"),'
               f'MAP(n,o,LAMBDA(a,b,IF(COUNTIF({A_NAMES},a)>1,a&" ("&b&")",a)))),"")')


def _card_parts(x: str) -> str:
    return f'nm,REGEXREPLACE({x}," \([^)]*\)$",""),ow,IFERROR(REGEXEXTRACT({x},"\(([^)]*)\)$"),"")'


def card_usage(x: str, month: str, kind: tuple = ((TYPE, EXP),)) -> str:
    """카드 목록 이름(소유자 표시 포함) → 그 달 사용액. 소유자가 붙어 있으면 그 사람이 쓴 것만."""
    base = sumifs((YM, month), *kind, (ASSET, "nm"))
    mine = sumifs((YM, month), *kind, (ASSET, "nm"), (USER, "ow"))
    return f'LET({_card_parts(x)},IF(ow="",{base},{mine}))'


def card_target(x: str) -> str:
    return (f'LET({_card_parts(x)},IFERROR(INDEX(FILTER({A_TARGETS},{A_NAMES}=nm,(ow="")+({A_OWNERS}=ow)),1),""))')


def card_owner(x: str) -> str:
    return f'LET({_card_parts(x)},IF(ow<>"",ow,IFERROR(INDEX(FILTER({A_OWNERS},{A_NAMES}=nm),1),"")))'


def dashboard_cards(head: int) -> list[dict]:
    """대시보드 카드 표(I~K열): 머리글 head행 아래 16줄. 운영은 head가 19."""
    a, z = head + 1, head + 16
    cards = f"I{a}:I{z}"
    return [v(f"{DASH}!I{a}", [[CARD_LABELS]]),
            v(f"{DASH}!J{a}", [[f'={per_row(cards, card_usage("x", "$B$2"))}']]),
            v(f"{DASH}!K{a}", [[f'={per_row(cards, card_target("x"))}']])]


def _own_sum(*conds) -> str:
    """같은 이름 자산이 둘 이상이면(하나카드 신랑·신부) 그 자산 소유자가 적은 내역만."""
    return f'IF(COUNTIF($A$2:$A$50,x)>1,{sumifs(*conds, (USER, "own"))},{sumifs(*conds)})'


def asset_values() -> list[dict]:
    inc = _own_sum((ASSET, "x"), (TYPE, INC))
    exp = _own_sum((ASSET, "x"), *OUTFLOW)
    out = _own_sum((ASSET, "x"), (TYPE, TRF))
    in_ = _own_sum((TO_ASSET, "x"), (TYPE, TRF))
    # 적립 카테고리(F열): 그 카테고리로 나간 돈(저축 등)이 이 자산에 쌓인다 (예: 주택청약 → 우리은행_주택청약).
    # 소유자(I열)가 사람이면 그 사람이 적은 것만 — 부부가 같은 카테고리로 각자 통장에 넣기 때문. 비었거나 공동이면 전부.
    everyone = sumifs((CAT, "link"), *OUTFLOW)
    mine = sumifs((CAT, "link"), *OUTFLOW, (USER, "own"))
    saved = f'IF(link="",0,IF(OR(own="",own={SETTINGS}!$E$4),{everyone},{mine}))'
    bal = f"init+{inc}-{exp}-{out}+{in_}+{saved}"
    # 연동(G열)에 고른 계좌의 [투자] 탭 최종 평가금액(직접입력 우선). 값이 없으면 기존 계산으로 되돌림.
    choices = "{" + ",".join(f'"{n}"' for n, _r in INVEST_ACCOUNTS) + "}"
    pick = lambda col: (f'IFERROR(CHOOSE(MATCH(sync,{choices},0),'
                        + ",".join(f"{INVEST}!${col}${r}" for _n, r in INVEST_ACCOUNTS) + '),"")')
    synced = f'LET(net,{pick("B")},IF(AND(sync<>"",ISNUMBER(net)),net,{bal}))'
    # 통화(J)가 외화이고 외화 잔액(K)이 있으면 실시간 환율로 환산 (달러통장 등)
    valued = (f'LET(krw,{synced},IF(AND(cur<>"",cur<>"KRW",ISNUMBER(fx)),'
              f'IFERROR(fx*GOOGLEFINANCE("CURRENCY:"&cur&"KRW"),krw),krw))')
    status = (f'IF(OR(x="",sync=""),"",LET(net,{pick("B")},at,{pick("F")},IF(NOT(ISNUMBER(net)),"미갱신",'
              f'IF(NOT(ISNUMBER(at)),"직접입력",IF(NOW()-at>3,"오래됨 ("&TEXT(at,"mm/dd")&")",'
              f'"연동 "&TEXT(at,"mm/dd hh:mm"))))))')
    return [v(f"{ASSETS}!E1:E2", [["현재 잔액"],
                                  [f'=MAP(A2:A,C2:C,F2:F,G2:G,I2:I,J2:J,K2:K,LAMBDA(x,init,link,sync,own,cur,fx,'
                                   f'IF(x="","",{valued})))']]),
            v(f"{ASSETS}!H1:H2", [["연동 상태"], [f'=MAP(A2:A,G2:G,J2:J,K2:K,LAMBDA(x,sync,cur,fx,'
                                                  f'IF(AND(x<>"",cur<>"",cur<>"KRW",ISNUMBER(fx)),cur&" 환율 자동",{status})))']]),
            v(f"{ASSETS}!L1:L2", [["결제수단 목록"], [f'=IFERROR(FILTER(A2:A50,A2:A50<>"",'
                                                    f'ISNA(MATCH(B2:B50,{{"대출","연금","기타"}},0))),"")']])]


def recur_krw(col: str = "G", sheet_abs: bool = True) -> str:
    """[반복] 금액을 원화로: 통화(N)가 비었거나 KRW면 그대로, 외화면 [설정] 통화표 환율을 곱한다. 배열 식(SUMPRODUCT 안·FILTER 안)."""
    a = lambda c: f"{RECUR}!${c}$2:${c}$50" if sheet_abs else f"{RECUR}!{c}2:{c}50"
    return (f'ARRAYFORMULA({a(col)}*IF(({a("N")}="")+({a("N")}="KRW"),1,'
            f'SUMIF({SETTINGS}!$G$2:$G$20,{a("N")},{SETTINGS}!$H$2:$H$20)))')


def projection(m: str) -> str:
    """월말 예상 지출 = 지금까지 지출 + (이번 달이면) 아직 안 생긴 반복 지출 + 변동비 일평균 × 남은 일수.
    고정비를 일평균으로 늘리면 월초 큰 고정비 때문에 몇 배로 부풀려진다."""
    now = f"{CALC}!$C$2"
    elapsed, days = "MAX(1,MIN(TODAY(),$C$3)-$B$3+1)", "($C$3-$B$3+1)"
    # SUMIFS의 "<>"&월 조건은 빈 칸(아직 한 번도 안 생긴 항목)을 빼 버린다 → SUMPRODUCT
    pending = (f'SUMPRODUCT({recur_krw()}*({RECUR}!$A$2:$A$50=TRUE)*({RECUR}!$D$2:$D$50="지출")'
               f'*({RECUR}!$I$2:$I$50<>{now}))')
    variable = sumifs((YM, m), (TYPE, EXP), (MAJOR, '"변동비"'))
    return f"=B6+IF({m}={now},{pending}+{variable}/{elapsed}*({days}-{elapsed}),0)"


def asset_status() -> dict:
    """대시보드 월간 숫자 줄 오른쪽(J5:L6): 지금 자산 현황. 운영 대시보드도 이 자리는 비어 있다."""
    return v(f"{DASH}!J5:L6", [["순자산", "주식 합계", "청약 합계"],
                              [f"=SUM({ASSETS}!E2:E50)", f"=N({INVEST}!A4)",
                               f'=SUMIFS({ASSETS}!E2:E50,{ASSETS}!B2:B50,"청약")']])


def dashboard_values() -> list[dict]:
    m, cats, users, cards = "$B$2", "A62:A91", "F61:F76", "I61:I76"
    prev = f"IF(MOD({m},100)=1,{m}-89,{m}-1)"
    top = [["조회 월", "", MONTH_MOVE_HINT],
           ["적용 월", f"={month_pick('B1')}", ""],
           ["기간", f"=DATE(INT({m}/100),MOD({m},100),{START})", "=EDATE(B3,1)-1"]]
    kpi = [["수입", "지출", "잔액", "전월 대비 지출", "일평균 지출", "월말 예상 지출", "저축·기타", "고정비", "변동비"],
           [f"={sumifs((YM, m), (TYPE, INC))}", f"={sumifs((YM, m), (TYPE, EXP))}", "=A6-B6-G6",
            f'=IFERROR(B6/{sumifs((YM, prev), (TYPE, EXP))}-1,"")',
            "=B6/MAX(1,MIN(TODAY(),$C$3)-$B$3+1)", projection(m),
            f"={sumifs((YM, m), *OUTFLOW, (TYPE, '\"<>지출\"'))}",
            f"={sumifs((YM, m), *OUTFLOW, (MAJOR, '\"고정비\"'))}",
            f"={sumifs((YM, m), *OUTFLOW, (MAJOR, '\"변동비\"'))}"]]
    head = [["카테고리", "지출", "예산", "사용률", "대분류", "사용자", "지출", "", "카드", "사용액", "실적 목표", "달성률"]]
    cat_row = [f"={by_major()}",
               f'={per_row(cats, sumifs((YM, m), *OUTFLOW, (CAT, "x")))}',
               f'=ARRAYFORMULA(IF({cats}="","",IFERROR(VLOOKUP({cats},{SETTINGS}!$A:$C,3,FALSE),"")))',
               '=ARRAYFORMULA(IF(A62:A91="","",IF((C62:C91="")+(C62:C91=0),"",B62:B91/C62:C91)))',
               f'=ARRAYFORMULA(IF({cats}="","",IFERROR(VLOOKUP({cats},{SETTINGS}!$A:$D,4,FALSE),"")))']
    side_row = [f'=IFERROR(FILTER({SETTINGS}!$E$2:$E,{SETTINGS}!$E$2:$E<>""),"")',
                f'={per_row(users, sumifs((YM, m), (TYPE, EXP), (USER, "x")))}',
                "",
                CARD_LABELS, f'={per_row(cards, card_usage("x", m))}', f'={per_row(cards, card_target("x"))}',
                '=ARRAYFORMULA(IF(I61:I76="","",IF((K61:K76="")+(K61:K76=0),"",J61:J76/K61:K76)))']
    return [v(f"{DASH}!A1:C3", top), v(f"{DASH}!A5:I6", kpi), asset_status(), v(f"{DASH}!A60:L60", head),
            v(f"{DASH}!A61:B61", [["미분류", "=B6+G6-SUM(B62:B91)"]]),
            v(f"{DASH}!A62:E62", [cat_row]), v(f"{DASH}!F61:L61", [side_row]), pie_labels(61, 91)]


_USED_PAYMENTS = "VSTACK(내역!$F$2:$F$5000,내역!$G$2:$G$5000,반복!$F$2:$F$50)"  # 내역·반복에 적힌 결제수단·입금자산


def bad_rows_expr() -> str:
    """[내역]에서 금액·날짜가 형식에 안 맞거나 사용자가 빈 줄 수 (빨간 줄)."""
    return ('SUMPRODUCT((내역!$H$2:$H$5000<>"")*(1-ISNUMBER(내역!$K$2:$K$5000)*ISNUMBER(내역!$L$2:$L$5000)'
            '*(내역!$B$2:$B$5000<>"")))')


def negative_accounts_expr() -> str:
    """잔액이 음수인 통장·현금 수 (초기 잔액을 안 넣은 신호)."""
    kind = lambda k: f'(자산!$B$2:$B$50="{k}")'
    return f'SUMPRODUCT((자산!$A$2:$A$50<>"")*({kind("계좌")}+{kind("현금")})*(자산!$E$2:$E$50<0))'


def blank_recurring_expr() -> str:
    """사용 중인데 금액이 빈 반복 수 (자동으로 못 만든다)."""
    return ('SUMPRODUCT((반복!$A$2:$A$50=TRUE)*(반복!$B$2:$B$50<>"")*((반복!$G$2:$G$50="")+(반복!$G$2:$G$50=0)>0))')


def missing_payments_count_expr() -> str:
    """내역·반복에 쓰였는데 [자산]에 없는 결제수단 가짓수."""
    u = _USED_PAYMENTS
    return (f'LET(쓴,IFERROR(UNIQUE(FILTER({u},{u}<>"")),""),없음,IFERROR(FILTER(쓴,ISNA(MATCH(쓴,자산!$A$2:$A$50,0))),""),'
            'IF(ISTEXT(INDEX(없음,1)),ROWS(없음),0))')


def attention_formula() -> str:
    """대시보드 D2 '확인 필요' 한 줄: 내역 빨간 줄 수 · 미등록 결제수단 · 잔액 음수 통장 · 금액 빈 반복. 문제 없으면 빈 칸."""
    used = _USED_PAYMENTS
    return ('=LET('
            f'버그,{bad_rows_expr()},'
            f'쓴,IFERROR(UNIQUE(FILTER({used},{used}<>"")),""),'
            '없음,IFERROR(FILTER(쓴,ISNA(MATCH(쓴,자산!$A$2:$A$50,0))),""),'
            '개수,IF(ISTEXT(INDEX(없음,1)),ROWS(없음),0),'
            f'음수,{negative_accounts_expr()},'
            f'빈반복,{blank_recurring_expr()},'
            '글,TEXTJOIN(" · ",TRUE,'
            'IF(버그>0,"내역 빨간 줄 "&버그&"건",""),'
            'IF(개수>0,"미등록 결제수단 "&INDEX(없음,1)&IF(개수>1," 외 "&(개수-1)&"건",""),""),'
            'IF(음수>0,"잔액 음수 통장 "&음수&"개",""),'
            'IF(빈반복>0,"금액 빈 반복 "&빈반복&"개","")),'
            'IF(글="","","※ 확인 필요: "&글))')


def attention_values() -> list[dict]:
    return [v(f"{DASH}!D2", [[attention_formula()]])]


def core_values() -> list[dict]:
    return txn_values() + settings_values() + calc_values() + asset_values() + dashboard_values() + attention_values()


def core_formats() -> list[dict]:
    fmts = [
        (f"{DASH}!B1:B2", "NUMBER", MONTH_FMT), (f"{DASH}!B3:C3", "DATE", "yyyy-mm-dd"),
        (f"{DASH}!A6:C6", "NUMBER", "#,##0"), (f"{DASH}!D6", "PERCENT", "0.0%"),
        (f"{DASH}!E6:I6", "NUMBER", "#,##0"), (f"{DASH}!J6:L6", "NUMBER", "#,##0"), (f"{DASH}!B61:C91", "NUMBER", "#,##0"),
        (f"{DASH}!D62:D91", "PERCENT", "0%"), (f"{DASH}!G61:G76", "NUMBER", "#,##0"),
        (f"{DASH}!J61:K76", "NUMBER", "#,##0"), (f"{DASH}!L61:L76", "PERCENT", "0%"),
    ]
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]
