const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
for (const f of ['logic.gs', 'meritz_logic.gs', 'invest_logic.gs']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
}
const plain = (x) => JSON.parse(JSON.stringify(x));

test('investLogRow: 계좌 4개 평가·원금, 합계, 빠진 계좌 수', () => {
  const d = new Date(2026, 9, 12);
  const row = ctx.investLogRow(d, [[1000, 900], ['', ''], [500, ''], ['키없음', 3]]);
  assert.equal(row.length, 12);
  assert.equal(row[0], d);
  assert.deepEqual(plain(row.slice(1)), [1000, 900, '', '', 500, '', '', 3, 1500, 900, 2]);
});

test('investLogRow: 평가가 없으면 그 계좌 원금도 합계에서 뺀다', () => {
  const row = ctx.investLogRow(new Date(2026, 9, 12), [['', 700], [10, 5], ['', ''], ['', '']]);
  assert.deepEqual(plain(row.slice(9)), [10, 5, 3]);
});

test('dateRowIndex: 같은 날짜(시각 무시)면 그 행에 덮어쓰고, 없으면 다음 빈 행', () => {
  const col = [['날짜'], [new Date(2026, 9, 10)], [new Date(2026, 9, 11, 6, 3)], ['']];
  assert.equal(ctx.dateRowIndex(col, new Date(2026, 9, 11)), 3);
  assert.equal(ctx.dateRowIndex(col, new Date(2026, 9, 12)), 4);
  assert.equal(ctx.dateRowIndex([['날짜']], new Date(2026, 9, 12)), 2);
});

test('yesterday: 월 첫날이면 전달 말일', () => {
  const y = ctx.yesterday(new Date(2026, 10, 1));
  assert.deepEqual([y.getFullYear(), y.getMonth(), y.getDate()], [2026, 9, 31]);
});

test('shouldRecordInvest: 계좌 4개가 모두 빈 날은 기록하지 않는다 (키 넣기 전 0원 줄이 그래프를 망침)', () => {
  const d = new Date(2026, 9, 12);
  assert.equal(ctx.shouldRecordInvest(ctx.investLogRow(d, [['', ''], ['', ''], ['', ''], ['', '']])), false);
  assert.equal(ctx.shouldRecordInvest(ctx.investLogRow(d, [[1, 1], ['', ''], ['', ''], ['', '']])), true);
});
