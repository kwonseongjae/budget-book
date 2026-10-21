/* 한투(KIS) 순수 로직 — Apps Script 전역에 의존하지 않는다 (node --test 대상).
   조회 전용: 잔고 조회 하나뿐이고 주문 경로는 없다. toNum·num은 meritz_logic.gs(같은 전역)의 것을 쓴다. */

var KIS_BASE = 'https://openapi.koreainvestment.com:9443';
var KIS_BALANCE_PATH = '/uapi/domestic-stock/v1/trading/inquire-balance';
var KIS_RAW_ROW = [2, 3]; // 한투원본: 슬롯(0 소유자, 1 배우자) → 행
var KIS_BALANCE_PARAMS = [['AFHR_FLPR_YN', 'N'], ['OFL_YN', ''], ['INQR_DVSN', '02'], ['UNPR_DVSN', '01'],
  ['FUND_STTL_ICLD_YN', 'N'], ['FNCG_AMT_AUTO_RDPT_YN', 'N'], ['PRCS_DVSN', '00'],
  ['CTX_AREA_FK100', ''], ['CTX_AREA_NK100', '']];

// '12345678-01' → {cano:'12345678', prdt:'01'}. 숫자 10자리가 아니면 null.
function splitAccount(s) {
  var d = String(s === null || s === undefined ? '' : s).replace(/[-\s]/g, '');
  return /^\d{10}$/.test(d) ? { cano: d.slice(0, 8), prdt: d.slice(8) } : null;
}

function buildKisToken(key, secret) {
  return {
    url: KIS_BASE + '/oauth2/tokenP',
    options: {
      method: 'post', muteHttpExceptions: true, contentType: 'application/json; charset=UTF-8',
      payload: JSON.stringify({ grant_type: 'client_credentials', appkey: key, appsecret: secret })
    }
  };
}

function parseKisToken(text, nowMs) {
  var body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    return { error: '토큰 응답이 JSON이 아님' };
  }
  if (!body || !body.access_token) {
    return { error: String((body && (body.error_code || body.msg_cd)) || '') + ' '
      + String((body && (body.error_description || body.msg1)) || '') };
  }
  var sec = toNum(body.expires_in);
  return { token: String(body.access_token), expiresAt: nowMs + (isNaN(sec) ? 0 : sec) * 1000 };
}

function buildKisBalance(token, key, secret, acct) {
  var q = [['CANO', acct.cano], ['ACNT_PRDT_CD', acct.prdt]].concat(KIS_BALANCE_PARAMS)
    .map(function (p) { return p[0] + '=' + encodeURIComponent(p[1]); }).join('&');
  return {
    url: KIS_BASE + KIS_BALANCE_PATH + '?' + q,
    options: {
      method: 'get', muteHttpExceptions: true, contentType: 'application/json; charset=UTF-8',
      headers: { authorization: 'Bearer ' + token, appkey: key, appsecret: secret, tr_id: 'TTTC8434R', custtype: 'P' }
    }
  };
}

// 성공은 rt_cd "0". 평가 = 순자산(nass_amt), 원금 추정 = 매입금액 합계 + 예수금.
// 예수금은 D+2(prvs_rcdl_excc_amt)가 있으면 그것 — D+0은 매수 직후 이틀간 매입금액과 겹쳐 원금이 부풀려진다.
function parseKisBalance(text) {
  var body;
  try {
    body = JSON.parse(String(text));
  } catch (e) {
    return { kind: 'error', code: '', msg: '응답이 JSON이 아님' };
  }
  if (!body || typeof body !== 'object') return { kind: 'error', code: '', msg: '응답 형식 오류' };
  var code = String(body.msg_cd || '');
  if (String(body.rt_cd) !== '0') {
    var kind = code === 'EGW00201' ? 'throttled' : (code === 'EGW00123' || code === 'EGW00121') ? 'expired' : 'error';
    return { kind: kind, code: code, msg: String(body.msg1 || '').trim() };
  }
  var o = Array.isArray(body.output2) ? body.output2[0] : null;
  if (!o) return { kind: 'error', code: code, msg: 'output2 없음' };
  try {
    return { kind: 'ok', code: code, msg: '', value: num(o, 'nass_amt'),
      principal: num(o, 'pchs_amt_smtl_amt') + cashOf(o), holdings: kisHoldings(body.output1) };
  } catch (e) {
    return { kind: 'error', code: code, msg: e.message };
  }
}

// 종목 목록 [구분, 코드, 이름, 매입금액, 평가금액] — 보유수량이 있는 것만.
// ponytail: 첫 페이지(최대 50종목)만, ISA에서 넘칠 일 없음 — 넘치면 CTX_AREA 연속조회 추가
function kisHoldings(rows) {
  return (Array.isArray(rows) ? rows : []).filter(function (r) { return toNum(r.hldg_qty) > 0; })
    .map(function (r) { return ['ISA', String(r.pdno), String(r.prdt_name || '').trim(), num(r, 'pchs_amt'), num(r, 'evlu_amt')]; });
}

function cashOf(o) {
  var d2 = o.prvs_rcdl_excc_amt;
  return d2 === undefined || d2 === null || d2 === '' ? num(o, 'dnca_tot_amt') : num(o, 'prvs_rcdl_excc_amt');
}

// 화면에 보일 오류 문구: 연결 오류 메시지에 섞이는 URL 쿼리(계좌번호 CANO)와 8자리 이상 숫자를 지운다.
function safeErrorText(msg) {
  return String(msg === null || msg === undefined ? '' : msg).replace(/\?\S*/g, '').replace(/\d{8,}/g, '***');
}
