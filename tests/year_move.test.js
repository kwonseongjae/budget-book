// 추이 C1 연도 이동 드롭다운 (월 이동과 같은 방식).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet } = require('./fake_sheets');

function setup(b1, nowYm = 202610) {
  const ctx = vm.createContext({});
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  const trend = new FakeSheet([['연도', b1 === undefined ? '' : b1, '◀ 연도 이동 ▶']]);
  const calc = new FakeSheet([['월목록', '연도목록', nowYm]]);
  [2026, 2025, 2024].forEach((y, i) => calc.set(2 + i, 2, y));
  calc.set(2, 3, nowYm);
  const sheets = { '추이': trend, '계산': calc };
  return { ctx, trend, run: (choice) => ctx.moveYear({ getSheetByName: (n) => sheets[n] }, choice) };
}

test('yearMove: 이전 해 → 숫자 연도, 올해에 닿으면 비움, 데이터 밖은 그대로', () => {
  const c = setup().ctx;
  assert.equal(c.yearMove('', '◀ 이전 해', 2026, 2024), 2025);
  assert.equal(c.yearMove(2025, '다음 해 ▶', 2026, 2024), '');
  assert.equal(c.yearMove(2024, '◀ 이전 해', 2026, 2024), null);
  assert.equal(c.yearMove('', '다음 해 ▶', 2026, 2024), null);
  assert.equal(c.yearMove(2024, '올해', 2026, 2024), '');
  assert.equal(c.yearMove('2025', '다음 해 ▶', 2026, 2024), '');   // 글자 연도도 읽는다
});

test('moveYear: 추이 B1을 바꾸고 C1은 안내 문구로 복귀', () => {
  const t = setup('');
  t.run('◀ 이전 해');
  assert.equal(t.trend.get(1, 2), 2025);
  assert.equal(t.trend.get(1, 3), '◀ 연도 이동 ▶');
});

test('moveYear: 가장 오래된 해 이전으로는 가지 않는다', () => {
  const t = setup(2024);
  t.run('◀ 이전 해');
  assert.equal(t.trend.get(1, 2), 2024);
  assert.equal(t.trend.get(1, 3), '◀ 연도 이동 ▶');
});

test('routeEdit: 추이 C1 선택은 year, 다른 값·다른 칸은 무시', () => {
  const c = setup().ctx;
  const ev = (o) => Object.assign({ sheet: '추이', row: 1, col: 3, numRows: 1, numCols: 1, value: '◀ 이전 해' }, o);
  assert.deepEqual(JSON.parse(JSON.stringify(c.routeEdit(ev({})))), { type: 'year', choice: '◀ 이전 해' });
  assert.equal(c.routeEdit(ev({ value: '◀ 연도 이동 ▶' })), null);
  assert.equal(c.routeEdit(ev({ col: 2 })), null);
});
