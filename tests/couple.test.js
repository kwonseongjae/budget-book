const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', 'logic.gs'), 'utf8'), ctx);
const plain = (x) => JSON.parse(JSON.stringify(x));

// 내역 A:L 한 행
const txn = (o) => ['', o.user || '신랑', o.type || '지출', o.cat || '', '', o.pay || '', '', 0, 'KRW',
  o.memo || '', o.krw || 0, o.ym || 202610];

test('suggestCategory: 같은 메모로 가장 많이 쓴 구분·카테고리, 동률이면 최근', () => {
  const h = [['지출', '식비', '이마트'], ['지출', '생활용품', '이마트'], ['지출', '식비', '이마트 '],
    ['지출', '구독비', '쿠팡'], ['지출', '쇼핑', '쿠팡']];
  assert.deepEqual(plain(ctx.suggestCategory(h, '이마트')), { type: '지출', category: '식비' });
  assert.deepEqual(plain(ctx.suggestCategory(h, '쿠팡')), { type: '지출', category: '쇼핑' }); // 동률 → 최근
});

test('suggestCategory: 완전 일치가 없으면 서로 포함(2글자 이상), 없으면 null', () => {
  const h = [['지출', '구독비', '쿠팡'], ['지출', '카페·간식', '스타벅스 강남점']];
  assert.deepEqual(plain(ctx.suggestCategory(h, '쿠팡(주)')), { type: '지출', category: '구독비' });
  assert.deepEqual(plain(ctx.suggestCategory(h, '스타벅스')), { type: '지출', category: '카페·간식' });
  assert.equal(ctx.suggestCategory(h, '편의점'), null);
  assert.equal(ctx.suggestCategory(h, ''), null);
  assert.equal(ctx.suggestCategory([['지출', '', '쿠팡']], '쿠팡'), null); // 카테고리 없는 과거 행은 무시
});

test('routeEdit: 내역 메모 입력 → 카테고리 추천, 지울 때는 무시', () => {
  const ev = (o) => Object.assign({ numRows: 1, numCols: 1 }, o);
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '내역', row: 7, col: 10, value: '쿠팡' }))),
    { type: 'memo', row: 7 });
  assert.equal(ctx.routeEdit(ev({ sheet: '내역', row: 7, col: 10 })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '내역', row: 1, col: 10, value: 'x' })), null);
});

test('spendByCategoryUser: 귀속월 나가는 돈을 카테고리×사용자로', () => {
  const out = ctx.spendByCategoryUser([
    txn({ cat: '주택청약', type: '저축', krw: 100000 }), txn({ user: '신부', cat: '주택청약', type: '저축', krw: 100000 }),
    txn({ cat: '식비', krw: 5000 }), txn({ cat: '식비', krw: 7000, ym: 202609 }),
    txn({ cat: '월급1', type: '수입', krw: 1 }), txn({ type: '이체', krw: 9 })], 202610);
  assert.deepEqual(plain(out), { '주택청약': { '신랑': 100000, '신부': 100000 }, '식비': { '신랑': 5000 } });
});

test('budgetRows: 지출 카테고리만, 사람별 예산 칸(K:M)과 그 사람 지출', () => {
  const settings = [['식비', '지출', 900000, '변동비', '신랑', '', '', '', '', '', 300000, '', 600000],
    ['주택청약', '저축', 200000, '고정비', '신부', '', '', '', '', '', 100000, 100000, ''],
    ['', '', '', '', '공동']];
  const rows = ctx.budgetRows(settings, ['신랑', '신부', '공동'], { '식비': { '신랑': 310000 } });
  assert.deepEqual(plain(rows), [{ category: '식비', user: '신랑', spent: 310000, budget: 300000 },
    { category: '식비', user: '공동', spent: 0, budget: 600000 }]);
});

test('newAlerts: 사람별 키, 같은 단계는 한 번만', () => {
  const rows = [{ category: '식비', user: '신랑', spent: 310000, budget: 300000 },
    { category: '식비', user: '신부', spent: 85, budget: 100 }];
  const first = plain(ctx.newAlerts(rows, {}, 202610));
  assert.deepEqual(first.map((a) => a.key), ['202610|식비|신랑|100', '202610|식비|신부|80']);
  assert.deepEqual(plain(ctx.newAlerts(rows, { '202610|식비|신랑|100': true, '202610|식비|신부|80': true }, 202610)), []);
  assert.equal(ctx.formatAlerts([first[0]]), '식비(신랑): 310,000 / 300,000원 (103%) — 예산 초과');
});

test('settlement: 공동 지출 반반 — 소유자별 낸 돈의 차이 ÷ 2, 공동 자산·미지정 분리', () => {
  const owners = { '현대카드': '신랑', '하나카드': '신부', '공동통장': '공동', '현금': '' };
  const rows = [txn({ user: '공동', pay: '현대카드', krw: 100000 }), txn({ user: '공동', pay: '하나카드', krw: 40000 }),
    txn({ user: '공동', pay: '공동통장', krw: 500000 }), txn({ user: '공동', pay: '현금', krw: 7000 }),
    txn({ user: '공동', pay: '없는카드', krw: 3000 }), txn({ user: '신랑', pay: '하나카드', krw: 999 }),
    txn({ user: '공동', pay: '현대카드', type: '수입', krw: 5 }), txn({ user: '공동', pay: '현대카드', krw: 8, ym: 202609 })];
  const s = plain(ctx.settlement(rows, 202610, owners, ['신랑', '신부'], '공동'));
  assert.deepEqual(s, { paid: { '신랑': 100000, '신부': 40000 }, unknown: 2, from: '신부', to: '신랑', amount: 30000 });
  const even = plain(ctx.settlement([], 202610, owners, ['신랑', '신부'], '공동'));
  assert.equal(even.amount, 0);
  assert.equal(even.from, '');
});

test('prevYm: 1월이면 전년 12월', () => {
  assert.equal(ctx.prevYm(202601), 202512);
  assert.equal(ctx.prevYm(202610), 202609);
});

test('netWorthRow: 카드는 부채, 나머지는 자산, 빈 이름·숫자 아님 제외', () => {
  const assets = [['현금', '현금', 0, '', 10000], ['IBK', '계좌', 0, '', 4000000], ['현대카드', '카드', 0, '', -220000],
    ['', '', '', '', ''], ['메리츠', '주식', 0, '', '미갱신']];
  assert.deepEqual(plain(ctx.netWorthRow(assets)), [3790000, 4010000, -220000]);
});

test('netWorthRow: 대출도 카드처럼 부채 칸으로', () => {
  const assets = [['IBK', '계좌', 0, '', 4000000], ['전세대출', '대출', -50000000, '', -49000000],
    ['현대카드', '카드', 0, '', -220000]];
  assert.deepEqual(plain(ctx.netWorthRow(assets)), [-45220000, 4000000, -49220000]);
});

test('ymRowIndex: 같은 월 행이 있으면 그 행, 없으면 다음 빈 행', () => {
  assert.equal(ctx.ymRowIndex([['월'], [202609], [202610]], 202610), 3);
  assert.equal(ctx.ymRowIndex([['월'], [202609], ['']], 202610), 3);
  assert.equal(ctx.ymRowIndex([['월']], 202610), 2);
});

test('monthReport: 사람별 수입·지출·저축, 지출 상위, 예산 초과, 정산, 순자산 증감', () => {
  const rows = [txn({ type: '수입', cat: '월급', krw: 3000000 }), txn({ cat: '식비', krw: 350000 }),
    txn({ user: '신부', type: '저축', cat: '주택청약', krw: 100000 }), txn({ user: '공동', cat: '외식', pay: '현대카드', krw: 60000 }),
    txn({ cat: '식비', krw: 1, ym: 202609 })];
  const r = ctx.monthReport({
    rows, ym: 202610, users: ['신랑', '신부', '공동'], people: ['신랑', '신부'], joint: '공동',
    owners: { '현대카드': '신랑' }, budgets: [{ category: '식비', user: '신랑', budget: 300000 }],
    net: [10000000, 10500000] });
  assert.equal(r.subject, '[가계부] 2026-10 결산');
  assert.match(r.body, /신랑: 수입 3,000,000 · 지출 350,000 · 저축·기타 0/);
  assert.match(r.body, /신부: 수입 0 · 지출 0 · 저축·기타 100,000/);
  assert.match(r.body, /1\. 식비 350,000/);
  assert.match(r.body, /식비\(신랑\) 350,000 \/ 300,000/);
  assert.match(r.body, /신부 → 신랑 30,000원/);
  assert.match(r.body, /순자산 10,500,000원 \(전월 대비 \+500,000\)/);
});

test('monthReport: 그 달 내역이 없으면 null (보낼 것 없음)', () => {
  assert.equal(ctx.monthReport({ rows: [], ym: 202609, users: [], people: ['a', 'b'], joint: '공동',
    owners: {}, budgets: [], net: [null, null] }), null);
});

test('safeText: 수식으로 해석될 문자열 앞에 작은따옴표', () => {
  assert.equal(ctx.safeText('=IMPORTXML("x")'), "'=IMPORTXML(\"x\")");
  assert.equal(ctx.safeText('+82'), "'+82");
  assert.equal(ctx.safeText('@a'), "'@a");
  assert.equal(ctx.safeText('스타벅스'), '스타벅스');
  assert.equal(ctx.safeText(''), '');
});
