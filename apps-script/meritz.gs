/* 메리츠 API 연결부 — 판단 로직은 meritz_logic.gs. 조회 전용(주문·환전 경로 없음).
   키·MAC·토큰은 각자의 사용자 속성에만 둔다 (스크립트 속성은 편집자가 설정 화면에서 볼 수 있음).
   갱신은 실행한 사람 권한으로 돌고, 그 사람 슬롯(MERITZ_SLOTS)의 원본 탭에만 쓴다. */

var PROP = { key: 'MERITZ_APP_KEY', secret: 'MERITZ_APP_SECRET', mac: 'MERITZ_MAC',
  token: 'MERITZ_TOKEN', exp: 'MERITZ_TOKEN_EXP' };

function onOpen() {
  SpreadsheetApp.getUi().createMenu('증권 연동')
    .addItem('메리츠 키 입력 (내 계좌)', 'setMeritzKeys')
    .addItem('한투 ISA 키 입력 (내 계좌)', 'setKisKeys')
    .addItem('자동 갱신 켜기 (내 계좌)', 'setupMeritzTriggers')
    .addItem('내 키 삭제 (메리츠·한투)', 'clearMeritzKeys')
    .addSeparator()
    .addItem('연동 점검 (내 계좌)', 'diagnoseMeritz')
    .addToUi();
  addViewMenu_();
}

// 연동이 안 될 때 어느 단계에서 막히는지 실행한 사람에게 보여 준다. 키 값은 표시하지 않는다(있음/없음만).
function diagnoseMeritz() {
  var ui = SpreadsheetApp.getUi();
  var lines = [];
  var step = function (label, fn) {
    try { lines.push(label + ': ' + fn()); } catch (e) { lines.push(label + ': 오류 — ' + String(e.message).slice(0, 150)); }
  };
  step('내 계정', function () { return Session.getEffectiveUser().getEmail() || '(이메일을 읽지 못함)'; });
  step('시트 소유자', function () {
    var o = SpreadsheetApp.getActive().getOwner();
    return (o ? o.getEmail() : '(없음)') + (isOwner_() ? ' — 나 (신랑 칸)' : ' — 다른 사람 (신부 칸)');
  });
  step('내 칸', function () { return slot_().raw + ' / ' + slot_().stock; });
  step('메리츠 키', function () {
    var p = PropertiesService.getUserProperties();
    return [PROP.key, PROP.secret, PROP.mac].map(function (k) { return p.getProperty(k) ? '있음' : '없음'; })
      .join(' · ') + ' (Key·Secret·MAC)';
  });
  step('내 자동 갱신 트리거', function () {
    return ScriptApp.getProjectTriggers().map(function (t) { return t.getHandlerFunction(); }).join(', ') || '없음';
  });
  step('지금 조회', function () {
    refreshMeritz();
    return SpreadsheetApp.getActive().getSheetByName(slot_().raw).getRange('B2:D2').getValues()[0].join(' | ');
  });
  ui.alert('연동 점검', lines.join('\n'), ui.ButtonSet.OK);
}

function isOwner_() {
  var owner = SpreadsheetApp.getActive().getOwner();
  return !owner || owner.getEmail() === Session.getEffectiveUser().getEmail();
}

function slot_() {
  return MERITZ_SLOTS[isOwner_() ? 0 : 1];
}

function askValue_(ui, label, title) {
  var r = ui.prompt(title || '메리츠 키 입력', label, ui.ButtonSet.OK_CANCEL);
  return r.getSelectedButton() === ui.Button.OK ? r.getResponseText().trim() : '';
}

function setMeritzKeys() {
  var ui = SpreadsheetApp.getUi();
  var key = askValue_(ui, 'App Key');
  if (!key) return;
  var secret = askValue_(ui, 'App Secret');
  if (!secret) return;
  var mac = normalizeMac(askValue_(ui, 'MAC 주소 12자리 (윈도우 getmac 결과, 예: 00-1A-2B-3C-4D-5E)'));
  if (!mac) {
    ui.alert('MAC 주소 형식이 아닙니다. 0-9, A-F 12자리로 넣어 주세요.');
    return;
  }
  var p = PropertiesService.getUserProperties();
  p.setProperty(PROP.key, key);
  p.setProperty(PROP.secret, secret);
  p.setProperty(PROP.mac, mac);
  p.deleteProperty(PROP.token);
  p.deleteProperty(PROP.exp);
  showTab_('투자');
  ui.alert("저장했습니다. 처음이면 메뉴 증권 연동 > 자동 갱신 켜기를 한 번 누르고, [투자] 탭의 '지금 갱신'을 체크해 확인하세요.");
}

function clearMeritzKeys() {
  var p = PropertiesService.getUserProperties();
  [PROP.key, PROP.secret, PROP.mac, PROP.token, PROP.exp].forEach(function (k) { p.deleteProperty(k); });
  clearKisKeys_();
  var ss = SpreadsheetApp.getActive(); // 옛 평가금액이 합계에 남지 않게 바로 '키 없음'으로
  writeAllStatus_(ss, { kind: 'nokey', code: '', msg: '' });
  writeKis_(ss, { kind: 'nokey', code: '', msg: '' });
  SpreadsheetApp.getUi().alert('내 메리츠·한투 키를 지웠습니다.');
}


// 실행한 사람의 메리츠 갱신 트리거만 다시 만든다 (다른 사람·일일 작업 트리거는 그대로).
function setupMeritzTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    var f = t.getHandlerFunction();
    if (f === 'refreshMeritz' || f === 'onEditMeritz') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('refreshMeritz').timeBased().everyDays(1).atHour(7).nearMinute(0).create();  // 7시 00~15분 (두 PC가 같은 시각대에)
  ScriptApp.newTrigger('refreshMeritz').timeBased().everyDays(1).atHour(16).nearMinute(0).create();
  ScriptApp.newTrigger('onEditMeritz').forSpreadsheet(SpreadsheetApp.getActive()).onEdit().create();
  try { SpreadsheetApp.getUi().alert('자동 갱신을 켰습니다 (매일 07:00~07:15·16:00~16:15, [' + slot_().stock + '] 탭).'); } catch (e) {}
}

// 설치형 onEdit (각자 만든 것이 모두 받음) — 자기 슬롯의 주식 탭 H1일 때만. 이름이 onEdit이면 단순 트리거로 한 번 더 돌기 때문에 다른 이름.
function onEditMeritz(e) {
  var r = e.range;
  var name = r.getSheet().getName();
  if ((name !== slot_().stock && name !== '투자') || r.getA1Notation() !== 'H1' || e.value !== 'TRUE') return;
  r.setValue(false);
  refreshMeritz();
}

// 시간 트리거·체크박스 공용. 예외를 밖으로 던지지 않는다 (던지면 구글이 실패 메일을 보냄).
function refreshMeritz() {
  var lock = LockService.getUserLock(); // 두 사람의 갱신은 서로 막지 않는다
  if (!lock.tryLock(1000)) return; // 내가 이미 갱신 중
  var ss = SpreadsheetApp.getActive();
  try {
    try {
      refreshMeritz_(ss);
    } catch (err) {
      writeAllStatus_(ss, { kind: 'error', code: '', msg: '예외: ' + safeErrorText(err.message).slice(0, 100) });
    }
    refreshKis_(ss);
  } finally {
    lock.releaseLock();
  }
}

function refreshMeritz_(ss) {
  var p = PropertiesService.getUserProperties();
  var key = p.getProperty(PROP.key);
  var secret = p.getProperty(PROP.secret);
  var mac = p.getProperty(PROP.mac);
  if (!key || !secret || !mac) {
    writeAllStatus_(ss, { kind: 'nokey', code: '', msg: '메뉴 증권 연동 > 메리츠 키 입력' });
    return;
  }
  var token = getToken_(p, key, secret, false);
  if (!token.token) {
    writeAllStatus_(ss, { kind: 'error', code: '', msg: '토큰 발급 실패 ' + token.error });
    return;
  }
  var res = {};
  var renewed = false;
  MERITZ_ORDER.forEach(function (name) {
    var r = fetchQuery_(name, token.token, mac);
    if (r.kind === 'error' && r.code !== 'EGW00200' && r.code !== '5766' && !renewed) { // 토큰 문제일 수 있음 — 갱신당 한 번만 새로 받는다
      renewed = true;
      var fresh = getToken_(p, key, secret, true);
      if (fresh.token) {
        token = fresh;
        r = fetchQuery_(name, token.token, mac);
      }
    }
    res[name] = r;
    Utilities.sleep(300);
  });
  writeResults_(ss, res);
}

function getToken_(p, key, secret, force) {
  var now = Date.now();
  var saved = p.getProperty(PROP.token);
  if (!force && saved && tokenFresh(Number(p.getProperty(PROP.exp)), now)) return { token: saved };
  var req = buildTokenRequest(key, secret);
  var t = parseToken(UrlFetchApp.fetch(req.url, req.options).getContentText(), now);
  if (t.token) {
    p.setProperty(PROP.token, t.token);
    p.setProperty(PROP.exp, String(t.expiresAt));
  }
  return t;
}

function fetchQuery_(name, token, mac) {
  var req = buildGet(MERITZ_PATHS[name], token, mac);
  for (var attempt = 0; attempt < 4; attempt++) {
    var r = parseResponse(UrlFetchApp.fetch(req.url, req.options).getContentText(), name !== 'valuation');
    if (r.kind !== 'throttled') return r;
    Utilities.sleep(1000);
  }
  return { kind: 'error', code: 'EGW00200', msg: '초당 호출 제한이 계속됨', data: null };
}

function writeBlock_(sh, row, col, maxRows, cols, rows) {
  sh.getRange(row, col, maxRows, cols).clearContent();
  if (rows.length) sh.getRange(row, col, rows.length, cols).setValues(rows);
}

function writeStatus_(sh, name, r, note, now) {
  var row = MERITZ_STATUS_ROW[name];
  var msg = String(r.msg || '') + (note ? ' / ' + note : '');
  sh.getRange(row, 2, 1, 3).setValues([[STATUS_LABEL[r.kind] || '오류', r.code || '', msg]]);
  if (r.kind === 'ok' || r.kind === 'empty') sh.getRange(row, 5).setValue(now);
}

function writeAllStatus_(ss, r) {
  var sh = ss.getSheetByName(slot_().raw);
  if (!sh) return;
  MERITZ_ORDER.forEach(function (name) { writeStatus_(sh, name, r, '', new Date()); });
}

function failed_(r, err) {
  return { kind: 'error', code: r.code, msg: err.message, data: null };
}

// 성공한 조회의 블록만 덮어쓴다. 실패한 블록과 그 마지막 성공 시각은 그대로 둔다.
function writeResults_(ss, res) {
  var sh = ss.getSheetByName(slot_().raw);
  var now = new Date();
  var notes = {};
  if (res.valuation.kind === 'ok') {
    try {
      sh.getRange('H1:H7').setValues(summaryValues(res.valuation.data).map(function (x) { return [x]; }));
      sh.getRange('H8').setValue(now);
    } catch (err) { res.valuation = failed_(res.valuation, err); }
  }
  var c = res.currencies;
  if (c.kind === 'ok' || c.kind === 'empty') {
    try { writeBlock_(sh, 2, 10, FX_MAX, 5, fxRows(c.data)); } catch (err) { res.currencies = failed_(c, err); }
  }
  var o = res.overseas;
  var ovs = null;
  if (o.kind === 'ok' || o.kind === 'empty') {
    try { groupOverseas(o.data); ovs = o.data; } catch (err) { res.overseas = failed_(o, err); }
  }
  var h = res.holdings;
  if (h.kind === 'ok' || h.kind === 'empty') {
    try {
      var built = holdingRows(h.data, ovs);
      writeBlock_(sh, 11, 1, HOLD_MAX, 14, built.rows);
      notes.holdings = (built.mismatch ? '해외 종목 불일치 ' + built.mismatch + '건 ' : '')
        + (built.truncated ? '종목 수 초과(100개만 표시)' : '');
    } catch (err) { res.holdings = failed_(h, err); }
  }
  MERITZ_ORDER.forEach(function (name) { writeStatus_(sh, name, res[name], notes[name], now); });
}
