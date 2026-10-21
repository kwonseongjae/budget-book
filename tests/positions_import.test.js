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
  const paste = (account, rows, mode) => {
    pos.set(2, 2, account);
    pos.set(4, 2, mode === undefined ? '' : mode);
    rows.forEach((r, i) => r.forEach((v, j) => pos.set(6 + i, 1 + j, v)));
    let checkbox = null;
    ctx.importPositions(ss, { setValue(v) { checkbox = v; } });
    return checkbox;
  };
  const table = () => tbl.getRange('A2:G1001').getValues().filter((r) => r[0] !== '');
  return { ctx, ss, pos, tbl, acct, paste, table, result: () => pos.get(3, 3) };
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

test('importPositions: 방식이 전체 교체면 같은 계좌를 다시 붙여넣을 때 교체되고 다른 계좌 줄은 그대로', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신부 삼성', [HEAD, ['B', 1, 200, 210]]);
  t.paste('신랑 키움', [HEAD, ['C', 2, 300, 330]], '전체 교체');
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
  t.paste('1', [HEAD, ['C', 2, 300, 330]], '전체 교체');
  assert.deepEqual(t.table().map((r) => r[2]), ['C']);
});

// ---- 반영하면 계좌 탭에 종목별 비중 원형 그래프 (실제 SpreadsheetApp 차트 API를 흉내) ----
function chartProbe(t, account) {
  const charts = [], calls = [];
  t.ctx.Charts = { ChartType: { PIE: 'PIE' } };
  const tab = t.ss.insertSheet('계좌_' + account);
  const getRange = tab.getRange.bind(tab);
  tab.getRange = (a, b, c, d) => Object.assign(getRange(a, b, c, d), { a1: a });
  tab.newChart = () => {
    const spec = { ranges: [], options: {} };
    const b = { setChartType: (x) => { spec.type = x; return b; }, addRange: (r) => { spec.ranges.push(r.a1); return b; },
      setPosition: (...p) => { spec.position = p; return b; }, setOption: (k, v) => { spec.options[k] = v; return b; }, build: () => spec };
    return b;
  };
  tab.getCharts = () => charts.slice();
  tab.removeChart = (c) => { calls.push('remove'); charts.splice(charts.indexOf(c), 1); };
  tab.insertChart = (c) => { calls.push('insert'); charts.push(c); };
  return { charts, calls };
}

test('importPositions: 반영하면 계좌 탭에 종목명·평가금액 원형 그래프가 들어가고, 다시 반영하면 교체된다', () => {
  const t = setup();
  const probe = chartProbe(t, '신랑 키움');
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110], ['B', 2, 200, 190]]);
  assert.equal(probe.charts.length, 1);
  assert.deepEqual([probe.charts[0].type, probe.charts[0].ranges], ['PIE', ['B12:B13', 'E12:E13']]);
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110], ['B', 2, 200, 190], ['C', 3, 300, 330]], '전체 교체');
  assert.equal(probe.charts.length, 1);                                       // 옛 그래프는 지우고 새로
  assert.deepEqual(probe.charts[0].ranges, ['B12:B14', 'E12:E14']);
  assert.match(t.result(), /^✓ 3종목 반영$/);
});

test('importPositions: 종목이 50개를 넘어도 그래프는 50개까지, 반영이 거부되면 그래프는 그대로', () => {
  const t = setup();
  const probe = chartProbe(t, '신랑 키움');
  const many = Array.from({ length: 60 }, (_, i) => ['S' + i, 1, 10, 11]);
  t.paste('신랑 키움', [HEAD].concat(many), '전체 교체');
  assert.deepEqual(probe.charts[0].ranges, ['B12:B61', 'E12:E61']);
  t.paste('신랑 키움', [['foo', 'bar'], ['1', '2']]);                          // 머리글 없음 → 거부
  assert.equal(probe.charts.length, 1);
});

test('importPositions: 계좌 탭이 아직 없으면 만들어서 그래프까지 넣는다', () => {
  const t = setup();
  t.ctx.Charts = { ChartType: { PIE: 'PIE' } };
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  assert.ok(t.ss.getSheetByName('계좌_신랑 키움'));
  assert.match(t.result(), /^✓ 1종목 반영/);
});

test('importPositions: 그래프를 못 만들어도 종목 반영은 되고 결과에 알린다', () => {
  const t = setup();
  const probe = chartProbe(t, '신랑 키움');
  const tab = t.ss.getSheetByName('계좌_신랑 키움');
  tab.insertChart = () => { throw new Error('boom'); };
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  assert.equal(t.table().length, 1);
  assert.match(t.result(), /그래프는 만들지 못/);
  assert.equal(probe.charts.length, 0);
});

// ---- 방식: 기본은 '추가·갱신' (있는 종목은 그대로 두고 같은 종목은 갱신, 새 종목은 추가), '전체 교체'는 표 전체로 바꿈 ----
test('importPositions: 기본(추가·갱신)은 기존 종목을 지우지 않고 새 종목을 더한다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['삼성전자', 10, 700000, 750000]]);
  t.paste('신랑 키움', [HEAD, ['SK하이닉스', 2, 400000, 380000]]);
  assert.deepEqual(t.table().map((r) => [r[0], r[2], r[5]]), [['신랑 키움', '삼성전자', 750000], ['신랑 키움', 'SK하이닉스', 380000]]);
  assert.match(t.result(), /^✓ 1종목 반영 · 계좌 전체 2종목$/);
});

test('importPositions: 추가·갱신에서 같은 종목(코드 또는 이름)은 값을 갱신하고 줄이 늘지 않는다', () => {
  const t = setup();
  t.paste('신랑 키움', [['종목코드', '종목명', '수량', '매입금액', '평가금액'], ['005930', '삼성전자', 10, 700000, 750000]]);
  t.paste('신랑 키움', [['종목코드', '종목명', '수량', '매입금액', '평가금액'], ['005930', '삼성전자(우)', 12, 800000, 900000]]);   // 같은 코드 → 갱신
  t.paste('신랑 키움', [HEAD, ['삼성전자(우)', 13, 810000, 910000]]);                                                   // 코드 없음 → 이름으로 갱신
  assert.deepEqual(t.table().map((r) => [r[2], r[3], r[5]]), [['삼성전자(우)', 13, 910000]]);
});

test("importPositions: '전체 교체'는 붙여넣은 표에 없는 종목을 지운다 (판 종목 정리)", () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110], ['B', 1, 100, 110]]);
  t.paste('신랑 키움', [HEAD, ['B', 2, 200, 220]], '전체 교체');
  assert.deepEqual(t.table().map((r) => [r[2], r[5]]), [['B', 220]]);
});

test('importPositions: 그래프는 계좌 전체 종목 수에 맞춘다 (추가·갱신)', () => {
  const t = setup();
  const probe = chartProbe(t, '신랑 키움');
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신랑 키움', [HEAD, ['B', 1, 100, 110]]);
  assert.deepEqual(probe.charts[0].ranges, ['B12:B13', 'E12:E13']);
});
