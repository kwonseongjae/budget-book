// 붙여넣은 보유종목 표 해석: 머리글 이름으로 열을 찾고, 숫자 표기·합계 줄·CSV를 견딘다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function load() {
  const ctx = vm.createContext({});
  for (const f of ['logic.gs', 'positions_logic.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  return ctx;
}
const plain = (x) => JSON.parse(JSON.stringify(x));

test('posNum: 쉼표·원·%·플러스·괄호 음수, 못 읽으면 NaN', () => {
  const c = load();
  assert.equal(c.posNum('1,234원'), 1234);
  assert.equal(c.posNum('+5.2%'), 5.2);
  assert.equal(c.posNum('(1,234)'), -1234);
  assert.equal(c.posNum(7), 7);
  assert.ok(Number.isNaN(c.posNum('-')));
  assert.ok(Number.isNaN(c.posNum('abc')));
});

test('parsePositions: 칸 단위 표 — 수량×단가로 계산, 합계 줄은 건너뜀', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목명', '보유수량', '평균단가', '현재가', '평가금액(원)'],
    ['삼성전자', 10, '70,000', '75,000', '750,000'], ['합계', '', '', '', '750,000'], ['', '', '', '', '']]));
  assert.deepEqual(r.positions, [{ code: '', name: '삼성전자', qty: 10, cost: 700000, value: 750000, currency: 'KRW' }]);
  assert.deepEqual(r.failed, []);
});

test('parsePositions: 평가금액이 없으면 수량×현재가, 코드·통화 열은 있으면 읽음', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목코드', '종목명', '수량', '매입금액', '현재가', '통화'], ['AAPL', 'Apple', 2, '300,000', '200,000', 'krw']]));
  assert.deepEqual(r.positions[0], { code: 'AAPL', name: 'Apple', qty: 2, cost: 300000, value: 400000, currency: 'KRW' });
});

test('parsePositions: 첫 열에 한 줄씩 들어온 CSV(따옴표 안 쉼표)와 탭 구분', () => {
  const c = load();
  const csv = plain(c.parsePositions([['종목명,수량,매입금액,평가금액'], ['"A, Inc",3,"300,000","330,000"'], ['bad,x,y,z']]));
  assert.equal(csv.positions[0].name, 'A, Inc');
  assert.equal(csv.positions[0].value, 330000);
  assert.deepEqual(csv.failed, ['bad x y z']);
  const tab = plain(c.parsePositions([['종목명\t수량\t평균단가\t현재가'], ['TIGER\t5\t10,000\t11,000']]));
  assert.equal(tab.positions[0].value, 55000);
});

test('parsePositions: 머리글을 못 찾으면 error만 돌려준다', () => {
  const c = load();
  const r = plain(c.parsePositions([['foo', 'bar'], ['1', '2']]));
  assert.match(r.error, /머리글/);
  assert.equal(r.positions, undefined);
});

test('parsePositions: 음수 평가(괄호)와 종목명이 빈 줄은 실패로', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목명', '평가금액'], ['환헤지', '(5,000)'], ['', '1,000']]));
  assert.equal(r.positions[0].value, -5000);
  assert.deepEqual(r.failed, ['1,000']);
});

test('replaceAccountRows: 그 계좌만 교체하고 다른 계좌 줄은 그대로, 두 번 해도 쌓이지 않는다', () => {
  const c = load();
  const table = [['a', '1', 'x', 1, 2, 3, 'KRW'], ['b', '2', 'y', 1, 2, 3, 'KRW'], ['', '', '', '', '', '', '']];
  const p = [{ code: '9', name: 'n', qty: 1, cost: 2, value: 3, currency: 'KRW' }];
  const once = plain(c.replaceAccountRows(table, 'a', p));
  assert.deepEqual(once, [['b', '2', 'y', 1, 2, 3, 'KRW'], ['a', '9', 'n', 1, 2, 3, 'KRW']]);
  assert.deepEqual(plain(c.replaceAccountRows(once, 'a', p)), once);
});

test('renameAccountRows: 계좌명만 바꾼다', () => {
  const c = load();
  const out = plain(c.renameAccountRows([['a', '1', 'x', 1, 2, 3, 'KRW'], ['b', '2', 'y', 1, 2, 3, 'KRW']], 'a', 'z'));
  assert.deepEqual(out.map((r) => r[0]), ['z', 'b']);
});

test('validAccountName: 금지 문자·빈 이름·너무 긴 이름은 문장으로, 정상은 빈 문자열', () => {
  const c = load();
  assert.equal(c.validAccountName('신랑 키움'), '');
  for (const bad of ['a/b', 'a[1]', 'a*', 'a?', 'a:b', 'a\\b']) assert.match(c.validAccountName(bad), /사용할 수 없는 문자/, bad);
  assert.match(c.validAccountName(''), /이름/);
  assert.match(c.validAccountName('가'.repeat(91)), /90자/);
});

test('parsePositions: 원화가 아닌 통화 줄은 실패로 (원화 금액에 섞여 합산되지 않게)', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목명', '평가금액', '통화'], ['삼성', 1000, 'KRW'], ['AAPL', 100, 'USD']]));
  assert.deepEqual(r.positions.map((p) => p.name), ['삼성']);
  assert.equal(r.failed.length, 1);
  assert.match(r.failed[0], /AAPL/);
});

test('parsePositions: 같은 항목 열이 둘이면 (원)·원화가 붙은 열을 고른다', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목명', '평가금액(USD)', '평가금액(원)'], ['AAPL', 100, 140000]]));
  assert.equal(r.positions[0].value, 140000);
});

test('replaceAccountRows·renameAccountRows: 계좌 이름이 숫자로 저장된 줄도 같은 계좌로 본다', () => {
  const c = load();
  const table = [[1, 'x', 'a', 1, 2, 3, 'KRW'], ['b', 'y', 'c', 1, 2, 3, 'KRW']];
  const p = [{ code: '9', name: 'n', qty: 1, cost: 2, value: 3, currency: 'KRW' }];
  assert.deepEqual(plain(c.replaceAccountRows(table, '1', p)).map((r) => r[0]), ['b', '1']);
  assert.deepEqual(plain(c.renameAccountRows(table, '1', 'z')).map((r) => r[0]), ['z', 'b']);
});
