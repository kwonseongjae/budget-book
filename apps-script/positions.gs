/* 증권 계좌 목록·붙여넣기·계좌 탭 (시트 연결). 순수 로직은 positions_logic.gs. 조회 전용 — 주문 경로 없음. */

var POS_TAB = '증권종목';
var POS_TABLE_TAB = '증권종목표';
var ACCT_TAB = '증권계좌';
var POS_ACCOUNT = 'B2';
var POS_CHECK = 'B3';
var POS_MODE = 'B4';
var POS_RESULT = 'C3';
var POS_PASTE = 'A6:T205';
var POS_TABLE = 'A2:G1001';
var ACCT_NAMES = 'A5:A14';
var ACCT_PASTED = 'F5:F14';
var ACCOUNT_TAB_PREFIX = '계좌_';

function blankRows_(n, m) {
  var out = [];
  for (var i = 0; i < n; i++) out.push(new Array(m).fill(''));
  return out;
}

function nameKey_(x) {
  return String(isBlank(x) ? '' : x).trim().toLowerCase();
}

// 증권종목 B3 체크: 붙여넣기 칸(A6:T205)을 해석해 고른 계좌(B2)의 종목을 정규 표(증권종목표 A2:G1001)에 교체해 넣는다.
function importPositions(ss, checkbox) {
  checkbox.setValue(false);
  var sh = ss.getSheetByName(POS_TAB);
  var out = sh.getRange(POS_RESULT);
  var account = String(sh.getRange(POS_ACCOUNT).getValue() || '').trim();
  if (!account) { out.setValue('✗ 계좌를 먼저 고르세요 (B2).'); return; }
  var list = ss.getSheetByName(ACCT_TAB);
  var names = list.getRange(ACCT_NAMES).getValues();
  var at = -1;
  for (var i = 0; i < names.length; i++) if (String(names[i][0]).trim() === account) { at = i; break; }
  if (at < 0) { out.setValue('✗ [증권계좌] 목록에 없는 이름입니다. B2에서 계좌를 다시 고르세요.'); return; }
  var cells = sh.getRange(POS_PASTE).getValues();
  while (cells.length && cells[cells.length - 1].every(isBlank)) cells.pop();
  if (!cells.length) { out.setValue('✗ A6부터 증권사 보유종목 표를 붙여넣어 주세요.'); return; }
  var r = parsePositions(cells);
  if (r.error) { out.setValue('✗ ' + r.error); return; }       // 못 읽으면 기존 종목과 붙여넣은 표를 그대로 둔다
  if (!r.positions.length) {                                    // 줄은 있는데 하나도 못 읽음 → 기존 종목을 지우지 않는다
    out.setValue('✗ 읽은 종목이 없습니다 (실패 ' + r.failed.length + '줄). 금액이 원화인지, 머리글이 한 줄인지 확인해 주세요. 기존 종목은 그대로 둡니다.');
    return;
  }
  var tbl = ss.getSheetByName(POS_TABLE_TAB);
  var mode = String(sh.getRange(POS_MODE).getValue() || '').trim();       // 비우거나 '추가·갱신 (기본)' = 합치기, '전체 교체' = 이 계좌를 표로 바꾸기
  var replaceAll = mode.indexOf('교체') !== -1;
  var current = tbl.getRange(POS_TABLE).getValues();
  var rows = replaceAll ? replaceAccountRows(current, account, r.positions) : mergeAccountRows(current, account, r.positions);
  if (rows.length > 1000) { out.setValue('✗ 종목이 너무 많습니다 (전체 1000줄까지).'); return; }
  tbl.getRange(POS_TABLE).setValues(rows.concat(blankRows_(1000 - rows.length, 7)));
  list.getRange(5 + at, 6).setValue(todayDate());
  sh.getRange(POS_PASTE).clearContent();
  if (r.failed.length) {
    sh.getRange(6, 1, r.failed.length, 6).setValues(r.failed.map(function (t) { return [safeText(t), '', '', '', '', '인식 실패']; }));
  }
  var total = rows.filter(function (x) { return String(x[0]).trim() === account; }).length;
  var chartOk = refreshAccountChart_(ss, account, total);
  out.setValue('✓ ' + r.positions.length + '종목 반영' + (total !== r.positions.length ? ' · 계좌 전체 ' + total + '종목' : '')
    + (r.failed.length ? ' / 실패 ' + r.failed.length + '줄' : '')
    + (chartOk ? '' : ' / 그래프는 만들지 못했습니다'));
}

// 계좌 탭의 종목별 비중 원형 그래프를 지우고 현재 종목 수(최대 50)에 맞춰 다시 만든다. 탭이 없으면 먼저 만든다.
// 차트 API를 쓸 수 없는 환경이면 건너뛰고 true, 만들다 실패하면 false(종목 반영은 이미 끝난 뒤라 막지 않는다).
function refreshAccountChart_(ss, account, count) {
  try {
    var sh = ss.getSheetByName(ACCOUNT_TAB_PREFIX + account);
    if (!sh) { syncAccountTab(ss, '', account, null); sh = ss.getSheetByName(ACCOUNT_TAB_PREFIX + account); }
    if (!sh || typeof sh.newChart !== 'function' || typeof Charts === 'undefined') return true;
    sh.getCharts().forEach(function (c) { sh.removeChart(c); });
    var end = 11 + Math.min(count, 50);
    sh.insertChart(sh.newChart().setChartType(Charts.ChartType.PIE).addRange(sh.getRange('B12:B' + end)).addRange(sh.getRange('E12:E' + end))
      .setPosition(2, 8, 0, 0).setOption('title', '종목별 비중').setOption('pieSliceText', 'percentage').build());
    return true;
  } catch (e) {
    return false;
  }
}

// 증권계좌 A5:A14 편집 → 그 계좌의 탭을 만들거나(없으면) 보이게/이름 바꾸기/숨기기. 반환값은 처리 결과(테스트·토스트용).
// 거부(invalid·duplicate·exists)하면 row 칸을 이전 이름(from)으로 되돌린다.
function syncAccountTab(ss, from, to, row) {
  var revert = function (code, msg) {
    if (ss.toast) ss.toast(msg, '증권계좌', 8);
    if (row) ss.getSheetByName(ACCT_TAB).getRange(row, 1).setValue(from);
    return code;
  };
  var problem = to ? validAccountName(to) : '';
  if (problem) return revert('invalid', problem);
  if (to) {
    var same = ss.getSheetByName(ACCT_TAB).getRange(ACCT_NAMES).getValues()
      .filter(function (r) { return nameKey_(r[0]) === nameKey_(to); }).length;
    if (same > 1) return revert('duplicate', '같은 이름의 계좌가 이미 있습니다 (공백·대소문자 무시).');
  }
  if (!to) {
    var old = from ? ss.getSheetByName(ACCOUNT_TAB_PREFIX + from) : null;
    if (!old) return 'none';
    old.hideSheet();                       // 기록 보존을 위해 삭제하지 않는다
    return 'hidden';
  }
  to = String(to).trim();
  var target = ss.getSheetByName(ACCOUNT_TAB_PREFIX + to);
  if (!from) {
    if (target) { target.showSheet(); return 'shown'; }
    buildAccountTab_(ss.insertSheet(ACCOUNT_TAB_PREFIX + to), to);
    return 'created';
  }
  var oldTab = ss.getSheetByName(ACCOUNT_TAB_PREFIX + from);
  if (!oldTab) {
    if (target) { target.showSheet(); return 'shown'; }
    buildAccountTab_(ss.insertSheet(ACCOUNT_TAB_PREFIX + to), to);
    return 'created';
  }
  if (target) return revert('exists', '같은 이름의 계좌 탭이 이미 있습니다 (숨긴 탭 포함). 다른 이름을 쓰세요.');
  oldTab.setName(ACCOUNT_TAB_PREFIX + to);
  oldTab.getRange('B1').setValue(to);
  var tbl = ss.getSheetByName(POS_TABLE_TAB);
  if (tbl) tbl.getRange(POS_TABLE).setValues(renameAccountRows(tbl.getRange(POS_TABLE).getValues(), from, to));
  var pos = ss.getSheetByName(POS_TAB);
  if (pos && String(pos.getRange(POS_ACCOUNT).getValue()).trim() === from) pos.getRange(POS_ACCOUNT).setValue(to);
  return 'renamed';
}

// 계좌 탭: B1 = 계좌 이름(수식이 이 칸을 읽는다), 요약 B2:B9, 종목 표 A11:F(필터), 오른쪽에 종목 비중 원형 그래프.
// 증권종목표 열: A 계좌 · B 코드 · C 종목명 · D 수량 · E 매입금액 · F 평가금액 · G 통화
function buildAccountTab_(sh, name) {
  var T = '증권종목표', L = '증권계좌';
  var match = 'MATCH($B$1,ARRAYFORMULA(TRIM(' + L + '!$A$5:$A$14)),0)';
  var find = function (col) { return 'IFERROR(INDEX(' + L + '!$' + col + '$5:$' + col + '$14,' + match + '),"")'; };
  var sum = function (col) { return '=SUMIFS(' + T + '!$' + col + '$2:$' + col + '$1001,' + T + '!$A$2:$A$1001,$B$1)'; };
  sh.getRange('A1:B1').setValues([['계좌', name]]);
  sh.getRange('A2:A9').setValues([['소유자 · 증권사'], ['종목 평가'], ['원금 (매입금액)'], ['예수금'], ['평가금액 (총)'], ['손익 (종목 기준)'], ['수익률'], ['마지막 붙여넣기']]);
  sh.getRange('B2:B9').setFormulas([
    ['=' + find('B') + '&" · "&' + find('C')], [sum('F')], [sum('E')], ['=N(' + find('E') + ')'], ['=B3+B5'],
    ['=IF(COUNTIFS(' + T + '!$A$2:$A$1001,$B$1,' + T + '!$D$2:$D$1001,"")>0,"",B3-B4)'],      // 매입금액이 빈 종목이 있으면 손익을 비운다
    ['=IF(AND(ISNUMBER(B7),B4>0),B7/B4,"")'], ['=' + find('F')]]);
  sh.getRange('A11:F11').setValues([['코드', '종목명', '수량', '매입금액', '평가금액', '통화']]);
  sh.getRange('A12').setFormula('=IFERROR(FILTER(' + T + '!$B$2:$G$1001,' + T + '!$A$2:$A$1001=$B$1),"")');
  sh.getRange('B3:B7').setNumberFormat('#,##0');
  sh.getRange('B9').setNumberFormat('yyyy-mm-dd');
  sh.getRange('B8').setNumberFormat('0.0%');
  sh.getRange('D12:E61').setNumberFormat('#,##0');
}
