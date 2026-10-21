// 카드 대금 자동 이체 (2026-10-19): [카드] 결제일·결제 계좌를 적으면 결제일에 카드 잔액(빚)만큼 결제 계좌 → 카드 '이체'를 넣는다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet } = require('./fake_sheets');

function load() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.refreshCategoryRules = () => {};
  return ctx;
}
const ctx = load();
const plain = (x) => JSON.parse(JSON.stringify(x));
const D = (m, d) => new Date(2026, m - 1, d);
const PEOPLE = ['신랑', '신부'];
const SAMSUNG = { name: '삼성카드', owner: '신랑', day: 15, account: '기업은행' };

test('cardPayments: 결제일이 되고 잔액이 음수면 결제 계좌 → 카드 이체 (결제일 날짜, 빚 전액)', () => {
  const t = ctx.cardPayments([SAMSUNG], { 삼성카드: -415912 }, [], PEOPLE, D(10, 19));
  assert.deepEqual(plain(t), [[plain(D(10, 15)), '신랑', '이체', '', '', '기업은행', '삼성카드', 415912, 'KRW', '카드 대금 자동 · 삼성카드']]);
});

test('cardPayments: 결제일 전, 빚이 없음, 값이 모자라면 만들지 않는다', () => {
  assert.equal(ctx.cardPayments([SAMSUNG], { 삼성카드: -1000 }, [], PEOPLE, D(10, 14)).length, 0);   // 14일 < 15일
  for (const bal of [0, 5000, 'x', undefined]) assert.equal(ctx.cardPayments([SAMSUNG], { 삼성카드: bal }, [], PEOPLE, D(10, 19)).length, 0);
  for (const c of [{ ...SAMSUNG, day: '' }, { ...SAMSUNG, account: '' }, { ...SAMSUNG, day: 0 }])
    assert.equal(ctx.cardPayments([c], { 삼성카드: -1000 }, [], PEOPLE, D(10, 19)).length, 0);
});

test('cardPayments: 이번 달에 그 카드로 들어가는 이체가 이미 있으면(손으로 넣었어도) 건너뛴다', () => {
  const mine = [D(10, 16), '신랑', '이체', '', '', '기업은행', '삼성카드', 300000, 'KRW', '카드값'];
  assert.equal(ctx.cardPayments([SAMSUNG], { 삼성카드: -415912 }, [mine], PEOPLE, D(10, 19)).length, 0);
  const lastMonth = [D(9, 16), ...mine.slice(1)];
  assert.equal(ctx.cardPayments([SAMSUNG], { 삼성카드: -415912 }, [lastMonth], PEOPLE, D(10, 19)).length, 1);
  const spend = [D(10, 16), '신랑', '지출', '식비', '', '삼성카드', '', 8000, 'KRW', '점심'];   // 카드 사용(지출)은 대금 이체가 아님
  assert.equal(ctx.cardPayments([SAMSUNG], { 삼성카드: -415912 }, [spend], PEOPLE, D(10, 19)).length, 1);
});

test('cardPayments: 31일 결제일은 짧은 달 말일에, 소유자가 사람이 아니면 공동', () => {
  const c = { name: '우리카드', owner: '', day: 31, account: '우리은행' };
  const t = ctx.cardPayments([c], { 우리카드: -5000.4 }, [], PEOPLE, new Date(2027, 1, 28));
  assert.deepEqual([plain(t[0][0]), t[0][1], t[0][7]], [plain(new Date(2027, 1, 28)), '공동', 5000]);
});

function setup(cardRows, balances, ledger) {
  const cards = new FakeSheet([[], [], [], ['카드', '소유자', '카드사', '혜택', '연회비', '용도', '한도', '유효기간', '결제일', '결제 계좌']]);
  cardRows.forEach((r, i) => r.forEach((v, j) => cards.set(5 + i, 1 + j, v)));
  cards.set(5 + cardRows.length + 2, 1, '포인트·마일리지');   // 사용자가 줄인 레이아웃: 카드 표 아래 빈 줄 두 개 뒤 포인트 표
  cards.set(5 + cardRows.length + 3, 1, '구분');
  const assets = new FakeSheet([['자산명']]);
  Object.entries(balances).forEach(([n, b], i) => { assets.set(2 + i, 1, n); assets.set(2 + i, 5, b); });
  const txns = new FakeSheet([['날짜']]);
  ledger.forEach((r, i) => r.forEach((v, j) => txns.set(2 + i, 1 + j, v)));
  const sheets = { '카드': cards, '자산': assets, '내역': txns, '설정': new FakeSheet([['카테고리'], ['x', '', '', '', '신랑'], ['x', '', '', '', '신부']]) };
  const c2 = load();
  c2.todayDate = () => D(10, 19);
  return { c2, sheets, run: () => c2.payCards({ getSheetByName: (n) => sheets[n] }), ledger: () => txns.rows.slice(1) };
}

test('payCards: [카드] 탭을 읽어(헤더 아래~포인트 표 전) 대금 이체를 넣고, 다시 돌려도 한 번만', () => {
  const t = setup([['삼성카드', '신랑', '삼성', '', '', '', '', '', 15, '기업은행'], ['우리카드', '신랑', '우리', '', '', '', '', '', '', '우리은행'],
                   ['하나카드_신부', '신부', '하나', '', '', '', '', '', 25, '신한은행']],
                  { 삼성카드: -415912, 우리카드: -2000, 하나카드_신부: -95280 }, []);
  t.run();
  const rows = t.ledger();
  assert.equal(rows.length, 1);                                  // 우리카드는 결제일 없음, 하나는 25일 전
  assert.deepEqual([rows[0][1], rows[0][2], rows[0][5], rows[0][6], rows[0][7]], ['신랑', '이체', '기업은행', '삼성카드', 415912]);
  t.run();
  assert.equal(t.ledger().length, 1);
});

test('payCards: 카드가 없거나 표를 못 찾아도 오류 없이 지나간다', () => {
  const t = setup([], {}, []);
  t.run();
  assert.equal(t.ledger().length, 0);
});
