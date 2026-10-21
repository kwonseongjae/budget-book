/* 순수 로직 — SpreadsheetApp 등 Apps Script 전역에 의존하지 않는다 (node --test 대상). */

var TXN_COLS = 10; // 내역 A:J (K:M은 수식 열)
var TXN_RATE_COL = 14; // 내역 N = 적용 환율 (외화 줄에 입력 시점 환율을 고정, 사용자가 고칠 수 있음)

// 시트 이름 → 편집된 열(1-based) → 이름을 바꿔야 할 [시트, 열] 목록
var RENAME_TARGETS = {
  '설정': {
    1: [['내역', 4], ['반복', 5], ['즐겨찾기', 4], ['자산', 6]], // A열 카테고리 (자산 F = 적립 카테고리)
    5: [['내역', 2], ['반복', 3], ['즐겨찾기', 2]]  // E열 사용자
  },
  '자산': {
    1: [['내역', 6], ['내역', 7], ['반복', 6], ['즐겨찾기', 5]] // A열 자산명
  }
};

function isBlank(x) {
  return x === '' || x === null || x === undefined;
}

// ARRAYFORMULA 열 때문에 getLastRow()/appendRow()는 시트 끝을 가리키므로 A열로 판단한다.
function nextEmptyRow(colAValues) {
  for (var i = colAValues.length - 1; i >= 1; i--) {
    if (!isBlank(colAValues[i][0])) return i + 2;
  }
  return 2;
}

function replaceExact(values, from, to) {
  var changed = 0;
  var out = values.map(function (row) {
    if (row[0] === from) {
      changed++;
      return [to];
    }
    return [row[0]];
  });
  return { values: out, changed: changed };
}

// 구분 열(1-based): 여기 값을 바꾸면 바로 오른쪽 카테고리 칸의 드롭다운을 그 구분 목록으로 바꾼다.
var TYPE_COLS = { '내역': 3, '반복': 4, '즐겨찾기': 3 };
var CAT_LIST_FIRST_COL = 7; // 계산 탭 G열부터 구분별 카테고리 목록
var CAT_LIST_COUNT = 10;

// headers: 계산 탭 1행(G~P)의 구분 이름 → 0부터 센 열 위치, 없으면 -1
function typeColumnIndex(headers, type) {
  var t = isBlank(type) ? '' : String(type).trim();
  if (!t) return -1;
  for (var i = 0; i < headers.length; i++) {
    if (String(headers[i]).trim() === t) return i;
  }
  return -1;
}

function routeEdit(ev) {
  var tc = TYPE_COLS[ev.sheet];
  if (tc && ev.row >= 2 && ev.col <= tc && tc < ev.col + ev.numCols) { // 구분 칸이 수정 범위에 포함
    return { type: 'typeset', sheet: ev.sheet, row: ev.row, numRows: ev.numRows, col: tc };
  }
  if (ev.numRows !== 1 || ev.numCols !== 1) return null;
  if (ev.sheet === '문자입력' && ev.row === 1 && ev.col === 2) {
    return ev.value === 'TRUE' ? { type: 'sms' } : null;
  }
  if (MONTH_SHEETS.indexOf(ev.sheet) !== -1 && ev.row === 1 && ev.col === 3) {  // 월 이동 드롭다운
    return MONTH_MOVES.indexOf(ev.value) !== -1 ? { type: 'month', sheet: ev.sheet, choice: ev.value } : null;
  }
  if (ev.sheet === '추이' && ev.row === 1 && ev.col === 3) {  // 연도 이동 드롭다운
    return YEAR_MOVES.indexOf(ev.value) !== -1 ? { type: 'year', choice: ev.value } : null;
  }
  if (ev.sheet === '설정' && ev.row === 12 && ev.col === 10) return ev.value === 'TRUE' ? { type: 'budget' } : null;  // 추천 예산 채우기
  if (ev.sheet === '빠른입력' && ev.row === 13 && ev.col === 2) {  // 폰 빠른 입력: 맨 아래 '추가' 체크
    return ev.value === 'TRUE' ? { type: 'quick' } : null;
  }
  if (ev.row < 2) return null;
  if (ev.sheet === '내역' && ev.col === 10) return isBlank(ev.value) ? null : { type: 'memo', row: ev.row };
  // 통화(I)를 바꾸면 새 환율로 덮어쓰고, 금액(H)을 쓰면 빈 환율만 채운다
  if (ev.sheet === '내역' && (ev.col === 8 || ev.col === 9)) return { type: 'rate', row: ev.row, overwrite: ev.col === 9 };
  if (ev.sheet === '설정' && ev.col === 2) return routeReclass(ev);
  if (ev.sheet === '즐겨찾기' && ev.col === 1) {
    return ev.value === 'TRUE' ? { type: 'favorite', row: ev.row } : null;
  }
  var targets = (RENAME_TARGETS[ev.sheet] || {})[ev.col];
  if (!targets) return null;
  var from = isBlank(ev.oldValue) ? '' : String(ev.oldValue).trim();
  var to = isBlank(ev.value) ? '' : String(ev.value).trim();
  if (!from || !to || from === to) return null; // 새 항목 추가·삭제는 과거 내역을 건드리지 않는다
  return { type: 'rename', from: from, to: to, targets: targets };
}

// 설정 B열(카테고리의 구분)을 바꾸면 그 카테고리의 내역·반복·즐겨찾기 구분도 바꾼다.
// 대상: [시트, 구분 열] — 세 시트 모두 구분 열 바로 오른쪽이 카테고리 열이다.
var RECLASS_TARGETS = [['내역', 3], ['반복', 4], ['즐겨찾기', 3]];

function routeReclass(ev) {
  var from = isBlank(ev.oldValue) ? '' : String(ev.oldValue).trim();
  var to = isBlank(ev.value) ? '' : String(ev.value).trim();
  if (!from || !to || from === to) return null;
  return { type: 'reclass', row: ev.row, from: from, to: to, targets: RECLASS_TARGETS };
}

// values: [[구분, 카테고리], ...] → 구분 열만 돌려준다.
function reclassify(values, category, from, to) {
  var changed = 0;
  var out = values.map(function (r) {
    if (r[1] === category && r[0] === from) {
      changed++;
      return [to];
    }
    return [r[0]];
  });
  return { values: out, changed: changed };
}

function ymKey(date, startDay) {
  var back = date.getDate() < startDay ? 1 : 0;
  var first = new Date(date.getFullYear(), date.getMonth() - back, 1);
  return first.getFullYear() * 100 + first.getMonth() + 1;
}

function calendarYm(date) {
  return date.getFullYear() * 100 + date.getMonth() + 1;
}

// 월 이동(대시보드·부부 C1 드롭다운). 문구는 migrate·layout과 같아야 한다(tests가 대조).
var MONTH_MOVE_HINT = '◀ 월 이동 ▶';
var MONTH_MOVES = ['◀ 이전 달', '다음 달 ▶', '이번 달'];
var MONTH_SHEETS = ['대시보드', '부부'];

function shiftYm(ym, delta) {
  var idx = Math.floor(ym / 100) * 12 + (ym % 100 - 1) + delta;
  return Math.floor(idx / 12) * 100 + idx % 12 + 1;
}

// 월 선택칸 값(숫자 202610 · 글자 '2026-10' · 빈칸) → YYYYMM, 읽을 수 없으면 null
function ymOf(v) {
  if (typeof v === 'number') return v;
  var m = String(v === null || v === undefined ? '' : v).match(/^(\d{4})-(\d{1,2})$/);
  return m ? Number(m[1]) * 100 + Number(m[2]) : null;
}

// 선택한 이동 → 새 월 칸 값: 숫자 월 / ''(비움 = 이번 달 따라가기) / null(움직이지 않음: 이번 달 다음·가장 오래된 데이터 달 이전·모르는 선택)
function monthMove(cur, choice, nowYm, minYm) {
  if (choice === '이번 달') return '';
  var base = ymOf(cur);
  if (base === null) base = nowYm;
  var to = choice === '◀ 이전 달' ? shiftYm(base, -1) : choice === '다음 달 ▶' ? shiftYm(base, 1) : null;
  if (to === null || to > nowYm || (minYm !== null && minYm !== undefined && to < minYm)) return null;
  return to === nowYm ? '' : to;
}

// 연도 이동(추이 C1 드롭다운). 문구는 migrate·layout과 같아야 한다(tests가 대조).
var YEAR_MOVE_HINT = '◀ 연도 이동 ▶';
var YEAR_MOVES = ['◀ 이전 해', '다음 해 ▶', '올해'];

// 선택한 이동 → 새 연도 칸 값: 숫자 연도 / ''(비움 = 올해 따라가기) / null(움직이지 않음: 올해 다음·데이터 있는 첫 해 이전·모르는 선택)
function yearMove(cur, choice, nowYear, minYear) {
  if (choice === '올해') return '';
  var base = Number(cur);
  if (isBlank(cur) || !(base > 0)) base = nowYear;
  var to = choice === '◀ 이전 해' ? base - 1 : choice === '다음 해 ▶' ? base + 1 : null;
  if (to === null || to > nowYear || (minYear !== null && minYear !== undefined && to < minYear)) return null;
  return to === nowYear ? '' : to;
}

function lastDayOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
}

// 칸 서식이 날짜로 바뀌면 202610 같은 숫자가 Date(시트 일련번호)로 읽힌다 → 일련번호로 되돌린다.
function ymValue(x) {
  if (Object.prototype.toString.call(x) !== '[object Date]') return Number(x);
  return Math.round((x.getTime() - Date.UTC(1899, 11, 30)) / 864e5); // 시간대 차(±12h)는 반올림으로 흡수
}

// 반복 항목은 달력 월 기준. 오늘이 (보정된) 일자 이후이고 이번 달에 아직 안 만들었으면 생성.
function isRecurringDue(day, lastYm, today) {
  if (ymValue(lastYm) === calendarYm(today)) return false;
  return today.getDate() >= Math.min(day, lastDayOfMonth(today));
}

// 통화 코드 → 환율. 외화만 (원화·빈칸·모르는 통화·환율 계산 오류는 빈칸). table = 설정 G:H 줄.
function rateFor(code, table) {
  var c = isBlank(code) ? '' : String(code).trim().toUpperCase();
  if (!c || c === 'KRW') return '';
  for (var i = 0; i < table.length; i++) {
    if (String(table[i][0]).trim().toUpperCase() === c) {
      var r = Number(table[i][1]);
      return r > 0 ? r : '';
    }
  }
  return '';
}

// 환율 고정: rows = [금액, 통화, 적용 환율](내역 H·I·N) 줄들 → 환율 칸에 쓸 {row, value}.
// 외화 줄의 빈 환율만 채운다(overwrite=true면 통화를 바꾼 줄이라 덮어쓰고, 원화로 바꾼 줄은 환율을 지운다).
function ratesToFill(rows, table, firstRow, overwrite) {
  var out = [];
  rows.forEach(function (r, i) {
    var cur = isBlank(r[1]) ? '' : String(r[1]).trim().toUpperCase();
    var has = !isBlank(r[2]);
    if (!cur || cur === 'KRW') {
      if (overwrite && has) out.push({ row: firstRow + i, value: '' });
      return;
    }
    var rate = rateFor(cur, table);
    if (rate === '' || (has && !overwrite)) return;
    out.push({ row: firstRow + i, value: rate });
  });
  return out;
}

// 빠른입력 탭 폼 → 내역 한 줄. f = {date, user, type, category, amount, currency, pay, inAsset, memo}(셀 값).
// 고치면 되는 문제는 {error}로 알려 준다(내역에 넣지 않음). 빈 날짜=오늘, 빈 구분=지출, 빈 통화=원화.
function quickTxn(f, today, table) {
  var trim = function (x) { return isBlank(x) ? '' : String(x).trim(); };
  var type = trim(f.type) || '지출';
  var user = trim(f.user);
  var category = trim(f.category);
  var amount = Number(f.amount);
  if (!user) return { error: '사용자를 골라 주세요' };
  if (isBlank(f.amount) || isNaN(amount) || amount === 0) return { error: '금액을 숫자로 적어 주세요' };
  if (type !== '이체' && !category) return { error: '카테고리를 골라 주세요' };
  if (type === '이체' && (!trim(f.pay) || !trim(f.inAsset))) return { error: '이체는 결제수단(보내는 곳)과 입금자산(받는 곳)을 모두 골라 주세요' };
  var date = Object.prototype.toString.call(f.date) === '[object Date]' ? f.date : (isBlank(f.date) ? today : null);
  if (!date) return { error: '날짜는 날짜 형식으로 적거나 비워 두세요(비우면 오늘)' };
  var cur = trim(f.currency).toUpperCase() || 'KRW';
  var rate = rateFor(cur, table);
  if (cur !== 'KRW' && rate === '') return { error: cur + ' 환율을 찾을 수 없어요([설정] 통화표를 확인하세요)' };
  return {
    txn: [date, user, type, category, '', trim(f.pay), trim(f.inAsset), amount, cur, safeText(trim(f.memo))], rate: rate,
    summary: (date.getMonth() + 1) + '/' + date.getDate() + ' ' + (category || type) + ' ' + comma(amount) + (cur === 'KRW' ? '원' : ' ' + cur) + ' (' + user + ')'
  };
}

// 카드 대금 자동 이체: [카드]에 결제일·결제 계좌가 적힌 카드마다, 결제일이 됐고 잔액이 빚(음수)이고
// 이번 달에 그 카드로 들어가는 이체가 아직 없으면 '결제 계좌 → 카드' 이체 한 줄(빚 전액). 실제 청구액과 다르면 사람이 그 줄 금액을 고친다.
// cards = [{name, owner, day, account}], balances = {카드명: 현재 잔액}, rows = 내역 A:J 줄, people = 사용자 이름들.
function cardPayments(cards, balances, rows, people, today) {
  var ym = calendarYm(today);
  var out = [];
  cards.forEach(function (c) {
    var day = Number(c.day);
    var bal = Number(balances[c.name]);
    if (!c.name || !c.account || !(day >= 1) || !(bal < 0)) return;
    if (today.getDate() < Math.min(day, lastDayOfMonth(today))) return;
    var paid = rows.some(function (r) {
      return isDateValue(r[0]) && calendarYm(r[0]) === ym && r[2] === '이체' && r[6] === c.name;
    });
    if (paid) return;
    out.push([dueDate(day, today), people.indexOf(c.owner) !== -1 ? c.owner : '공동', '이체', '', '', c.account, c.name,
      Math.round(-bal), 'KRW', '카드 대금 자동 · ' + c.name]);
  });
  return out;
}

function isDateValue(x) {
  return Object.prototype.toString.call(x) === '[object Date]';
}

// 반복 중복 방지: 이번 달 내역(rows, A:J 줄)에 같은 건이 이미 있으면 true.
// 같은 건 = 카테고리·금액·통화가 같고 메모가 서로 포함(2글자 이상). 메모 없는 내역은 판단 불가라 제외.
// 금액·카테고리만 같은 계모임 둘처럼 메모가 다르면 다른 건이다.
function isDuplicateTxn(rows, txn, today) {
  var m = normMemo(txn[9]);
  if (m.length < 2) return false;
  var cur = String(txn[8]).trim().toUpperCase();
  return rows.some(function (r) {
    if (Object.prototype.toString.call(r[0]) !== '[object Date]' || calendarYm(r[0]) !== calendarYm(today)) return false;
    var cm = normMemo(r[9]);
    var rc = isBlank(r[8]) ? 'KRW' : String(r[8]).trim().toUpperCase();
    return cm.length >= 2 && r[3] === txn[3] && Number(r[7]) === Number(txn[7]) && rc === cur
      && (cm.indexOf(m) !== -1 || m.indexOf(cm) !== -1);
  });
}

// 반복 한 줄(A:N) → 내역 줄(A:J)과 적용 환율. 통화(N)가 비면 원화.
function recurringTxn(r, table, today) {
  var cur = isBlank(r[13]) ? 'KRW' : String(r[13]).trim().toUpperCase();
  return { txn: [dueDate(Number(r[1]), today), r[2], r[3], r[4], '', r[5], '', Number(r[6]), cur, r[7]], rate: rateFor(cur, table) };
}

function dueDate(day, today) {
  return new Date(today.getFullYear(), today.getMonth(), Math.min(day, lastDayOfMonth(today)));
}

// 이번 달 일자가 이미 지난 뒤 새로 등록한 항목은 이번 달을 만들지 않고 생성 표시만 한다(수동 입력 중복 방지).
function isNewAfterDue(day, lastYm, today) {
  return isBlank(lastYm) && today.getDate() > Math.min(day, lastDayOfMonth(today));
}

// 카드사마다 문자 형식이 달라 휴리스틱으로 파싱한다. 실패한 문자는 '인식 실패'로 남겨 사람이 처리.
var CARD_RE = /KB국민|NH농협|카카오뱅크|토스뱅크|케이뱅크|네이버페이|카카오페이|국민|신한|삼성|현대|롯데|우리|하나|BC|비씨|농협|씨티|SC제일|수협|신협|우체국/;
var CARD_ALIAS = { 'KB국민': '국민', 'NH농협': '농협', '비씨': 'BC' };

function cardName(text) {
  var m = String(text).match(CARD_RE);
  if (!m) return '';
  return CARD_ALIAS[m[0]] || m[0];
}

// 카드 문자의 카드사 → [자산] 카드. 한 장뿐이면 그 카드와 소유자(사람이면 사용자로), 여러 장이면 모름.
// assets: 자산 [이름, 종류, 소유자] 줄. people: 사람 이름(공동 제외).
function matchCard(card, assets, people) {
  var hits = card ? assets.filter(function (a) { return String(a[0]).indexOf(card) !== -1; }) : [];
  if (hits.length !== 1) return { name: '', user: '공동', ambiguous: hits.length > 1 };
  var owner = String(hits[0][2] || '').trim();
  return { name: hits[0][0], user: people.indexOf(owner) !== -1 ? owner : '공동', ambiguous: false };
}

function pad2(n) {
  return (n < 10 ? '0' : '') + n;
}

function isComplete(text) {
  return /[\d,]+\s*원/.test(text) && /\d{1,2}\/\d{1,2}/.test(text);
}

function splitMessages(lines) {
  var msgs = [];
  var cur = null;
  lines.forEach(function (raw, i) {
    var line = isBlank(raw) ? '' : String(raw).trim();
    if (!line) return;
    var startsNew = /\[Web발신\]/.test(line) ||
      (cur && isComplete(cur.text) && /승인|취소|입금|출금/.test(line) && (cardName(line) || bankName(line)));
    if (!cur || startsNew) {
      cur = { startRow: i, text: '' };
      msgs.push(cur);
    }
    cur.text += (cur.text ? '\n' : '') + line;
  });
  return msgs;
}

// 폰에서 셀 편집 중 붙여넣으면 여러 문자가 한 칸에 들어간다 → 칸 안의 줄바꿈도 줄로 나눈다.
function cellsToLines(values) {
  var out = [];
  values.forEach(function (r) {
    if (isBlank(r[0])) { out.push(''); return; }
    String(r[0]).split('\n').forEach(function (s) { out.push(s); });
    out.push('');
  });
  return out;
}

function merchantAfter(body, dateMatch) {
  var rest = body.slice(dateMatch.index + dateMatch[0].length);
  var lines = rest.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  return lines.length ? lines[0] : '';
}

// 문자의 날짜: 2026.10.05 · 26-10-05 · 10월 5일 · 10/05 (뒤에 시각이 붙어도 함께 읽는다). 못 읽으면 null.
function smsDate(body, today) {
  var t = '(?:\\s+\\d{1,2}:\\d{2})?';
  var m = body.match(new RegExp('(20\\d{2}|\\d{2})[.\\-](\\d{1,2})[.\\-](\\d{1,2})' + t));
  var year = null, month, day;
  if (m) {
    year = Number(m[1]) < 100 ? 2000 + Number(m[1]) : Number(m[1]);
    month = Number(m[2]);
    day = Number(m[3]);
  } else {
    m = body.match(new RegExp('(\\d{1,2})월\\s*(\\d{1,2})일' + t)) || body.match(new RegExp('(\\d{1,2})/(\\d{1,2})' + t));
    if (!m) return null;
    month = Number(m[1]);
    day = Number(m[2]);
  }
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  if (year === null) {
    year = today.getFullYear();
    if (new Date(year, month - 1, day) > today) year -= 1; // 연말 문자를 연초에 처리
  }
  return { date: year + '-' + pad2(month) + '-' + pad2(day), index: m.index, length: m[0].length };
}

// 문자의 금액: 원화(○○원)가 있으면 원화, 없으면 외화(USD 22.00 · $9.99 · 1,500 JPY). {amount, currency} 또는 null.
function smsAmount(body) {
  var won = body.match(/([\d,]+)\s*원/);
  if (won) {
    var n = Number(won[1].replace(/,/g, ''));
    return n ? { amount: n, currency: 'KRW' } : null;
  }
  var cur = '(USD|EUR|JPY|CNY|GBP)', num = '([\\d,]+(?:\\.\\d+)?)';
  // 코드 뒤 숫자가 날짜(10/05)·시각의 일부면 금액이 아니다: JPY 10/05 → 건너뛰고 '1,500 JPY' 쪽을 읽는다
  var m = body.match(new RegExp(cur + '\\s*' + num + '(?![\\d/:월])')) || body.match(new RegExp(num + '\\s*' + cur));
  if (m) {
    var first = isNaN(Number(m[1].replace(/,/g, '')));  // 통화 코드가 앞이면 m[1]이 코드
    var amt = Number((first ? m[2] : m[1]).replace(/,/g, ''));
    return amt ? { amount: amt, currency: first ? m[1] : m[2] } : null;
  }
  var d = body.match(/\$\s*([\d,]+(?:\.\d+)?)/);
  return d && Number(d[1].replace(/,/g, '')) ? { amount: Number(d[1].replace(/,/g, '')), currency: 'USD' } : null;
}

function parseCardSms(text, today) {
  var body = text.replace(/(누적|잔액)\s*[\d,]+\s*원/g, '');
  var amt = smsAmount(body);
  var dm = smsDate(body, today);
  if (!amt || !dm) return { status: 'fail' };
  return {
    status: /취소/.test(text) ? 'cancel' : 'ok', date: dm.date, amount: amt.amount, currency: amt.currency,
    card: cardName(text), merchant: merchantAfter(body, { index: dm.index, 0: body.substr(dm.index, dm.length) })
  };
}

// 통장 입출금 문자: 입금 → 'in'(수입), 출금 → 'out'(지출). 카드사로 나가는 출금은 카드 대금이라 'cardpay'.
// 승인 문자·날짜/금액 없는 문자는 fail. 은행명은 [자산] 통장 찾기용(KB·NH·IBK 접두어는 뗀다).
var BANK_RE = /(KB국민|국민|우리|신한|하나|NH농협|농협|IBK기업|기업|카카오뱅크|토스뱅크|케이뱅크|SC제일|제일|새마을금고|새마을|우체국|수협|부산|대구|광주|전북|경남|제주)/;

function bankName(text) {
  var m = String(text).match(BANK_RE);
  return m ? m[0].replace(/^(KB|NH|IBK)/, '') : '';
}

function parseBankSms(text, today) {
  var dir = text.match(/입금|출금/);
  if (!dir || /승인/.test(text)) return { status: 'fail' };
  var body = text.replace(/(누적|잔액)\s*[\d,]+\s*원/g, '');
  var amt = smsAmount(body);
  var dm = smsDate(body, today);
  if (!amt || !dm || amt.currency !== 'KRW') return { status: 'fail' };
  var memo = body.replace(/\[[^\]]*\]/g, ' ').replace(body.substr(dm.index, dm.length), ' ').replace(/\d{1,2}:\d{2}/g, ' ')
    .replace(/입금|출금/g, ' ').replace(/[\d,]+\s*원/g, ' ').replace(/\s+/g, ' ').trim();
  var isOut = dir[0] === '출금';
  return { status: isOut && /카드/.test(text) ? 'cardpay' : (isOut ? 'out' : 'in'), date: dm.date, amount: amt.amount,
    currency: 'KRW', bank: bankName(text), memo: memo };
}

// 은행명 → [자산] 통장(이름에 포함, 카드 제외). 정확히 한 곳이면 그 통장과 소유자, 아니면 빈칸(unsure = 사용자가 골라야 함).
function matchBank(bank, assets, people) {
  var hits = bank ? assets.filter(function (a) { return String(a[0]).indexOf(bank) !== -1 && String(a[0]).indexOf('카드') === -1; }) : [];
  if (hits.length !== 1) return { name: '', user: '공동', unsure: true };
  var owner = String(hits[0][2] || '').trim();
  return { name: hits[0][0], user: people.indexOf(owner) !== -1 ? owner : '공동', unsure: false };
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function isDate(x) {
  return Object.prototype.toString.call(x) === '[object Date]';
}

// 카드 문자 중복 방지: pool(내역 A:J 줄들) 안에 같은 건이 있으면 그 줄을 하나 소모하고 true.
// 같은 건 = 같은 날·금액(부호 포함)·통화 + 메모가 서로 포함(2글자 이상) 또는 둘 다 메모 없고 결제수단이 같음.
// 한 줄은 한 번만 소모되므로 같은 문자를 다시 붙여넣으면 모두 건너뛰고, 진짜 같은 금액 두 건은 둘 다 들어간다.
function takeDuplicate(pool, txn) {
  var m = normMemo(txn[9]);
  var cur = String(txn[8]).trim().toUpperCase();
  for (var i = 0; i < pool.length; i++) {
    var r = pool[i];
    if (!isDate(r[0]) || !sameDay(r[0], txn[0]) || Number(r[7]) !== Number(txn[7])) continue;
    if ((isBlank(r[8]) ? 'KRW' : String(r[8]).trim().toUpperCase()) !== cur) continue;
    var cm = normMemo(r[9]);
    var memoMatch = cm.length >= 2 && m.length >= 2 && (cm.indexOf(m) !== -1 || m.indexOf(cm) !== -1);
    var bothBlank = !cm && !m && !isBlank(txn[5]) && r[5] === txn[5];
    if (memoMatch || bothBlank) {
      pool.splice(i, 1);
      return true;
    }
  }
  return false;
}

// 취소 문자의 원 거래: 같은 금액·통화, 가맹점이 서로 포함, 취소일 이전(당일 포함) 중 가장 최근. 없으면 -1.
function cancelTarget(rows, p) {
  var m = normMemo(p.merchant);
  if (m.length < 2) return -1;
  var parts = p.date.split('-');
  var cancelDay = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  var best = -1;
  rows.forEach(function (r, i) {
    var cm = normMemo(r[9]);
    var rc = isBlank(r[8]) ? 'KRW' : String(r[8]).trim().toUpperCase();
    if (!isDate(r[0]) || r[0] > new Date(cancelDay.getFullYear(), cancelDay.getMonth(), cancelDay.getDate(), 23, 59, 59)) return;
    if (Number(r[7]) !== p.amount || rc !== p.currency || cm.length < 2) return;
    if (cm.indexOf(m) === -1 && m.indexOf(cm) === -1) return;
    if (best === -1 || r[0] >= rows[best][0]) best = i;
  });
  return best;
}

// 내역 A:L 한 행: [날짜, 사용자, 구분, 카테고리, 소분류, 결제수단, 입금자산, 금액, 통화, 메모, 원화금액, 귀속월]
function isOutflow(type) {
  return !isBlank(type) && type !== '수입' && type !== '이체'; // 나가는 돈 = 지출 + 저축 등 새 구분
}

// {카테고리: {사용자: 원화 합계}} — 해당 귀속월의 나가는 돈
function spendByCategoryUser(rows, ym) {
  var out = {};
  rows.forEach(function (r) {
    if (!isOutflow(r[2]) || Number(r[11]) !== ym) return;
    var byUser = out[r[3]] = out[r[3]] || {};
    byUser[r[1]] = (byUser[r[1]] || 0) + (Number(r[10]) || 0);
  });
  return out;
}

var BUDGET_FIRST_COL = 10; // 설정 K열(0부터 10)부터 사용자 슬롯 순서대로 예산

// 설정 A:M 행 → 알림 대상 [{category, user, spent, budget}]. 구분이 '지출'인 카테고리, 예산 있는 사람만.
function budgetRows(settings, users, spent) {
  var out = [];
  settings.forEach(function (r) {
    if (isBlank(r[0]) || r[1] !== '지출') return;
    users.forEach(function (u, j) {
      var budget = Number(r[BUDGET_FIRST_COL + j]) || 0;
      if (!u || !(budget > 0)) return;
      out.push({ category: r[0], user: u, spent: ((spent[r[0]] || {})[u]) || 0, budget: budget });
    });
  });
  return out;
}

// 예산 추천: 이번 달 앞 3개월 중 지출이 있는 달들의 사람별·카테고리별 월평균(1만 원 단위, 최소 1만 원)을
// 설정 K:M 빈 칸에만 채울 목록으로. txns = 내역 A:M 줄(사용자 B·구분 C·카테고리 D·원화금액 K·귀속월 L), settings = 설정 A:M 줄.
// 돌려주는 값: fills [{row: settings 배열 index, col: 0부터 센 열, value}], kept = 추천값이 있지만 이미 예산이 있어 둔 칸 수, months = 평균에 쓴 달 수.
function recommendBudgets(txns, settings, users, curYm) {
  var window = [shiftYm(curYm, -1), shiftYm(curYm, -2), shiftYm(curYm, -3)];
  var seen = {}, sums = {};
  txns.forEach(function (r) {
    var ym = r[11], krw = Number(r[10]);
    if (r[2] !== '지출' || window.indexOf(ym) === -1 || !(krw > 0)) return;
    seen[ym] = true;
    var k = r[3] + '|' + r[1];
    sums[k] = (sums[k] || 0) + krw;
  });
  var months = Object.keys(seen).length;
  var out = { fills: [], kept: 0, months: months };
  if (!months) return out;
  settings.forEach(function (row, i) {
    if (isBlank(row[0]) || row[1] !== '지출') return;
    users.forEach(function (u, j) {
      var total = sums[row[0] + '|' + u];
      if (!u || !(total > 0)) return;
      var value = Math.max(10000, Math.round(total / months / 10000) * 10000);
      if (Number(row[BUDGET_FIRST_COL + j]) > 0) { out.kept++; return; }
      out.fills.push({ row: i, col: BUDGET_FIRST_COL + j, value: value });
    });
  });
  return out;
}

function newAlerts(rows, sent, ym) {
  var out = [];
  rows.forEach(function (r) {
    if (!(r.budget > 0)) return;
    var ratio = r.spent / r.budget;
    var level = ratio >= 1 ? 100 : ratio >= 0.8 ? 80 : 0;
    if (!level) return;
    var key = ym + '|' + r.category + (r.user ? '|' + r.user : '') + '|' + level;
    if (sent[key]) return;
    out.push({ category: r.category, user: r.user, level: level, spent: r.spent, budget: r.budget, key: key });
  });
  return out;
}

function comma(n) {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatAlerts(alerts) {
  return alerts.map(function (a) {
    var pct = Math.round(a.spent / a.budget * 100);
    var label = a.level === 100 ? '예산 초과' : '80% 도달';
    return a.category + (a.user ? '(' + a.user + ')' : '') + ': ' + comma(a.spent) + ' / ' + comma(a.budget) + '원 (' + pct + '%) — ' + label;
  }).join('\n');
}

// 셀에 쓸 외부 문자열(문자 가맹점 등)이 수식으로 해석되지 않게
function safeText(s) {
  var t = isBlank(s) ? '' : String(s);
  return /^[=+\-@]/.test(t) ? "'" + t : t;
}

function normMemo(s) {
  return isBlank(s) ? '' : String(s).replace(/\s+/g, ' ').trim().toLowerCase();
}

// history: [[구분, 카테고리, 메모], ...] 오래된 순. 같은 메모(없으면 서로 포함, 2글자 이상)로
// 가장 많이 쓴 {type, category}, 동률이면 최근 것. 없으면 null.
function suggestCategory(history, memo) {
  var m = normMemo(memo);
  if (!m) return null;
  return pickCategory(history, function (h) { return h === m; })
    || pickCategory(history, function (h) {
      return h.length >= 2 && m.length >= 2 && (h.indexOf(m) !== -1 || m.indexOf(h) !== -1);
    });
}

function pickCategory(history, match) {
  var count = {}, last = {}, best = null;
  history.forEach(function (r, i) {
    var h = normMemo(r[2]);
    if (!h || isBlank(r[1]) || !match(h)) return;
    var k = r[0] + '\u0000' + r[1];
    count[k] = (count[k] || 0) + 1;
    last[k] = i;
  });
  Object.keys(count).forEach(function (k) {
    if (!best || count[k] > count[best] || (count[k] === count[best] && last[k] > last[best])) best = k;
  });
  if (!best) return null;
  var parts = best.split('\u0000');
  return { type: parts[0], category: parts[1] };
}

// 공동(joint) 사용자의 나가는 돈을 반반. 결제수단 소유자가 낸 것으로 보고, 공동 소유 자산은 제외,
// 소유자를 모르는 결제수단은 unknown 건수로.
function settlement(rows, ym, owners, people, joint) {
  var paid = {};
  people.forEach(function (p) { paid[p] = 0; });
  var unknown = 0;
  rows.forEach(function (r) {
    if (r[1] !== joint || !isOutflow(r[2]) || Number(r[11]) !== ym) return;
    var o = owners[r[5]];
    if (o === joint) return;
    if (isBlank(o) || !(o in paid)) { unknown++; return; }
    paid[o] += Number(r[10]) || 0;
  });
  var diff = (paid[people[0]] - paid[people[1]]) / 2;
  return { paid: paid, unknown: unknown, from: diff > 0 ? people[1] : diff < 0 ? people[0] : '',
    to: diff > 0 ? people[0] : diff < 0 ? people[1] : '', amount: Math.abs(diff) };
}

function prevYm(ym) {
  return ym % 100 === 1 ? ym - 89 : ym - 1;
}

// 자산 A:E 행 → [순자산, 부채 외 합계, 카드·대출 합계]. E(현재 잔액)가 숫자인 행만.
function netWorthRow(assets) {
  var pos = 0, debt = 0;
  assets.forEach(function (r) {
    if (isBlank(r[0]) || typeof r[4] !== 'number') return;
    if (r[1] === '카드' || r[1] === '대출') debt += r[4]; else pos += r[4];
  });
  return [pos + debt, pos, debt];
}

// 자산기록 A열 값 → 이 월(ym)을 쓸 행 번호(1부터). 있으면 그 행, 없으면 다음 빈 행.
function ymRowIndex(colA, ym) {
  for (var i = 1; i < colA.length; i++) {
    if (ymValue(colA[i][0]) === ym) return i + 1;
  }
  return nextEmptyRow(colA);
}

function ymText(ym) {
  return Math.floor(ym / 100) + '-' + pad2(ym % 100);
}

function signed(n) {
  return (n >= 0 ? '+' : '-') + comma(Math.abs(n));
}

// 월간 결산 메일. 그 달 내역이 없으면 null.
// o = {rows, ym, users, people, joint, owners, budgets:[{category,user,budget}], net:[전월, 이번 달]}
function monthReport(o) {
  var rows = o.rows.filter(function (r) { return Number(r[11]) === o.ym; });
  if (!rows.length) return null;
  var lines = ['■ 사람별'].concat(o.users.map(function (u) { return reportUserLine(rows, u); }));
  lines.push('', '■ 지출 상위');
  topSpend(rows).forEach(function (t, i) { lines.push((i + 1) + '. ' + t[0] + ' ' + comma(t[1])); });
  var spent = spendByCategoryUser(rows, o.ym);
  var over = o.budgets.filter(function (b) { return ((spent[b.category] || {})[b.user] || 0) > b.budget; });
  lines.push('', '■ 예산 초과');
  if (!over.length) lines.push('없음');
  over.forEach(function (b) {
    lines.push(b.category + '(' + b.user + ') ' + comma(spent[b.category][b.user]) + ' / ' + comma(b.budget));
  });
  var s = settlement(rows, o.ym, o.owners, o.people, o.joint);
  lines.push('', '■ 공동 지출 정산(반반)', s.amount ? s.from + ' → ' + s.to + ' ' + comma(s.amount) + '원' : '정산할 금액 없음');
  if (s.unknown) lines.push('소유자 미지정 결제 ' + s.unknown + '건 ([자산] I열)');
  if (typeof o.net[1] === 'number') {
    lines.push('', '■ 순자산 ' + comma(o.net[1]) + '원'
      + (typeof o.net[0] === 'number' ? ' (전월 대비 ' + signed(o.net[1] - o.net[0]) + ')' : ''));
  }
  return { subject: '[가계부] ' + ymText(o.ym) + ' 결산', body: lines.join('\n') };
}

function reportUserLine(rows, user) {
  var inc = 0, exp = 0, other = 0;
  rows.forEach(function (r) {
    if (r[1] !== user) return;
    var krw = Number(r[10]) || 0;
    if (r[2] === '수입') inc += krw;
    else if (r[2] === '지출') exp += krw;
    else if (isOutflow(r[2])) other += krw;
  });
  return user + ': 수입 ' + comma(inc) + ' · 지출 ' + comma(exp) + ' · 저축·기타 ' + comma(other);
}

function topSpend(rows) {
  var sum = {};
  rows.forEach(function (r) {
    if (r[2] === '지출') sum[r[3] || '미분류'] = (sum[r[3] || '미분류'] || 0) + (Number(r[10]) || 0);
  });
  return Object.keys(sum).map(function (k) { return [k, sum[k]]; })
    .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 5);
}

// steps: [[이름, 함수]] — 하나가 실패해도 나머지를 돌린다. 실패한 '이름: 메시지' 목록을 돌려준다.
function runSteps(steps) {
  var errors = [];
  steps.forEach(function (s) {
    try { s[1](); } catch (e) { errors.push(s[0] + ': ' + String(e && e.message || e)); }
  });
  return errors;
}
