// 증권계좌 A열에 이름을 적으면 '계좌_이름' 탭이 자동으로 만들어지고, 바꾸면 따라 바뀌고, 지우면 숨긴다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet, FakeSpreadsheet } = require('./fake_sheets');

function setup() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs', 'positions_logic.gs', 'positions.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  const pos = new FakeSheet([[], [], [], [], []]);
  const ss = new FakeSpreadsheet({ '증권종목': pos, '증권계좌': new FakeSheet([[]]) });
  return { ctx, ss, pos, tab: (n) => ss.getSheetByName('계좌_' + n) };
}

test('새 이름 → 계좌 탭 생성(이름 칸·요약·종목 표 수식), 같은 이름을 또 적으면 다시 만들지 않음', () => {
  const t = setup();
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움'), 'created');
  const sh = t.tab('신랑 키움');
  assert.ok(sh);
  assert.equal(sh.get(1, 2), '신랑 키움');
  assert.match(sh.get(3, 2), /^=SUMIFS\(증권종목!\$M\$6:\$M\$1005,증권종목!\$H\$6:\$H\$1005,\$B\$1\)$/);
  assert.match(sh.get(12, 1), /^=IFERROR\(FILTER\(증권종목!\$I\$6:\$N\$1005/);
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움'), 'shown');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 1);
});

test('이름 바꾸기 → 탭 이름·B1·증권종목의 계좌명이 함께 바뀐다', () => {
  const t = setup();
  t.ctx.syncAccountTab(t.ss, '', '신랑 키움');
  t.pos.getRange('H6:N7').setValues([['신랑 키움', '1', 'A', 1, 2, 3, 'KRW'], ['신부 삼성', '2', 'B', 1, 2, 3, 'KRW']]);
  assert.equal(t.ctx.syncAccountTab(t.ss, '신랑 키움', '신랑 키움증권'), 'renamed');
  assert.ok(!t.tab('신랑 키움') && t.tab('신랑 키움증권'));
  assert.equal(t.tab('신랑 키움증권').get(1, 2), '신랑 키움증권');
  assert.deepEqual([t.pos.get(6, 8), t.pos.get(7, 8)], ['신랑 키움증권', '신부 삼성']);
});

test('이름 지우기 → 탭은 삭제하지 않고 숨긴다, 다시 적으면 보인다', () => {
  const t = setup();
  t.ctx.syncAccountTab(t.ss, '', '신랑 키움');
  assert.equal(t.ctx.syncAccountTab(t.ss, '신랑 키움', ''), 'hidden');
  assert.equal(t.tab('신랑 키움').isSheetHidden(), true);
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움'), 'shown');
  assert.equal(t.tab('신랑 키움').isSheetHidden(), false);
});

test('금지 문자·너무 긴 이름은 탭을 만들지 않는다', () => {
  const t = setup();
  assert.equal(t.ctx.syncAccountTab(t.ss, '', 'a/b'), 'invalid');
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '가'.repeat(91)), 'invalid');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 0);
});

test('바꾸려는 이름의 탭이 이미 있으면 건드리지 않고 exists', () => {
  const t = setup();
  t.ctx.syncAccountTab(t.ss, '', 'A');
  t.ctx.syncAccountTab(t.ss, '', 'B');
  assert.equal(t.ctx.syncAccountTab(t.ss, 'A', 'B'), 'exists');
  assert.ok(t.tab('A') && t.tab('B'));
});

test('이전 탭이 없는 이름 바꾸기(사용자가 탭을 지운 경우)는 새 탭을 만든다', () => {
  const t = setup();
  assert.equal(t.ctx.syncAccountTab(t.ss, 'X', 'Y'), 'created');
  assert.ok(t.tab('Y'));
});

test('routeEdit: 증권종목 B3 체크는 positions, 증권계좌 A5:A14 편집은 brokerTab(이전·새 이름)', () => {
  const c = setup().ctx;
  const ev = (o) => Object.assign({ sheet: '증권종목', row: 3, col: 2, numRows: 1, numCols: 1, value: 'TRUE' }, o);
  const plain = (x) => JSON.parse(JSON.stringify(x));
  assert.deepEqual(plain(c.routeEdit(ev({}))), { type: 'positions' });
  assert.equal(c.routeEdit(ev({ value: 'FALSE' })), null);
  const acct = (o) => Object.assign({ sheet: '증권계좌', row: 5, col: 1, numRows: 1, numCols: 1, value: '신랑 키움', oldValue: undefined }, o);
  assert.deepEqual(plain(c.routeEdit(acct({}))), { type: 'brokerTab', from: '', to: '신랑 키움' });
  assert.deepEqual(plain(c.routeEdit(acct({ value: undefined, oldValue: '신랑 키움' }))), { type: 'brokerTab', from: '신랑 키움', to: '' });
  assert.equal(c.routeEdit(acct({ row: 15 })), null);       // 목록 밖
  assert.equal(c.routeEdit(acct({ col: 2 })), null);        // 이름 칸이 아님
  assert.equal(c.routeEdit(acct({ value: 'a', oldValue: 'a' })), null);
});
