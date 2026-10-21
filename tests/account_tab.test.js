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
  const tbl = new FakeSheet([[]]);
  const acct = new FakeSheet([[], [], [], [], []]);
  const ss = new FakeSpreadsheet({ '증권종목': pos, '증권종목표': tbl, '증권계좌': acct });
  const names = (...n) => n.forEach((x, i) => acct.set(5 + i, 1, x));   // 증권계좌 A5부터 이름 (편집이 끝난 뒤의 목록)
  return { ctx, ss, pos, tbl, acct, names, tab: (n) => ss.getSheetByName('계좌_' + n) };
}

test('새 이름 → 계좌 탭 생성(이름 칸·요약·종목 표 수식), 같은 이름을 또 적으면 다시 만들지 않음', () => {
  const t = setup();
  t.names('신랑 키움');
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움', 5), 'created');
  const sh = t.tab('신랑 키움');
  assert.ok(sh);
  assert.equal(sh.get(1, 2), '신랑 키움');
  assert.match(sh.get(3, 2), /^=SUMIFS\(증권종목표!\$F\$2:\$F\$1001,증권종목표!\$A\$2:\$A\$1001,\$B\$1\)$/);
  assert.match(sh.get(12, 1), /^=IFERROR\(FILTER\(증권종목표!\$B\$2:\$G\$1001/);
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움', 5), 'shown');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 1);
});

test('손익·수익률은 모든 종목에 매입금액이 있을 때만 (원금이 빈 종목이 있으면 비움)', () => {
  const t = setup();
  t.names('A');
  t.ctx.syncAccountTab(t.ss, '', 'A', 5);
  const sh = t.tab('A');
  assert.match(sh.get(7, 2), /^=IF\(COUNTIFS\(증권종목표!\$A\$2:\$A\$1001,\$B\$1,증권종목표!\$D\$2:\$D\$1001,""\)>0,"",B3-B4\)$/);
  assert.match(sh.get(8, 2), /^=IF\(AND\(ISNUMBER\(B7\),B4>0\),B7\/B4,""\)$/);
});

test('계좌 탭 수식은 목록 이름의 앞뒤 공백을 무시하고 찾는다', () => {
  const t = setup();
  t.names('A');
  t.ctx.syncAccountTab(t.ss, '', 'A', 5);
  assert.match(t.tab('A').get(2, 2), /MATCH\(\$B\$1,ARRAYFORMULA\(TRIM\(증권계좌!\$A\$5:\$A\$14\)\),0\)/);
});

test('이름 바꾸기 → 탭 이름·B1·증권종목표의 계좌명·증권종목 B2가 함께 바뀐다', () => {
  const t = setup();
  t.names('신랑 키움');
  t.ctx.syncAccountTab(t.ss, '', '신랑 키움', 5);
  t.tbl.getRange('A2:G3').setValues([['신랑 키움', '1', 'A', 1, 2, 3, 'KRW'], ['신부 삼성', '2', 'B', 1, 2, 3, 'KRW']]);
  t.pos.set(2, 2, '신랑 키움');
  t.names('신랑 키움증권');
  assert.equal(t.ctx.syncAccountTab(t.ss, '신랑 키움', '신랑 키움증권', 5), 'renamed');
  assert.ok(!t.tab('신랑 키움') && t.tab('신랑 키움증권'));
  assert.equal(t.tab('신랑 키움증권').get(1, 2), '신랑 키움증권');
  assert.deepEqual([t.tbl.get(2, 1), t.tbl.get(3, 1)], ['신랑 키움증권', '신부 삼성']);
  assert.equal(t.pos.get(2, 2), '신랑 키움증권');
});

test('이름 지우기 → 탭은 삭제하지 않고 숨긴다, 다시 적으면 보인다', () => {
  const t = setup();
  t.names('신랑 키움');
  t.ctx.syncAccountTab(t.ss, '', '신랑 키움', 5);
  assert.equal(t.ctx.syncAccountTab(t.ss, '신랑 키움', '', 5), 'hidden');
  assert.equal(t.tab('신랑 키움').isSheetHidden(), true);
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움', 5), 'shown');
  assert.equal(t.tab('신랑 키움').isSheetHidden(), false);
});

test('금지 문자·너무 긴 이름은 탭을 만들지 않고 칸을 이전 값으로 되돌린다', () => {
  const t = setup();
  t.acct.set(5, 1, 'a/b');
  assert.equal(t.ctx.syncAccountTab(t.ss, '', 'a/b', 5), 'invalid');
  assert.equal(t.acct.get(5, 1), '');
  t.acct.set(6, 1, '가'.repeat(91));
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '가'.repeat(91), 6), 'invalid');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 0);
});

test('바꾸려는 이름의 탭이 이미 있으면(숨긴 탭 포함) 건드리지 않고 칸을 되돌린다', () => {
  const t = setup();
  t.names('A', 'B');
  t.ctx.syncAccountTab(t.ss, '', 'A', 5);
  t.ctx.syncAccountTab(t.ss, '', 'B', 6);
  t.acct.set(5, 1, '');
  t.ctx.syncAccountTab(t.ss, 'A', '', 5);                  // A 지움 → 계좌_A 숨김
  t.acct.set(6, 1, 'A');                                   // B를 A로 바꿈
  assert.equal(t.ctx.syncAccountTab(t.ss, 'B', 'A', 6), 'exists');
  assert.equal(t.acct.get(6, 1), 'B');                     // 되돌림
  assert.ok(t.tab('B') && t.tab('A').isSheetHidden());
});

test('이미 목록에 있는 이름(공백·대소문자만 다른 것 포함)을 또 적으면 duplicate로 거부하고 되돌린다', () => {
  const t = setup();
  t.names('Kiwoom');
  t.ctx.syncAccountTab(t.ss, '', 'Kiwoom', 5);
  t.acct.set(6, 1, 'kiwoom ');
  assert.equal(t.ctx.syncAccountTab(t.ss, '', 'kiwoom ', 6), 'duplicate');
  assert.equal(t.acct.get(6, 1), '');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 1);
});

test('이전 탭이 없는 이름 바꾸기(사용자가 탭을 지운 경우)는 새 탭을 만든다', () => {
  const t = setup();
  t.names('Y');
  assert.equal(t.ctx.syncAccountTab(t.ss, 'X', 'Y', 5), 'created');
  assert.ok(t.tab('Y'));
});

test('routeEdit: 증권종목 B3 체크는 positions, 증권계좌 A5:A14 편집은 brokerTab(행·이전·새 이름)', () => {
  const c = setup().ctx;
  const ev = (o) => Object.assign({ sheet: '증권종목', row: 3, col: 2, numRows: 1, numCols: 1, value: 'TRUE' }, o);
  const plain = (x) => JSON.parse(JSON.stringify(x));
  assert.deepEqual(plain(c.routeEdit(ev({}))), { type: 'positions' });
  assert.equal(c.routeEdit(ev({ value: 'FALSE' })), null);
  const acct = (o) => Object.assign({ sheet: '증권계좌', row: 5, col: 1, numRows: 1, numCols: 1, value: '신랑 키움', oldValue: undefined }, o);
  assert.deepEqual(plain(c.routeEdit(acct({}))), { type: 'brokerTab', row: 5, from: '', to: '신랑 키움' });
  assert.deepEqual(plain(c.routeEdit(acct({ value: undefined, oldValue: '신랑 키움' }))), { type: 'brokerTab', row: 5, from: '신랑 키움', to: '' });
  assert.equal(c.routeEdit(acct({ row: 15 })), null);       // 목록 밖
  assert.equal(c.routeEdit(acct({ col: 2 })), null);        // 이름 칸이 아님
  assert.equal(c.routeEdit(acct({ value: 'a', oldValue: 'a' })), null);
});
