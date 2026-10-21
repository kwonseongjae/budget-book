// 폰 빠른 입력 탭(빠른입력): 폼 값 → 내역 한 줄. 순수 로직(quickTxn)과 체크박스 흐름(addQuick)을 가짜 시트로.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet } = require('./fake_sheets');

const plain = (x) => JSON.parse(JSON.stringify(x));
const FX = [['KRW', 1], ['USD', 1340]];
const TODAY = new Date(2026, 9, 16);

function load() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => TODAY;
  ctx.refreshCategoryRules = () => {};
  return ctx;
}
const ctx = load();
const form = (o) => Object.assign({ date: '', user: '신랑', type: '', category: '식비', amount: 8000, currency: '', pay: '삼성카드', inAsset: '', memo: '점심' }, o);

test('quickTxn: 빈 날짜=오늘, 빈 구분=지출, 빈 통화=원화 → 내역 A:J 줄', () => {
  const q = ctx.quickTxn(form({}), TODAY, FX);
  assert.deepEqual(plain(q.txn), [plain(TODAY), '신랑', '지출', '식비', '', '삼성카드', '', 8000, 'KRW', '점심']);
  assert.equal(q.rate, '');
  assert.equal(q.summary, '10/16 식비 8,000원 (신랑)');
});

test('quickTxn: 외화는 그 통화 금액과 입력 시점 환율, 환율을 모르면 오류', () => {
  const q = ctx.quickTxn(form({ amount: 22, currency: 'usd', category: '구독비' }), TODAY, FX);
  assert.deepEqual([q.txn[7], q.txn[8], q.rate], [22, 'USD', 1340]);
  assert.match(q.summary, /22 USD/);
  assert.match(ctx.quickTxn(form({ currency: 'GBP' }), TODAY, FX).error, /GBP 환율/);
});

test('quickTxn: 사용자·금액·카테고리·이체 필수값과 날짜 형식을 검사', () => {
  assert.match(ctx.quickTxn(form({ user: '' }), TODAY, FX).error, /사용자/);
  for (const amount of ['', 0, 'abc']) assert.match(ctx.quickTxn(form({ amount }), TODAY, FX).error, /금액/);
  assert.match(ctx.quickTxn(form({ category: '' }), TODAY, FX).error, /카테고리/);
  assert.match(ctx.quickTxn(form({ type: '이체', category: '', inAsset: '' }), TODAY, FX).error, /이체/);
  assert.equal(ctx.quickTxn(form({ type: '이체', category: '', inAsset: '현금', pay: 'IBK기업은행' }), TODAY, FX).txn[6], '현금');
  assert.match(ctx.quickTxn(form({ date: '어제' }), TODAY, FX).error, /날짜/);
  const d = new Date(2026, 9, 1);
  assert.equal(plain(ctx.quickTxn(form({ date: d }), TODAY, FX).txn[0]), plain(d));
  assert.equal(ctx.quickTxn(form({ amount: -5000 }), TODAY, FX).txn[7], -5000);  // 환불
});

test('routeEdit: 빠른입력 B13 체크박스를 켰을 때만', () => {
  const ev = (o) => Object.assign({ numRows: 1, numCols: 1, sheet: '빠른입력', row: 13, col: 2, value: 'TRUE' }, o);
  assert.deepEqual(plain(ctx.routeEdit(ev({}))), { type: 'quick' });
  assert.equal(ctx.routeEdit(ev({ value: 'FALSE' })), null);
  assert.equal(ctx.routeEdit(ev({ row: 8 })), null);
});

function setup(values) {
  const ctx2 = load();
  const quick = new FakeSheet([[], [], [], [], [], [], [], [], [], [], [], [], [], []]);
  Object.entries(values).forEach(([row, v]) => quick.set(Number(row), 2, v));
  const sheets = {
    '빠른입력': quick, '내역': new FakeSheet([['날짜']]),
    '설정': new FakeSheet([['카테고리'], ['x', '', '', '', '신랑'], ['x', '', '', '', '신부']]),
  };
  sheets['설정'].set(2, 7, 'KRW'); sheets['설정'].set(2, 8, 1); sheets['설정'].set(3, 7, 'USD'); sheets['설정'].set(3, 8, 1340);
  const ss = { getSheetByName: (n) => sheets[n] };
  const box = { value: true, setValue(v) { this.value = v; } };
  return { ctx: ctx2, sheets, ss, box, run: () => ctx2.addQuick(ss, box), ledger: () => sheets['내역'].rows.slice(1).map((r) => r.slice(0, 14)) };
}

test('addQuick: 내역에 한 줄 추가하고 입력칸은 비우되 사용자·구분·결제수단은 남긴다', () => {
  const t = setup({ 5: '신랑', 6: '지출', 7: '식비', 8: 8000, 10: '삼성카드', 12: '점심' });
  t.run();
  assert.equal(t.ledger().length, 1);
  assert.deepEqual([t.ledger()[0][1], t.ledger()[0][3], t.ledger()[0][7], t.ledger()[0][9]], ['신랑', '식비', 8000, '점심']);
  const q = t.sheets['빠른입력'];
  assert.deepEqual([q.get(7, 2), q.get(8, 2), q.get(12, 2)], ['', '', '']);            // 카테고리·금액·메모 비움
  assert.deepEqual([q.get(5, 2), q.get(6, 2), q.get(10, 2)], ['신랑', '지출', '삼성카드']);  // 다음 입력에 그대로
  assert.equal(t.box.value, false);
  assert.match(q.get(14, 2), /^✓ .*식비 8,000원/);
});

test('addQuick: 오류면 내역에 넣지 않고 입력값을 그대로 둔 채 이유를 알린다', () => {
  const t = setup({ 5: '신랑', 7: '식비', 8: '', 10: '삼성카드' });
  t.run();
  assert.equal(t.ledger().length, 0);
  assert.match(t.sheets['빠른입력'].get(14, 2), /^✗ .*금액/);
  assert.equal(t.sheets['빠른입력'].get(7, 2), '식비');
  assert.equal(t.box.value, false);
});

test('addQuick: 카테고리를 비우고 메모만 적으면 예전 내역의 같은 메모 카테고리를 추천', () => {
  const t = setup({ 5: '신랑', 8: 4500, 12: '스타벅스' });
  t.sheets['내역'].set(2, 1, new Date(2026, 9, 1)); t.sheets['내역'].set(2, 3, '지출'); t.sheets['내역'].set(2, 4, '카페·간식'); t.sheets['내역'].set(2, 10, '스타벅스');
  t.run();
  assert.equal(t.ledger().length, 2);
  assert.equal(t.ledger()[1][3], '카페·간식');
});

test('addQuick: USD는 환율(N)이 함께 고정된다', () => {
  const t = setup({ 5: '신랑', 7: '구독비', 8: 22, 9: 'USD', 10: '삼성카드', 12: '클로드' });
  t.run();
  assert.deepEqual([t.ledger()[0][7], t.ledger()[0][8], t.ledger()[0][13]], [22, 'USD', 1340]);
});
