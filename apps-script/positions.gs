/* 증권 계좌 목록·붙여넣기·계좌 탭 (시트 연결). 순수 로직은 positions_logic.gs. 조회 전용 — 주문 경로 없음. */

var POS_TAB = '증권종목';
var ACCT_TAB = '증권계좌';
var POS_ACCOUNT = 'B2';
var POS_CHECK = 'B3';
var POS_RESULT = 'C3';
var POS_PASTE = 'A6:F205';
var POS_TABLE = 'H6:N1005';
var ACCT_NAMES = 'A5:A14';
var ACCT_PASTED = 'F5:F14';
var ACCOUNT_TAB_PREFIX = '계좌_';

function blankRows_(n, m) {
  var out = [];
  for (var i = 0; i < n; i++) out.push(new Array(m).fill(''));
  return out;
}

// 증권종목 B3 체크: 붙여넣기 칸(A6:F205)을 해석해 고른 계좌(B2)의 종목을 정규 표(H6:N1005)에 교체해 넣는다.
function importPositions(ss, checkbox) {
  checkbox.setValue(false);
  var sh = ss.getSheetByName(POS_TAB);
  var out = sh.getRange(POS_RESULT);
  var account = String(sh.getRange(POS_ACCOUNT).getValue() || '').trim();
  if (!account) { out.setValue('✗ 계좌를 먼저 고르세요 (B2).'); return; }
  var cells = sh.getRange(POS_PASTE).getValues();
  while (cells.length && cells[cells.length - 1].every(isBlank)) cells.pop();
  if (!cells.length) { out.setValue('✗ A6부터 증권사 보유종목 표를 붙여넣어 주세요.'); return; }
  var r = parsePositions(cells);
  if (r.error) { out.setValue('✗ ' + r.error); return; }       // 못 읽으면 기존 종목과 붙여넣은 표를 그대로 둔다
  var rows = replaceAccountRows(sh.getRange(POS_TABLE).getValues(), account, r.positions);
  if (rows.length > 1000) { out.setValue('✗ 종목이 너무 많습니다 (전체 1000줄까지).'); return; }
  sh.getRange(POS_TABLE).setValues(rows.concat(blankRows_(1000 - rows.length, 7)));
  var names = ss.getSheetByName(ACCT_TAB).getRange(ACCT_NAMES).getValues();
  for (var i = 0; i < names.length; i++) {
    if (String(names[i][0]).trim() === account) { ss.getSheetByName(ACCT_TAB).getRange(5 + i, 6).setValue(todayDate()); break; }
  }
  sh.getRange(POS_PASTE).clearContent();
  if (r.failed.length) {
    sh.getRange(6, 1, r.failed.length, 6).setValues(r.failed.map(function (t) { return [safeText(t), '', '', '', '', '인식 실패']; }));
  }
  out.setValue('✓ ' + r.positions.length + '종목 반영' + (r.failed.length ? ' / 실패 ' + r.failed.length + '줄' : ''));
}

// 증권계좌 A5:A14 편집 → 그 계좌의 탭을 만들거나(없으면) 보이게/이름 바꾸기/숨기기. 반환값은 처리 결과(테스트·토스트용).
function syncAccountTab(ss, from, to) {
  var problem = to ? validAccountName(to) : '';
  if (problem) { if (ss.toast) ss.toast(problem, '증권계좌', 8); return 'invalid'; }
  if (!to) {
    var old = from ? ss.getSheetByName(ACCOUNT_TAB_PREFIX + from) : null;
    if (!old) return 'none';
    old.hideSheet();                       // 기록 보존을 위해 삭제하지 않는다
    return 'hidden';
  }
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
  if (target) { if (ss.toast) ss.toast('같은 이름의 계좌 탭이 이미 있습니다.', '증권계좌', 8); return 'exists'; }
  oldTab.setName(ACCOUNT_TAB_PREFIX + to);
  oldTab.getRange('B1').setValue(to);
  var pos = ss.getSheetByName(POS_TAB);
  if (pos) pos.getRange(POS_TABLE).setValues(renameAccountRows(pos.getRange(POS_TABLE).getValues(), from, to));
  return 'renamed';
}

// 계좌 탭: B1 = 계좌 이름(수식이 이 칸을 읽는다), 요약 B2:B9, 종목 표 A11:F(필터), 오른쪽에 종목 비중 원형 그래프.
function buildAccountTab_(sh, name) {
  var T = '증권종목', L = '증권계좌';
  var find = function (col) { return 'IFERROR(INDEX(' + L + '!$' + col + '$5:$' + col + '$14,MATCH($B$1,' + L + '!$A$5:$A$14,0)),"")'; };
  var sum = function (col) { return '=SUMIFS(' + T + '!$' + col + '$6:$' + col + '$1005,' + T + '!$H$6:$H$1005,$B$1)'; };
  sh.getRange('A1:B1').setValues([['계좌', name]]);
  sh.getRange('A2:A9').setValues([['소유자 · 증권사'], ['종목 평가'], ['원금 (매입금액)'], ['예수금'], ['평가금액 (총)'], ['손익 (종목 기준)'], ['수익률'], ['마지막 붙여넣기']]);
  sh.getRange('B2:B9').setFormulas([
    ['=' + find('B') + '&" · "&' + find('C')], [sum('M')], [sum('L')], ['=N(' + find('E') + ')'], ['=B3+B5'],
    ['=B3-B4'], ['=IF(B4>0,B7/B4,"")'], ['=' + find('F')]]);
  sh.getRange('A11:F11').setValues([['코드', '종목명', '수량', '매입금액', '평가금액', '통화']]);
  sh.getRange('A12').setFormula('=IFERROR(FILTER(' + T + '!$I$6:$N$1005,' + T + '!$H$6:$H$1005=$B$1),"")');
  sh.getRange('B3:B7').setNumberFormat('#,##0');
  sh.getRange('B9').setNumberFormat('yyyy-mm-dd');
  sh.getRange('B8').setNumberFormat('0.0%');
  sh.getRange('D12:E61').setNumberFormat('#,##0');
  if (typeof sh.newChart === 'function' && typeof Charts !== 'undefined') {
    sh.insertChart(sh.newChart().setChartType(Charts.ChartType.PIE).addRange(sh.getRange('B12:B61')).addRange(sh.getRange('E12:E61'))
      .setPosition(2, 8, 0, 0).setOption('title', '종목별 비중').build());
  }
}
