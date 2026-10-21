const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({ encodeURIComponent });
for (const f of ['meritz_logic.gs', 'kis_logic.gs']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
}
const plain = (x) => JSON.parse(JSON.stringify(x));

test('splitAccount: 8-2 형식만, 하이픈·공백 허용', () => {
  assert.deepEqual(plain(ctx.splitAccount('12345678-01')), { cano: '12345678', prdt: '01' });
  assert.deepEqual(plain(ctx.splitAccount('1234567801')), { cano: '12345678', prdt: '01' });
  assert.deepEqual(plain(ctx.splitAccount(' 12345678 - 01 ')), { cano: '12345678', prdt: '01' });
  assert.equal(ctx.splitAccount('123456789'), null);
  assert.equal(ctx.splitAccount(''), null);
  assert.equal(ctx.splitAccount(null), null);
});

test('buildKisToken: JSON 본문 client_credentials', () => {
  const r = ctx.buildKisToken('K', 'S');
  assert.equal(r.url, 'https://openapi.koreainvestment.com:9443/oauth2/tokenP');
  assert.equal(r.options.method, 'post');
  assert.equal(r.options.muteHttpExceptions, true);
  assert.deepEqual(JSON.parse(r.options.payload), { grant_type: 'client_credentials', appkey: 'K', appsecret: 'S' });
});

test('parseKisToken: 만료 시각 = 지금 + expires_in, 실패는 코드·설명', () => {
  assert.deepEqual(plain(ctx.parseKisToken('{"access_token":"T","expires_in":86400}', 1000)),
    { token: 'T', expiresAt: 1000 + 86400000 });
  assert.match(ctx.parseKisToken('{"error_code":"EGW00133","error_description":"1분당 1회"}', 0).error, /EGW00133 1분당 1회/);
  assert.equal(ctx.parseKisToken('<html>', 0).error, '토큰 응답이 JSON이 아님');
});

test('buildKisBalance: 잔고 조회 경로·tr_id·필수 파라미터, 주문 경로 없음', () => {
  const r = ctx.buildKisBalance('T', 'K', 'S', { cano: '12345678', prdt: '01' });
  assert.ok(r.url.startsWith('https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance?'));
  for (const kv of ['CANO=12345678', 'ACNT_PRDT_CD=01', 'AFHR_FLPR_YN=N', 'OFL_YN=', 'INQR_DVSN=02', 'UNPR_DVSN=01',
    'FUND_STTL_ICLD_YN=N', 'FNCG_AMT_AUTO_RDPT_YN=N', 'PRCS_DVSN=00', 'CTX_AREA_FK100=', 'CTX_AREA_NK100=']) {
    assert.ok(r.url.includes(kv), kv);
  }
  assert.ok(!/order/i.test(r.url));
  assert.deepEqual(plain(r.options.headers), { authorization: 'Bearer T', appkey: 'K', appsecret: 'S',
    tr_id: 'TTTC8434R', custtype: 'P' });
  assert.equal(r.options.method, 'get');
});

test('parseKisBalance: 정상 → 평가 = 순자산, 원금 = 매입금액 합계 + 예수금 (쉼표 문자열 허용)', () => {
  const ok = JSON.stringify({ rt_cd: '0', msg_cd: 'KIOK0510', msg1: '조회가 완료되었습니다',
    output1: [], output2: [{ nass_amt: '5,300,000', pchs_amt_smtl_amt: '4,800,000', dnca_tot_amt: '200000' }] });
  assert.deepEqual(plain(ctx.parseKisBalance(ok)), { kind: 'ok', code: 'KIOK0510', msg: '', value: 5300000, principal: 5000000, holdings: [] });
});

test('parseKisBalance: 실패 종류 — 호출 제한, 토큰 만료, 그 밖의 오류, 빈 output2, 숫자 아님, JSON 아님', () => {
  const err = (cd, m) => JSON.stringify({ rt_cd: '1', msg_cd: cd, msg1: m });
  assert.equal(ctx.parseKisBalance(err('EGW00201', '초당 거래건수 초과')).kind, 'throttled');
  assert.equal(ctx.parseKisBalance(err('EGW00123', '기간이 만료된 token')).kind, 'expired');
  assert.deepEqual(plain(ctx.parseKisBalance(err('OPSQ0002', '없는 계좌 '))), { kind: 'error', code: 'OPSQ0002', msg: '없는 계좌' });
  assert.equal(ctx.parseKisBalance(JSON.stringify({ rt_cd: '0', output2: [] })).msg, 'output2 없음');
  assert.equal(ctx.parseKisBalance(JSON.stringify({ rt_cd: '0', output2: [{ nass_amt: 'x', pchs_amt_smtl_amt: 1, dnca_tot_amt: 1 }] })).kind, 'error');
  assert.equal(ctx.parseKisBalance('<html>').msg, '응답이 JSON이 아님');
});

test('EGW00121(유효하지 않은 토큰)도 재발급 대상', () => {
  const body = JSON.stringify({ rt_cd: '1', msg_cd: 'EGW00121', msg1: '유효하지 않은 token' });
  assert.equal(ctx.parseKisBalance(body).kind, 'expired');
});

test('원금 예수금은 D+2(prvs_rcdl_excc_amt) 우선, 없으면 D+0', () => {
  const ok = (o) => JSON.stringify({ rt_cd: '0', msg_cd: 'KIOK0000', output1: [], output2: [o] });
  const base = { nass_amt: '5,300,000', pchs_amt_smtl_amt: '4,800,000', dnca_tot_amt: '700000' };
  assert.equal(ctx.parseKisBalance(ok({ ...base, prvs_rcdl_excc_amt: '200000' })).principal, 5000000);
  assert.equal(ctx.parseKisBalance(ok(base)).principal, 5500000);
});

test('오류 문구에서 URL 쿼리·긴 숫자(계좌번호) 제거', () => {
  const msg = 'Address unavailable: https://openapi.koreainvestment.com:9443/uapi/x?CANO=12345678&ACNT_PRDT_CD=01';
  const out = ctx.safeErrorText(msg);
  assert.ok(!out.includes('12345678') && !out.includes('CANO'), out);
  assert.equal(ctx.safeErrorText('계좌 1234567801 오류'), '계좌 *** 오류');
});

test('parseKisBalance: 종목 목록 — 보유수량 0 넘는 것만 [ISA, 코드, 이름, 매입, 평가]', () => {
  const ok = JSON.stringify({ rt_cd: '0', msg_cd: 'KIOK0510', output2: [{ nass_amt: '1', pchs_amt_smtl_amt: '0', dnca_tot_amt: '0' }],
    output1: [{ pdno: '360750', prdt_name: 'TIGER 미국S&P500', hldg_qty: '10', pchs_amt: '1,000,000', evlu_amt: '1,100,000' },
              { pdno: '005930', prdt_name: '삼성전자', hldg_qty: '0', pchs_amt: '0', evlu_amt: '0' }] });
  assert.deepEqual(plain(ctx.parseKisBalance(ok).holdings), [['ISA', '360750', 'TIGER 미국S&P500', 1000000, 1100000]]);
});
