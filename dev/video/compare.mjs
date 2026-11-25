// Compares what a script says (spoken form) with a transcript of the final soundtrack: word error
// rate and the places they differ.
// Usage: node compare.mjs <script.json> <transcript.txt>
import { readFileSync } from 'node:fs'

const [SCRIPT, HEARD] = process.argv.slice(2)
const script = JSON.parse(readFileSync(SCRIPT, 'utf8')).map((s) => s.say ?? s.caption).join(' ')
const norm = (t) => t.toLowerCase().replace(/[‘’']/g, '').replace(/[^a-z0-9 ]+/g, ' ').split(/\s+/).filter(Boolean)
const a = norm(script)
const b = norm(readFileSync(HEARD, 'utf8'))
// edit distance with backtrace
const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)])
for (let j = 1; j <= b.length; j++) d[0][j] = j
for (let i = 1; i <= a.length; i++)
  for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
const diffs = []
let i = a.length, j = b.length
while (i > 0 || j > 0) {
  if (i > 0 && j > 0 && d[i][j] === d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)) {
    if (a[i - 1] !== b[j - 1]) diffs.push(`said "${a[i - 1]}" heard "${b[j - 1]}"`)
    i--; j--
  } else if (i > 0 && d[i][j] === d[i - 1][j] + 1) { diffs.push(`said "${a[i - 1]}" heard nothing`); i-- }
  else { diffs.push(`heard extra "${b[j - 1]}"`); j-- }
}
console.log(`script ${a.length} words, heard ${b.length}; word error rate ${((d[a.length][b.length] / a.length) * 100).toFixed(1)}%`)
console.log(diffs.reverse().join('\n'))
