// importPositions 글루: 붙여넣기 칸 → 정규 종목 표(증권종목표 탭), 계좌 목록의 마지막 붙여넣기 날짜, 결과 메시지.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet, FakeSpreadsheet } = require('./fake_sheets');

function setup() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs', 'positions_logic.gs', 'positions.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => new Date(2026, 9, 21);
  const pos = new FakeSheet([[], [], [], [], []]);
  const tbl = new FakeSheet([[]]);
  const acct = new FakeSheet([[], [], [], [], ['신랑 키움'], ['신부 삼성']]);
  const ss = new FakeSpreadsheet({ '증권종목': pos, '증권종목표': tbl, '증권계좌': acct });
  const paste = (account, rows) => {
    pos.set(2, 2, account);
    rows.forEach((r, i) => r.forEach((v, j) => pos.set(6 + i, 1 + j, v)));
    let checkbox = null;
    ctx.importPositions(ss, { setValue(v) { checkbox = v; } });
    return checkbox;
  };
  const table = () => tbl.getRange('A2:G1001').getValues().filter((r) => r[0] !== '');
  return { ctx, pos, tbl, acct, paste, table, result: () => pos.get(3, 3) };
}

const HEAD = ['종목명', '수량', '매입금액', '평가금액'];

test('importPositions: 종목이 정규 표에 들어가고, 붙여넣기 칸은 비워지고, 마지막 붙여넣기 날짜가 기록된다', () => {
  const t = setup();
  assert.equal(t.paste('신랑 키움', [HEAD, ['삼성전자', 10, '700,000', '750,000'], ['SK하이닉스', 2, '400,000', '380,000']]), false);
  assert.deepEqual(t.table().map((r) => [r[0], r[2], r[5]]), [['신랑 키움', '삼성전자', 750000], ['신랑 키움', 'SK하이닉스', 380000]]);
  assert.equal(t.pos.get(6, 1), '');                                   // 붙여넣기 칸 비움
  assert.equal(t.acct.get(5, 6).getTime(), new Date(2026, 9, 21).getTime());
  assert.match(t.result(), /^✓ 2종목 반영/);
});

test('importPositions: 같은 계좌를 다시 붙여넣으면 교체되고 다른 계좌 줄은 그대로', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신부 삼성', [HEAD, ['B', 1, 200, 210]]);
  t.paste('신랑 키움', [HEAD, ['C', 2, 300, 330]]);
  assert.deepEqual(t.table().map((r) => [r[0], r[2]]), [['신부 삼성', 'B'], ['신랑 키움', 'C']]);
});

test('importPositions: 머리글을 못 찾으면 기존 종목을 그대로 두고 안내만 한다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신랑 키움', [['foo', 'bar'], ['1', '2']]);
  assert.deepEqual(t.table().map((r) => r[2]), ['A']);
  assert.match(t.result(), /^✗ .*머리글/);
  assert.equal(t.pos.get(6, 1), 'foo');                                // 못 읽은 표는 지우지 않는다
});

test('importPositions: 계좌를 안 골랐거나 붙여넣기가 비면 안내만', () => {
  const t = setup();
  t.paste('', [HEAD, ['A', 1, 100, 110]]);
  assert.match(t.result(), /계좌를 먼저/);
  const t2 = setup();
  t2.paste('신랑 키움', []);
  assert.match(t2.result(), /붙여넣어/);
});

test('importPositions: 일부 줄이 실패하면 나머지는 반영하고 실패 줄을 표시한다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110], ['', 1, 5, '??']]);
  assert.equal(t.table().length, 1);
  assert.match(t.result(), /실패 1줄/);
  assert.equal(t.pos.get(6, 6), '인식 실패');
});

test('importPositions: 계좌 목록에 없는 이름(예전 이름 등)이면 거부하고 아무것도 바꾸지 않는다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('옛 이름', [HEAD, ['Z', 1, 1, 1]]);
  assert.match(t.result(), /^✗ .*목록에 없/);
  assert.deepEqual(t.table().map((r) => r[0]), ['신랑 키움']);
  assert.equal(t.pos.get(6, 1), '종목명');                              // 붙여넣은 표 그대로
});

test('importPositions: 읽은 종목이 하나도 없으면(전부 실패) 기존 종목을 지우지 않는다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신랑 키움', [['종목명', '평가금액'], ['X', '$1,000'], ['Y', '$2,000']]);
  assert.deepEqual(t.table().map((r) => r[2]), ['A']);
  assert.match(t.result(), /^✗ .*읽은 종목이 없/);
  assert.equal(t.pos.get(6, 1), '종목명');
});

test('importPositions: 열이 많은 표(20열)를 붙여넣어도 다른 계좌 종목 표가 망가지지 않는다', () => {
  const t = setup();
  t.paste('신부 삼성', [HEAD, ['B', 1, 200, 210]]);
  const wide = [HEAD.concat(['현재가', '손익', '손익률', '비중', '통화', '시장', '메모', '기타', '기타2', '기타3', '기타4', '기타5', '기타6', '기타7', '기타8', '기타9']),
    ['삼성', 3, '300', '330', 110, 30, '10%', '5%', '', '', '', '', '', '', '', '', '', '', '', '']];
  t.paste('신랑 키움', wide);
  assert.deepEqual(t.table().map((r) => [r[0], r[2]]), [['신부 삼성', 'B'], ['신랑 키움', '삼성']]);
});

test('importPositions: 계좌 이름이 숫자로 저장된 줄도 같은 계좌로 보고 교체한다 (실제 시트는 "1"을 숫자 1로 바꿔 저장)', () => {
  const t = setup();
  t.acct.set(5, 1, '1');
  t.paste('1', [HEAD, ['A', 1, 100, 110]]);
  t.tbl.set(2, 1, 1);                                                  // 시트가 숫자로 바꿔 저장한 모양
  t.paste('1', [HEAD, ['C', 2, 300, 330]]);
  assert.deepEqual(t.table().map((r) => r[2]), ['C']);
});
