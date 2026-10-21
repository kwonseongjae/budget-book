// importSms 전체 흐름(문자입력 → 내역)을 가짜 스프레드시트로 돌려 본다: 중복 건너뜀·취소 반영·외화·실패 유지.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const { FakeSheet } = require('./fake_sheets');

function setup() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => new Date(2026, 9, 16);
  ctx.refreshCategoryRules = () => {};
  const sheets = {
    '문자입력': new FakeSheet([['↓ 붙여넣기', false, '']]),
    '내역': new FakeSheet([['날짜']]),
    '자산': new FakeSheet([['자산명'], ['삼성카드', '카드', '', '', '', '', '', '', '신랑'], ['하나카드', '카드', '', '', '', '', '', '', '신랑']]),
    '설정': new FakeSheet([['카테고리'], ['x', '', '', '', '신랑'], ['x', '', '', '', '신부'], ['x'], ['x']]),
  };
  sheets['설정'].set(2, 7, 'KRW'); sheets['설정'].set(2, 8, 1);
  sheets['설정'].set(3, 7, 'USD'); sheets['설정'].set(3, 8, 1340);
  const ss = { getSheetByName: (n) => sheets[n] };
  const checkbox = { setValue() {} };
  const paste = (lines) => { lines.forEach((t, i) => sheets['문자입력'].set(2 + i, 1, t)); ctx.importSms(ss, checkbox); };
  const ledger = () => sheets['내역'].rows.slice(1).map((r) => r.slice(0, 14));
  return { ctx, sheets, paste, ledger, status: () => sheets['문자입력'].get(1, 3) };
}

const A = '[Web발신]\n삼성카드 승인 12,000원 일시불 10/15 12:30 스타벅스';
const B = '[Web발신]\n삼성카드 승인 5,000원 일시불 10/15 13:00 GS25';

test('importSms: 두 문자가 내역에 들어가고, 같은 문자를 다시 붙여넣으면 모두 건너뛴다', () => {
  const t = setup();
  t.paste([A, B]);
  assert.equal(t.ledger().length, 2);
  assert.match(t.status(), /^2건 추가/);
  assert.equal(t.ledger()[0][7], 12000);
  t.paste([A, B]);
  assert.equal(t.ledger().length, 2);
  assert.match(t.status(), /^0건 추가 \/ 중복 2건 건너뜀/);
});

test('importSms: 같은 금액의 진짜 두 건은 둘 다 들어간다', () => {
  const t = setup();
  t.paste([A, A]);
  assert.equal(t.ledger().length, 2);
  t.paste([A, A, A]);                 // 이미 둘이 있으니 새로 하나만
  assert.equal(t.ledger().length, 3);
});

test('importSms: 취소 문자는 원 거래의 사용자·카테고리·결제수단을 쓴 음수 줄, 다시 붙여넣어도 한 번만', () => {
  const t = setup();
  t.paste([A]);
  t.sheets['내역'].set(2, 4, '카페·간식');   // 사용자가 카테고리를 채움
  const cancel = '[Web발신]\n삼성카드 승인취소 12,000원 10/16 09:00 스타벅스';
  t.paste([cancel]);
  const rows = t.ledger();
  assert.equal(rows.length, 2);
  assert.deepEqual([rows[1][3], rows[1][5], rows[1][7], rows[1][9]], ['카페·간식', '삼성카드', -12000, '취소 스타벅스']);
  assert.match(t.status(), /취소 1건 반영/);
  t.paste([cancel]);
  assert.equal(t.ledger().length, 2);
});

test('importSms: 원 거래를 못 찾은 취소도 음수 줄로 넣고 알린다', () => {
  const t = setup();
  t.paste(['[Web발신]\n삼성카드 승인취소 7,000원 10/16 09:00 어딘가']);
  assert.equal(t.ledger()[0][7], -7000);
  assert.match(t.status(), /원 거래를 못 찾은 취소 1건/);
});

test('importSms: 해외 USD 문자는 USD 금액과 입력 시점 환율(N)로', () => {
  const t = setup();
  t.paste(['[Web발신]\n삼성카드 해외승인 USD 22.00 10/15 20:00 ANTHROPIC']);
  const r = t.ledger()[0];
  assert.deepEqual([r[7], r[8], r[13]], [22, 'USD', 1340]);
});

test('importSms: 못 읽은 문자는 시트에 남기고 나머지는 처리', () => {
  const t = setup();
  t.paste([A, '[Web발신]\n광고입니다 무료 체험']);
  assert.equal(t.ledger().length, 1);
  assert.match(t.status(), /실패 1건/);
  assert.equal(t.sheets['문자입력'].get(2, 3), '인식 실패');
});
