/* 투자 탭 순수 로직 (node --test 대상). 기록은 06시 일일 작업 한 곳에서만 쓴다. */

var INVEST_ACCOUNT_ROWS = [7, 8, 10, 11]; // [투자] 계좌 행: 신랑 메리츠, 신랑 ISA, 신부 메리츠, 신부 ISA
var INVEST_LOG_COLS = 14;      // A 날짜 · B~I 4계좌(평가,원금) · J 합계 평가 · K 합계 원금 · L 빠진 계좌 수 · M 기타 평가 · N 기타 원금
var INVEST_LOG_MISSING = 11;   // L열(0부터 11)

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

// 4계좌가 모두 빈 날(키 넣기 전 등)은 기록하지 않는다 — 0원 줄이 추이 그래프와 전일 대비를 망친다.
// 기타(붙여넣기) 계좌만 있는 날은 기록하되, 직전 기록에는 4계좌 값이 있었다면(키 오류 등 일시 장애) 기록하지 않는다 — 합계가 기타 계좌만큼으로 급락하는 것을 막는다.
function shouldRecordInvest(row, prevRow) {
  if (row[INVEST_LOG_MISSING] < INVEST_ACCOUNT_ROWS.length) return true;
  if (!(row.length > 12 && isNum(row[12]))) return false;
  return !(prevRow && isNum(prevRow[INVEST_LOG_MISSING]) && prevRow[INVEST_LOG_MISSING] < INVEST_ACCOUNT_ROWS.length);
}

// 투자기록 값(2행부터)에서 date보다 앞선 날짜의 마지막 줄. 없으면 null.
function prevLogRow(values, date) {
  var key = dayStart(date).getTime(), found = null;
  values.forEach(function (r) {
    if (Object.prototype.toString.call(r[0]) === '[object Date]' && dayStart(r[0]).getTime() < key) found = r;
  });
  return found;
}

// 증권계좌 A5:K14 줄 → 총평가(J)가 숫자인 계좌 [{name, value, principal}] (원금 I가 숫자가 아니면 '')
function extraAccounts(rows) {
  var out = [];
  rows.forEach(function (r) {
    var name = isBlank(r[0]) ? '' : String(r[0]).trim();
    if (name && isNum(r[9])) out.push({ name: name, value: r[9], principal: isNum(r[8]) ? r[8] : '' });
  });
  return out;
}

// 4계좌 기록 줄(12열)에 기타 증권사 계좌를 더해 14열로: 합계(J·K)에 포함하고 M·N에 기타 합계를 따로 남긴다. 기타가 없으면 M·N은 빈칸.
function withExtras(row, extras) {
  var out = row.slice(0, 12);
  if (!extras.length) return out.concat(['', '']);
  var v = 0, p = 0, hasP = false;
  extras.forEach(function (e) {
    v += e.value;
    if (e.principal !== '') { p += e.principal; hasP = true; }
  });
  out[9] += v;
  out[10] += p;
  return out.concat([v, hasP ? p : '']);
}

function accountLogRows(date, extras) {
  return extras.map(function (e) { return [date, e.name, e.value, e.principal]; });
}

// 투자기록_계좌(날짜|계좌|평가|원금): date(그날)의 줄은 이름과 상관없이 전부 새 줄로 바꾸고 다른 날짜는 유지한다.
// (같은 날 다시 실행해도, 계좌 이름을 바꾸거나 계좌가 사라져도 낡은 줄이 남지 않는다.) 날짜가 아닌 줄(빈 줄)은 버린다.
function upsertAccountLog(existing, rows, date) {
  var key = dayStart(date).getTime();
  var kept = existing.filter(function (r) {
    return Object.prototype.toString.call(r[0]) === '[object Date]' && dayStart(r[0]).getTime() !== key;
  });
  return kept.concat(rows);
}
