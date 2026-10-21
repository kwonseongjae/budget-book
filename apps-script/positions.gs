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
