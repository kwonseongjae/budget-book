# 메리츠증권 주식 연동 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 가계부 시트에 메리츠증권 Open API 조회 결과(순자산·보유 종목·외화 예수금)를 숨김 탭 `메리츠원본`에 쓰는 Apps Script와, 그 값을 보여 주는 `주식`·`메리츠` 탭, `자산` 탭 연동 열을 더하고, 운영 시트에 제자리로 적용한다.

**Architecture:** 판단 로직은 `apps-script/meritz_logic.gs`(순수 함수, node 시험), API 호출·잠금·속성·쓰기는 `apps-script/meritz.gs`. 시트 쪽은 `meritz_sheet.py`(블록 위치·수식 값)와 `meritz_style.py`(검증·서식·차트)가 요청 JSON을 만들고, 새 시트는 `build_budget.py`, 운영 시트는 `migrate_meritz.py`가 쓴다. 두 언어가 공유하는 계약은 `tests/fixtures/meritz_expected.json`(원본 블록 기대값)이다.

**Tech Stack:** Python 3.12, google-api-python-client, pytest / Google Apps Script V8 / Node 22 (`node --test`)

**Spec:** `docs/superpowers/specs/2026-10-07-meritz-stock-design.md` (v2)

## Global Constraints

- 작업 폴더 `/mnt/d/budget book`, 브랜치 `feature/budget-sheet`. 모든 명령은 `cd "/mnt/d/budget book" && ...`.
- 커밋 메시지 끝: 빈 줄 + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 새 탭 이름 정확히: `주식`(sheetId 1500, 보임), `메리츠`(1600, 보임), `메리츠원본`(1400, 숨김). `자산` 탭은 8열(A~H).
- `메리츠원본` 블록 위치(고정): 상태 `A1:E5`(2~5행 = 총자산·보유종목·해외보유·외화예수금), 요약 `G1:H8`(H1 총자산, H2 원화 현금, H3 유가증권 평가, H4 외화 예수금(원), H5 대출, H6 자동투자 인출가능, H7 순자산, H8 갱신 시각), 외화 `J1:N6`(데이터 2~6행), 종목 `A10:N110`(데이터 11~110행, 14열).
- 호출 경로는 `/oauth2/token`과 조회 4개(`/accounts/v1/me/valuation`, `/accounts/v1/me/holdings`, `/accounts/v1/me/overseas/holdings`, `/accounts/v1/me/overseas/currencies`)뿐. 주문·환전 경로 금지. 요청에 `tr_cont`를 넣지 않는다.
- 키·MAC·토큰은 `PropertiesService.getUserProperties()`에만. 시트·로그·오류 메시지·git·대화에 키를 쓰지 않는다.
- 운영 시트(`.spreadsheet_id`)에는 샘플 값을 쓰지 않는다. 시험은 임시 시트에서만.
- 운영 시트의 기존 데이터 칸(내역·반복·즐겨찾기·설정, 자산 A~D·F열)은 쓰지 않는다.
- 파일 800줄, 함수 50줄 이하.
- 이 계획의 산출물 중 실제 API 호출은 키 발급 전에는 검증할 수 없다. 키 관련 확인(9443 접속, IP 제한, MAC 검사, 자동투자 포함 여부)은 스펙의 "키 발급 뒤 순서"로 남는다.

## Review Focus

1. **같은 종목이 여러 행으로 옴(일반+신용, 일반+소수)** → 한 줄로 묶이고 수량·금액이 합쳐짐 (Task 2 `holdingRows` 기대값 시험).
2. **요청에 `tr_cont`가 섞임 / 응답 `tr_cont`가 "1"** → 요청에 없고 다음 페이지를 부르지 않음 (Task 1 `buildGet` 시험, 픽스처 `tr_cont:"1"`).
3. **해외 조회만 실패** → 원화 열은 갱신, 외화 열은 비고, 불일치 집계 안 함 (Task 2 `holdingRows(h, null)` 시험).
4. **키 없음 / 배우자가 실행** → 예외 없이 `키없음` 상태 (Task 6 코드 경로, Task 9 운영 확인).
5. **마이그레이션 두 번 실행** → 탭·차트·보호·조건부서식이 중복 생성되지 않고 기존 데이터·자산 잔액 그대로 (Task 7 `plan` 시험, Task 9 운영 전후 비교).

---

### Task 1: 메리츠 순수 로직 — 응답 판정·숫자·요약·외화·토큰·요청

**Files:**
- Create: `apps-script/meritz_logic.gs`, `tests/meritz.test.js`, `tests/fixtures/meritz_valuation.json`, `tests/fixtures/meritz_currencies.json`

**Interfaces:**
- Produces (Apps Script 전역): `MERITZ_BASE`, `MERITZ_PATHS{valuation,holdings,overseas,currencies}`, `MERITZ_ORDER`, `MERITZ_STATUS_ROW`, `HOLD_MAX=100`, `FX_MAX=5`, `STATUS_LABEL`, `classifyRsp(code)->'ok'|'empty'|'denied'|'throttled'|'error'`, `parseResponse(text, expectArray)->{kind,code,msg,data}`, `toNum(x)->number|NaN`, `num(obj,key,optional)->number` (NaN이면 throw), `summaryValues(val)->number[7]`, `fxRows(list)->any[][]`, `tokenFresh(expiresAtMs, nowMs)->bool`, `normalizeMac(s)->string`, `buildGet(path, token, mac)->{url,options}`, `buildTokenRequest(key, secret)->{url,options}`, `parseToken(text, nowMs)->{token,expiresAt}|{error}`

- [ ] **Step 1: 픽스처 작성**

`tests/fixtures/meritz_valuation.json`:
```json
{"data":{"tfam":1000000,"d2_aft_tfam":1000000,"mksc_vltn_amt":5252500,"loan_amt":300000,"vltn_amt":6392500,"wtmn_able_cash_amt":700000,"wtmn_able_atmt_invt_amt":5000000,"byng_amt":5084000,"aset_vltn_amt":6392500,"frcr_tfam":140000},"rsp_cd":"5766","rsp_msg":"조회가 완료되었습니다.","tr_cont":"0"}
```

`tests/fixtures/meritz_currencies.json`:
```json
{"data":[{"crcd":"USD","frcr_amt":"100.000","estm_frcr_amt":"100.000","entm_aset_vltn_amt":"1200.00000","vltn_exrt":"1400.0000","ovrs_stck_vltn_amt":2080000,"excl_wncr_vltn_amt":140000,"srno":1}],"rsp_cd":"5766","rsp_msg":"조회가 완료되었습니다.","tr_cont":"0"}
```

- [ ] **Step 2: Write the failing test** — `tests/meritz.test.js`

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', 'meritz_logic.gs'), 'utf8'), ctx);
const plain = (x) => JSON.parse(JSON.stringify(x));
const fixture = (name) => fs.readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');

test('classifyRsp: 명세의 코드별 처리', () => {
  assert.equal(ctx.classifyRsp('5766'), 'ok');
  assert.equal(ctx.classifyRsp('5820'), 'empty');
  assert.equal(ctx.classifyRsp('0760'), 'denied');
  assert.equal(ctx.classifyRsp('EGW00200'), 'throttled');
  assert.equal(ctx.classifyRsp('IGW50004'), 'error');
  assert.equal(ctx.classifyRsp(''), 'error');
});

test('parseResponse: 성공·자료없음·JSON 아님·형태 오류', () => {
  const ok = ctx.parseResponse(fixture('meritz_valuation.json'), false);
  assert.equal(ok.kind, 'ok');
  assert.equal(ok.data.aset_vltn_amt, 6392500);
  assert.deepEqual(plain(ctx.parseResponse('{"rsp_cd":"5820","rsp_msg":"없음"}', true)),
    { kind: 'empty', code: '5820', msg: '없음', data: [] });
  assert.equal(ctx.parseResponse('<html>bad gateway</html>', true).kind, 'error');
  assert.equal(ctx.parseResponse('{"rsp_cd":"5766","data":{"a":1}}', true).kind, 'error'); // 배열 기대
  assert.equal(ctx.parseResponse('{"rsp_cd":"5766","data":[]}', false).kind, 'error');    // 객체 기대
  assert.equal(ctx.parseResponse('{"rsp_cd":"0760","rsp_msg":"권한 없음"}', true).kind, 'denied');
});

test('toNum / num: 문자열 숫자, 쉼표, 빈 값, 선택 항목', () => {
  assert.equal(ctx.toNum('10000.0000000000'), 10000);
  assert.equal(ctx.toNum('1,234'), 1234);
  assert.ok(Number.isNaN(ctx.toNum('')));
  assert.ok(Number.isNaN(ctx.toNum('abc')));
  assert.equal(ctx.num({ a: '5' }, 'a'), 5);
  assert.equal(ctx.num({}, 'loan_amt', true), 0);
  assert.throws(() => ctx.num({ a: 'x' }, 'a'), /a/);
  assert.throws(() => ctx.num({}, 'a'), /a/);
});

test('summaryValues: 총자산·구성·대출·자동투자·순자산', () => {
  const v = JSON.parse(fixture('meritz_valuation.json')).data;
  assert.deepEqual(plain(ctx.summaryValues(v)), [6392500, 1000000, 5252500, 140000, 300000, 5000000, 6092500]);
  assert.throws(() => ctx.summaryValues({ aset_vltn_amt: 'x', tfam: 1, mksc_vltn_amt: 1 }));
});

test('fxRows: 통화·예수금·환율·원화 환산·해외주식 평가(원), 최대 5개', () => {
  const c = JSON.parse(fixture('meritz_currencies.json')).data;
  assert.deepEqual(plain(ctx.fxRows(c)), [['USD', 100, 1400, 140000, 2080000]]);
  const many = Array.from({ length: 7 }, (_, i) => ({ crcd: 'C' + i, frcr_amt: '1', vltn_exrt: '1' }));
  assert.equal(ctx.fxRows(many).length, 5);
});

test('tokenFresh: 남은 시간 24시간 이상만 재사용', () => {
  const now = 1_000_000_000_000;
  assert.equal(ctx.tokenFresh(now + 25 * 3600e3, now), true);
  assert.equal(ctx.tokenFresh(now + 23 * 3600e3, now), false);
  assert.equal(ctx.tokenFresh(0, now), false);
});

test('normalizeMac: 구분자 제거·대문자·12자리 검사', () => {
  assert.equal(ctx.normalizeMac('00-1a-2B-3c-4D-5e'), '001A2B3C4D5E');
  assert.equal(ctx.normalizeMac('00:1A:2B:3C:4D:5E'), '001A2B3C4D5E');
  assert.equal(ctx.normalizeMac('001A2B3C4D'), '');
  assert.equal(ctx.normalizeMac('00-1A-2B-3C-4D-ZZ'), '');
  assert.equal(ctx.normalizeMac(null), '');
});

test('buildGet: 인증·MAC 헤더, 연속조회 항목 없음, 500도 예외 없이', () => {
  const r = ctx.buildGet('/accounts/v1/me/overseas/holdings', 'TKN', '001A2B3C4D5E');
  assert.equal(r.url, 'https://openapi.imeritz.com:9443/accounts/v1/me/overseas/holdings');
  assert.equal(r.options.method, 'get');
  assert.equal(r.options.muteHttpExceptions, true);
  assert.equal(r.options.headers.Authorization, 'Bearer TKN');
  assert.equal(r.options.headers.mac_address, '001A2B3C4D5E');
  assert.ok(!JSON.stringify(r).includes('tr_cont'));
  assert.ok(!r.options.payload);
});

test('buildTokenRequest / parseToken', () => {
  const r = ctx.buildTokenRequest('K', 'S');
  assert.equal(r.url, 'https://openapi.imeritz.com:9443/oauth2/token');
  assert.equal(r.options.method, 'post');
  assert.equal(r.options.contentType, 'application/x-www-form-urlencoded');
  assert.deepEqual(plain(r.options.payload),
    { grant_type: 'client_credentials', client_id: 'K', client_secret: 'S', scope: 'login' });
  assert.deepEqual(plain(ctx.parseToken('{"access_token":"abc","expires_in":604800}', 1000)),
    { token: 'abc', expiresAt: 1000 + 604800000 });
  assert.match(ctx.parseToken('{"rsp_cd":"EGW00121","rsp_msg":"유효하지 않은 키"}', 0).error, /EGW00121/);
  assert.ok(ctx.parseToken('oops', 0).error);
});

test('경로는 조회 4개뿐이고 주문·환전이 없다', () => {
  const paths = Object.values(plain(ctx.MERITZ_PATHS));
  assert.deepEqual(paths.sort(), ['/accounts/v1/me/holdings', '/accounts/v1/me/overseas/currencies',
    '/accounts/v1/me/overseas/holdings', '/accounts/v1/me/valuation']);
  const src = fs.readFileSync(path.join(__dirname, '..', 'apps-script', 'meritz_logic.gs'), 'utf8');
  assert.ok(!/trading|forex|orders/.test(src));
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `node --test tests/meritz.test.js`
Expected: FAIL — `ENOENT ... apps-script/meritz_logic.gs`

- [ ] **Step 4: Write implementation** — `apps-script/meritz_logic.gs`

```js
/* 메리츠 순수 로직 — Apps Script 전역(UrlFetchApp 등)에 의존하지 않는다 (node --test 대상). 조회 전용. */

var MERITZ_BASE = 'https://openapi.imeritz.com:9443';
var MERITZ_PATHS = {
  valuation: '/accounts/v1/me/valuation',
  holdings: '/accounts/v1/me/holdings',
  overseas: '/accounts/v1/me/overseas/holdings',
  currencies: '/accounts/v1/me/overseas/currencies'
};
var MERITZ_ORDER = ['valuation', 'holdings', 'overseas', 'currencies'];
var MERITZ_STATUS_ROW = { valuation: 2, holdings: 3, overseas: 4, currencies: 5 }; // 메리츠원본 상태 블록 행
var HOLD_MAX = 100;
var FX_MAX = 5;
var TOKEN_MARGIN_MS = 24 * 3600 * 1000;
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
    body = JSON.parse(text);
  } catch (e) {
    return { kind: 'error', code: '', msg: '응답이 JSON이 아님', data: null };
  }
  if (!body || typeof body !== 'object') return { kind: 'error', code: '', msg: '응답 형식 오류', data: null };
  var code = String(body.rsp_cd || '');
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `node --test tests/meritz.test.js`
Expected: `# pass 10`, `# fail 0`

- [ ] **Step 6: Commit**

```bash
git add apps-script/meritz_logic.gs tests/meritz.test.js tests/fixtures/meritz_valuation.json tests/fixtures/meritz_currencies.json
git commit -m "feat: 메리츠 응답 판정·요약·외화·토큰·요청 순수 로직"
```

---

### Task 2: 메리츠 순수 로직 — 보유 종목 묶기와 원본 블록 기대값

**Files:**
- Modify: `apps-script/meritz_logic.gs` (끝에 추가), `tests/meritz.test.js` (끝에 추가)
- Create: `tests/fixtures/meritz_holdings.json`, `tests/fixtures/meritz_overseas.json`, `tests/fixtures/meritz_expected.json`

**Interfaces:**
- Consumes: Task 1 `num`, `HOLD_MAX`
- Produces: `kindOf(code)`, `tickerOf(iscd, kind)`, `groupHoldings(list)`, `groupOverseas(list)`, `holdingRows(holdings, overseasOrNull)->{rows: any[][14], mismatch: number, truncated: bool}`; 파일 `tests/fixtures/meritz_expected.json` = `{summary:number[7], fx:any[][], holdings:any[][]}` (Task 8의 통합 시험이 그대로 시트에 씀)

- [ ] **Step 1: 픽스처 작성**

`tests/fixtures/meritz_holdings.json` (같은 종목 여러 행, 소수 수량, 신용 대출, 해외 2종목, 알 수 없는 구분 `D`, 수량 0, `tr_cont:"1"`):
```json
{"data":[
{"iscd":"A005930","isnm":"삼성전자","pros_trgt_cls_code":"1","mksc_cls_name":"주식일반","rmnd_qty":10,"rmnd_dqty":"0.5000000000","byng_unpr":"67047.62","psnt_prc":"75000.000000","vltn_amt":787500,"vltn_prls_amt":83500,"ert":"11.86080","byng_amt":704000,"loan_amt":0},
{"iscd":"A005930","isnm":"삼성전자","pros_trgt_cls_code":"1","mksc_cls_name":"신용","rmnd_qty":5,"rmnd_dqty":"0.0000000000","byng_unpr":"70000.00","psnt_prc":"75000.000000","vltn_amt":375000,"vltn_prls_amt":25000,"ert":"7.14286","byng_amt":350000,"loan_amt":300000},
{"iscd":"MU.OQ","isnm":"마이크론","pros_trgt_cls_code":"J","mksc_cls_name":"해외주식","rmnd_qty":10,"rmnd_dqty":"0.0000000000","byng_unpr":"95.00","psnt_prc":"100.000000","vltn_amt":1400000,"vltn_prls_amt":100000,"ert":"7.69231","byng_amt":1300000,"loan_amt":0},
{"iscd":"MU.OQ","isnm":"마이크론","pros_trgt_cls_code":"J","mksc_cls_name":"해외주식","rmnd_qty":0,"rmnd_dqty":"1.0000000000","byng_unpr":"95.00","psnt_prc":"100.000000","vltn_amt":140000,"vltn_prls_amt":10000,"ert":"7.69231","byng_amt":130000,"loan_amt":0},
{"iscd":"TSLA.OQ","isnm":"테슬라","pros_trgt_cls_code":"J","mksc_cls_name":"해외주식","rmnd_qty":3,"rmnd_dqty":"0.0000000000","byng_unpr":"150.00","psnt_prc":"135.000000","vltn_amt":540000,"vltn_prls_amt":-60000,"ert":"-10.00000","byng_amt":600000,"loan_amt":0},
{"iscd":"X001","isnm":"Super365 발행어음","pros_trgt_cls_code":"D","mksc_cls_name":"주식일반","rmnd_qty":2000,"rmnd_dqty":"0.0000000000","byng_unpr":"1000.00","psnt_prc":"1005.000000","vltn_amt":2010000,"vltn_prls_amt":10000,"ert":"0.50000","byng_amt":2000000,"loan_amt":0},
{"iscd":"A000660","isnm":"SK하이닉스","pros_trgt_cls_code":"1","mksc_cls_name":"주식일반","rmnd_qty":0,"rmnd_dqty":"0.0000000000","byng_unpr":"0.00","psnt_prc":"200000.000000","vltn_amt":0,"vltn_prls_amt":0,"ert":"0.00000","byng_amt":0,"loan_amt":0}
],"rsp_cd":"5766","rsp_msg":"조회가 완료되었습니다.","tr_cont":"1"}
```

`tests/fixtures/meritz_overseas.json` (MU 일반+소수 2행, `/me/holdings`에 없는 AAPL):
```json
{"data":[
{"prod_cls_name":"일반","rmnd_clcd":"1","crcd":"USD","iscd":"MU.OQ","isnm":"MICRON TECHNOLOGY","rmnd_dqty":"10.0000000000","avrg_unpr":"95.000000","vltn_prls_camt":"50.0000","vltn_ert":"5.2632","psnt_prc":"100.000000","byov_camt":"950.0000","frcr_vltn_amt":"1000.000","exrt":"1400.0000","ovrs_stck_symb_iscd":"MU"},
{"prod_cls_name":"소수","rmnd_clcd":"2","crcd":"USD","iscd":"MU.OQ","isnm":"MICRON TECHNOLOGY","rmnd_dqty":"1.0000000000","avrg_unpr":"95.000000","vltn_prls_camt":"5.0000","vltn_ert":"5.2632","psnt_prc":"100.000000","byov_camt":"95.0000","frcr_vltn_amt":"100.000","exrt":"1400.0000","ovrs_stck_symb_iscd":"MU"},
{"prod_cls_name":"일반","rmnd_clcd":"1","crcd":"USD","iscd":"AAPL.OQ","isnm":"APPLE INC","rmnd_dqty":"2.0000000000","avrg_unpr":"190.000000","vltn_prls_camt":"20.0000","vltn_ert":"5.2632","psnt_prc":"200.000000","byov_camt":"380.0000","frcr_vltn_amt":"400.000","exrt":"1400.0000","ovrs_stck_symb_iscd":"AAPL"}
],"rsp_cd":"5766","rsp_msg":"조회가 완료되었습니다.","tr_cont":"0"}
```

`tests/fixtures/meritz_expected.json` (원본 블록 기대값 — 평가금액(원) 큰 순, 원화 없는 해외 종목은 맨 뒤):
```json
{
  "summary": [6392500, 1000000, 5252500, 140000, 300000, 5000000, 6092500],
  "fx": [["USD", 100, 1400, 140000, 2080000]],
  "holdings": [
    ["기타", "X001", "Super365 발행어음", 2000, 1000, 2000000, 2010000, 10000, 0, "", "", "", "", ""],
    ["해외", "MU", "마이크론", 11, 130000, 1430000, 1540000, 110000, 0, "USD", 95, 100, 1045, 1100],
    ["국내", "005930", "삼성전자", 15.5, 68000, 1054000, 1162500, 108500, 300000, "", "", "", "", ""],
    ["해외", "TSLA", "테슬라", 3, 200000, 600000, 540000, -60000, 0, "", "", "", "", ""],
    ["해외", "AAPL", "APPLE INC", 2, "", "", "", "", "", "USD", 190, 200, 380, 400]
  ],
  "mismatch": 2
}
```

- [ ] **Step 2: Write the failing test** — `tests/meritz.test.js` 끝에 추가

```js
const data = (name) => JSON.parse(fixture(name)).data;
const expected = JSON.parse(fixture('meritz_expected.json'));

test('holdingRows: 픽스처 → 원본 블록 기대값 (묶기·소수 수량·기타·불일치·정렬)', () => {
  const out = plain(ctx.holdingRows(data('meritz_holdings.json'), data('meritz_overseas.json')));
  assert.deepEqual(out.rows, expected.holdings);
  assert.equal(out.mismatch, expected.mismatch);
  assert.equal(out.truncated, false);
});

test('holdingRows: 원화 합계 = /me/holdings 평가금액 합 = 유가증권 평가 (이중 계산 없음)', () => {
  const rows = plain(ctx.holdingRows(data('meritz_holdings.json'), data('meritz_overseas.json'))).rows;
  const krw = rows.reduce((s, r) => s + (r[6] === '' ? 0 : r[6]), 0);
  assert.equal(krw, expected.summary[2]);
});

test('holdingRows: 해외 조회 실패(null) → 외화 열 비움, 불일치 집계 안 함', () => {
  const out = plain(ctx.holdingRows(data('meritz_holdings.json'), null));
  assert.equal(out.mismatch, 0);
  const mu = out.rows.find((r) => r[1] === 'MU');
  assert.deepEqual(mu.slice(9), ['', '', '', '', '']);
  assert.equal(mu[3], 11); // 해외 응답이 없으면 /me/holdings 수량(10 + 1)
  assert.ok(!out.rows.some((r) => r[1] === 'AAPL'));
});

test('holdingRows: 같은 종목 여러 행 → 한 줄, 수량 0 행은 버림', () => {
  const rows = plain(ctx.holdingRows(data('meritz_holdings.json'), [])).rows;
  assert.equal(rows.filter((r) => r[1] === '005930').length, 1);
  assert.ok(!rows.some((r) => r[1] === '000660'));
});

test('holdingRows: 100종목 초과 → 평가금액 큰 순 100개, truncated', () => {
  const many = Array.from({ length: 105 }, (_, i) => ({
    iscd: 'A' + String(100000 + i), isnm: 'S' + i, pros_trgt_cls_code: '1', rmnd_qty: 1, rmnd_dqty: '0',
    byng_amt: 1000, vltn_amt: 1000 + i, vltn_prls_amt: i
  }));
  const out = plain(ctx.holdingRows(many, []));
  assert.equal(out.rows.length, 100);
  assert.equal(out.truncated, true);
  assert.equal(out.rows[0][6], 1104);
  assert.equal(out.rows[99][6], 1005);
});

test('holdingRows: 숫자가 아닌 금액 → 예외 (그 조회 실패로 처리)', () => {
  const bad = [{ iscd: 'A1', pros_trgt_cls_code: '1', rmnd_qty: 1, byng_amt: 'x', vltn_amt: 1, vltn_prls_amt: 0 }];
  assert.throws(() => ctx.holdingRows(bad, []), /byng_amt/);
});

test('tickerOf / kindOf', () => {
  assert.equal(ctx.tickerOf('A005930', '국내'), '005930');
  assert.equal(ctx.tickerOf('MU.OQ', '해외'), 'MU');
  assert.equal(ctx.kindOf('1'), '국내');
  assert.equal(ctx.kindOf('J'), '해외');
  assert.equal(ctx.kindOf('D'), '기타');
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `node --test tests/meritz.test.js`
Expected: FAIL — `TypeError: ctx.holdingRows is not a function`

- [ ] **Step 4: Write implementation** — `apps-script/meritz_logic.gs` 끝에 추가

```js
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `node --test tests/meritz.test.js && node --test tests/logic.test.js`
Expected: meritz `# pass 17`, `# fail 0`; logic `# pass 27`, `# fail 0`

- [ ] **Step 6: Commit**

```bash
git add apps-script/meritz_logic.gs tests/meritz.test.js tests/fixtures/meritz_holdings.json tests/fixtures/meritz_overseas.json tests/fixtures/meritz_expected.json
git commit -m "feat: 메리츠 보유 종목 묶기·짝맞추기와 원본 블록 기대값"
```

---

### Task 3: 탭 추가, 자산 G·H열, 자산 잔액 연동 수식, 사용법

**Files:**
- Modify: `layout.py`, `formulas.py`, `styling.py`, `guide.py`, `tests/test_layout.py`, `tests/test_formulas.py`, `tests/test_styling.py`

**Interfaces:**
- Produces: `layout.RAW="메리츠원본"`, `layout.STOCK="주식"`, `layout.MERITZ="메리츠"`; `SHEETS`에 `(STOCK,1500,120,16,False)`, `(MERITZ,1600,100,8,False)`, `(RAW,1400,110,14,True)`; 자산 8열; `guide.guide_requests(start: int = 0)`
- 자산 E2 수식 시그니처 `=MAP(A2:A,C2:C,F2:F,G2:G,LAMBDA(x,init,link,sync,...))`, H2 `=MAP(A2:A,G2:G,LAMBDA(x,sync,...))`

- [ ] **Step 1: Write the failing tests**

`tests/test_layout.py` 끝에 추가:
```python


def test_meritz_tabs_defined_and_raw_hidden():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props["주식"] == (1500, 120, 16, False)
    assert props["메리츠"] == (1600, 100, 8, False)
    assert props["메리츠원본"] == (1400, 110, 14, True)
    assert props["자산"][2] == 8


def test_asset_link_column_dropdown_and_status_protected():
    seeds = {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}
    assert seeds["자산!G1"] == [["연동"]]
    rules = [r["setDataValidation"] for r in layout.validation_requests()]
    g = [r for r in rules if r["range"] == layout.a1_to_grid("자산!G2:G50")][0]
    assert g["rule"]["condition"] == {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": "메리츠"}]}
    ranges = [r["addProtectedRange"]["protectedRange"]["range"] for r in layout.protection_requests()]
    assert layout.a1_to_grid("자산!H1:H50") in ranges


def test_stock_tab_protected_except_refresh_checkbox():
    prs = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()]
    stock = [p for p in prs if p["range"] == {"sheetId": 1500}][0]
    assert stock["unprotectedRanges"] == [layout.a1_to_grid("주식!H1")]
    assert any(p["range"] == {"sheetId": 1600} for p in prs)
    assert any(p["range"] == {"sheetId": 1400} for p in prs)
```

`tests/test_formulas.py` 끝에 추가:
```python


def test_asset_balance_uses_meritz_net_when_linked():
    e2 = _by_range(formulas.core_values())["자산!E1:E2"][1][0]
    assert e2.startswith("=MAP(A2:A,C2:C,F2:F,G2:G,LAMBDA(x,init,link,sync,")
    assert 'IF(AND(sync="메리츠",ISNUMBER(메리츠원본!$H$7)),메리츠원본!$H$7,' in e2


def test_asset_link_status_shows_time_stale_or_missing():
    h = _by_range(formulas.core_values())["자산!H1:H2"]
    assert h[0] == ["연동 상태"]
    f = h[1][0]
    assert f.startswith("=MAP(A2:A,G2:G,LAMBDA(x,sync,")
    assert '"미갱신"' in f and '"오래됨 ("' in f and "NOW()-메리츠원본!$H$8>3" in f
    assert '"메리츠 "&TEXT(메리츠원본!$H$8,"mm/dd hh:mm")' in f
```

`tests/test_styling.py` 끝에 추가:
```python


def test_guide_requests_can_start_from_new_rows():
    full = guide.guide_requests()
    tail = guide.guide_requests(start=len(guide.CONTENT) - 2)
    assert len(tail) < len(full)
    starts = [r["repeatCell"]["range"]["startRowIndex"] for r in tail if "repeatCell" in r
              and r["repeatCell"]["range"]["endRowIndex"] - r["repeatCell"]["range"]["startRowIndex"] == 1]
    assert min(starts) == len(guide.CONTENT) - 2


def test_guide_explains_meritz_owner_and_colors():
    text = "\n".join(str(c) for row in guide.GUIDE_ROWS for c in row)
    for must in ("[주식]", "[메리츠]", "소유자", "setupTriggers", "자동투자", "수익이 빨강"):
        assert must in text, must
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest -q tests/test_layout.py tests/test_formulas.py tests/test_styling.py 2>&1 | tail -3`
Expected: FAIL — 새 시험 7개 실패(`KeyError: '주식'`, `KeyError: '자산!G1'`, `KeyError: '자산!H1:H2'` 등)

- [ ] **Step 3: layout.py 수정**

`GUIDE = "사용법"` 다음 줄에 추가:
```python
RAW, STOCK, MERITZ = "메리츠원본", "주식", "메리츠"
```
`SHEETS`에서 `(SEARCH, 700, 1000, 10, False),` 바로 다음 줄에 추가:
```python
    (STOCK, 1500, 120, 16, False),
    (MERITZ, 1600, 100, 8, False),
```
`(STATE, 1200, 500, 2, True),` 바로 다음 줄에 추가:
```python
    (RAW, 1400, 110, 14, True),
```
`(ASSETS, 300, 50, 6, False),` → `(ASSETS, 300, 50, 8, False),`

`seed_values`의 `v(f"{ASSETS}!F1", [["적립 카테고리"]]),` 다음 줄에 추가:
```python
        v(f"{ASSETS}!G1", [["연동"]]),
```
`validation_requests`의 `(f"{ASSETS}!F2:F50", _rule("ONE_OF_RANGE", CATS)),` 다음 줄에 추가:
```python
        (f"{ASSETS}!G2:G50", _rule("ONE_OF_LIST", "메리츠")),
```
`protection_requests` 전체를 다음으로 교체:
```python
def protection_requests() -> list[dict]:
    whole = [(DASH, ["B1"]), (TREND, ["B1"]), (CAL, ["B1"]), (CALC, []),
             (STOCK, ["H1"]), (MERITZ, []), (RAW, [])]
    parts = [f"{TXN}!K1:M5000", f"{SETTINGS}!H1:H20", f"{ASSETS}!E1:E50", f"{ASSETS}!H1:H50",
             f"{SEARCH}!A6:J1000", f"{SEARCH}!E1:E2"]
    reqs = [_protect({"sheetId": SHEET_ID[t]}, [a1_to_grid(f"{t}!{c}") for c in free]) for t, free in whole]
    return reqs + [_protect(a1_to_grid(a1), []) for a1 in parts]
```

- [ ] **Step 4: formulas.py 수정** — `from layout import` 줄에 `RAW` 추가, `asset_values` 끝부분 교체

`asset_values`의 마지막 두 줄
```python
    bal = f"init+{inc}-{exp}-{out}+{in_}+{saved}"
    return [v(f"{ASSETS}!E1:E2", [["현재 잔액"], [f'=MAP(A2:A,C2:C,F2:F,LAMBDA(x,init,link,IF(x="","",{bal})))']])]
```
을 다음으로 교체:
```python
    bal = f"init+{inc}-{exp}-{out}+{in_}+{saved}"
    # 연동(G열)='메리츠'인 계좌는 증권사 순자산으로 채운다. 한 번도 갱신 못 했으면 기존 계산으로 되돌림.
    net, at = f"{RAW}!$H$7", f"{RAW}!$H$8"
    synced = f'IF(AND(sync="메리츠",ISNUMBER({net})),{net},{bal})'
    status = (f'IF(OR(x="",sync=""),"",IF(NOT(ISNUMBER({net})),"미갱신",'
              f'IF(NOW()-{at}>3,"오래됨 ("&TEXT({at},"mm/dd")&")","메리츠 "&TEXT({at},"mm/dd hh:mm"))))')
    return [v(f"{ASSETS}!E1:E2", [["현재 잔액"],
                                  [f'=MAP(A2:A,C2:C,F2:F,G2:G,LAMBDA(x,init,link,sync,IF(x="","",{synced})))']]),
            v(f"{ASSETS}!H1:H2", [["연동 상태"], [f'=MAP(A2:A,G2:G,LAMBDA(x,sync,{status}))']])]
```

기존 시험 3곳을 새 시그니처로 갱신(이번 변경이 의도적으로 바꾼 값):
- `tests/test_formulas.py:48` `assert e2.startswith("=MAP(A2:A,C2:C,F2:F,LAMBDA(x,init,link,")` → `assert e2.startswith("=MAP(A2:A,C2:C,F2:F,G2:G,LAMBDA(x,init,link,sync,")`
- `tests/test_formulas.py:49` `assert "IF(x=\"\",\"\",init+" in e2` → `assert ",init+" in e2 and 'IF(x="","",IF(AND(sync="메리츠",' in e2`
- `tests/test_formulas.py:133` 줄도 48행과 같은 교체
- `tests/test_layout.py:32` `assert hidden == {"계산", "알림기록"}` → `assert hidden == {"계산", "알림기록", "메리츠원본"}`

- [ ] **Step 5: styling.py 수정**

`from layout import (...)`에 `MERITZ, STOCK` 추가. `TAB_COLORS`에 `STOCK: VIEW_TAB, MERITZ: VIEW_TAB` 추가. `HEADERS`의 `(f"{ASSETS}!A1:F1", SETUP_TAB)` → `(f"{ASSETS}!A1:H1", SETUP_TAB)`. `COL_WIDTHS`의 `ASSETS: [170, 80, 120, 130, 130, 140],` → `ASSETS: [170, 80, 120, 130, 130, 140, 90, 160],` 그리고 다음 두 줄 추가:
```python
    STOCK: [70, 90, 160, 80, 110, 110, 120, 130, 120, 90, 60, 100, 100, 110, 90, 70],
    MERITZ: [150, 150, 110, 170, 30, 120, 120, 120],
```
`base_requests`의 `for title in (GUIDE, DASH, TREND, CAL):` → `for title in (GUIDE, DASH, TREND, CAL, STOCK, MERITZ):`

- [ ] **Step 6: guide.py 수정**

`CONTENT` 리스트 맨 끝(마지막 `("row", "", "회색 자동 계산 칸, ...")` 다음)에 추가 — 기존 행 위치를 바꾸지 않도록 반드시 끝에 붙인다:
```python
    ("section", "📈 주식 (메리츠증권)", ""),
    ("row", "[주식]", "메리츠증권 계좌의 순자산·보유 종목·평단가·수량·평가금액을 자동으로 보여 줍니다. 매일 07시대·16시대에 갱신되고, 맨 위 '지금 갱신'을 체크하면 바로 갱신됩니다. 이 탭과 [메리츠] 탭에서는 수익이 빨강, 손실이 파랑입니다 (가계부의 지출·수입 색과 뜻이 다름)."),
    ("row", "[메리츠]", "총 평가·손익·수익률과 자산 구성·종목 비중·수익률 차트, 조회별 갱신 상태와 검산 결과를 보여 줍니다. 검산에 ⚠가 뜨면 조회 시차나 데이터 오류이니 '지금 갱신'을 한 번 더 해 보세요."),
    ("row", "자산 연동", "[자산] G열 '연동'에 '메리츠'를 고른 계좌는 잔액이 증권사 순자산(총자산−대출)으로 채워지고 초기 잔액·적립 카테고리는 쓰지 않습니다. H열에 마지막 갱신 시각이 나오며 3일 넘게 갱신이 안 되면 '오래됨'이 표시됩니다."),
    ("row", "키 입력 (소유자만)", "PC에서 시트 메뉴 '메리츠 → 키 입력'으로 App Key·App Secret·MAC 주소(윈도우 getmac 결과)를 넣습니다. 시트 소유자(신랑)만 넣을 수 있고, 새 기능을 올린 뒤에는 소유자가 Apps Script에서 setupTriggers를 한 번 더 실행해야 자동 갱신이 켜집니다."),
    ("row", "자동투자", "슈퍼365의 발행어음·RP 자동투자분은 '자동투자 인출가능'에 따로 보여 주고 합계에 더하지 않습니다 (증권사 총자산 포함 여부를 실제 앱과 대조한 뒤 정합니다)."),
```

`guide_requests` 전체를 다음으로 교체(`start`부터만 서식을 만든다 — 운영 시트에 새 행만 서식 입히기용):
```python
def guide_requests(start: int = 0) -> list[dict]:
    styles = {
        "title": {"backgroundColor": TITLE_BG, "textFormat": {"fontSize": 22, "bold": True, "foregroundColor": WHITE}},
        "section": {"backgroundColor": SECTION_BG, "textFormat": {"fontSize": 16, "bold": True, "foregroundColor": NAVY}},
        "row": {"textFormat": {"fontSize": 12}},
    }
    reqs = []
    for i, (kind, a, _b) in enumerate(CONTENT):
        if i < start:
            continue
        reqs.append(_fmt(_grid(i), styles[kind], "userEnteredFormat(backgroundColor,textFormat)"))
        if kind == "row" and a:  # 왼쪽 항목 이름만 굵게
            reqs.append(_fmt(_grid(i, 1), {"textFormat": {"bold": True}}, "userEnteredFormat.textFormat.bold"))
        if kind != "row":
            reqs.append({"mergeCells": {"mergeType": "MERGE_ALL", "range": _grid(i)}})
    body = {"sheetId": SHEET_ID[GUIDE], "startRowIndex": start, "endRowIndex": len(CONTENT),
            "startColumnIndex": 0, "endColumnIndex": 2}
    reqs.append(_fmt(body, {"wrapStrategy": "WRAP"}, "userEnteredFormat.wrapStrategy"))
    reqs.append({"autoResizeDimensions": {"dimensions": {"sheetId": SHEET_ID[GUIDE], "dimension": "ROWS",
                                                         "startIndex": start, "endIndex": len(CONTENT)}}})
    return reqs
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -2`
Expected: `85 passed` (기존 78 + 새 7, 갱신한 4곳 포함 실패 0)

- [ ] **Step 8: Commit**

```bash
git add layout.py formulas.py styling.py guide.py tests/test_layout.py tests/test_formulas.py tests/test_styling.py
git commit -m "feat: 주식·메리츠·메리츠원본 탭 정의, 자산 연동 열·순자산 수식, 사용법 주식 구역"
```

---

### Task 4: meritz_sheet.py — 원본 머리글과 주식·메리츠 탭 수식

**Files:**
- Create: `meritz_sheet.py`, `tests/test_meritz_sheet.py`
- Modify: `build_budget.py` (`value_data`)

**Interfaces:**
- Consumes: `layout.RAW, STOCK, MERITZ, v`
- Produces: `meritz_sheet.HOLD_FIRST=11`, `HOLD_LAST=110`, `STOCK_FIRST=16`, `STOCK_LAST=115`, `raw_values()`, `stock_values()`, `meritz_values()`, `all_values() -> list[dict]`

- [ ] **Step 1: Write the failing test** — `tests/test_meritz_sheet.py`

```python
import json
from pathlib import Path

import build_budget
import layout
import meritz_sheet as ms

FIX = json.loads((Path(__file__).parent / "fixtures" / "meritz_expected.json").read_text(encoding="utf-8"))


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_raw_headers_match_block_layout():
    raw = _by_range(ms.raw_values())
    assert raw["메리츠원본!A2:A5"] == [["총자산"], ["보유종목"], ["해외보유"], ["외화예수금"]]
    assert [r[0] for r in raw["메리츠원본!G1:G8"]] == [
        "총자산", "원화 현금", "유가증권 평가", "외화 예수금(원)", "대출", "자동투자 인출가능", "순자산", "갱신 시각"]
    assert len(raw["메리츠원본!A10:N10"][0]) == 14
    assert len(raw["메리츠원본!J1:N1"][0]) == 5


def test_holdings_header_width_matches_logic_rows():
    raw = _by_range(ms.raw_values())
    assert len(raw["메리츠원본!A10:N10"][0]) == len(FIX["holdings"][0])


def test_stock_rows_read_raw_holdings_block():
    vals = _by_range(ms.stock_values())
    row = vals["주식!A16:P16"][0]
    assert len(row) == 16
    assert all(f.startswith("=ARRAYFORMULA(IF(메리츠원본!A11:A110=\"\",\"\",") for f in row)
    assert "메리츠원본!G11:G110/메리츠원본!D11:D110" in row[5]  # 현재가(원) = 평가 ÷ 수량
    assert "메리츠원본!H11:H110/메리츠원본!F11:F110" in row[9]  # 수익률(원)
    assert "(메리츠원본!N11:N110-메리츠원본!M11:M110)/메리츠원본!M11:M110" in row[14]  # 수익률(외화)


def test_stock_summary_shows_before_first_refresh():
    vals = _by_range(ms.stock_values())
    assert vals["주식!A5:G5"][0] == ["순자산", "유가증권 평가", "원화 현금", "외화 예수금(원)", "평가손익", "수익률", "자동투자 인출가능"]
    assert vals["주식!A6:G6"][0][0] == '=IF(ISNUMBER(메리츠원본!H7),메리츠원본!H7,"-")'
    assert '"아직 갱신 전"' in vals["주식!A3:B3"][0][1]
    assert vals["주식!G1:I1"][0][1] is False


def test_meritz_check_compares_documented_relations():
    vals = _by_range(ms.meritz_values())
    b3 = vals["메리츠!A3:B3"][0][1]
    assert "SUM(메리츠원본!G11:G110)" in b3 and "메리츠원본!H3" in b3
    assert 'SUMIF(메리츠원본!A11:A110,"해외",메리츠원본!G11:G110)' in b3 and "SUM(메리츠원본!N2:N6)" in b3
    assert '"정상"' in b3


def test_meritz_values_included_in_build():
    ranges = {e["range"] for e in build_budget.value_data("a@b.com")}
    assert {"주식!A16:P16", "메리츠!A3:B3", "메리츠원본!A10:N10"} <= ranges
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_meritz_sheet.py 2>&1 | tail -2`
Expected: FAIL — `ModuleNotFoundError: No module named 'meritz_sheet'`

- [ ] **Step 3: Write implementation** — `meritz_sheet.py`

```python
"""메리츠 연동 탭 값: 원본 머리글, 주식 탭, 메리츠 상세 탭 (모두 메리츠원본을 읽는 수식)."""
from layout import MERITZ, RAW, STOCK, v

HOLD_FIRST, HOLD_LAST = 11, 110      # 메리츠원본 종목 블록 데이터 행
STOCK_FIRST, STOCK_LAST = 16, 115    # 주식 탭 종목 표 데이터 행
STATUS_NAMES = ["총자산", "보유종목", "해외보유", "외화예수금"]
SUMMARY_LABELS = ["총자산", "원화 현금", "유가증권 평가", "외화 예수금(원)", "대출", "자동투자 인출가능", "순자산", "갱신 시각"]
FX_HEADERS = ["통화", "예수금", "환율", "예수금(원)", "해외주식 평가(원)"]
RAW_HOLD_HEADERS = ["구분", "티커", "종목명", "수량", "평단가(원)", "매입금액(원)", "평가금액(원)", "평가손익(원)",
                    "대출(원)", "통화", "평단가(외화)", "현재가(외화)", "매입금액(외화)", "평가금액(외화)"]
STOCK_HEADERS = ["구분", "티커", "종목명", "수량", "평단가(원)", "현재가(원)", "매입금액(원)", "평가금액(원)",
                 "평가손익(원)", "수익률(원)", "통화", "평단가(외화)", "현재가(외화)", "평가금액(외화)", "수익률(외화)", "비중"]
STATUS_TEXT = (f'=IF(COUNTA({RAW}!B2:B5)=0,"아직 갱신 전",'
               f'TEXTJOIN("  ·  ",TRUE,ARRAYFORMULA({RAW}!A2:A5&": "&{RAW}!B2:B5)))')


def col(c: str) -> str:
    """메리츠원본 종목 블록의 한 열."""
    return f"{RAW}!{c}{HOLD_FIRST}:{c}{HOLD_LAST}"


def _show(expr: str) -> str:
    return f'=ARRAYFORMULA(IF({col("A")}="","",{expr}))'


def _copy(c: str) -> str:
    return _show(f'IF({col(c)}="","",{col(c)})')


def _num_or_dash(cell: str) -> str:
    return f'=IF(ISNUMBER({cell}),{cell},"-")'


def raw_values() -> list[dict]:
    return [v(f"{RAW}!A1:E1", [["조회", "상태", "코드", "메시지", "마지막 성공"]]),
            v(f"{RAW}!A2:A5", [[n] for n in STATUS_NAMES]),
            v(f"{RAW}!G1:G8", [[n] for n in SUMMARY_LABELS]),
            v(f"{RAW}!J1:N1", [FX_HEADERS]),
            v(f"{RAW}!A10:N10", [RAW_HOLD_HEADERS])]


def _stock_row() -> list[str]:
    return [_copy("A"), _copy("B"), _copy("C"), _copy("D"), _copy("E"),
            _show(f'IFERROR({col("G")}/{col("D")},"")'),
            _copy("F"), _copy("G"), _copy("H"),
            _show(f'IFERROR({col("H")}/{col("F")},"")'),
            _copy("J"), _copy("K"), _copy("L"), _copy("N"),
            _show(f'IFERROR(({col("N")}-{col("M")})/{col("M")},"")'),
            _show(f'IFERROR({col("G")}/SUM({col("G")}),"")')]


def stock_values() -> list[dict]:
    r = RAW
    summary = [_num_or_dash(f"{r}!H7"), _num_or_dash(f"{r}!H3"), _num_or_dash(f"{r}!H2"), _num_or_dash(f"{r}!H4"),
               f'=IF(COUNTA({col("A")})=0,"-",SUM({col("H")}))',
               f'=IFERROR(SUM({col("H")})/SUM({col("F")}),"-")',
               _num_or_dash(f"{r}!H6")]
    return [v(f"{STOCK}!A1", [["📈 메리츠증권 보유 주식"]]),
            v(f"{STOCK}!G1:I1", [["지금 갱신", False, "◀ 체크하면 바로 갱신 (1~2분)"]]),
            v(f"{STOCK}!A2:B2", [["상태", STATUS_TEXT]]),
            v(f"{STOCK}!A3:B3", [["마지막 갱신", f'=IF(ISNUMBER({r}!H8),{r}!H8,"아직 갱신 전")']]),
            v(f"{STOCK}!A5:G5", [["순자산", "유가증권 평가", "원화 현금", "외화 예수금(원)", "평가손익", "수익률", "자동투자 인출가능"]]),
            v(f"{STOCK}!A6:G6", [summary]),
            v(f"{STOCK}!A8:E8", [FX_HEADERS]),
            v(f"{STOCK}!A9", [[f'=ARRAYFORMULA(IF({r}!J2:J6="","",{r}!J2:N6))']]),
            v(f"{STOCK}!A15:P15", [STOCK_HEADERS]),
            v(f"{STOCK}!A16:P16", [_stock_row()])]


def meritz_values() -> list[dict]:
    r = RAW
    mk, hsum = f"{r}!H3", f'SUM({col("G")})'
    ov, fx = f'SUMIF({col("A")},"해외",{col("G")})', f"SUM({r}!N2:N6)"
    check = (f'=IF(NOT(ISNUMBER({mk})),"-",IF(OR(ABS({hsum}-{mk})>ABS({mk})*0.01,'
             f'ABS({ov}-{fx})>MAX(1,ABS({fx}))*0.01),'
             f'"⚠ 종목 합계가 증권사 평가금액과 1% 넘게 다릅니다 — 조회 시차 또는 데이터 오류","정상"))')
    count = (f'=IF(COUNTIF({col("A")},"?*")=0,"-",COUNTIF({col("A")},"?*")&"개 ("&'
             f'COUNTIF({col("H")},">0")&" / "&COUNTIF({col("H")},"<0")&")")')
    by_kind = [[k, f'=SUMIF({col("A")},"{k}",{col("G")})'] for k in ("국내", "해외", "기타")]
    return [v(f"{MERITZ}!A1", [["🔎 메리츠증권 상세"]]),
            v(f"{MERITZ}!A2:B2", [["상태", STATUS_TEXT]]),
            v(f"{MERITZ}!A3:B3", [["검산", check]]),
            v(f"{MERITZ}!A5:D5", [["순자산", "평가손익", "수익률", "보유 종목 (수익 / 손실)"]]),
            v(f"{MERITZ}!A6:D6", [[f"={STOCK}!A6", f"={STOCK}!E6", f"={STOCK}!F6", count]]),
            v(f"{MERITZ}!A9:B12", [["자산 구성", "금액"], ["유가증권", f"=N({r}!H3)"],
                                   ["원화 현금", f"=N({r}!H2)"], ["외화 예수금", f"=N({r}!H4)"]]),
            v(f"{MERITZ}!D9:E12", [["구분", "평가금액(원)"]] + by_kind)]


def all_values() -> list[dict]:
    return raw_values() + stock_values() + meritz_values()
```

`build_budget.py`: `import guide` 다음 줄에 `import meritz_sheet` 추가, `value_data`를 다음으로 교체:
```python
def value_data(email: str) -> list[dict]:
    return (layout.seed_values(email) + formulas.core_values() + views.view_values()
            + guide.guide_values() + styling.title_values() + meritz_sheet.all_values())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -2`
Expected: `91 passed` (Task 3의 85 + 6). `test_build.py`의 값 범위 모양·겹침·괄호 시험도 새 값까지 통과해야 한다.

- [ ] **Step 5: Commit**

```bash
git add meritz_sheet.py tests/test_meritz_sheet.py build_budget.py
git commit -m "feat: 메리츠원본 머리글, 주식·메리츠 탭 수식"
```

---

### Task 5: meritz_style.py — 검증·서식·머리글·차트·손익 색

**Files:**
- Create: `meritz_style.py`, `tests/test_meritz_style.py`
- Modify: `build_budget.py` (`structure_requests`, `visual_requests`)

**Interfaces:**
- Consumes: `layout.a1_to_grid, number_format, SHEET_ID, STOCK, MERITZ, RAW`; `charts._chart, _basic, _src`; `styling.HEADER_FONT, TITLE_FONT, KPI_FONT, WHITE, VIEW_TAB, CHECK_BG, RED_TEXT, BLUE_TEXT, LABEL_BG`
- Produces: `meritz_style.structure_requests()`, `visual_requests()`, `chart_requests()`, `conditional_requests()`

- [ ] **Step 1: Write the failing test** — `tests/test_meritz_style.py`

```python
import build_budget
import layout
import meritz_style as mst


def _formats():
    return {tuple(sorted(r["repeatCell"]["range"].items())): r["repeatCell"]["cell"]["userEnteredFormat"]
            for r in mst.structure_requests() + mst.visual_requests() if "repeatCell" in r}


def _fmt(a1):
    return _formats()[tuple(sorted(layout.a1_to_grid(a1).items()))]


def test_refresh_checkbox_is_boolean():
    v = [r["setDataValidation"] for r in mst.structure_requests() if "setDataValidation" in r]
    assert v == [{"range": layout.a1_to_grid("주식!H1"), "rule": {"condition": {"type": "BOOLEAN"},
                                                                  "strict": False, "showCustomUi": True}}]


def test_number_formats_for_money_percent_and_time():
    assert _fmt("메리츠원본!H8")["numberFormat"]["pattern"] == "yyyy-mm-dd hh:mm"
    assert _fmt("주식!B3")["numberFormat"]["pattern"] == "yyyy-mm-dd hh:mm"
    assert _fmt("주식!J16:J115")["numberFormat"]["type"] == "PERCENT"
    assert _fmt("주식!E16:I115")["numberFormat"]["pattern"] == "#,##0"
    assert _fmt("주식!D16:D115")["numberFormat"]["pattern"] == "#,##0.####"


def test_four_charts_on_meritz_tab_stacked():
    charts = [r["addChart"]["chart"] for r in mst.chart_requests()]
    assert [c["spec"]["title"] for c in charts] == ["자산 구성", "국내·해외·기타", "종목별 평가금액", "종목별 수익률"]
    anchors = [c["position"]["overlayPosition"]["anchorCell"] for c in charts]
    assert all(a["sheetId"] == 1600 and a["columnIndex"] == 0 for a in anchors)
    assert [a["rowIndex"] for a in anchors] == sorted(a["rowIndex"] for a in anchors)


def test_profit_red_loss_blue_only_on_stock_tabs():
    rules = [r["addConditionalFormatRule"]["rule"] for r in mst.conditional_requests()]
    sheets = {g["sheetId"] for r in rules for g in r["ranges"]}
    assert sheets == {1500, 1600}
    gt = [r for r in rules if r["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"]
    lt = [r for r in rules if r["booleanRule"]["condition"]["type"] == "NUMBER_LESS"]
    assert gt and lt
    assert all(r["booleanRule"]["format"]["textFormat"]["foregroundColor"] == mst.RED_TEXT for r in gt)
    assert all(r["booleanRule"]["format"]["textFormat"]["foregroundColor"] == mst.BLUE_TEXT for r in lt)


def test_meritz_requests_included_in_build():
    assert any("addChart" in r and r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 1600
               for r in build_budget.visual_requests())
    assert any(r.get("setDataValidation", {}).get("range") == layout.a1_to_grid("주식!H1")
               for r in build_budget.structure_requests())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_meritz_style.py 2>&1 | tail -2`
Expected: FAIL — `ModuleNotFoundError: No module named 'meritz_style'`

- [ ] **Step 3: Write implementation** — `meritz_style.py`

```python
"""메리츠 연동 탭 서식: 체크박스 검증, 숫자 서식, 머리글·제목, 차트, 손익 색(수익 빨강·손실 파랑)."""
from charts import _basic, _chart, _src
from layout import MERITZ, RAW, STOCK, a1_to_grid, number_format
from styling import (BLUE_TEXT, CHECK_BG, HEADER_FONT, KPI_FONT, LABEL_BG, RED_TEXT, TITLE_FONT, VIEW_TAB,
                     WHITE)

TIME_FMT = "yyyy-mm-dd hh:mm"
HEADER_RANGES = [f"{STOCK}!A5:G5", f"{STOCK}!A8:E8", f"{STOCK}!A15:P15",
                 f"{MERITZ}!A5:D5", f"{MERITZ}!A9:B9", f"{MERITZ}!D9:E9", f"{RAW}!A1:E1", f"{RAW}!A10:N10"]


def _fmt(a1: str, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1), "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def _formats() -> list[dict]:
    fmts = [(f"{RAW}!H1:H7", "NUMBER", "#,##0"), (f"{RAW}!H8", "DATE_TIME", TIME_FMT),
            (f"{RAW}!E2:E5", "DATE_TIME", TIME_FMT),
            (f"{STOCK}!B3", "DATE_TIME", TIME_FMT), (f"{STOCK}!A6:E6", "NUMBER", "#,##0"),
            (f"{STOCK}!F6", "PERCENT", "0.00%"), (f"{STOCK}!G6", "NUMBER", "#,##0"),
            (f"{STOCK}!B9:C13", "NUMBER", "#,##0.00"), (f"{STOCK}!D9:E13", "NUMBER", "#,##0"),
            (f"{STOCK}!D16:D115", "NUMBER", "#,##0.####"), (f"{STOCK}!E16:I115", "NUMBER", "#,##0"),
            (f"{STOCK}!J16:J115", "PERCENT", "0.00%"), (f"{STOCK}!L16:N115", "NUMBER", "#,##0.00"),
            (f"{STOCK}!O16:O115", "PERCENT", "0.00%"), (f"{STOCK}!P16:P115", "PERCENT", "0.0%"),
            (f"{MERITZ}!A6:B6", "NUMBER", "#,##0"), (f"{MERITZ}!C6", "PERCENT", "0.00%"),
            (f"{MERITZ}!B10:B12", "NUMBER", "#,##0"), (f"{MERITZ}!E10:E12", "NUMBER", "#,##0")]
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]


def structure_requests() -> list[dict]:
    check = {"setDataValidation": {"range": a1_to_grid(f"{STOCK}!H1"), "rule": {
        "condition": {"type": "BOOLEAN"}, "strict": False, "showCustomUi": True}}}
    return [check] + _formats()


def style_requests() -> list[dict]:
    head = {"backgroundColor": VIEW_TAB, "horizontalAlignment": "CENTER",
            "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}
    reqs = [_fmt(a1, head, "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)")
            for a1 in HEADER_RANGES]
    title = {"textFormat": {"fontSize": TITLE_FONT, "bold": True}}
    reqs += [_fmt(a1, title, "userEnteredFormat.textFormat") for a1 in (f"{STOCK}!A1", f"{MERITZ}!A1")]
    kpi = {"horizontalAlignment": "CENTER", "textFormat": {"fontSize": KPI_FONT, "bold": True}}
    reqs += [_fmt(a1, kpi, "userEnteredFormat(horizontalAlignment,textFormat)")
             for a1 in (f"{STOCK}!A6:G6", f"{MERITZ}!A6:D6")]
    reqs.append(_fmt(f"{STOCK}!G1:H1", {"backgroundColor": CHECK_BG, "textFormat": {"bold": True}},
                     "userEnteredFormat(backgroundColor,textFormat.bold)"))
    reqs.append(_fmt(f"{MERITZ}!A2:A3", {"backgroundColor": LABEL_BG, "textFormat": {"bold": True}},
                     "userEnteredFormat(backgroundColor,textFormat.bold)"))
    return reqs


def chart_requests() -> list[dict]:
    m, s = MERITZ, STOCK
    donut = {"title": "자산 구성", "pieChart": {"legendPosition": "RIGHT_LEGEND", "pieHole": 0.5,
                                            "domain": _src(f"{m}!A10:A12"), "series": _src(f"{m}!B10:B12")}}
    return [_chart(donut, m, 13),
            _chart(_basic("국내·해외·기타", "COLUMN", f"{m}!D9:D12", [(f"{m}!E9:E12", "COLUMN")]), m, 30),
            _chart(_basic("종목별 평가금액", "COLUMN", f"{s}!C15:C115", [(f"{s}!H15:H115", "COLUMN")]), m, 47),
            _chart(_basic("종목별 수익률", "COLUMN", f"{s}!C15:C115", [(f"{s}!J15:J115", "COLUMN")]), m, 64)]


def _sign_rule(a1: str, ctype: str, color: dict) -> dict:
    cond = {"type": ctype, "values": [{"userEnteredValue": "0"}]}
    return {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(a1)], "booleanRule": {
        "condition": cond, "format": {"textFormat": {"foregroundColor": color, "bold": True}}}}}}


def conditional_requests() -> list[dict]:
    ranges = [f"{STOCK}!I16:J115", f"{STOCK}!O16:O115", f"{STOCK}!E6:F6", f"{MERITZ}!B6:C6"]
    return ([_sign_rule(a1, "NUMBER_GREATER", RED_TEXT) for a1 in ranges]
            + [_sign_rule(a1, "NUMBER_LESS", BLUE_TEXT) for a1 in ranges])


def visual_requests() -> list[dict]:
    return style_requests() + chart_requests() + conditional_requests()
```

`build_budget.py`: `import meritz_sheet` 다음 줄에 `import meritz_style` 추가. `structure_requests`와 `visual_requests`를 다음으로 교체:
```python
def structure_requests() -> list[dict]:
    return (layout.validation_requests() + layout.format_requests() + formulas.core_formats()
            + views.view_formats() + meritz_style.structure_requests() + layout.protection_requests())


def visual_requests() -> list[dict]:
    return (styling.style_requests() + guide.guide_requests()
            + charts.chart_requests() + charts.conditional_requests() + meritz_style.visual_requests())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -2`
Expected: `96 passed` (91 + 5)

- [ ] **Step 5: Commit**

```bash
git add meritz_style.py tests/test_meritz_style.py build_budget.py
git commit -m "feat: 주식·메리츠 탭 검증·서식·차트·손익 색"
```

---

### Task 6: meritz.gs — API 호출·잠금·키 메뉴·쓰기, setupTriggers, 배포 목록

**Files:**
- Create: `apps-script/meritz.gs`
- Modify: `apps-script/triggers.gs` (`setupTriggers`), `deploy_script.py` (`SOURCES`), `tests/test_deploy.py`

**Interfaces:**
- Consumes: Task 1·2의 모든 `meritz_logic.gs` 전역
- Produces: Apps Script 전역 `onOpen`, `setMeritzKeys`, `clearMeritzKeys`, `onEditMeritz(e)`, `refreshMeritz()`; `deploy_script.SOURCES = ["logic", "triggers", "meritz_logic", "meritz"]`

`meritz.gs`는 `UrlFetchApp`·`PropertiesService`·`LockService`에 묶인 연결부라 단위 시험 대신 구문 검사와 Task 9·키 발급 뒤 확인으로 검증한다(판단은 모두 Task 1·2에서 시험됨). Python 배포 목록만 TDD.

- [ ] **Step 1: Write the failing test** — `tests/test_deploy.py`의 `assert set(files) == {"appsscript", "logic", "triggers"}`를 다음으로 교체하고 시험 하나를 끝에 추가:

```python
    assert set(files) == {"appsscript", "logic", "triggers", "meritz_logic", "meritz"}
```
```python


def test_meritz_script_has_no_trading_paths_and_owner_guard():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    src = files["meritz"] + files["meritz_logic"]
    assert "/trading/" not in src and "/forex/" not in src and "tr_cont:" not in src
    assert "getUserProperties" in src and "getScriptProperties" not in src
    assert "function onEditMeritz" in files["meritz"] and "function onEdit(" not in files["meritz"]
    assert "'onEditMeritz'" in files["triggers"] and "'refreshMeritz'" in files["triggers"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_deploy.py 2>&1 | tail -2`
Expected: FAIL — `assert {'appsscript', 'logic', 'triggers'} == {...}`

- [ ] **Step 3: Write implementation**

`apps-script/meritz.gs`:
```js
/* 메리츠 API 연결부 — 판단 로직은 meritz_logic.gs. 조회 전용(주문·환전 경로 없음).
   키·MAC·토큰은 소유자의 사용자 속성에만 둔다 (스크립트 속성은 편집자가 설정 화면에서 볼 수 있음). */

var RAW_SHEET = '메리츠원본';
var PROP = { key: 'MERITZ_APP_KEY', secret: 'MERITZ_APP_SECRET', mac: 'MERITZ_MAC',
  token: 'MERITZ_TOKEN', exp: 'MERITZ_TOKEN_EXP' };

function onOpen() {
  SpreadsheetApp.getUi().createMenu('메리츠')
    .addItem('키 입력 (소유자)', 'setMeritzKeys')
    .addItem('키 삭제', 'clearMeritzKeys')
    .addToUi();
}

function isOwner_() {
  var owner = SpreadsheetApp.getActive().getOwner();
  return !owner || owner.getEmail() === Session.getEffectiveUser().getEmail();
}

function askValue_(ui, label) {
  var r = ui.prompt('메리츠 키 입력', label, ui.ButtonSet.OK_CANCEL);
  return r.getSelectedButton() === ui.Button.OK ? r.getResponseText().trim() : '';
}

function setMeritzKeys() {
  var ui = SpreadsheetApp.getUi();
  if (!isOwner_()) {
    ui.alert('시트 소유자만 키를 넣을 수 있습니다. (자동 갱신이 소유자 권한으로 돌기 때문)');
    return;
  }
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
  ui.alert("저장했습니다. [주식] 탭의 '지금 갱신'을 체크해 확인하세요.");
}

function clearMeritzKeys() {
  var p = PropertiesService.getUserProperties();
  [PROP.key, PROP.secret, PROP.mac, PROP.token, PROP.exp].forEach(function (k) { p.deleteProperty(k); });
  SpreadsheetApp.getUi().alert('메리츠 키를 지웠습니다.');
}

// 설치형 onEdit (setupTriggers가 만듦). 이름이 onEdit이면 단순 트리거로 한 번 더 돌기 때문에 다른 이름.
function onEditMeritz(e) {
  var r = e.range;
  if (r.getSheet().getName() !== '주식' || r.getA1Notation() !== 'H1' || e.value !== 'TRUE') return;
  r.setValue(false);
  refreshMeritz();
}

// 시간 트리거·체크박스 공용. 예외를 밖으로 던지지 않는다 (던지면 구글이 실패 메일을 보냄).
function refreshMeritz() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return; // 이미 갱신 중
  var ss = SpreadsheetApp.getActive();
  try {
    refreshMeritz_(ss);
  } catch (err) {
    writeAllStatus_(ss, { kind: 'error', code: '', msg: '예외: ' + err.message });
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
    writeAllStatus_(ss, { kind: 'nokey', code: '', msg: '메뉴 메리츠 > 키 입력 (소유자)' });
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
    if (r.kind === 'error' && !renewed) { // 토큰 문제일 수 있음 — 갱신당 한 번만 새로 받는다
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
  var sh = ss.getSheetByName(RAW_SHEET);
  MERITZ_ORDER.forEach(function (name) { writeStatus_(sh, name, r, '', new Date()); });
}

function failed_(r, err) {
  return { kind: 'error', code: r.code, msg: err.message, data: null };
}

// 성공한 조회의 블록만 덮어쓴다. 실패한 블록과 그 마지막 성공 시각은 그대로 둔다.
function writeResults_(ss, res) {
  var sh = ss.getSheetByName(RAW_SHEET);
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
```

`apps-script/triggers.gs`의 `setupTriggers` 전체를 다음으로 교체:
```js
// 시트 소유자가 1회 직접 실행: 확장 프로그램 > Apps Script > setupTriggers ▶ 실행 → 권한 허용
// (메리츠 자동 갱신은 실행한 사람 권한으로 돌므로 소유자가 실행해야 함)
function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('dailyJob').timeBased().everyDays(1).atHour(6).create();
  ScriptApp.newTrigger('refreshMeritz').timeBased().everyDays(1).atHour(7).create();
  ScriptApp.newTrigger('refreshMeritz').timeBased().everyDays(1).atHour(16).create();
  ScriptApp.newTrigger('onEditMeritz').forSpreadsheet(SpreadsheetApp.getActive()).onEdit().create();
}
```

`deploy_script.py`: `SOURCES = ["logic", "triggers"]` → `SOURCES = ["logic", "triggers", "meritz_logic", "meritz"]`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -1 && node --test tests/meritz.test.js 2>&1 | grep -E "^# (pass|fail)" && node --test tests/logic.test.js 2>&1 | grep -E "^# (pass|fail)" && for f in meritz triggers; do node -e "new Function(require('fs').readFileSync('apps-script/$f.gs','utf8'))" || exit 1; done && echo SYNTAX_OK`
Expected: pytest `97 passed`, meritz `# pass 17 # fail 0`, logic `# pass 27 # fail 0`, `SYNTAX_OK`

- [ ] **Step 5: 전역 이름 충돌 검사** — Apps Script는 모든 `.gs`가 한 전역을 공유하므로 같은 이름 함수가 있으면 뒤 파일이 조용히 덮어쓴다.

Run: `grep -ho "^function [A-Za-z_]*\|^var [A-Za-z_]*" apps-script/*.gs | sort | uniq -d`
Expected: 출력 없음

- [ ] **Step 6: Commit**

```bash
git add apps-script/meritz.gs apps-script/triggers.gs deploy_script.py tests/test_deploy.py
git commit -m "feat: 메리츠 API 연결부(잠금·키 메뉴·블록 쓰기)와 갱신 트리거"
```

---

### Task 7: migrate_meritz.py — 운영 시트 제자리 적용 (반복 안전)

**Files:**
- Create: `migrate_meritz.py`, `tests/test_migrate_meritz.py`

**Interfaces:**
- Consumes: `layout.SHEETS, SHEET_ID, protection_requests, validation_requests, a1_to_grid`, `formulas.asset_values`, `guide.GUIDE_ROWS, guide_requests`, `meritz_sheet.all_values`, `meritz_style.structure_requests, visual_requests`, `styling.base_requests, layout_requests, header_requests`
- Produces: `migrate_meritz.plan(existing: set[str], asset_cols: int, asset_g1: str, guide_rows: int) -> tuple[list[dict], list[dict], list[dict]]` (구조 요청, 값, 보기 요청), `main()`

- [ ] **Step 1: Write the failing test** — `tests/test_migrate_meritz.py`

```python
import re

import guide
import layout
import migrate_meritz as mm

OLD_TABS = {t for t, *_ in layout.SHEETS} - {"주식", "메리츠", "메리츠원본"}
FRESH = (OLD_TABS, 6, "", len(guide.CONTENT) - 6)
DONE = (OLD_TABS | {"주식", "메리츠", "메리츠원본"}, 8, "연동", len(guide.CONTENT))


def _kinds(reqs):
    return [next(iter(r)) for r in reqs]


def test_fresh_sheet_gets_tabs_columns_and_visuals():
    structure, values, visual = mm.plan(*FRESH)
    added = [r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r]
    assert sorted(added) == ["메리츠", "메리츠원본", "주식"]
    raw = [r["addSheet"]["properties"] for r in structure if "addSheet" in r and
           r["addSheet"]["properties"]["title"] == "메리츠원본"][0]
    assert raw["hidden"] is True and raw["sheetId"] == 1400
    assert {"appendDimension": {"sheetId": 300, "dimension": "COLUMNS", "length": 2}} in structure
    assert "addChart" in _kinds(visual) and "addConditionalFormatRule" in _kinds(visual)
    assert "addProtectedRange" in _kinds(structure)
    ranges = {v["range"] for v in values}
    assert {"자산!G1", "자산!E1:E2", "자산!H1:H2", "주식!A16:P16"} <= ranges


def test_second_run_adds_nothing_duplicable():
    structure, values, visual = mm.plan(*DONE)
    for kind in ("addSheet", "appendDimension", "addProtectedRange", "addChart", "addConditionalFormatRule",
                 "mergeCells", "setDataValidation"):
        assert kind not in _kinds(structure) + _kinds(visual), kind


def test_never_writes_existing_data_ranges():
    _structure, values, _visual = mm.plan(*FRESH)
    forbidden = re.compile(r"^(내역|반복|즐겨찾기|설정|대시보드|추이|달력|검색|문자입력|알림기록)!")
    for v in values:
        assert not forbidden.match(v["range"]), v["range"]
        if v["range"].startswith("자산!"):
            assert v["range"] in {"자산!G1", "자산!E1:E2", "자산!H1:H2"}, v["range"]


def test_new_guide_rows_formatted_only_from_old_end():
    _s, _v, visual = mm.plan(*FRESH)
    guide_cells = [r["repeatCell"]["range"] for r in visual if "repeatCell" in r
                   and r["repeatCell"]["range"]["sheetId"] == layout.SHEET_ID["사용법"]]
    assert min(g["startRowIndex"] for g in guide_cells) == len(guide.CONTENT) - 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_migrate_meritz.py 2>&1 | tail -2`
Expected: FAIL — `ModuleNotFoundError: No module named 'migrate_meritz'`

- [ ] **Step 3: Write implementation** — `migrate_meritz.py`

```python
"""운영 시트에 메리츠 연동을 제자리 적용한다. 두 번 실행해도 안전(이미 된 부분은 건너뜀).

사용: python3 migrate_meritz.py   (대상: .spreadsheet_id)
"""
import sys
from pathlib import Path

from googleapiclient.discovery import build

import formulas
import guide
import layout
import meritz_sheet
import meritz_style
import styling
from auth import get_credentials
from layout import ASSETS, GUIDE, MERITZ, RAW, SHEET_ID, SHEETS, STOCK

NEW_TABS = (STOCK, MERITZ, RAW)
ASSET_COLS = 8
ID_FILE = Path(__file__).parent / ".spreadsheet_id"


def _sheet_ids(req: dict) -> set[int]:
    """요청이 건드리는 sheetId 모음 (범위가 여러 개인 조건부 서식 포함)."""
    body = next(iter(req.values()))
    found = set()
    stack = [body]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if isinstance(cur.get("sheetId"), int):
                found.add(cur["sheetId"])
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return found


def _only(reqs: list[dict], ids: set[int]) -> list[dict]:
    return [r for r in reqs if _sheet_ids(r) and _sheet_ids(r) <= ids]


def _add_sheet(title: str) -> dict:
    _t, sid, rows, cols, hidden = [s for s in SHEETS if s[0] == title][0]
    return {"addSheet": {"properties": {"sheetId": sid, "title": title, "hidden": hidden,
                                        "gridProperties": {"rowCount": rows, "columnCount": cols, "frozenRowCount": 1}}}}


def _asset_requests() -> list[dict]:
    g = layout.a1_to_grid(f"{ASSETS}!G2:G50")
    h = layout.a1_to_grid(f"{ASSETS}!H1:H50")
    valid = [r for r in layout.validation_requests() if r["setDataValidation"]["range"] == g]
    protect = [r for r in layout.protection_requests() if r["addProtectedRange"]["protectedRange"]["range"] == h]
    return valid + protect


def plan(existing: set[str], asset_cols: int, asset_g1: str, guide_rows: int):
    new = [t for t in NEW_TABS if t not in existing]
    new_ids = {SHEET_ID[t] for t in new}
    structure = [_add_sheet(t) for t in new]
    if asset_cols < ASSET_COLS:
        structure.append({"appendDimension": {"sheetId": SHEET_ID[ASSETS], "dimension": "COLUMNS",
                                              "length": ASSET_COLS - asset_cols}})
    structure += _only(meritz_style.structure_requests() + layout.protection_requests(), new_ids)
    asset_new = asset_g1 != "연동"
    if asset_new:
        structure += _asset_requests()

    values = meritz_sheet.all_values() if new else []
    values += [v for v in formulas.asset_values()] + [layout.v(f"{ASSETS}!G1", [["연동"]])]
    values += guide.guide_values()

    visual = _only(styling.base_requests() + styling.layout_requests(), new_ids)
    visual += _only(meritz_style.visual_requests(), new_ids | {SHEET_ID[STOCK]} if new else set())
    if asset_new:
        visual += _only(styling.layout_requests() + styling.header_requests(), {SHEET_ID[ASSETS]})
    if guide_rows < len(guide.CONTENT):
        visual += guide.guide_requests(start=guide_rows)
    return structure, values, visual


def _state(sheets, sid: str):
    meta = sheets.get(spreadsheetId=sid, fields="sheets(properties(sheetId,title,gridProperties(columnCount)))").execute()
    props = [s["properties"] for s in meta["sheets"]]
    existing = {p["title"] for p in props}
    asset_cols = [p["gridProperties"]["columnCount"] for p in props if p["sheetId"] == SHEET_ID[ASSETS]][0]
    got = sheets.values().batchGet(spreadsheetId=sid, ranges=[f"{ASSETS}!G1", f"{GUIDE}!A1:A200"]).execute()
    g1 = (got["valueRanges"][0].get("values") or [[""]])[0][0]
    guide_rows = len(got["valueRanges"][1].get("values") or [])
    return existing, asset_cols, g1, guide_rows


def main() -> int:
    sid = ID_FILE.read_text().strip()
    sheets = build("sheets", "v4", credentials=get_credentials()).spreadsheets()
    state = _state(sheets, sid)
    structure, values, visual = plan(*state)
    if structure:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": structure}).execute()
    sheets.values().batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED", "data": values}).execute()
    if visual:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": visual}).execute()
    print(f"적용: 탭 추가 {sum('addSheet' in r for r in structure)}개, 값 {len(values)}개 범위, 서식 {len(visual)}개 요청")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

주의: `visual`의 `_only(meritz_style.visual_requests(), ...)` 줄은 새 탭이 있을 때만 메리츠 서식·차트·조건부서식을 넣는다. 차트가 `주식` 범위를 데이터로 읽어도 차트 자체는 `메리츠` 탭(1600)에 있으므로 `_sheet_ids`가 {1600, 1500}을 돌려준다 — 그래서 허용 집합에 `주식` id를 더한다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -1`
Expected: `101 passed` (97 + 4)

- [ ] **Step 5: Commit**

```bash
git add migrate_meritz.py tests/test_migrate_meritz.py
git commit -m "feat: 운영 시트 메리츠 연동 제자리 적용 (반복 실행 안전)"
```

---

### Task 8: verify_meritz.py — 임시 시트 통합 시험 (키 없이)

**Files:**
- Create: `verify_meritz.py`, `tests/test_verify_meritz.py`

**Interfaces:**
- Consumes: `build_budget.structure_requests, value_data, visual_requests`, `layout.create_body`, `tests/fixtures/meritz_expected.json`
- Produces: `verify_meritz.raw_data(expected, now_serial) -> list[dict]`, `verify_meritz.checks(expected) -> dict[str, object]`, `main()` (종료코드 0 = 통과)

- [ ] **Step 1: Write the failing test** — `tests/test_verify_meritz.py`

```python
import json
from pathlib import Path

import verify_meritz as vm

EXP = json.loads((Path(__file__).parent / "fixtures" / "meritz_expected.json").read_text(encoding="utf-8"))


def test_raw_data_writes_only_raw_blocks_and_asset_link_row():
    data = vm.raw_data(EXP, 46000.5)
    ranges = {d["range"] for d in data}
    assert ranges == {"메리츠원본!H1:H8", "메리츠원본!B2:E5", "메리츠원본!J2:N2",
                      f"메리츠원본!A11:N{10 + len(EXP['holdings'])}", "자산!A5:D5", "자산!G5"}
    h = [d for d in data if d["range"] == "메리츠원본!H1:H8"][0]["values"]
    assert [r[0] for r in h] == EXP["summary"] + [46000.5]


def test_checks_cover_net_profit_rate_count_and_asset():
    c = vm.checks(EXP)
    assert c["주식!A6"] == 6092500
    assert c["주식!E6"] == 168500
    assert abs(c["주식!F6"] - 168500 / 5084000) < 1e-9
    assert c["메리츠!B3"] == "정상"
    assert c["메리츠!D6"] == "5개 (3 / 1)"
    assert c["자산!E5"] == 6092500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_verify_meritz.py 2>&1 | tail -2`
Expected: FAIL — `ModuleNotFoundError: No module named 'verify_meritz'`

- [ ] **Step 3: Write implementation** — `verify_meritz.py`

```python
"""메리츠 화면 통합 시험 — 임시 시트를 새로 만들어 샘플 원본을 넣고 화면 값을 확인한 뒤 휴지통으로 보낸다.

운영 시트에는 손대지 않는다. 공유하지 않는다. 사용: python3 verify_meritz.py  (종료코드 0 = 통과)
"""
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import layout
from auth import get_credentials

FIX = Path(__file__).parent / "tests" / "fixtures" / "meritz_expected.json"


def serial(t: dt.datetime) -> float:
    """시트 날짜 일련번호 (1899-12-30 기준, 시트 시간대 Asia/Seoul의 벽시계 시각)."""
    base = dt.datetime(1899, 12, 30)
    return (t.replace(tzinfo=None) - base).total_seconds() / 86400


def raw_data(expected: dict, now_serial: float) -> list[dict]:
    rows = expected["holdings"]
    status = [["성공", "5766", "", now_serial]] * 4
    return [layout.v("메리츠원본!H1:H8", [[x] for x in expected["summary"]] + [[now_serial]]),
            layout.v("메리츠원본!B2:E5", status),
            layout.v("메리츠원본!J2:N2", expected["fx"]),
            layout.v(f"메리츠원본!A11:N{10 + len(rows)}", rows),
            layout.v("자산!A5:D5", [["메리츠증권", "통장", 0, ""]]),
            layout.v("자산!G5", [["메리츠"]])]


def checks(expected: dict) -> dict:
    rows = expected["holdings"]
    krw = [r for r in rows if r[5] != ""]
    profit = sum(r[7] for r in krw)
    cost = sum(r[5] for r in krw)
    wins, losses = sum(r[7] > 0 for r in krw), sum(r[7] < 0 for r in krw)
    return {"주식!A6": expected["summary"][6], "주식!E6": profit, "주식!F6": profit / cost,
            "메리츠!B3": "정상", "메리츠!D6": f"{len(rows)}개 ({wins} / {losses})",
            "자산!E5": expected["summary"][6]}


def _same(got, want) -> bool:
    if isinstance(want, float):
        return isinstance(got, (int, float)) and abs(got - want) < 1e-9
    return got == want


def _read(vals, sid: str, a1: str):
    got = vals.get(spreadsheetId=sid, range=a1, valueRenderOption="UNFORMATTED_VALUE").execute().get("values")
    return got[0][0] if got else None


def run(sheets, vals, drive) -> list[str]:
    expected = json.loads(FIX.read_text(encoding="utf-8"))
    sid = sheets.create(body=layout.create_body("메리츠 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
    try:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.structure_requests()}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": build_budget.value_data("nobody@example.com")}).execute()
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.visual_requests()}).execute()
        now = serial(dt.datetime.now(ZoneInfo("Asia/Seoul")))
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": raw_data(expected, now)}).execute()
        errors = [f"{a1}: 기대 {want!r}, 실제 {_read(vals, sid, a1)!r}"
                  for a1, want in checks(expected).items() if not _same(_read(vals, sid, a1), want)]
        fresh = _read(vals, sid, "자산!H5")
        if not str(fresh).startswith("메리츠 "):
            errors.append(f"자산!H5: '메리츠 …' 기대, 실제 {fresh!r}")
        vals.update(spreadsheetId=sid, range="메리츠원본!H8", valueInputOption="RAW", body={"values": [[now - 5]]}).execute()
        stale = _read(vals, sid, "자산!H5")
        if not str(stale).startswith("오래됨"):
            errors.append(f"자산!H5(5일 전): '오래됨' 기대, 실제 {stale!r}")
        return errors
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else "통과: 메리츠 화면 8개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

주의: `create_body`의 시트에는 `자산` 시드가 4행까지라 5행은 비어 있다. `자산!E5`는 E2의 MAP 수식이 채우므로 직접 쓰지 않는다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -1`
Expected: `103 passed`

- [ ] **Step 5: 실제 임시 시트로 실행** (토큰 `token.json` 이미 있음, 운영 시트와 무관, 공유 안 함)

Run: `python3 verify_meritz.py; echo "exit=$?"`
Expected: `통과: 메리츠 화면 8개 항목 일치 (임시 시트는 휴지통으로)`, `exit=0`.
실패하면 해당 칸의 수식을 고친다(`meritz_sheet.py`·`formulas.py`). 수식 오류(#REF!/#VALUE!/#NAME?)가 원인이면 그 셀을 실패 메시지에서 확인하고, 시험 기대값(`meritz_expected.json`)은 고치지 않는다.

- [ ] **Step 6: Commit**

```bash
git add verify_meritz.py tests/test_verify_meritz.py
git commit -m "test: 메리츠 화면 임시 시트 통합 시험"
```

---

### Task 9: 운영 시트 적용·배포·README

**Files:**
- Modify: `README.md`
- 운영 작업: `migrate_meritz.py`, `deploy_script.py` 실행

**Interfaces:**
- Consumes: Task 6·7 산출물, `.spreadsheet_id`, `.script_id`

- [ ] **Step 1: 적용 전 자산 잔액 기록**

Run:
```bash
python3 - <<'EOF' > /tmp/claude-1000/-home-jack/216c03f3-56ca-434c-bdad-1837a6b06ba5/scratchpad/assets_before.json
import json
from googleapiclient.discovery import build
from auth import get_credentials
sid = open('.spreadsheet_id').read().strip()
v = build('sheets', 'v4', credentials=get_credentials()).spreadsheets().values()
print(json.dumps(v.get(spreadsheetId=sid, range='자산!A1:F20', valueRenderOption='UNFORMATTED_VALUE').execute().get('values'), ensure_ascii=False))
EOF
wc -c /tmp/claude-1000/-home-jack/216c03f3-56ca-434c-bdad-1837a6b06ba5/scratchpad/assets_before.json
```
Expected: 0보다 큰 바이트 수

- [ ] **Step 2: 마이그레이션 2회 실행 (두 번째는 아무것도 추가하지 않아야 함)**

Run: `python3 migrate_meritz.py && python3 migrate_meritz.py`
Expected: 첫 줄 `적용: 탭 추가 3개, ...`, 둘째 줄 `적용: 탭 추가 0개, ...`

- [ ] **Step 3: 적용 후 확인 — 기존 잔액 불변, 새 탭 "아직 갱신 전", 중복 없음**

Run:
```bash
python3 - <<'EOF'
import json
from googleapiclient.discovery import build
from auth import get_credentials
sid = open('.spreadsheet_id').read().strip()
s = build('sheets', 'v4', credentials=get_credentials()).spreadsheets()
before = json.load(open('/tmp/claude-1000/-home-jack/216c03f3-56ca-434c-bdad-1837a6b06ba5/scratchpad/assets_before.json'))
after = s.values().get(spreadsheetId=sid, range='자산!A1:F20', valueRenderOption='UNFORMATTED_VALUE').execute().get('values')
print('자산 A:F 동일:', before == after)
print('주식!B3:', s.values().get(spreadsheetId=sid, range='주식!B3').execute().get('values'))
m = s.get(spreadsheetId=sid, fields='sheets(properties(title,hidden),charts(chartId))').execute()
print({x['properties']['title']: (x['properties'].get('hidden', False), len(x.get('charts', []))) for x in m['sheets']
       if x['properties']['title'] in ('주식', '메리츠', '메리츠원본')})
EOF
```
Expected: `자산 A:F 동일: True`, `주식!B3: [['아직 갱신 전']]`, `{'주식': (False, 0), '메리츠': (False, 4), '메리츠원본': (True, 0)}`

- [ ] **Step 4: 스크립트 배포**

Run: `python3 deploy_script.py`
Expected: `업로드 완료: scriptId=...`

- [ ] **Step 5: README 갱신** — `README.md`의 `## 사용법` 아래 마지막 항목 다음에 추가:

```markdown
- **주식(메리츠증권)**: `주식`·`메리츠` 탭이 메리츠 Open API로 매일 07시대·16시대 자동 갱신됩니다. `주식` 탭 H1 '지금 갱신' 체크로 바로 갱신.
  - 처음 한 번(소유자만): PC에서 시트 메뉴 `메리츠 > 키 입력` → App Key·App Secret·MAC 주소(윈도우 `getmac`) 입력 → `확장 프로그램 > Apps Script`에서 `setupTriggers` ▶ 실행·권한 허용.
  - `자산` 탭 G열 '연동'에 `메리츠`를 고른 계좌는 잔액이 증권사 순자산(총자산−대출)으로 채워집니다.
  - 키는 소유자의 사용자 속성에만 저장됩니다(시트·git에 없음). 노출이 의심되면 포털에서 재발급 후 `키 입력`을 다시 하세요.
```

`## 개발`의 테스트 줄을 `- 테스트: \`python3 -m pytest -q\` / \`node --test tests/logic.test.js\` / \`node --test tests/meritz.test.js\``로 바꾸고, 그 아래에 추가:
```markdown
- 메리츠 화면 통합 시험(임시 시트, 키 불필요): `python3 verify_meritz.py`
- 운영 시트에 메리츠 탭 적용(반복 안전): `python3 migrate_meritz.py`
```

`## 알려진 한계`에 추가:
```markdown
- 메리츠 키 발급 전에는 실제 연결을 확인하지 못함: 구글 서버→9443 포트 접속, IP 제한, MAC 검사, 슈퍼365 자동투자분이 총자산에 포함되는지.
- 시트 편집 권한자는 Apps Script 코드를 고칠 수 있고 갱신은 소유자 권한으로 돌므로, 악의적 코드 수정으로 키를 빼낼 수 있음(부부 공유 범위에서 수용).
```

- [ ] **Step 6: 전체 시험 후 Commit**

Run: `python3 -m pytest -q 2>&1 | tail -1 && node --test tests/meritz.test.js 2>&1 | grep -E "^# (pass|fail)" && node --test tests/logic.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: `103 passed`, meritz `# pass 17 # fail 0`, logic `# pass 27 # fail 0`

```bash
git add README.md
git commit -m "docs: 메리츠 연동 사용법·개발·한계"
```

- [ ] **Step 7: 사용자 작업 안내 (소유자 신랑)**
1. 시트를 새로고침 → 메뉴에 `메리츠`가 보이는지 확인.
2. `확장 프로그램 > Apps Script` → `setupTriggers` ▶ 실행 → 새 권한(외부 요청) 허용.
3. 키 발급 전이면 `주식` 탭 H1 체크 → `메리츠원본` 상태가 `키없음`, 화면은 "아직 갱신 전"으로 남는지 확인(Review Focus 4).
4. 키 발급 후: 스펙 "키 발급 뒤 순서" ①~⑥.

---

## 스펙 대비 커버리지

| 스펙 항목 | Task |
|---|---|
| 조회 4개·토큰·코드별 처리·연속조회 금지·숫자 검증 | 1, 6 |
| 종목 묶기·기타 구분·소수 수량·짝맞추기·이중 계산 없음·100종목 | 2 |
| 순자산(총자산−대출)·자동투자 별도 표시 | 1(요약), 4(화면) |
| 검산 두 관계·1% 경고 | 4 |
| `메리츠원본` 블록·성공 블록만 덮어쓰기·해외 실패 시 외화 열 비움 | 1, 2, 4, 6 |
| `자산` G·H열·되돌림·오래됨 | 3, 8 |
| `주식`·`메리츠` 탭 열·카드·차트·손익 색·체크박스 보호 제외 | 3, 4, 5 |
| 갱신 시점·설치형 onEditMeritz·잠금·예외 안 던짐·토큰 재사용/갱신당 1회 | 6 |
| 키 사용자 속성·소유자 메뉴·소유자 setupTriggers | 6, 9 |
| 운영 시트 샘플 금지·임시 시트 시험 | 8 |
| 마이그레이션 제자리·반복 안전 | 7, 9 |
| 사용법·README | 3, 9 |
| 키 발급 뒤 실제 연결 시험 | 범위 밖(스펙 "키 발급 뒤 순서", 사용자 작업) |
