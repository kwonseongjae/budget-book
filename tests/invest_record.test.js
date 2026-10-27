// recordInvest 글루: 4계좌 + 기타(붙여넣기) 계좌 → 투자기록 14열, 투자기록_계좌 줄.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet, FakeSpreadsheet } = require('./fake_sheets');

function setup(accountRows) {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'meritz_logic.gs', 'invest_logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => new Date(2026, 9, 22);                       // 어제 = 10-21
  const tab = new FakeSheet(Array.from({ length: 12 }, () => ['', '', '']));
  [[7, 1000, 900], [10, 500, 400]].forEach(([r, v, p]) => { tab.set(r, 2, v); tab.set(r, 3, p); });
  const list = new FakeSheet([[], [], [], [], ...accountRows]);
  const log = new FakeSheet([['날짜']]);
  const detail = new FakeSheet([['날짜']]);
  const ss = new FakeSpreadsheet({ '투자': tab, '투자기록': log, '증권계좌': list, '투자기록_계좌': detail });
  return { ctx, ss, log, detail, list };
}
const acct = (name, principal, value) => [name, '', '', '', '', '', '', '', principal, value, '', ''];
const plain = (x) => JSON.parse(JSON.stringify(x));

test('recordInvest: 기타 계좌가 합계(J·K)에 들어가고 M·N에 따로, 계좌별 줄도 쌓인다', () => {
  const t = setup([acct('신랑 키움', 800, 900), acct('신부 삼성', '', 100)]);
  t.ctx.recordInvest(t.ss);
  const row = plain(t.log.getRange('A2:N2').getValues()[0]);
  assert.deepEqual(row.slice(1), [1000, 900, '', '', 500, 400, '', '', 2500, 2100, 2, 1000, 800]);
  assert.deepEqual(plain(t.detail.getRange('B2:D3').getValues()), [['신랑 키움', 900, 800], ['신부 삼성', 100, '']]);
});

test('recordInvest: 기타 계좌가 없으면 기존과 똑같은 합계, M·N 빈칸, 계좌별 탭은 그대로', () => {
  const t = setup([]);
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.log.getRange('J2:N2').getValues()[0]), [1500, 1300, 2, '', '']);
  assert.equal(t.detail.get(2, 1), '');
});

test('recordInvest: 같은 날 두 번 돌려도 계좌별 줄은 늘지 않고 값만 바뀐다', () => {
  const t = setup([acct('신랑 키움', 800, 900)]);
  t.ctx.recordInvest(t.ss);
  t.list.set(5, 10, 950);
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.detail.getRange('B2:D3').getValues()), [['신랑 키움', 950, 800], ['', '', '']]);
  assert.equal(t.log.get(3, 1), '');
});

test('recordInvest: 4계좌가 모두 비어도 기타 계좌만 있으면 기록, 아무것도 없으면 기록하지 않는다', () => {
  const t = setup([acct('신랑 키움', 800, 900)]);
  [[7], [10]].forEach(([r]) => { t.ss.getSheetByName('투자').set(r, 2, ''); t.ss.getSheetByName('투자').set(r, 3, ''); });
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.log.getRange('J2:L2').getValues()[0]), [900, 800, 4]);
  const none = setup([]);
  [[7], [10]].forEach(([r]) => { none.ss.getSheetByName('투자').set(r, 2, ''); none.ss.getSheetByName('투자').set(r, 3, ''); });
  none.ctx.recordInvest(none.ss);
  assert.equal(none.log.get(2, 1), '');
});

test('recordInvest: 4계좌가 일시적으로 모두 빠진 날은 기타 계좌만으로 기록하지 않는다 (합계 급락 방지)', () => {
  const t = setup([acct('신랑 키움', 800, 900)]);
  t.ctx.recordInvest(t.ss);                                                      // 10-21: 4계좌 일부 값 있음 → 기록
  t.ctx.todayDate = () => new Date(2026, 9, 23);                                 // 10-22 기록 시도
  [7, 10].forEach((r) => { t.ss.getSheetByName('투자').set(r, 2, ''); t.ss.getSheetByName('투자').set(r, 3, ''); });
  t.ctx.recordInvest(t.ss);
  assert.equal(t.log.get(3, 1), '');
});

test('recordInvest: 붙여넣기 계좌만 쓰는 사용자(직전 기록도 4계좌 없음)는 계속 기록된다', () => {
  const t = setup([acct('신랑 키움', 800, 900)]);
  [7, 10].forEach((r) => { t.ss.getSheetByName('투자').set(r, 2, ''); t.ss.getSheetByName('투자').set(r, 3, ''); });
  t.ctx.recordInvest(t.ss);
  t.ctx.todayDate = () => new Date(2026, 9, 23);
  t.ctx.recordInvest(t.ss);
  assert.notEqual(t.log.get(3, 1), '');
});

test('recordInvest: 계좌 이름을 바꾸고 같은 날 다시 돌려도 계좌별 줄은 하나, 기타 계좌가 사라지면 그날 줄이 지워진다', () => {
  const t = setup([acct('키움', 800, 900)]);
  t.ctx.recordInvest(t.ss);
  t.list.set(5, 1, '신랑 키움');
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.detail.getRange('B2:B3').getValues()), [['신랑 키움'], ['']]);
  t.list.set(5, 1, '');
  t.ctx.recordInvest(t.ss);
  assert.equal(t.detail.get(2, 1), '');                                          // 줄어든 꼬리는 지워진다
});
