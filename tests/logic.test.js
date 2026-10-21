const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', 'logic.gs'), 'utf8'), ctx);
const plain = (x) => JSON.parse(JSON.stringify(x)); // vm 렐름 객체 비교용

const ev = (o) => Object.assign({ numRows: 1, numCols: 1 }, o);

test('nextEmptyRow: 마지막 값 다음 행 (중간 공백 무시)', () => {
  assert.equal(ctx.nextEmptyRow([['날짜'], ['2026-10-01'], [''], ['x'], [''], ['']]), 5);
  assert.equal(ctx.nextEmptyRow([['날짜'], [''], ['']]), 2);
  assert.equal(ctx.nextEmptyRow([['날짜'], [new Date(2026, 9, 1)], [null]]), 3);
});

test('replaceExact: 정확히 일치하는 값만 바꾸고 원본은 그대로', () => {
  const orig = [['식비'], ['식비2'], ['식비']];
  const res = ctx.replaceExact(orig, '식비', '외식');
  assert.deepEqual(plain(res), { values: [['외식'], ['식비2'], ['외식']], changed: 2 });
  assert.deepEqual(orig, [['식비'], ['식비2'], ['식비']]);
});

test('routeEdit: 설정 카테고리 이름 변경 → 내역·반복·즐겨찾기', () => {
  const a = ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, oldValue: '식비', value: '외식' }));
  assert.deepEqual(plain(a), { type: 'rename', from: '식비', to: '외식',
    targets: [['내역', 4], ['반복', 5], ['즐겨찾기', 4], ['자산', 6]] });
});

test('routeEdit: 사용자·자산 이름 변경 대상 열', () => {
  const u = ctx.routeEdit(ev({ sheet: '설정', row: 2, col: 5, oldValue: '사용자1', value: '성재' }));
  assert.deepEqual(plain(u.targets), [['내역', 2], ['반복', 3], ['즐겨찾기', 2]]);
  const a = ctx.routeEdit(ev({ sheet: '자산', row: 4, col: 1, oldValue: '신용카드1', value: '신한카드' }));
  assert.deepEqual(plain(a.targets), [['내역', 6], ['내역', 7], ['반복', 6], ['즐겨찾기', 5]]);
});

test('routeEdit: 새로 추가/지우기/여러 칸/헤더/같은 값은 무시', () => {
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 20, col: 1, oldValue: undefined, value: '반려동물' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, oldValue: '식비', value: undefined })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, numRows: 3, oldValue: '식비', value: '외식' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 1, col: 1, oldValue: '카테고리', value: '분류' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, oldValue: '식비', value: ' 식비 ' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 3, oldValue: '1', value: '2' })), null);
});

test('routeEdit: 즐겨찾기 체크 / 문자입력 체크', () => {
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '즐겨찾기', row: 2, col: 1, value: 'TRUE' }))),
    { type: 'favorite', row: 2 });
  assert.equal(ctx.routeEdit(ev({ sheet: '즐겨찾기', row: 2, col: 1, value: 'FALSE' })), null);
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '문자입력', row: 1, col: 2, value: 'TRUE' }))), { type: 'sms' });
});

test('ymKey: 월 시작일 기준 귀속월', () => {
  assert.equal(ctx.ymKey(new Date(2026, 9, 5), 1), 202610);
  assert.equal(ctx.ymKey(new Date(2026, 9, 5), 10), 202609);
  assert.equal(ctx.ymKey(new Date(2026, 0, 5), 10), 202512);
  assert.equal(ctx.ymKey(new Date(2026, 9, 10), 10), 202610);
});

test('isRecurringDue: 31일 항목은 짧은 달 말일에 생성', () => {
  assert.equal(ctx.isRecurringDue(31, '', new Date(2027, 1, 28)), true);
  assert.equal(ctx.isRecurringDue(31, '', new Date(2027, 1, 27)), false);
  assert.equal(ctx.isRecurringDue(31, 202609, new Date(2026, 8, 30)), false); // 이미 생성
});

test('isRecurringDue: 트리거가 하루 빠져도 다음날 생성, 같은 달 중복 없음', () => {
  assert.equal(ctx.isRecurringDue(5, 202609, new Date(2026, 9, 7)), true);
  assert.equal(ctx.isRecurringDue(5, 202610, new Date(2026, 9, 7)), false);
  assert.equal(ctx.isRecurringDue(5, '202610', new Date(2026, 9, 7)), false); // 시트 값이 문자열이어도
});

test('isRecurringDue: 칸 서식이 날짜로 바뀌어 202610이 Date로 읽혀도 같은 달 중복 없음', () => {
  const serial = (n, tzHours) => new Date(Date.UTC(1899, 11, 30) + n * 864e5 - tzHours * 3600e3);
  assert.equal(ctx.isRecurringDue(5, serial(202610, 9), new Date(2026, 9, 9)), false); // 시트 시간대 KST 자정
  assert.equal(ctx.isRecurringDue(5, serial(202610, 0), new Date(2026, 9, 9)), false);
  assert.equal(ctx.isRecurringDue(5, serial(202609, 9), new Date(2026, 9, 9)), true);
});

test('dueDate: 말일 보정', () => {
  const d = ctx.dueDate(31, new Date(2027, 1, 28));
  assert.deepEqual([d.getFullYear(), d.getMonth(), d.getDate()], [2027, 1, 28]);
  assert.equal(ctx.calendarYm(new Date(2026, 9, 6)), 202610);
});

const SHINHAN = '신한카드(1234)승인 홍*동 12,000원(일시불)10/05 12:30 스타벅스 누적1,234,567원';
const KB = ['[Web발신]', 'KB국민카드1*2*승인', '홍*동님', '45,000원 일시불', '10/04 19:10', '이마트', '누적987,000원'];
const TODAY = new Date(2026, 9, 6);

test('parseCardSms: 신한 한 줄 형식', () => {
  assert.deepEqual(plain(ctx.parseCardSms(SHINHAN, TODAY)),
    { status: 'ok', date: '2026-10-05', amount: 12000, currency: 'KRW', card: '신한', merchant: '스타벅스' });
});

test('parseCardSms: KB 여러 줄 형식, 누적금액을 결제금액으로 착각하지 않음', () => {
  const p = ctx.parseCardSms(KB.join('\n'), TODAY);
  assert.deepEqual(plain(p), { status: 'ok', date: '2026-10-04', amount: 45000, currency: 'KRW', card: '국민', merchant: '이마트' });
});

test('parseCardSms: 취소·인식 불가', () => {
  assert.equal(ctx.parseCardSms('[Web발신]\n삼성1234승인취소 12,000원 10/05 12:30 스타벅스', TODAY).status, 'cancel');
  assert.equal(ctx.parseCardSms('삼성카드 승인취소', TODAY).status, 'fail');  // 금액·날짜를 못 읽으면 조용히 버리지 않고 실패로 알린다
  assert.equal(ctx.parseCardSms('안녕하세요 광고입니다', TODAY).status, 'fail');
  assert.equal(ctx.parseCardSms('현대카드 승인 12,000원 13/45 12:30 가게', TODAY).status, 'fail');
});

test('parseCardSms: 1월에 받은 12/31 문자는 작년', () => {
  const p = ctx.parseCardSms('현대카드 승인 홍*동 8,000원 일시불 12/31 23:50 편의점', new Date(2027, 0, 2));
  assert.equal(p.date, '2026-12-31');
});

test('splitMessages: 여러 문자를 행 단위로 붙여넣어도 나눈다', () => {
  const lines = [SHINHAN, ''].concat(KB, ['']);
  const msgs = plain(ctx.splitMessages(lines));
  assert.equal(msgs.length, 2);
  assert.equal(msgs[0].startRow, 0);
  assert.equal(msgs[1].startRow, 2);
  assert.ok(msgs[1].text.startsWith('[Web발신]\nKB국민카드'));
});

test('cardName', () => {
  assert.equal(ctx.cardName('NH농협카드 승인'), '농협');
  assert.equal(ctx.cardName('알 수 없음'), '');
});

test('spendByCategoryUser: 해당 귀속월 나가는 돈만 원화금액(K)으로 합산', () => {
  const row = (type, cat, krw, ym) => ['', '공동', type, cat, '', '', '', 0, 'KRW', '', krw, ym];
  const out = ctx.spendByCategoryUser([
    row('지출', '식비', 10000, 202610), row('지출', '식비', 5000, 202610),
    row('수입', '월급', 3000000, 202610), row('지출', '식비', 99999, 202609)], 202610);
  assert.deepEqual(plain(out), { '식비': { '공동': 15000 } });
});

test('newAlerts: 80%·100% 각 1회, 예산 없으면 제외', () => {
  const rows = [{ category: '식비', spent: 85, budget: 100 }, { category: '쇼핑', spent: 120, budget: 100 },
    { category: '교통', spent: 50, budget: 100 }, { category: '기타', spent: 500, budget: 0 }];
  const first = plain(ctx.newAlerts(rows, {}, 202610));
  assert.deepEqual(first.map((a) => [a.category, a.level]), [['식비', 80], ['쇼핑', 100]]);
  const sent = { '202610|식비|80': true, '202610|쇼핑|100': true };
  assert.deepEqual(plain(ctx.newAlerts(rows, sent, 202610)), []);
});

test('formatAlerts: 사람이 읽는 문장', () => {
  const text = ctx.formatAlerts([{ category: '쇼핑', level: 100, spent: 312000.4, budget: 300000 }]);
  assert.equal(text, '쇼핑: 312,000 / 300,000원 (104%) — 예산 초과');
});

test('cellsToLines: 한 칸에 여러 문자를 붙여넣어도 각각 파싱', () => {
  const lines = ctx.cellsToLines([[SHINHAN + '\n' + KB.join('\n')], ['']]);
  const msgs = ctx.splitMessages(lines);
  assert.equal(msgs.length, 2);
  assert.equal(ctx.parseCardSms(msgs[1].text, TODAY).amount, 45000);
});

test('cellsToLines: 칸마다 한 문자도 그대로', () => {
  const msgs = ctx.splitMessages(ctx.cellsToLines([[SHINHAN], [KB.join('\n')]]));
  assert.equal(msgs.length, 2);
});

test('isNewAfterDue: 일자 지난 뒤 새 항목은 이번 달 생성 안 함', () => {
  assert.equal(ctx.isNewAfterDue(5, '', new Date(2026, 9, 20)), true);
  assert.equal(ctx.isNewAfterDue(5, '', new Date(2026, 9, 5)), false);
  assert.equal(ctx.isNewAfterDue(5, 202609, new Date(2026, 9, 20)), false);
});

test('routeEdit: 설정 B열 구분 변경 → 그 카테고리 행 구분 일괄 변경', () => {
  const a = ctx.routeEdit(ev({ sheet: '설정', row: 20, col: 2, oldValue: '지출', value: '청약' }));
  assert.deepEqual(plain(a), { type: 'reclass', row: 20, from: '지출', to: '청약',
    targets: [['내역', 3], ['반복', 4], ['즐겨찾기', 3]] });
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 20, col: 2, oldValue: undefined, value: '청약' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 1, col: 2, oldValue: '구분', value: 'x' })), null);
});

test('reclassify: 카테고리·기존 구분이 같은 행만 구분 변경, 원본 불변', () => {
  const orig = [['지출', '주택청약'], ['지출', '식비'], ['수입', '주택청약']];
  const res = ctx.reclassify(orig, '주택청약', '지출', '청약');
  assert.deepEqual(plain(res), { values: [['청약'], ['지출'], ['수입']], changed: 1 });
  assert.deepEqual(orig[0], ['지출', '주택청약']);
});

test('spendByCategoryUser: 새 구분(청약)도 나가는 돈으로 합산, 수입·이체·빈 구분 제외', () => {
  const row = (type, cat, krw) => ['', '공동', type, cat, '', '', '', 0, 'KRW', '', krw, 202610];
  const out = ctx.spendByCategoryUser([row('청약', '주택청약', 100000), row('지출', '식비', 5000),
    row('이체', '', 50000), row('수입', '월급', 1), row('', '식비', 7)], 202610);
  assert.deepEqual(plain(out), { '주택청약': { '공동': 100000 }, '식비': { '공동': 5000 } });
});

test('typeColumnIndex: 구분 이름으로 계산 탭 카테고리 목록 열 찾기', () => {
  const headers = ['수입', '지출', '저축', '', ''];
  assert.equal(ctx.typeColumnIndex(headers, '저축'), 2);
  assert.equal(ctx.typeColumnIndex(headers, ' 지출 '), 1);
  assert.equal(ctx.typeColumnIndex(headers, '이체'), -1);
  assert.equal(ctx.typeColumnIndex(headers, ''), -1);
});

test('routeEdit: 구분 칸 입력 → 그 행 카테고리 목록 갱신 (여러 행 붙여넣기 포함)', () => {
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '내역', row: 5, col: 3, value: '저축' }))),
    { type: 'typeset', sheet: '내역', row: 5, numRows: 1, col: 3 });
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '반복', row: 2, col: 4, numRows: 3 }))),
    { type: 'typeset', sheet: '반복', row: 2, numRows: 3, col: 4 });
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '즐겨찾기', row: 3, col: 3 }))),
    { type: 'typeset', sheet: '즐겨찾기', row: 3, numRows: 1, col: 3 });
  assert.equal(ctx.routeEdit(ev({ sheet: '내역', row: 1, col: 3, value: 'x' })), null);
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '내역', row: 5, col: 1, numCols: 10, numRows: 2 }))),
    { type: 'typeset', sheet: '내역', row: 5, numRows: 2, col: 3 });  // 행 통째 붙여넣기
  assert.equal(ctx.routeEdit(ev({ sheet: '내역', row: 5, col: 4, numCols: 3 })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '내역', row: 5, col: 4, value: '식비' })), null);
});

test('runSteps: 한 단계가 실패해도 나머지는 돌고 실패 목록을 돌려준다', () => {
  const ran = [];
  const errs = ctx.runSteps([['a', () => ran.push('a')], ['b', () => { throw new Error('메일 한도'); }], ['c', () => ran.push('c')]]);
  assert.deepEqual(ran, ['a', 'c']);
  assert.deepEqual(JSON.parse(JSON.stringify(errs)), ['b: 메일 한도']);
});

test('matchCard: 소유자 한 명이면 그 사람, 같은 카드가 여러 장이면 모름 (2026-10-14 하나카드 ×2)', () => {
  const assets = [['현금', '', ''], ['하나카드_신랑', '카드', '신랑'], ['하나카드_신부', '카드', '신부'],
    ['삼성카드', '카드', '신랑'], ['공동카드', '카드', '공동']];
  const people = ['신랑', '신부'];
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.matchCard('삼성', assets, people))), { name: '삼성카드', user: '신랑', ambiguous: false });
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.matchCard('하나', assets, people))), { name: '', user: '공동', ambiguous: true });
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.matchCard('공동', assets, people))), { name: '공동카드', user: '공동', ambiguous: false });
  assert.deepEqual(JSON.parse(JSON.stringify(ctx.matchCard('롯데', assets, people))), { name: '', user: '공동', ambiguous: false });
});

// ── 환율 고정 (2026-10-16): 외화 줄에 입력 시점 환율을 저장 ──
const FX = [['KRW', 1], ['USD', 1341.2], ['JPY', 8.48]];

test('rateFor: 외화만 환율, 원화·빈칸·모르는 통화는 빈칸', () => {
  assert.equal(ctx.rateFor('USD', FX), 1341.2);
  assert.equal(ctx.rateFor(' jpy ', FX), 8.48);
  assert.equal(ctx.rateFor('KRW', FX), '');
  assert.equal(ctx.rateFor('', FX), '');
  assert.equal(ctx.rateFor('GBP', FX), '');
  assert.equal(ctx.rateFor('USD', [['USD', '#N/A']]), '');  // 환율 계산 중 오류
});

test('ratesToFill: 외화 줄의 빈 환율만 채운다 (이미 있으면 그대로, 원화는 건드리지 않음)', () => {
  const rows = [[22, 'USD', ''], [5000, '', ''], [1500, 'JPY', 8.4], [30, 'USD', ''], [7, 'GBP', '']];
  assert.deepEqual(plain(ctx.ratesToFill(rows, FX, 2, false)), [{ row: 2, value: 1341.2 }, { row: 5, value: 1341.2 }]);
});

test('ratesToFill: 통화를 바꾼 줄은 새 환율로 덮어쓰고, 원화로 바꾸면 환율을 지운다', () => {
  assert.deepEqual(plain(ctx.ratesToFill([[22, 'JPY', 1341.2]], FX, 9, true)), [{ row: 9, value: 8.48 }]);
  assert.deepEqual(plain(ctx.ratesToFill([[22, 'KRW', 1341.2]], FX, 9, true)), [{ row: 9, value: '' }]);
  assert.deepEqual(plain(ctx.ratesToFill([[22, '', '']], FX, 9, true)), []);  // 지울 것도 없음
});

test('routeEdit: 내역 통화(I)를 바꾸면 환율 덮어쓰기, 금액(H)을 바꾸면 빈 환율만 채우기', () => {
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '내역', row: 5, col: 9, oldValue: 'USD', value: 'JPY' }))),
    { type: 'rate', row: 5, overwrite: true });
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '내역', row: 5, col: 8, oldValue: '1', value: '22' }))),
    { type: 'rate', row: 5, overwrite: false });
  assert.equal(ctx.routeEdit(ev({ sheet: '내역', row: 1, col: 9, value: '통화' })), null);
});

test('recurringTxn: 반복 한 줄 → 내역 줄 + 환율 (통화 빈칸은 원화·환율 없음)', () => {
  const today = new Date(2026, 9, 16);
  const row = [true, 16, '신랑', '지출', '구독비', '삼성카드', 22, '클로드', '', '', '', '', '', 'USD'];
  assert.deepEqual(plain(ctx.recurringTxn(row, FX, today)),
    { txn: [plain(ctx.dueDate(16, today)), '신랑', '지출', '구독비', '', '삼성카드', '', 22, 'USD', '클로드'], rate: 1341.2 });
  const krw = ctx.recurringTxn([true, 16, '신랑', '지출', '구독비', '삼성카드', 7890, '쿠팡', '', '', '', '', '', ''], FX, today);
  assert.equal(krw.txn[8], 'KRW');
  assert.equal(krw.rate, '');
});

// ── 반복 중복 방지 (2026-10-16): 같은 달에 손으로 적은 같은 건이 있으면 반복이 또 넣지 않는다 ──
const D = (m, d) => new Date(2026, m - 1, d);
const REC = [D(10, 16), '신랑', '지출', '구독비', '', '삼성카드', '', 7890, 'KRW', '쿠팡 구독비'];

test('isDuplicateTxn: 같은 달·카테고리·금액·통화에 메모가 서로 포함되면 중복 (쿠팡 ⊂ 쿠팡 구독비)', () => {
  const hist = [[D(10, 6), '신랑', '지출', '구독비', '', '삼성카드', '', 7890, 'KRW', '쿠팡']];
  assert.equal(ctx.isDuplicateTxn(hist, REC, D(10, 16)), true);
});

test('isDuplicateTxn: 금액·카테고리·통화·달이 다르거나 메모가 안 겹치면 중복 아님', () => {
  const base = [D(10, 6), '신랑', '지출', '구독비', '', '삼성카드', '', 7890, 'KRW', '쿠팡'];
  const dup = (over) => ctx.isDuplicateTxn([base.map((x, i) => (i in over ? over[i] : x))], REC, D(10, 16));
  assert.equal(dup({ 7: 8000 }), false);
  assert.equal(dup({ 3: '식비' }), false);
  assert.equal(dup({ 8: 'USD' }), false);
  assert.equal(dup({ 0: D(9, 30) }), false);   // 지난달
  assert.equal(dup({ 9: '넷플릭스' }), false);
  assert.equal(dup({ 9: '' }), false);          // 메모 없는 내역은 같은 건인지 알 수 없다
  // 금액·카테고리가 같아도 메모가 다른 계모임 둘은 서로 다른 건
  const kye = [D(10, 13), '신랑', '지출', '계모임', '', 'IBK기업은행', '', 50000, 'KRW', '성재가족 계모임'];
  assert.equal(ctx.isDuplicateTxn([kye], [D(10, 24), '신랑', '지출', '계모임', '', 'IBK기업은행', '', 50000, 'KRW', '현희가족 계모임'], D(10, 24)), false);
});

test('isDuplicateTxn: 원화 칸이 비어 있는 옛 내역은 원화로 본다', () => {
  const hist = [[D(10, 6), '신랑', '지출', '구독비', '', '삼성카드', '', 7890, '', '쿠팡']];
  assert.equal(ctx.isDuplicateTxn(hist, REC, D(10, 16)), true);
});

// ── 카드 문자 중복·취소·인식 폭 (2026-10-16) ──
const P = (t) => plain(ctx.parseCardSms(t, TODAY));

test('parseCardSms: 취소 문자도 금액·날짜·가맹점을 읽는다', () => {
  assert.deepEqual(P('[Web발신]\n삼성1234승인취소 12,000원 10/05 12:30 스타벅스'),
    { status: 'cancel', date: '2026-10-05', amount: 12000, currency: 'KRW', card: '삼성', merchant: '스타벅스' });
});

test('parseCardSms: 날짜 형식 — 2026.10.05, 26.10.05, 2026-10-05, 10월5일', () => {
  for (const d of ['2026.10.05 12:30', '26.10.05', '2026-10-05 12:30', '10월 5일', '10월5일 12:30']) {
    const p = P('신한카드 승인 12,000원 ' + d + ' 스타벅스');
    assert.equal(p.status, 'ok', d);
    assert.equal(p.date, '2026-10-05', d);
    assert.equal(p.merchant, '스타벅스', d);
  }
});

test('parseCardSms: 해외 외화 문자 — 원화 환산이 있으면 원화, 없으면 그 통화 금액', () => {
  assert.deepEqual(P('[Web발신]\n하나카드 해외승인\nUSD 22.00 10/05 12:30 ANTHROPIC'),
    { status: 'ok', date: '2026-10-05', amount: 22, currency: 'USD', card: '하나', merchant: 'ANTHROPIC' });
  assert.equal(P('하나카드 승인 $9.99 10/05 NETFLIX').currency, 'USD');
  assert.equal(P('하나카드 승인 1,500 JPY 10/05 라멘').amount, 1500);
  const both = P('삼성카드 해외승인 USD 22.00 (30,100원) 10/05 ANTHROPIC');
  assert.deepEqual([both.currency, both.amount], ['KRW', 30100]);
});

test('cardName: 인터넷은행·간편결제도 읽는다', () => {
  for (const [t, c] of [['카카오뱅크 체크카드 승인', '카카오뱅크'], ['토스뱅크 체크 승인', '토스뱅크'], ['케이뱅크 승인', '케이뱅크'],
    ['네이버페이 결제', '네이버페이'], ['비씨카드 승인', 'BC'], ['KB국민카드 승인', '국민']]) assert.equal(ctx.cardName(t), c, t);
});

const T = (m, d, amt, memo, over) => Object.assign([new Date(2026, m - 1, d), '신랑', '지출', '식비', '', '삼성카드', '', amt, 'KRW', memo], over || {});

test('takeDuplicate: 이미 있는 같은 건은 하나씩만 소모 — 같은 문자 두 번 붙여넣기와 진짜 두 건을 구분', () => {
  const pool = [T(10, 5, 4500, '스타벅스')];
  assert.equal(ctx.takeDuplicate(pool, T(10, 5, 4500, '스타벅스')), true);   // 첫 문자: 이미 들어 있음
  assert.equal(pool.length, 0);
  assert.equal(ctx.takeDuplicate(pool, T(10, 5, 4500, '스타벅스')), false);  // 둘째: 진짜 두 번째 구매
  const two = [T(10, 5, 4500, '스타벅스'), T(10, 5, 4500, '스타벅스 강남')];
  assert.equal(ctx.takeDuplicate(two, T(10, 5, 4500, '스타벅스')), true);
  assert.equal(ctx.takeDuplicate(two, T(10, 5, 4500, '스타벅스')), true);    // 다시 붙여넣은 둘 다 건너뜀
});

test('takeDuplicate: 날짜·금액·통화·메모가 다르면 다른 건, 메모가 둘 다 비면 결제수단이 같을 때만', () => {
  const base = () => [T(10, 5, 4500, '스타벅스')];
  assert.equal(ctx.takeDuplicate(base(), T(10, 6, 4500, '스타벅스')), false);
  assert.equal(ctx.takeDuplicate(base(), T(10, 5, 4600, '스타벅스')), false);
  assert.equal(ctx.takeDuplicate(base(), T(10, 5, 4500, '스타벅스', { 8: 'USD' })), false);
  assert.equal(ctx.takeDuplicate(base(), T(10, 5, 4500, '이마트')), false);
  assert.equal(ctx.takeDuplicate(base(), T(10, 5, -4500, '스타벅스')), false);  // 취소(음수)는 원 거래와 다른 건
  assert.equal(ctx.takeDuplicate([T(10, 5, 4500, '')], T(10, 5, 4500, '')), true);
  assert.equal(ctx.takeDuplicate([T(10, 5, 4500, '')], T(10, 5, 4500, '', { 5: '현대카드' })), false);
});

test('cancelTarget: 취소할 원 거래(같은 금액·통화, 가맹점 일치, 취소일 이전 중 가장 최근)를 찾는다', () => {
  const rows = [T(9, 20, 12000, '스타벅스'), T(10, 3, 12000, '스타벅스 강남'), T(10, 4, 12000, '이마트'), T(10, 9, 12000, '스타벅스')];
  const p = { date: '2026-10-05', amount: 12000, currency: 'KRW', merchant: '스타벅스' };
  assert.equal(ctx.cancelTarget(rows, p), 1);                                // 10/9는 취소일 이후라 제외
  assert.equal(ctx.cancelTarget(rows, { date: '2026-10-05', amount: 99, currency: 'KRW', merchant: '스타벅스' }), -1);
  assert.equal(ctx.cancelTarget(rows, { date: '2026-10-05', amount: 12000, currency: 'KRW', merchant: '' }), -1);
});

// ── 월 이동 (2026-10-18): 대시보드·부부 C1 드롭다운 '◀ 이전 달 / 다음 달 ▶ / 이번 달' ──
test('shiftYm: 연도 경계', () => {
  assert.equal(ctx.shiftYm(202610, -1), 202609);
  assert.equal(ctx.shiftYm(202601, -1), 202512);
  assert.equal(ctx.shiftYm(202612, 1), 202701);
});

test('ymOf: 셀 값(숫자·"2026-10" 글자·빈칸)을 YYYYMM으로', () => {
  assert.equal(ctx.ymOf(202610), 202610);
  assert.equal(ctx.ymOf('2026-10'), 202610);
  assert.equal(ctx.ymOf(''), null);
  assert.equal(ctx.ymOf(null), null);
  assert.equal(ctx.ymOf('아무거나'), null);
});

test('monthMove: 비어 있으면 이번 달에서 출발, 이번 달을 넘어가거나 데이터가 없는 달로는 가지 않는다', () => {
  assert.equal(ctx.monthMove('', '◀ 이전 달', 202610, 202509), 202609);
  assert.equal(ctx.monthMove(202609, '다음 달 ▶', 202610, 202509), '');       // 이번 달이 되면 빈칸(=이번 달 따라가기)
  assert.equal(ctx.monthMove('', '다음 달 ▶', 202610, 202509), null);          // 이번 달 다음은 없다
  assert.equal(ctx.monthMove(202509, '◀ 이전 달', 202610, 202509), null);     // 가장 오래된 데이터 달 이전은 없다
  assert.equal(ctx.monthMove(202601, '◀ 이전 달', 202610, 202509), 202512);
  assert.equal(ctx.monthMove(202607, '이번 달', 202610, 202509), '');
  assert.equal(ctx.monthMove('2026-08', '다음 달 ▶', 202610, 202509), 202609);   // 글자로 들어온 값도
  assert.equal(ctx.monthMove(202607, '이상한 값', 202610, 202509), null);
  assert.equal(ctx.monthMove('', '◀ 이전 달', 202610, null), 202609);          // 최소 달을 모르면 제한 없이
});

test('routeEdit: 대시보드·부부 C1 드롭다운만', () => {
  const ev = (o) => Object.assign({ numRows: 1, numCols: 1, sheet: '대시보드', row: 1, col: 3, value: '◀ 이전 달' }, o);
  assert.deepEqual(plain(ctx.routeEdit(ev({}))), { type: 'month', sheet: '대시보드', choice: '◀ 이전 달' });
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '부부', value: '다음 달 ▶' }))), { type: 'month', sheet: '부부', choice: '다음 달 ▶' });
  assert.equal(ctx.routeEdit(ev({ value: '◀ 월 이동 ▶' })), null);   // 안내 문구로 되돌릴 때는 무시
  assert.equal(ctx.routeEdit(ev({ sheet: '내역' })), null);
  assert.equal(ctx.routeEdit(ev({ col: 2 })), null);
});
