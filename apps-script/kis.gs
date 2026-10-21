/* 한투 ISA 연결부 — 판단 로직은 kis_logic.gs. 조회 전용.
   키·계좌번호·토큰은 각자의 사용자 속성에만 두고, 실행자 슬롯의 한투원본 행에만 쓴다. */

var KIS_RAW = '한투원본';
var KIS_HOLD = '한투종목';
var KIS_HOLD_COL = [1, 7]; // 슬롯(0 소유자, 1 배우자) → 첫 열 (A, G), 2~101행
var KPROP = { key: 'KIS_APP_KEY', secret: 'KIS_APP_SECRET', acct: 'KIS_ACCOUNT', token: 'KIS_TOKEN', exp: 'KIS_TOKEN_EXP' };

function setKisKeys() {
  var ui = SpreadsheetApp.getUi();
  var key = askValue_(ui, '한투 App Key', '한투 ISA 키 입력');
  if (!key) return;
  var secret = askValue_(ui, '한투 App Secret', '한투 ISA 키 입력');
  if (!secret) return;
  var acct = askValue_(ui, 'ISA 계좌번호 10자리 (예: 12345678-01)', '한투 ISA 키 입력');
  if (!splitAccount(acct)) {
    ui.alert('계좌번호는 숫자 10자리(앞 8자리-뒤 2자리)로 넣어 주세요.');
    return;
  }
  var p = PropertiesService.getUserProperties();
  p.setProperty(KPROP.key, key);
  p.setProperty(KPROP.secret, secret);
  p.setProperty(KPROP.acct, acct);
  p.deleteProperty(KPROP.token);
  p.deleteProperty(KPROP.exp);
  showTab_('투자');
  ui.alert("저장했습니다. 처음이면 메뉴 증권 연동 > 자동 갱신 켜기를 한 번 누르고, [투자] 탭의 '지금 갱신'을 체크해 확인하세요.");
}

function clearKisKeys_() {
  var p = PropertiesService.getUserProperties();
  [KPROP.key, KPROP.secret, KPROP.acct, KPROP.token, KPROP.exp].forEach(function (k) { p.deleteProperty(k); });
}

function writeKis_(ss, r) {
  var sh = ss.getSheetByName(KIS_RAW);
  if (!sh) return;
  var row = KIS_RAW_ROW[isOwner_() ? 0 : 1];
  sh.getRange(row, 2, 1, 3).setValues([[STATUS_LABEL[r.kind] || '오류', r.code || '', safeErrorText(r.msg).slice(0, 100)]]);
  if (r.kind === 'ok') sh.getRange(row, 5, 1, 3).setValues([[new Date(), r.value, r.principal]]); // 실패면 마지막 성공 값 유지
  if (r.kind === 'ok') writeKisHoldings_(ss, r.holdings || []);
}

function writeKisHoldings_(ss, list) {
  var sh = ss.getSheetByName(KIS_HOLD);
  if (!sh) return;
  var col = KIS_HOLD_COL[isOwner_() ? 0 : 1];
  sh.getRange(2, col, 100, 5).clearContent();
  if (list.length) sh.getRange(2, col, Math.min(list.length, 100), 5).setValues(list.slice(0, 100));
}

function getKisToken_(p, key, secret, force) {
  var now = Date.now();
  var saved = p.getProperty(KPROP.token);
  if (!force && saved && tokenFresh(Number(p.getProperty(KPROP.exp)), now)) return { token: saved };
  var req = buildKisToken(key, secret);
  var t = parseKisToken(UrlFetchApp.fetch(req.url, req.options).getContentText(), now);
  if (t.token) {
    p.setProperty(KPROP.token, t.token);
    p.setProperty(KPROP.exp, String(t.expiresAt));
  }
  return t;
}

function fetchKis_(token, key, secret, acct) {
  var req = buildKisBalance(token, key, secret, acct);
  for (var attempt = 0; attempt < 3; attempt++) {
    var r = parseKisBalance(UrlFetchApp.fetch(req.url, req.options).getContentText());
    if (r.kind !== 'throttled') return r;
    Utilities.sleep(1000);
  }
  return { kind: 'error', code: 'EGW00201', msg: '초당 호출 제한이 계속됨' };
}

// refreshMeritz 안에서 메리츠 다음에 돈다. 예외를 밖으로 던지지 않는다.
function refreshKis_(ss) {
  var p = PropertiesService.getUserProperties();
  var key = p.getProperty(KPROP.key);
  var secret = p.getProperty(KPROP.secret);
  var acct = splitAccount(p.getProperty(KPROP.acct));
  if (!key || !secret || !acct) {
    writeKis_(ss, { kind: 'nokey', code: '', msg: '메뉴 증권 연동 > 한투 ISA 키 입력' });
    return;
  }
  try {
    var t = getKisToken_(p, key, secret, false);
    if (!t.token) {
      writeKis_(ss, { kind: 'error', code: '', msg: '토큰 발급 실패 ' + t.error });
      return;
    }
    var r = fetchKis_(t.token, key, secret, acct);
    if (r.kind === 'expired') { // 저장된 토큰이 먼저 끊겼다 — 한 번만 새로 받는다
      t = getKisToken_(p, key, secret, true);
      r = t.token ? fetchKis_(t.token, key, secret, acct) : { kind: 'error', code: '', msg: '토큰 재발급 실패 ' + t.error };
    }
    writeKis_(ss, r);
  } catch (err) {
    writeKis_(ss, { kind: 'error', code: '', msg: '예외: ' + String(err.message) });
  }
}
