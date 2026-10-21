// 메리츠·한투 자동 갱신 트리거: 두 PC가 같은 시각대(07:00~07:15·16:00~16:15)에 돌게 nearMinute(0) (2026-10-20)
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('setupMeritzTriggers: 07시·16시 트리거를 nearMinute(0)로 만든다', () => {
  const made = [];
  const builder = (fn) => {
    const rec = { fn, hour: null, minute: null, daily: false };
    const api = {
      timeBased: () => api, everyDays: () => { rec.daily = true; return api; },
      atHour: (h) => { rec.hour = h; return api; }, nearMinute: (m) => { rec.minute = m; return api; },
      forSpreadsheet: () => api, onEdit: () => api, create: () => { made.push(rec); return rec; },
    };
    return api;
  };
  const ctx = vm.createContext({
    ScriptApp: { getProjectTriggers: () => [], deleteTrigger() {}, newTrigger: builder },
    SpreadsheetApp: { getActive: () => ({}), getUi: () => ({ alert() {} }) },
  });
  for (const f of ['logic.gs', 'meritz_logic.gs', 'meritz.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.slot_ = () => ({ stock: '주식_신랑' });
  ctx.setupMeritzTriggers();
  const timed = made.filter((t) => t.fn === 'refreshMeritz');
  assert.deepEqual(timed.map((t) => [t.hour, t.minute]), [[7, 0], [16, 0]]);
});
