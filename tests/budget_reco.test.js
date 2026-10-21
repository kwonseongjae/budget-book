// 예산 추천: 지난 3개월(이번 달 제외) 지출 평균 → 설정 K:M 빈 칸에만 채운다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet } = require('./fake_sheets');

function load() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  return ctx;
}

// 내역 줄 = A:M (사용자 B, 구분 C, 카테고리 D, 원화금액 K, 귀속월 L)
const txn = (user, type, cat, krw, ym) => [new Date(2026, 8, 1), user, type, cat, '', '', '', krw, 'KRW', '', krw, ym, ''];
const USERS = ['신랑', '신부', '공동'];
const settings = [  // 설정 A:M 줄 (K·L·M = 10·11·12)
  ['식비', '지출', '', '변동비', '', '', '', '', '', '', '', '', ''],
  ['용돈', '지출', '', '고정비', '', '', '', '', '', '', 300000, '', ''],
  ['월급1', '수입', '', '', '', '', '', '', '', '', '', '', ''],
];

test('recommendBudgets: 완료된 달 평균을 1만 원 단위로, 이번 달·수입은 제외하고 빈 칸에만', () => {
  const c = load();
  const rows = [
    txn('신랑', '지출', '식비', 400000, 202607), txn('신랑', '지출', '식비', 200000, 202608),
    txn('신랑', '지출', '식비', 300000, 202609), txn('신랑', '지출', '식비', 900000, 202610),  // 이번 달: 제외
    txn('신부', '지출', '식비', 25000, 202609), txn('신랑', '수입', '월급1', 3000000, 202609),
    txn('신랑', '지출', '용돈', 100000, 202609),
  ];
  const r = c.recommendBudgets(rows, settings, USERS, 202610);
  const key = (f) => f.row + ':' + f.col + '=' + f.value;
  // 식비 신랑: (400+200+300)/3 = 300,000 / 신부: 25,000/3 ≈ 8,333 → 최소 10,000 / 용돈 신랑는 이미 300,000이라 그대로
  assert.deepEqual(Array.from(r.fills, key).sort(), ['0:10=300000', '0:11=10000']);
  assert.equal(r.kept, 1);
});

test('recommendBudgets: 지난달 데이터가 없으면 아무것도 채우지 않는다', () => {
  const c = load();
  const r = c.recommendBudgets([txn('신랑', '지출', '식비', 50000, 202610)], settings, USERS, 202610);
  assert.deepEqual([r.fills.length, r.months], [0, 0]);
});

test('fillBudgets: 체크하면 설정 K:M 빈 칸만 채우고 결과를 알린다', () => {
  const c = load();
  c.todayDate = () => new Date(2026, 9, 21);
  const sheets = {
    '설정': new FakeSheet([['카테고리'], ['식비', '지출', '', '변동비', '신랑'], ['용돈', '지출', '', '고정비', '신부', '', '', '', '', '', 300000], ['월급1', '수입', '', '', '공동']]),
    '내역': new FakeSheet([['날짜'], ...[txn('신랑', '지출', '식비', 600000, 202609), txn('신랑', '지출', '용돈', 100000, 202609)]]),
    '계산': new FakeSheet([['월목록'], ['', '', 202610]]),
  };
  let cleared = null;
  c.fillBudgets({ getSheetByName: (n) => sheets[n] }, { setValue(v) { cleared = v; } });
  assert.equal(cleared, false);
  assert.equal(sheets['설정'].get(2, 11), 600000);   // 식비 신랑 K
  assert.equal(sheets['설정'].get(3, 11), 300000);   // 용돈은 이미 있던 값 유지
  assert.equal(sheets['설정'].get(3, 12), '');       // 용돈 신부는 지출 없음 → 빈칸
  assert.match(sheets['설정'].get(13, 9), /1칸 채움/);
});

test('routeEdit: 설정 J12를 체크하면 budget, 해제나 다른 칸은 무시', () => {
  const c = load();
  const ev = (o) => Object.assign({ sheet: '설정', row: 12, col: 10, numRows: 1, numCols: 1, value: 'TRUE' }, o);
  assert.equal(c.routeEdit(ev({})).type, 'budget');
  assert.equal(c.routeEdit(ev({ value: 'FALSE' })), null);
  assert.equal(c.routeEdit(ev({ row: 11 })), null);
});
