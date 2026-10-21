// 가상 스프레드시트 (Apps Script 글루 테스트용): 시트 = 2차원 배열, getRange/getValues/setValues/setValue/clearContent.
function colNum(s) { return s.split('').reduce((n, ch) => n * 26 + ch.charCodeAt(0) - 64, 0); }

class FakeSheet {
  constructor(rows) { this.rows = rows; }   // rows[0] = 1행
  get(r, c) { const row = this.rows[r - 1]; return row && row[c - 1] !== undefined ? row[c - 1] : ''; }
  set(r, c, v) { while (this.rows.length < r) this.rows.push([]); const row = this.rows[r - 1]; while (row.length < c) row.push(''); row[c - 1] = v; }
  getMaxRows() { return 1000; }
  insertRowsAfter() {}
  getRange(a, b, c, d) {
    let r = a, col = b, nr = c, nc = d;
    if (typeof a === 'string') {
      const m = a.match(/^([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?$/);  // 'B4' 또는 'B4:B12'
      col = colNum(m[1]); r = Number(m[2]); nc = m[3] ? colNum(m[3]) - col + 1 : 1; nr = m[4] ? Number(m[4]) - r + 1 : 1;
    }
    nr = nr || 1; nc = nc || 1;
    const sh = this;
    return {
      getValue: () => sh.get(r, col),
      setNumberFormat: () => {},
      getValues: () => Array.from({ length: nr }, (_, i) => Array.from({ length: nc }, (_, j) => sh.get(r + i, col + j))),
      setValues: (vals) => vals.forEach((row, i) => row.forEach((v, j) => sh.set(r + i, col + j, v))),
      setValue: (v) => sh.set(r, col, v),
      clearContent: () => { for (let i = 0; i < nr; i++) for (let j = 0; j < nc; j++) sh.set(r + i, col + j, ''); },
    };
  }
}

module.exports = { FakeSheet };
