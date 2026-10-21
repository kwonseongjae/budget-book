/* 메리츠 순수 로직 — Apps Script 전역(UrlFetchApp 등)에 의존하지 않는다 (node --test 대상). 조회 전용. */

var MERITZ_BASE = 'https://openapi.imeritz.com:9443';
var MERITZ_PATHS = {
  valuation: '/accounts/v1/me/valuation',
  holdings: '/accounts/v1/me/holdings',
  overseas: '/accounts/v1/me/overseas/holdings',
  currencies: '/accounts/v1/me/overseas/currencies'
};
var MERITZ_ORDER = ['valuation', 'holdings', 'overseas', 'currencies'];
// 계좌 슬롯: 앱 Key가 곧 계좌(/me). 시트 소유자 = 0, 그 밖의 편집자 = 1. ponytail: 2명 고정, 계좌가 늘면 한 줄 추가.
var MERITZ_SLOTS = [{ raw: '메리츠원본', stock: '주식_신랑', meritz: '메리츠_신랑' },
  { raw: '메리츠원본2', stock: '주식_신부', meritz: '메리츠_신부' }];
var MERITZ_STATUS_ROW = { valuation: 2, holdings: 3, overseas: 4, currencies: 5 }; // 메리츠원본 상태 블록 행
var HOLD_MAX = 100;
var FX_MAX = 5;
var TOKEN_MARGIN_MS = 3600 * 1000; // 토큰 유효기간이 12시간이라 만료 1시간 전부터 새로 받는다
var STATUS_LABEL = { ok: '성공', empty: '자료없음', denied: '권한없음', throttled: '오류', error: '오류', nokey: '키없음' };

// 명세: 오류는 모두 HTTP 500으로 오므로 rsp_cd로 판정한다. 조회 성공 코드는 5766.
function classifyRsp(code) {
  if (code === '5766') return 'ok';
  if (code === '5820') return 'empty';
  if (code === '0760') return 'denied';
  if (code === 'EGW00200') return 'throttled';
  return 'error';
}

function dataShapeOk(data, expectArray) {
  if (expectArray) return Array.isArray(data);
  return !!data && typeof data === 'object' && !Array.isArray(data);
}

function parseResponse(text, expectArray) {
  var body;
  try {
    body = JSON.parse(String(text).replace(/\u0000/g, '')); // 날것 널바이트가 섞여 와도 파싱되도록
  } catch (e) {
    return { kind: 'error', code: '', msg: '응답이 JSON이 아님', data: null };
  }
  if (!body || typeof body !== 'object') return { kind: 'error', code: '', msg: '응답 형식 오류', data: null };
  var code = String(body.rsp_cd || '').replace(/\u0000/g, ''); // 일부 API는 rsp_cd에 널바이트가 섞여 옴(메리츠 알려진 문제)
  var kind = classifyRsp(code);
  var msg = String(body.rsp_msg || '');
  if (kind === 'empty') return { kind: kind, code: code, msg: msg, data: expectArray ? [] : null };
  if (kind === 'ok' && !dataShapeOk(body.data, expectArray)) {
    return { kind: 'error', code: code, msg: 'data 형식이 예상과 다름', data: null };
  }
  return { kind: kind, code: code, msg: msg, data: kind === 'ok' ? body.data : null };
}

function toNum(x) {
  if (typeof x === 'number') return x;
  if (x === null || x === undefined) return NaN;
  var s = String(x).replace(/,/g, '').trim();
  return s === '' ? NaN : Number(s);
}

// 숫자가 아니면 그 조회 전체를 실패로 보도록 던진다. optional 항목은 없을 때만 0.
function num(obj, key, optional) {
  var raw = obj[key];
  if (optional && (raw === undefined || raw === null || raw === '')) return 0;
  var n = toNum(raw);
  if (isNaN(n)) throw new Error('숫자가 아닌 값: ' + key);
  return n;
}

// 메리츠원본 H1:H7 — 총자산, 원화 현금, 유가증권 평가, 외화 예수금(원), 대출, 자동투자 인출가능, 순자산
function summaryValues(val) {
  var aset = num(val, 'aset_vltn_amt');
  var loan = num(val, 'loan_amt', true);
  return [aset, num(val, 'tfam'), num(val, 'mksc_vltn_amt'), num(val, 'frcr_tfam', true), loan,
    num(val, 'wtmn_able_atmt_invt_amt', true), aset - loan];
}

// 메리츠원본 J~N — 통화, 예수금, 환율, 예수금(원), 해외주식 평가(원)
function fxRows(list) {
  return list.slice(0, FX_MAX).map(function (r) {
    var amt = num(r, 'frcr_amt');
    var rate = num(r, 'vltn_exrt');
    return [String(r.crcd || ''), amt, rate, Math.round(amt * rate), num(r, 'ovrs_stck_vltn_amt', true)];
  });
}

function tokenFresh(expiresAtMs, nowMs) {
  return !!expiresAtMs && expiresAtMs - nowMs >= TOKEN_MARGIN_MS;
}

function normalizeMac(s) {
  var m = String(s === null || s === undefined ? '' : s).replace(/[-:\s]/g, '').toUpperCase();
  return /^[0-9A-F]{12}$/.test(m) ? m : '';
}

// 조회 요청. 연속조회 항목(tr_cont)은 넣지 않는다 — 해외 조회에 넣으면 오류 없이 빈 결과가 온다.
function buildGet(path, token, mac) {
  return {
    url: MERITZ_BASE + path,
    options: {
      method: 'get', muteHttpExceptions: true, contentType: 'application/json; charset=UTF-8',
      headers: { Authorization: 'Bearer ' + token, mac_address: mac }
    }
  };
}

function buildTokenRequest(key, secret) {
  return {
    url: MERITZ_BASE + '/oauth2/token',
    options: {
      method: 'post', muteHttpExceptions: true, contentType: 'application/x-www-form-urlencoded',
      payload: { grant_type: 'client_credentials', client_id: key, client_secret: secret, scope: 'login' }
    }
  };
}

function parseToken(text, nowMs) {
  var body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    return { error: '토큰 응답이 JSON이 아님' };
  }
  if (!body || !body.access_token) {
    return { error: String((body && body.rsp_cd) || '') + ' ' + String((body && body.rsp_msg) || '') };
  }
  var sec = toNum(body.expires_in);
  return { token: String(body.access_token), expiresAt: nowMs + (isNaN(sec) ? 0 : sec) * 1000 };
}

function kindOf(code) {
  if (code === '1') return '국내';
  if (code === 'J') return '해외';
  return '기타'; // 명세: 목록에 없는 구분값도 올 수 있다 — 버리지 않는다
}

function tickerOf(iscd, kind) {
  var s = String(iscd || '');
  if (kind === '국내') return s.charAt(0) === 'A' ? s.slice(1) : s;
  return s.split('.')[0];
}

// /me/holdings: 같은 종목이 잔고 유형·대출 건마다 여러 행으로 온다 → iscd별로 원화 금액을 합친다.
function groupHoldings(list) {
  var order = [];
  var map = {};
  list.forEach(function (r) {
    var qty = num(r, 'rmnd_qty', true) + num(r, 'rmnd_dqty', true); // 정수분 + 소수점 거래분
    if (qty === 0) return;
    var key = String(r.iscd);
    if (!map[key]) {
      map[key] = { iscd: key, kind: kindOf(String(r.pros_trgt_cls_code)), name: String(r.isnm || ''),
        qty: 0, buy: 0, val: 0, pl: 0, loan: 0 };
      order.push(key);
    }
    var g = map[key];
    g.qty += qty;
    g.buy += num(r, 'byng_amt');
    g.val += num(r, 'vltn_amt');
    g.pl += num(r, 'vltn_prls_amt');
    g.loan += num(r, 'loan_amt', true);
  });
  return order.map(function (k) { return map[k]; });
}

// /overseas/holdings: 거래 통화 기준. 해외는 rmnd_dqty 하나에 전체 수량이 담긴다.
function groupOverseas(list) {
  var order = [];
  var map = {};
  list.forEach(function (r) {
    var qty = num(r, 'rmnd_dqty');
    if (qty === 0) return;
    var key = String(r.iscd);
    if (!map[key]) {
      map[key] = { iscd: key, symbol: String(r.ovrs_stck_symb_iscd || ''), name: String(r.isnm || ''),
        crcd: String(r.crcd || ''), price: num(r, 'psnt_prc'), qty: 0, buy: 0, val: 0 };
      order.push(key);
    }
    var g = map[key];
    g.qty += qty;
    g.buy += num(r, 'byov_camt');
    g.val += num(r, 'frcr_vltn_amt');
  });
  return order.map(function (k) { return map[k]; });
}

function fxCols(o) {
  return o ? [o.crcd, o.buy / o.qty, o.price, o.buy, o.val] : ['', '', '', '', ''];
}

function krwValue(row) {
  return row[6] === '' ? -1 : row[6];
}

// 원본 종목 블록 행(14칸): 구분 티커 종목명 수량 평단가(원) 매입(원) 평가(원) 손익(원) 대출(원) 통화 평단가(외) 현재가(외) 매입(외) 평가(외)
// 합계는 언제나 /me/holdings 원화 금액만 — 외화 열은 보여 주기만 해서 이중 계산이 없다.
function holdingRows(holdings, overseas) {
  var os = overseas ? groupOverseas(overseas) : [];
  var omap = {};
  os.forEach(function (o) { omap[o.iscd] = o; });
  var used = {};
  var mismatch = 0;
  var rows = groupHoldings(holdings).map(function (h) {
    var o = omap[h.iscd];
    if (o) used[h.iscd] = true;
    else if (h.kind === '해외' && overseas) mismatch++;
    var qty = o ? o.qty : h.qty;
    var ticker = o && o.symbol ? o.symbol : tickerOf(h.iscd, h.kind);
    return [h.kind, ticker, h.name, qty, h.buy / qty, h.buy, h.val, h.pl, h.loan].concat(fxCols(o));
  });
  os.forEach(function (o) {
    if (used[o.iscd]) return;
    mismatch++;
    rows.push(['해외', o.symbol || tickerOf(o.iscd, '해외'), o.name, o.qty, '', '', '', '', ''].concat(fxCols(o)));
  });
  rows.sort(function (a, b) { return krwValue(b) - krwValue(a); });
  return { rows: rows.slice(0, HOLD_MAX), mismatch: mismatch, truncated: rows.length > HOLD_MAX };
}
