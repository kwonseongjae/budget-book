// moveMonth 글루: 대시보드 C1 드롭다운 → B1 월 바꾸고 C1은 안내 문구로 되돌린다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet } = require('./fake_sheets');

function setup(b1, nowYm = 202610) {
  const ctx = vm.createContext({});
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  const dash = new FakeSheet([['조회 월', b1 === undefined ? '' : b1, '◀ 월 이동 ▶']]);
  const calc = new FakeSheet([['월목록', '연도목록', nowYm]]);
  [202610, 202609, 202608].forEach((m, i) => calc.set(2 + i, 1, m));
  calc.set(2, 3, nowYm);
  const sheets = { '대시보드': dash, '부부': new FakeSheet([['조회 월', '', '']]), '계산': calc };
  return { ctx, dash, run: (choice, sheet = '대시보드') => ctx.moveMonth({ getSheetByName: (n) => sheets[n] }, sheet, choice), sheets };
}

test('moveMonth: 이전 달 → B1에 숫자 월, C1은 안내 문구로 복귀', () => {
  const t = setup('');
  t.run('◀ 이전 달');
  assert.equal(t.dash.get(1, 2), 202609);
  assert.equal(t.dash.get(1, 3), '◀ 월 이동 ▶');
});

test('moveMonth: 다음 달로 이번 달에 닿으면 B1을 비운다(이번 달 따라가기)', () => {
  const t = setup(202609);
  t.run('다음 달 ▶');
  assert.equal(t.dash.get(1, 2), '');
});

test('moveMonth: 데이터가 없는 이전 달로는 가지 않고 B1을 그대로 둔다', () => {
  const t = setup(202608);
  t.run('◀ 이전 달');
  assert.equal(t.dash.get(1, 2), 202608);
  assert.equal(t.dash.get(1, 3), '◀ 월 이동 ▶');
});

test('moveMonth: 부부 탭도 같은 방식', () => {
  const t = setup('');
  t.run('◀ 이전 달', '부부');
  assert.equal(t.sheets['부부'].get(1, 2), 202609);
});
