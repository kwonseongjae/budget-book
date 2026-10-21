/* 투자 탭 순수 로직 (node --test 대상). 기록은 06시 일일 작업 한 곳에서만 쓴다. */

var INVEST_ACCOUNT_ROWS = [7, 8, 10, 11]; // [투자] 계좌 행: 신랑 메리츠, 신랑 ISA, 신부 메리츠, 신부 ISA
var INVEST_LOG_COLS = 12;

function dayStart(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function yesterday(today) {
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
}

function isNum(x) {
  return typeof x === 'number' && !isNaN(x);
}

// pairs: 계좌 4개 [평가, 원금] → 날짜 | 4×(평가, 원금) | 합계 평가 | 합계 원금 | 빠진 계좌 수
// 평가가 숫자가 아닌 계좌는 빠진 것으로 보고 합계(평가·원금 모두)에서 뺀다.
function investLogRow(date, pairs) {
  var row = [date];
  var value = 0, principal = 0, missing = 0;
  pairs.forEach(function (p) {
    var v = isNum(p[0]) ? p[0] : '';
    var c = isNum(p[1]) ? p[1] : '';
    row.push(v, c);
    if (v === '') { missing++; return; }
    value += v;
    if (c !== '') principal += c;
  });
  return row.concat([value, principal, missing]);
}

// 투자기록 A열 값 → 이 날짜를 쓸 행 번호(1부터). 같은 날짜가 있으면 그 행(덮어쓰기), 없으면 다음 빈 행.
function dateRowIndex(colA, date) {
  var key = dayStart(date).getTime();
  for (var i = 1; i < colA.length; i++) {
    var x = colA[i][0];
    if (Object.prototype.toString.call(x) === '[object Date]' && dayStart(x).getTime() === key) return i + 1;
  }
  return nextEmptyRow(colA);
}

// 계좌 4개가 모두 빈 날(키 넣기 전 등)은 기록하지 않는다 — 0원 줄이 추이 그래프와 전일 대비를 망친다.
function shouldRecordInvest(row) {
  return row[INVEST_LOG_COLS - 1] < INVEST_ACCOUNT_ROWS.length;
}
