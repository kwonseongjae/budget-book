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

test('tokenFresh: 유효기간 12시간 토큰 — 남은 시간이 1시간 이상이면 재사용', () => {
  const now = 1_000_000_000_000;
  assert.equal(ctx.tokenFresh(now + 12 * 3600e3, now), true);   // 막 받은 12시간짜리 토큰
  assert.equal(ctx.tokenFresh(now + 2 * 3600e3, now), true);
  assert.equal(ctx.tokenFresh(now + 30 * 60e3, now), false);
  assert.equal(ctx.tokenFresh(0, now), false);
});

test('parseResponse: rsp_cd에 널바이트가 섞여 와도 코드로 판정 (JSON 이스케이프 형태와 날것 모두)', () => {
  const escaped = ctx.parseResponse('{"rsp_cd":"57\\u000066","rsp_msg":"","data":{"a":1}}', false);
  assert.equal(escaped.kind, 'ok');
  assert.equal(escaped.code, '5766');
  const raw = ctx.parseResponse('{"rsp_cd":"57' + String.fromCharCode(0) + '66","rsp_msg":"","data":{"a":1}}', false);
  assert.equal(raw.kind, 'ok');
  assert.equal(raw.code, '5766');
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
