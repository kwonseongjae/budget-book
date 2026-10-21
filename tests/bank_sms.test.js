// 통장 입출금 문자: 입금 = 수입, 출금 = 지출 (이체는 사용자가 구분만 고친다). 카드 대금 출금은 건너뜀.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const { FakeSheet } = require('./fake_sheets');

function load() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => new Date(2026, 9, 16);
  ctx.refreshCategoryRules = () => {};
  return ctx;
}

const IN = '[Web발신]\n[우리은행] 10/16 09:00 입금 3,000,000원 월급 잔액 5,000,000원';
const OUT = '[Web발신]\n[국민은행] 10/16 12:30 출금 15,000원 홍길동 잔액 1,000,000원';
const CARDPAY = '[Web발신]\n[우리은행] 10/16 10:00 출금 420,000원 삼성카드 잔액 100원';

test('parseBankSms: 입금·출금·카드 대금·카드 승인·실패를 가른다', () => {
  const c = load();
  const t = new Date(2026, 9, 16);
  const i = c.parseBankSms(IN, t);
  assert.deepEqual([i.status, i.date, i.amount, i.bank, i.memo], ['in', '2026-10-16', 3000000, '우리', '월급']);
  const o = c.parseBankSms(OUT, t);
  assert.deepEqual([o.status, o.amount, o.bank, o.memo], ['out', 15000, '국민', '홍길동']);
  assert.equal(c.parseBankSms(CARDPAY, t).status, 'cardpay');
  assert.equal(c.parseBankSms('[Web발신]\n삼성카드 승인 12,000원 일시불 10/15 12:30 스타벅스', t).status, 'fail');
  assert.equal(c.parseBankSms('[우리은행] 입금 3,000원', t).status, 'fail');  // 날짜 없음
});

function setup() {
  const ctx = load();
  const sheets = {
    '문자입력': new FakeSheet([['↓ 붙여넣기', false, '']]),
    '내역': new FakeSheet([['날짜']]),
    '자산': new FakeSheet([['자산명'], ['우리은행', '통장', '', '', '', '', '', '', '신랑'], ['국민은행', '통장', '', '', '', '', '', '', '신부'],
      ['삼성카드', '카드', '', '', '', '', '', '', '신랑']]),
    '설정': new FakeSheet([['카테고리'], ['x', '', '', '', '신랑'], ['x', '', '', '', '신부'], ['x'], ['x']]),
  };
  sheets['설정'].set(2, 7, 'KRW'); sheets['설정'].set(2, 8, 1);
  const ss = { getSheetByName: (n) => sheets[n] };
  const paste = (lines) => { lines.forEach((t, i) => sheets['문자입력'].set(2 + i, 1, t)); ctx.importSms(ss, { setValue() {} }); };
  return { paste, ledger: () => sheets['내역'].rows.slice(1).map((r) => r.slice(0, 10)), status: () => sheets['문자입력'].get(1, 3) };
}

test('importSms: 입금=수입(통장·소유자), 출금=지출, 같은 문자 재붙여넣기는 건너뜀', () => {
  const t = setup();
  t.paste([IN, OUT]);
  const rows = t.ledger();
  assert.equal(rows.length, 2);
  assert.deepEqual([rows[0][1], rows[0][2], rows[0][5], rows[0][7], rows[0][9]], ['신랑', '수입', '우리은행', 3000000, '월급']);
  assert.deepEqual([rows[1][1], rows[1][2], rows[1][5], rows[1][7]], ['신부', '지출', '국민은행', 15000]);
  assert.match(t.status(), /^2건 추가 \/ 입금 1·출금 1/);
  t.paste([IN, OUT]);
  assert.equal(t.ledger().length, 2);
  assert.match(t.status(), /중복 2건 건너뜀/);
});

test('importSms: 카드 대금 출금은 건너뛰고 알린다, 은행명이 [자산]에 없으면 통장 확인', () => {
  const t = setup();
  t.paste([CARDPAY, '[Web발신]\n[신한은행] 10/16 11:00 입금 50,000원 환급']);
  const rows = t.ledger();
  assert.equal(rows.length, 1);
  assert.deepEqual([rows[0][1], rows[0][5]], ['공동', '']);
  assert.match(t.status(), /카드 대금 1건 건너뜀/);
  assert.match(t.status(), /통장 확인 1건/);
});
