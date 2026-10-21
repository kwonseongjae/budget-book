// 업데이트일 = 매일 아침 자동 실행(dailyJob)이 마지막으로 돈 날 (2026-10-20): 단계가 실패해도 도착한 날짜는 남긴다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet } = require('./fake_sheets');

const TODAY = new Date(2026, 9, 20);

function setup(failStep) {
  const calc = new FakeSheet([['월목록', '연도목록', '현재월']]);
  const ss = { getSheetByName: (n) => (n === '계산' ? calc : null) };
  const ctx = vm.createContext({ SpreadsheetApp: { getActive: () => ss } });
  for (const f of ['logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => TODAY;
  const calls = [];
  for (const name of ['runRecurring', 'fixRates', 'payCards', 'runAlerts', 'recordNetWorth', 'sendMonthlyReport', 'recordInvest']) {
    ctx[name] = () => { calls.push(name); if (name === failStep) throw new Error(name + ' 실패'); };
  }
  return { ctx, calc, calls };
}

test('dailyJob: 모든 단계가 돈 뒤 계산!C5에 오늘 날짜를 남긴다', () => {
  const t = setup(null);
  t.ctx.dailyJob();
  assert.equal(t.calls.length, 7);
  assert.equal(JSON.stringify(t.calc.get(5, 3)), JSON.stringify(TODAY));
});

test('dailyJob: 한 단계가 실패해도 날짜는 남기고 오류는 끝에 던진다(실패 알림 메일)', () => {
  const t = setup('runAlerts');
  assert.throws(() => t.ctx.dailyJob(), /runAlerts|예산 알림/);
  assert.equal(t.calls.length, 7);                       // 나머지 단계는 계속 돈다
  assert.equal(JSON.stringify(t.calc.get(5, 3)), JSON.stringify(TODAY));
});
