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

test('extraAccounts: 총평가가 숫자인 계좌만, 원금이 숫자가 아니면 빈칸', () => {
  const rows = [['신랑 키움', '', '', '', '', '', '', '', 1000, 1100], ['신부 삼성', '', '', '', '', '', '', '', '', 500],
    ['붙여넣기 전', '', '', '', '', '', '', '', '', ''], ['', '', '', '', '', '', '', '', 1, 2]];
  assert.deepEqual(plain(ctx.extraAccounts(rows)), [{ name: '신랑 키움', value: 1100, principal: 1000 }, { name: '신부 삼성', value: 500, principal: '' }]);
});

test('withExtras: 기타 계좌가 없으면 기존 12열 값은 그대로이고 M·N만 빈칸 (회귀 없음)', () => {
  const base = ctx.investLogRow(new Date(2026, 9, 12), [[1000, 900], ['', ''], [500, ''], ['키없음', 3]]);
  const out = ctx.withExtras(base, []);
  assert.equal(out.length, 14);
  assert.deepEqual(plain(out.slice(0, 12)), plain(base));
  assert.deepEqual(plain(out.slice(12)), ['', '']);
});

test('withExtras: 기타 평가·원금을 합계(J·K)에 더하고 M·N에 따로 남긴다, 원금이 하나도 없으면 N은 빈칸', () => {
  const base = ctx.investLogRow(new Date(2026, 9, 12), [[1000, 900], ['', ''], ['', ''], ['', '']]);
  const out = plain(ctx.withExtras(base, [{ name: 'a', value: 100, principal: 80 }, { name: 'b', value: 50, principal: '' }]));
  assert.deepEqual(out.slice(9), [1150, 980, 3, 150, 80]);
  const noP = plain(ctx.withExtras(base, [{ name: 'b', value: 50, principal: '' }]));
  assert.deepEqual(noP.slice(9), [1050, 900, 3, 50, '']);
});

test('shouldRecordInvest: 4계좌가 모두 비어도 기타 계좌가 있으면 기록한다, 둘 다 없으면 기록하지 않는다', () => {
  const d = new Date(2026, 9, 12);
  const empty = ctx.investLogRow(d, [['', ''], ['', ''], ['', ''], ['', '']]);
  assert.equal(ctx.shouldRecordInvest(ctx.withExtras(empty, [])), false);
  assert.equal(ctx.shouldRecordInvest(ctx.withExtras(empty, [{ name: 'a', value: 5, principal: '' }])), true);
  assert.equal(ctx.shouldRecordInvest(ctx.withExtras(ctx.investLogRow(d, [[1, 1], ['', ''], ['', ''], ['', '']]), [])), true);
});

test('upsertAccountLog: 같은 날짜+계좌는 교체, 다른 날짜·계좌는 유지, 날짜가 아닌 줄은 버림', () => {
  const d1 = new Date(2026, 9, 11), d2 = new Date(2026, 9, 12, 6, 3);
  const existing = [[d1, 'a', 1, 1], [new Date(2026, 9, 12), 'a', 2, 2], [new Date(2026, 9, 12), 'b', 3, 3], ['', '', '', '']];
  const out = ctx.upsertAccountLog(existing, ctx.accountLogRows(d2, [{ name: 'a', value: 9, principal: 8 }]));
  assert.deepEqual(plain(out).map((r) => [r[1], r[2]]), [['a', 1], ['b', 3], ['a', 9]]);
});
