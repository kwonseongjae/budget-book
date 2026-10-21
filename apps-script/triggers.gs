/* 시트 연결부 — 판단 로직은 logic.gs. 모바일에서도 동작하도록 체크박스(onEdit)와 시간 트리거만 사용. */

function onEdit(e) {
  var range = e.range;
  var action = routeEdit({
    sheet: range.getSheet().getName(), row: range.getRow(), col: range.getColumn(),
    numRows: range.getNumRows(), numCols: range.getNumColumns(),
    oldValue: e.oldValue, value: e.value
  });
  if (!action) return;
  if (action.type === 'rename') applyRename(e.source, action);
  if (action.type === 'reclass') applyReclass(e.source, action);
  if (action.type === 'typeset') refreshCategoryRules(e.source, action.sheet, action.col, action.row, action.numRows);
  if (action.type === 'favorite') addFavorite(e.source, action.row, range);
  if (action.type === 'sms') importSms(e.source, range);
  if (action.type === 'quick') addQuick(e.source, range);
  if (action.type === 'budget') fillBudgets(e.source, range);
  if (action.type === 'year') moveYear(e.source, action.choice);
  if (action.type === 'month') moveMonth(e.source, action.sheet, action.choice);
  if (action.type === 'memo') applyMemoSuggest(e.source, action.row);
  if (action.type === 'rate') applyRates(e.source, action.row, action.row, action.overwrite);
}

// 환율 고정: 내역 외화 줄의 N(적용 환율)을 입력 시점 환율로 채운다. 환율표는 설정 G:H(실시간).
function applyRates(ss, firstRow, lastRow, overwrite) {
  var sh = ss.getSheetByName('내역');
  var table = ss.getSheetByName('설정').getRange('G2:H20').getValues();
  var rows = sh.getRange(firstRow, 8, lastRow - firstRow + 1, 7).getValues()  // H:N
    .map(function (r) { return [r[0], r[1], r[6]]; });                         // 금액, 통화, 적용 환율
  ratesToFill(rows, table, firstRow, overwrite).forEach(function (f) {
    sh.getRange(f.row, TXN_RATE_COL).setValue(f.value);
  });
}

// 붙여넣기·가져오기로 들어와 환율이 비어 있는 외화 줄을 매일 한 번 채운다 (최대 하루 늦게 고정).
function fixRates(ss) {
  var sh = ss.getSheetByName('내역');
  var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
  if (last >= 2) applyRates(ss, 2, last, false);
}

// 내역 [구분, 카테고리, 메모] 이력 (C:J 중 C·D·J). skipRow(시트 행 번호)는 뺀다.
function categoryHistory(ss, skipRow) {
  var sh = ss.getSheetByName('내역');
  var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
  if (last < 2) return [];
  return sh.getRange(2, 3, last - 1, 8).getValues()
    .filter(function (r, i) { return i + 2 !== skipRow; })
    .map(function (r) { return [r[0], r[1], r[7]]; });
}

// 메모를 적었는데 카테고리가 비어 있으면 과거 내역에서 추천해 채운다. 구분이 이미 다르면 건드리지 않는다.
function applyMemoSuggest(ss, row) {
  var sh = ss.getSheetByName('내역');
  var cur = sh.getRange(row, 3, 1, 8).getValues()[0]; // C 구분 · D 카테고리 · … · J 메모
  if (!isBlank(cur[1])) return;
  var s = suggestCategory(categoryHistory(ss, row), cur[7]);
  if (!s || (!isBlank(cur[0]) && cur[0] !== s.type)) return;
  sh.getRange(row, 3, 1, 2).setValues([[s.type, s.category]]);
  refreshCategoryRules(ss, '내역', TYPE_COLS['내역'], row, 1);
}

// 자주 안 쓰는 보기 탭은 숨겨 두고 PC 메뉴로 꺼낸다 (폰 앱엔 메뉴가 없지만 폰은 내역·대시보드·투자 위주).
var TUCKED_VIEWS = ['추이', '달력', '검색', '주식_신랑', '메리츠_신랑', '주식_신부', '메리츠_신부'];

function addViewMenu_() {
  SpreadsheetApp.getUi().createMenu('가계부')
    .addItem('추이 (연간 그래프) 열기', 'openTrend')
    .addItem('달력 열기', 'openCalendar')
    .addItem('검색 열기', 'openSearch')
    .addSeparator()
    .addItem('내 주식 탭 열기', 'openMyStock')
    .addItem('내 메리츠 상세 열기', 'openMyMeritz')
    .addSeparator()
    .addItem('꺼낸 탭 다시 숨기기', 'tuckViews')
    .addToUi();
}

function showTab_(name) {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(name);
  if (!sh) return;
  sh.showSheet();
  ss.setActiveSheet(sh);
}

function openTrend() { showTab_('추이'); }
function openCalendar() { showTab_('달력'); }
function openSearch() { showTab_('검색'); }
function openMyStock() { showTab_(slot_().stock); }
function openMyMeritz() { showTab_(slot_().meritz); }

function tuckViews() {
  var ss = SpreadsheetApp.getActive();
  ss.setActiveSheet(ss.getSheetByName('대시보드'));
  TUCKED_VIEWS.forEach(function (n) {
    var sh = ss.getSheetByName(n);
    if (sh) sh.hideSheet();
  });
}

function applyRename(ss, action) {
  action.targets.forEach(function (t) {
    var sh = ss.getSheetByName(t[0]);
    var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
    if (last < 2) return;
    var rng = sh.getRange(2, t[1], last - 1, 1);
    var res = replaceExact(rng.getValues(), action.from, action.to);
    if (res.changed) rng.setValues(res.values);
  });
}

function applyReclass(ss, action) {
  var category = String(ss.getSheetByName('설정').getRange(action.row, 1).getValue()).trim();
  if (!category) return;
  action.targets.forEach(function (t) {
    var sh = ss.getSheetByName(t[0]);
    var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
    if (last < 2) return;
    var before = sh.getRange(2, t[1], last - 1, 2).getValues();
    var res = reclassify(before, category, action.from, action.to);
    if (!res.changed) return;
    sh.getRange(2, t[1], last - 1, 1).setValues(res.values);
    res.values.forEach(function (r, i) {  // 구분이 바뀐 행은 카테고리 목록도 새 구분으로
      if (r[0] !== before[i][0]) refreshCategoryRules(ss, t[0], t[1], i + 2, 1);
    });
  });
}

// 구분에 맞는 카테고리만 드롭다운에 나오게: 행마다 계산 탭의 해당 구분 목록을 가리킨다.
// 목록에 없는 구분(이체·빈 칸)은 전체 카테고리 목록.
function refreshCategoryRules(ss, sheetName, typeCol, startRow, numRows) {
  var sh = ss.getSheetByName(sheetName);
  var calc = ss.getSheetByName('계산');
  var headers = calc.getRange(1, CAT_LIST_FIRST_COL, 1, CAT_LIST_COUNT).getValues()[0];
  var all = ss.getSheetByName('설정').getRange('A2:A60');
  sh.getRange(startRow, typeCol, numRows, 1).getValues().forEach(function (r, i) {
    var idx = typeColumnIndex(headers, r[0]);
    var list = idx < 0 ? all : calc.getRange(2, CAT_LIST_FIRST_COL + idx, calc.getMaxRows() - 1, 1);
    var rule = SpreadsheetApp.newDataValidation().requireValueInRange(list, true).setAllowInvalid(true).build();
    sh.getRange(startRow + i, typeCol + 1).setDataValidation(rule);
  });
}

function todayDate() {
  var d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

// 모든 입력 경로의 유일한 내역 추가 함수. txn = TXN_COLS(10)칸 배열.
function appendTxn(ss, txn, rate) {
  var lock = LockService.getDocumentLock();
  lock.waitLock(10000);
  try {
    var sh = ss.getSheetByName('내역');
    var row = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues());
    if (row > sh.getMaxRows()) sh.insertRowsAfter(sh.getMaxRows(), 500);
    sh.getRange(row, 1, 1, TXN_COLS).setValues([txn]);
    if (rate) sh.getRange(row, TXN_RATE_COL).setValue(rate);  // 외화면 입력 시점 환율을 고정
    refreshCategoryRules(ss, '내역', TYPE_COLS['내역'], row, 1);
  } finally {
    lock.releaseLock();
  }
}

function addFavorite(ss, row, checkbox) {
  // 즐겨찾기: 추가, 사용자, 구분, 카테고리, 결제수단, 금액, 메모
  var f = ss.getSheetByName('즐겨찾기').getRange(row, 1, 1, 7).getValues()[0];
  checkbox.setValue(false);
  if (!(Number(f[5]) > 0)) {
    checkbox.setNote('금액이 없어 추가하지 않았습니다');
    return;
  }
  checkbox.clearNote();
  appendTxn(ss, [todayDate(), f[1], f[2], f[3], '', f[4], '', Number(f[5]), 'KRW', f[6]]);
}

function importSms(ss, checkbox) {
  checkbox.setValue(false);
  var sh = ss.getSheetByName('문자입력');
  var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
  if (last < 2) return;
  var lines = cellsToLines(sh.getRange(2, 1, last - 1, 1).getValues());
  var assets = ss.getSheetByName('자산').getRange('A2:I50').getValues()
    .filter(function (r) { return !isBlank(r[0]); }).map(function (r) { return [r[0], r[1], r[8]]; });
  var people = ss.getSheetByName('설정').getRange('E2:E3').getValues().map(function (r) { return String(r[0]).trim(); });
  var history = categoryHistory(ss, 0);
  var table = ss.getSheetByName('설정').getRange('G2:H20').getValues();
  var rows = allTxns(ss);          // 내역 A:J 전부 — 취소할 원 거래 찾기용 (이번에 넣는 건도 덧붙인다)
  var pool = rows.slice();         // 중복 판단용: 이미 있던 줄만, 한 줄은 한 번만 소모
  var failed = [];
  var added = 0, cancelled = 0, skipped = 0, noOrigin = 0, unsure = 0, ins = 0, outs = 0, cardPays = 0, bankUnsure = 0;
  splitMessages(lines).forEach(function (m) {
    var b = parseBankSms(m.text, todayDate());   // 통장 입출금 문자 (입금 = 수입, 출금 = 지출)
    if (b.status === 'cardpay') { cardPays++; return; }   // 카드 대금은 '카드 대금 자동 이체'가 만든다
    if (b.status === 'in' || b.status === 'out') {
      var bd = b.date.split('-');
      var bdate = new Date(Number(bd[0]), Number(bd[1]) - 1, Number(bd[2]));
      var bk = matchBank(b.bank, assets, people);
      var want = b.status === 'in' ? '수입' : '지출';
      var bs = suggestCategory(history, b.memo);
      var btxn = [bdate, bk.user, want, bs && bs.type === want ? bs.category : '', '', bk.name, '', b.amount, 'KRW', safeText(b.memo)];
      if (bk.unsure) bankUnsure++;
      if (takeDuplicate(pool, btxn)) { skipped++; return; }
      appendTxn(ss, btxn, '');
      rows.push(btxn);
      added++;
      if (b.status === 'in') ins++; else outs++;
      return;
    }
    var p = parseCardSms(m.text, todayDate());
    if (p.status === 'fail') { failed.push(m.text); return; }
    var d = p.date.split('-');
    var date = new Date(Number(d[0]), Number(d[1]) - 1, Number(d[2]));
    var c = matchCard(p.card, assets, people);  // 카드 소유자가 한 명이면 사용자 = 그 사람
    var txn;
    if (p.status === 'cancel') {  // 취소 = 원 거래의 사용자·카테고리·결제수단을 그대로 쓴 음수 지출
      var oi = cancelTarget(rows, p);
      var o = oi >= 0 ? rows[oi] : null;
      txn = [date, o ? o[1] : c.user, o ? o[2] : '지출', o ? o[3] : '', '', o ? o[5] : c.name, '', -p.amount, p.currency, safeText('취소 ' + p.merchant)];
      if (!o) noOrigin++;
    } else {
      var s = suggestCategory(history, p.merchant) || { type: '지출', category: '' };
      if (c.ambiguous) unsure++;
      txn = [date, c.user, s.type, s.category, '', c.name, '', p.amount, p.currency, safeText(p.merchant)];
    }
    if (takeDuplicate(pool, txn)) { skipped++; return; }  // 같은 문자를 또 붙여넣은 경우
    appendTxn(ss, txn, rateFor(p.currency, table));        // 외화는 입력 시점 환율도 고정
    rows.push(txn);
    if (p.status === 'cancel') cancelled++; else added++;
  });
  sh.getRange(2, 1, last - 1, 3).clearContent(); // 같은 문자를 두 번 추가하지 않도록 비운다
  if (failed.length) {
    sh.getRange(2, 1, failed.length, 3).setValues(failed.map(function (t) { return [safeText(t), '', '인식 실패']; }));
  }
  sh.getRange(1, 3).setValue(added + '건 추가' + (ins || outs ? ' / 입금 ' + ins + '·출금 ' + outs : '') + (cancelled ? ' / 취소 ' + cancelled + '건 반영' : '')
    + (skipped ? ' / 중복 ' + skipped + '건 건너뜀' : '') + ' / 실패 ' + failed.length + '건' +
    (noOrigin ? ' / 원 거래를 못 찾은 취소 ' + noOrigin + '건(카테고리를 채워주세요)' : '') +
    (cardPays ? ' / 카드 대금 ' + cardPays + '건 건너뜀(자동 이체가 처리)' : '') +
    (bankUnsure ? ' / 통장 확인 ' + bankUnsure + '건([자산]에 없거나 여러 곳 — 결제수단을 골라 주세요)' : '') +
    (unsure ? ' / 카드 확인 ' + unsure + '건(같은 카드 여러 장 — 결제수단을 골라 주세요)' : '') + ' (카테고리를 채워주세요)');
}

// 설정 J12 체크: 지난 3개월 평균으로 K:M 빈 예산 칸만 채운다 (이미 적은 예산은 그대로). 결과는 I13에.
function fillBudgets(ss, checkbox) {
  checkbox.setValue(false);
  var sh = ss.getSheetByName('설정');
  var tx = ss.getSheetByName('내역');
  var last = nextEmptyRow(tx.getRange(1, 1, tx.getMaxRows(), 1).getValues()) - 1;
  var txns = last >= 2 ? tx.getRange(2, 1, last - 1, 13).getValues() : [];
  var settings = sh.getRange('A2:M60').getValues();
  var users = sh.getRange('E2:E4').getValues().map(function (r) { return String(r[0]).trim(); });
  var cur = Number(ss.getSheetByName('계산').getRange('C2').getValue()) || calendarYm(todayDate());
  var r = recommendBudgets(txns, settings, users, cur);
  r.fills.forEach(function (f) { sh.getRange(f.row + 2, f.col + 1).setValue(f.value); });
  sh.getRange('I13').setValue(r.months
    ? r.fills.length + '칸 채움 (지난 ' + r.months + '개월 평균)' + (r.kept ? ' · 이미 있는 예산 ' + r.kept + '칸은 그대로' : '')
    : '지난 3개월 지출 내역이 없어 채울 값이 없습니다');
}

// 대시보드·부부의 월 이동: C1 드롭다운 선택대로 B1(조회 월)을 한 달씩 옮기고, C1은 안내 문구로 되돌린다.
function moveMonth(ss, sheetName, choice) {
  var sh = ss.getSheetByName(sheetName);
  var calc = ss.getSheetByName('계산');
  var now = Number(calc.getRange('C2').getValue()) || calendarYm(todayDate());     // 월 시작일을 반영한 이번 달
  var months = calc.getRange('A2:A200').getValues().map(function (r) { return r[0]; })
    .filter(function (x) { return typeof x === 'number'; });                       // 내역에 있는 달
  var to = monthMove(sh.getRange('B1').getValue(), choice, now, months.length ? Math.min.apply(null, months) : null);
  if (to === '') sh.getRange('B1').clearContent();
  else if (to !== null) sh.getRange('B1').setValue(to);
  sh.getRange('C1').setValue(MONTH_MOVE_HINT);
}

// 추이의 연도 이동: C1 드롭다운 선택대로 B1(조회 연도)을 한 해씩 옮기고, C1은 안내 문구로 되돌린다.
function moveYear(ss, choice) {
  var sh = ss.getSheetByName('추이');
  var calc = ss.getSheetByName('계산');
  var nowYear = Math.floor((Number(calc.getRange('C2').getValue()) || calendarYm(todayDate())) / 100);
  var years = calc.getRange('B2:B200').getValues().map(function (r) { return Number(r[0]); }).filter(function (x) { return x > 0; });
  var to = yearMove(sh.getRange('B1').getValue(), choice, nowYear, years.length ? Math.min.apply(null, years) : null);
  if (to === '') sh.getRange('B1').clearContent();
  else if (to !== null) sh.getRange('B1').setValue(to);
  sh.getRange('C1').setValue(YEAR_MOVE_HINT);
}

// 빠른입력 탭: B4~B12에 적은 한 건을 내역에 넣는다 (폰에서 내역 맨 아래 줄을 찾지 않고 입력).
// 성공하면 날짜·카테고리·금액·통화·입금자산·메모를 비우고 사용자·구분·결제수단은 다음 입력을 위해 남긴다.
function addQuick(ss, checkbox) {
  var sh = ss.getSheetByName('빠른입력');
  checkbox.setValue(false);
  var v = sh.getRange('B4:B12').getValues().map(function (r) { return r[0]; });
  var f = { date: v[0], user: v[1], type: v[2], category: v[3], amount: v[4], currency: v[5], pay: v[6], inAsset: v[7], memo: v[8] };
  if (isBlank(f.category) && !isBlank(f.memo) && (isBlank(f.type) || f.type === '지출')) {  // 메모로 카테고리 추천(예전 내역 기준)
    var s = suggestCategory(categoryHistory(ss, 0), f.memo);
    if (s && s.type === '지출') f.category = s.category;
  }
  var table = ss.getSheetByName('설정').getRange('G2:H20').getValues();
  var q = quickTxn(f, todayDate(), table);
  if (q.error) { sh.getRange('B14').setValue('✗ ' + q.error); return; }
  appendTxn(ss, q.txn, q.rate);
  ['B4', 'B7', 'B8', 'B9', 'B11', 'B12'].forEach(function (a1) { sh.getRange(a1).setValue(''); });
  sh.getRange('B14').setValue('✓ ' + q.summary + ' 추가');
}

// 내역 A:J 전부 (날짜는 Date). 비어 있으면 [].
function allTxns(ss) {
  var sh = ss.getSheetByName('내역');
  var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
  return last < 2 ? [] : sh.getRange(2, 1, last - 1, TXN_COLS).getValues();
}

function dailyJob() {
  var ss = SpreadsheetApp.getActive();
  // 한 단계가 실패해도(메일 한도 등) 나머지는 돌린다. 실패는 끝에 던져 트리거 실패 알림 메일로 받는다.
  var errors = runSteps([
    ['반복', function () { runRecurring(ss); }],
    ['환율 고정', function () { fixRates(ss); }],
    ['카드 대금', function () { payCards(ss); }],
    ['예산 알림', function () { runAlerts(ss); }],
    ['순자산 기록', function () { recordNetWorth(ss); }],
    ['월간 결산 메일', function () { sendMonthlyReport(ss); }],
    ['투자 기록', function () { recordInvest(ss); }]
  ]);
  stampDaily(ss);  // 각 탭 '업데이트일' = 자동 실행이 마지막으로 돈 날 (단계가 실패해도 돈 날은 남긴다)
  if (errors.length) throw new Error(errors.join(' / '));
}

function stampDaily(ss) {
  var cell = ss.getSheetByName('계산').getRange('C5');
  cell.setNumberFormat('yyyy-mm-dd');
  cell.setValue(todayDate());
}

// [카드] 탭의 카드 줄: 머리글('카드') 아래부터 '포인트·마일리지' 제목 위까지 (사용자가 줄을 줄여도 따라간다).
function readCards(sh) {
  var v = sh.getRange(1, 1, 60, 10).getValues();                    // A:J = 카드·소유자 … 결제일(I)·결제 계좌(J)
  var head = -1, end = v.length;
  for (var i = 0; i < v.length; i++) {
    if (head < 0 && String(v[i][0]).trim() === '카드') head = i;
    if (head >= 0 && String(v[i][0]).trim() === '포인트·마일리지') { end = i; break; }
  }
  if (head < 0) return [];
  return v.slice(head + 1, end).filter(function (r) { return !isBlank(r[0]); }).map(function (r) {
    return { name: String(r[0]).trim(), owner: String(r[1]).trim(), day: r[8], account: isBlank(r[9]) ? '' : String(r[9]).trim() };
  });
}

// 매일 06시: 결제일이 된 카드의 대금 이체를 넣는다. 결제일·결제 계좌를 적은 카드만(안 적으면 아무 일도 없음).
function payCards(ss) {
  var cards = readCards(ss.getSheetByName('카드'));
  if (!cards.length) return;
  var balances = {};
  ss.getSheetByName('자산').getRange('A2:E50').getValues().forEach(function (r) {
    if (!isBlank(r[0])) balances[String(r[0]).trim()] = r[4];
  });
  var people = ss.getSheetByName('설정').getRange('E2:E3').getValues().map(function (r) { return String(r[0]).trim(); });
  cardPayments(cards, balances, allTxns(ss), people, todayDate()).forEach(function (t) { appendTxn(ss, t); });
}

// 이번 달(달력 기준) 내역 줄 A:J — 반복 중복 방지에 쓴다.
function thisMonthTxns(ss, now) {
  var sh = ss.getSheetByName('내역');
  var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, TXN_COLS).getValues().filter(function (r) {
    return Object.prototype.toString.call(r[0]) === '[object Date]' && calendarYm(r[0]) === calendarYm(now);
  });
}

function runRecurring(ss) {
  var sh = ss.getSheetByName('반복');
  var rows = sh.getRange(2, 1, 49, 14).getValues();
  var table = ss.getSheetByName('설정').getRange('G2:H20').getValues();
  var now = todayDate();
  var hist = thisMonthTxns(ss, now);  // 중복 방지용: 이번 달 내역
  rows.forEach(function (r, i) {
    // 사용, 일자, 사용자, 구분, 카테고리, 결제수단, 금액, 메모, 마지막 생성 월
    if (r[0] !== true || !(Number(r[6]) > 0) || !(Number(r[1]) >= 1)) return;
    if (isNewAfterDue(Number(r[1]), r[8], now)) {
      markGenerated(sh.getRange(i + 2, 9), now);
      return;
    }
    if (!isRecurringDue(Number(r[1]), r[8], now)) return;
    var p = recurringTxn(r, table, now);  // 통화(N)가 외화면 그 통화 금액 + 생성 시점 환율
    if (isDuplicateTxn(hist, p.txn, now)) {  // 이번 달에 같은 건을 이미 적었다 → 또 넣지 않고 표시만
      markGenerated(sh.getRange(i + 2, 9), now);
      sh.getRange(i + 2, 9).setNote((now.getMonth() + 1) + '/' + now.getDate() + ' 건너뜀: 이번 달 내역에 같은 건이 이미 있어요');
      return;
    }
    appendTxn(ss, p.txn, p.rate);
    hist.push(p.txn);
    markGenerated(sh.getRange(i + 2, 9), now);
  });
}

// 서식이 날짜로 바뀌어 있어도 숫자 월(2026-10) 서식으로 되돌려 쓴다.
function markGenerated(cell, now) {
  cell.setNumberFormat('0000"-"00').setValue(calendarYm(now));
}

function runAlerts(ss) {
  var settings = ss.getSheetByName('설정');
  if (settings.getRange('J3').getValue() !== true) return;
  var ym = ymKey(todayDate(), Number(settings.getRange('J2').getValue()) || 1);
  var spent = spendByCategoryUser(txnRows(ss), ym);
  var rows = budgetRows(settings.getRange('A2:M60').getValues(), settingUsers(settings), spent);
  var state = ss.getSheetByName('알림기록');
  var sent = {};
  state.getDataRange().getValues().forEach(function (r) { if (r[0]) sent[r[0]] = true; });
  var alerts = newAlerts(rows, sent, ym);
  if (!alerts.length) return;
  MailApp.sendEmail(recipients(settings), '[가계부] 예산 알림 ' + alerts.length + '건', formatAlerts(alerts));
  state.getRange(state.getLastRow() + 1, 1, alerts.length, 2)
    .setValues(alerts.map(function (a) { return [a.key, new Date()]; }));
}

// 받는 사람: 실행자 + J4 중 이 시트를 공유받은 사람만 (편집자가 외부 주소로 내역을 내보내지 못하게)
function recipients(settings) {
  var ss = settings.getParent();
  var allowed = {};
  ss.getEditors().concat(ss.getViewers()).forEach(function (u) { allowed[u.getEmail().toLowerCase()] = true; });
  var extra = String(settings.getRange('J4').getValue()).split(',')
    .map(function (s) { return s.trim(); }).filter(function (s) { return allowed[s.toLowerCase()]; });
  return [Session.getEffectiveUser().getEmail()].concat(extra).join(',');
}

// 설정 E2:E4 = 사용자 슬롯(예산 K:M 순서와 같음)
function settingUsers(settings) {
  return settings.getRange('E2:E4').getValues().map(function (r) { return String(r[0]).trim(); });
}

function txnRows(ss) {
  var txn = ss.getSheetByName('내역');
  var last = nextEmptyRow(txn.getRange(1, 1, txn.getMaxRows(), 1).getValues()) - 1;
  return last < 2 ? [] : txn.getRange(2, 1, last - 1, 12).getValues();
}

// 자산기록: 이번 귀속월 행을 매일 덮어쓴다 → 그 달 마지막 실행 값이 월말 값.
function recordNetWorth(ss) {
  var sh = ss.getSheetByName('자산기록');
  if (!sh) return;
  var ym = ymKey(todayDate(), Number(ss.getSheetByName('설정').getRange('J2').getValue()) || 1);
  var row = ymRowIndex(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues(), ym);
  var vals = netWorthRow(ss.getSheetByName('자산').getRange('A2:E50').getValues());
  sh.getRange(row, 1).setNumberFormat('0000"-"00');
  sh.getRange(row, 1, 1, 4).setValues([[ym].concat(vals)]);
}

function netOf(ss, ym) {
  var sh = ss.getSheetByName('자산기록');
  if (!sh) return null;
  var hit = sh.getRange(2, 1, sh.getMaxRows() - 1, 2).getValues()
    .filter(function (r) { return ymValue(r[0]) === ym; });
  return hit.length && typeof hit[0][1] === 'number' ? hit[0][1] : null;
}

// 지난 귀속월 결산 메일. 보낸 기록(알림기록 report|YYYYMM)이 없고 그 달 내역이 있을 때 한 번.
function sendMonthlyReport(ss) {
  var settings = ss.getSheetByName('설정');
  var ym = prevYm(ymKey(todayDate(), Number(settings.getRange('J2').getValue()) || 1));
  var key = 'report|' + ym;
  var state = ss.getSheetByName('알림기록');
  if (state.getDataRange().getValues().some(function (r) { return r[0] === key; })) return;
  var users = settingUsers(settings);
  var owners = {};
  ss.getSheetByName('자산').getRange('A2:I50').getValues()
    .forEach(function (r) { if (!isBlank(r[0])) owners[r[0]] = String(r[8]).trim(); });
  var report = monthReport({
    rows: txnRows(ss), ym: ym, users: users, people: users.slice(0, 2), joint: users[2], owners: owners,
    budgets: budgetRows(settings.getRange('A2:M60').getValues(), users, {}), net: [netOf(ss, prevYm(ym)), netOf(ss, ym)] });
  if (!report) return;
  MailApp.sendEmail(recipients(settings), report.subject, report.body);
  state.getRange(state.getLastRow() + 1, 1, 1, 2).setValues([[key, new Date()]]);
}

// 투자기록: 06시에 전날 기준 한 줄(같은 날짜면 덮어씀). 값은 [투자] 탭 계좌 표의 최종 값(직접입력 우선).
function recordInvest(ss) {
  var tab = ss.getSheetByName('투자');
  var log = ss.getSheetByName('투자기록');
  if (!tab || !log) return;
  var vals = tab.getRange(1, 2, 12, 2).getValues(); // B1:C12 — 계좌 행의 평가·원금
  var pairs = INVEST_ACCOUNT_ROWS.map(function (r) { return vals[r - 1]; });
  var date = yesterday(todayDate());
  var row = investLogRow(date, pairs);
  if (!shouldRecordInvest(row)) return;
  var at = dateRowIndex(log.getRange(1, 1, log.getMaxRows(), 1).getValues(), date);
  if (at > log.getMaxRows()) log.insertRowsAfter(log.getMaxRows(), 365);
  log.getRange(at, 1, 1, INVEST_LOG_COLS).setValues([row]);
}

// 시트 소유자가 1회 직접 실행: 확장 프로그램 > Apps Script > setupTriggers ▶ 실행 → 권한 허용
// (메리츠 자동 갱신은 실행한 사람 권한으로 돌므로 소유자가 실행해야 함)
function setupTriggers() {
  if (!isOwner_()) throw new Error('시트 소유자만 실행할 수 있습니다');
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('dailyJob').timeBased().everyDays(1).atHour(6).create();
  setupMeritzTriggers();
}
