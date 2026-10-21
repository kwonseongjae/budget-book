/* 붙여넣은 보유종목 표 해석 (순수 로직, node --test 대상). isBlank는 logic.gs(같은 전역)의 것을 쓴다. */

var POS_ALIASES = {
  name: ['종목명', '종목', '상품명', '종목이름'],
  code: ['종목코드', '코드', '티커', '심볼'],
  qty: ['보유수량', '잔고수량', '수량', '보유량'],
  cost: ['매입금액', '매입가액', '투자원금', '매입원금', '취득금액'],
  unit: ['평균단가', '매입단가', '평단가', '매입가', '평균매입가'],
  value: ['평가금액', '평가액', '평가금'],
  price: ['현재가', '시세'],
  currency: ['통화', '통화코드']
};
var POS_SUMMARY = /합계|총계|소계|^total$/i;
var POS_WON = /\((원|원화|KRW)\)|원화/i;

// '1,234원' '+5.2%' '(1,234)' → 숫자. 못 읽으면 NaN.
function posNum(x) {
  if (typeof x === 'number') return x;
  if (x === null || x === undefined) return NaN;
  var s = String(x).trim();
  if (!s || /^[-–—]+$/.test(s)) return NaN;
  var neg = /^\(.*\)$/.test(s);
  s = s.replace(/[()원%,\s+]/g, '');
  if (!/^-?\d+(\.\d+)?$/.test(s)) return NaN;
  return neg ? -Number(s) : Number(s);
}

function posHeadKey(cell) {
  var h = String(isBlank(cell) ? '' : cell).replace(/\([^)]*\)/g, '').replace(/\s+/g, '');
  for (var k in POS_ALIASES) if (POS_ALIASES[k].indexOf(h) !== -1) return k;
  return '';
}

// 쉼표(따옴표 지원)·탭으로 나눈다. 탭이 있으면 탭 우선.
function posSplit(line) {
  if (line.indexOf('\t') !== -1) return line.split('\t');
  var out = [], cur = '', q = false;
  for (var i = 0; i < line.length; i++) {
    var c = line.charAt(i);
    if (c === '"') {
      if (q && line.charAt(i + 1) === '"') { cur += '"'; i++; } else q = !q;
    } else if (c === ',' && !q) { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

// 칸 단위 표(스프레드시트 붙여넣기) 또는 첫 열에 한 줄씩 들어온 CSV/탭 글을 같은 모양의 칸 표로.
function posRows(cells) {
  var rows = cells.map(function (r) { return r.slice(); });
  var oneCol = rows.every(function (r) { return r.slice(1).every(isBlank); });
  var hasSep = rows.some(function (r) { return typeof r[0] === 'string' && /[\t,]/.test(r[0]); });
  return oneCol && hasSep ? rows.map(function (r) { return isBlank(r[0]) ? [] : posSplit(String(r[0])); }) : rows;
}

// cells: 붙여넣기 칸 값(2차원). 돌려주는 값: {error} 또는 {positions:[{code,name,qty,cost,value,currency}], failed:[줄 글자]}
function parsePositions(cells) {
  var rows = posRows(cells);
  var head = -1, idx = {};
  for (var i = 0; i < Math.min(rows.length, 8) && head < 0; i++) {
    var m = {};
    rows[i].forEach(function (c, j) {
      var k = posHeadKey(c);
      if (!k) return;
      if (m[k] === undefined || (POS_WON.test(String(c)) && !POS_WON.test(String(rows[i][m[k]])))) m[k] = j;  // 같은 항목 열이 둘이면 (원)·원화 열
    });
    if (m.name !== undefined && (m.value !== undefined || m.cost !== undefined ||
        (m.qty !== undefined && (m.price !== undefined || m.unit !== undefined)))) {
      head = i; idx = m;
    }
  }
  if (head < 0) return { error: '머리글(종목명·평가금액 등)을 찾지 못했습니다. 표의 첫 줄(머리글)부터 붙여넣어 주세요.' };
  var positions = [], failed = [];
  rows.slice(head + 1).forEach(function (r) {
    var cell = function (k) { return idx[k] === undefined ? '' : r[idx[k]]; };
    var text = r.filter(function (c) { return !isBlank(c); }).join(' ');
    if (!text) return;
    var name = isBlank(cell('name')) ? '' : String(cell('name')).trim();
    if (!name) { failed.push(text); return; }
    if (POS_SUMMARY.test(name)) return;
    var qty = posNum(cell('qty'));
    var value = posNum(cell('value'));
    if (isNaN(value) && !isNaN(qty)) value = qty * posNum(cell('price'));
    var cost = posNum(cell('cost'));
    if (isNaN(cost) && !isNaN(qty)) cost = qty * posNum(cell('unit'));
    if (isNaN(value)) { failed.push(text); return; }
    var cur = isBlank(cell('currency')) ? 'KRW' : String(cell('currency')).trim().toUpperCase();
    if (cur !== 'KRW' && cur !== '원') { failed.push(text); return; }  // 금액은 원화로만 합산한다 (외화가 원화로 더해지지 않게)
    cur = 'KRW';
    positions.push({ code: isBlank(cell('code')) ? '' : String(cell('code')).trim(), name: name,
      qty: isNaN(qty) ? '' : qty, cost: isNaN(cost) ? '' : cost, value: value, currency: cur });
  });
  return { positions: positions, failed: failed };
}

// 증권종목 정규 표(계좌|코드|종목명|수량|매입금액|평가금액|통화)에서 그 계좌 줄을 새 줄로 바꾼다. 다른 계좌 줄은 그대로, 빈 줄은 버린다.
function replaceAccountRows(table, account, positions) {
  var kept = table.filter(function (r) { return !isBlank(r[0]) && String(r[0]).trim() !== String(account).trim(); });
  return kept.concat(positions.map(function (p) { return [account, p.code, p.name, p.qty, p.cost, p.value, p.currency]; }));
}

// 같은 계좌의 같은 종목(코드가 같거나 이름이 같음)은 새 값으로 갱신하고, 없는 종목은 줄을 더한다. 붙여넣지 않은 종목은 그대로 둔다.
function mergeAccountRows(table, account, positions) {
  var acct = String(account).trim();
  var rows = table.filter(function (r) { return !isBlank(r[0]); }).map(function (r) { return r.slice(); });
  var norm = function (x) { return String(isBlank(x) ? '' : x).trim().toLowerCase(); };
  positions.forEach(function (p) {
    var at = -1;
    for (var i = 0; i < rows.length && at < 0; i++) {
      var r = rows[i];
      if (String(r[0]).trim() !== acct) continue;
      if ((norm(p.code) && norm(p.code) === norm(r[1])) || norm(p.name) === norm(r[2])) at = i;
    }
    if (at >= 0) rows[at] = [acct, p.code || rows[at][1], p.name, p.qty, p.cost, p.value, p.currency];
    else rows.push([acct, p.code, p.name, p.qty, p.cost, p.value, p.currency]);
  });
  return rows;
}

function renameAccountRows(table, from, to) {
  return table.map(function (r) { return String(r[0]).trim() === String(from).trim() ? [to].concat(r.slice(1)) : r; });
}

// 계좌 이름 → 탭 이름('계좌_' + 이름)이 되므로 시트 탭에 쓸 수 없는 문자와 길이를 막는다. 정상이면 ''.
// 금지 문자는 broker_accounts.py의 입력 검사와 같아야 한다: [ ] * ? : / \
function validAccountName(name) {
  var n = isBlank(name) ? '' : String(name).trim();
  if (!n) return '계좌 이름을 적어 주세요.';
  if (n.length > 90) return '계좌 이름은 90자 이하로 적어 주세요.';
  if (/[\[\]*?:\/\\]/.test(n)) return '계좌 이름에 사용할 수 없는 문자가 있습니다: [ ] * ? : / \\';
  return '';
}
