// Speaks each segment of a script with the local Phonon voice model (Ollama, localhost only) and
// records each clip's length, which paces the scenes.
// Usage: node voice.mjs <script.json> <voice> <out-dir>
// Writes <out-dir>/<id>.wav and <out-dir>/durations.json.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

const [SCRIPT, VOICE, OUT] = process.argv.slice(2)
const segments = JSON.parse(readFileSync(SCRIPT, 'utf8'))
mkdirSync(OUT, { recursive: true })

// The voice model speaks a segment one sentence at a time, and each sentence opens with a ~5 ms
// blip in otherwise silent audio, which the final loudness normalisation makes an audible click.
// A blip is a 5 ms window louder than BLIP with the 100 ms before it and the 50 ms after it under a
// quarter of it and under BLIP (the next sentence can start ~95 ms after); it and its neighbours
// are set to silence. Speech is never that isolated.
const RATE = 24000, WINDOW = 120, BLIP = 0.003, BEFORE = 20, AFTER = 10
function declicked(wav, id) {
  const pcm = spawnSync('ffmpeg', ['-v', 'error', '-i', 'pipe:0', '-f', 's16le', '-ac', '1', '-ar', String(RATE), 'pipe:1'],
    { input: wav, maxBuffer: 1 << 28 }).stdout
  const a = new Int16Array(pcm.buffer, pcm.byteOffset, pcm.length / 2)
  const peaks = []
  for (let i = 0; i + WINDOW <= a.length; i += WINDOW) {
    let m = 0
    for (let j = i; j < i + WINDOW; j++) m = Math.max(m, Math.abs(a[j]))
    peaks.push(m / 32768)
  }
  let found = 0
  for (let w = 0; w < peaks.length; w++) {
    if (peaks[w] <= BLIP) continue
    const around = [...peaks.slice(Math.max(0, w - BEFORE), Math.max(0, w - 1)), ...peaks.slice(w + 2, w + 2 + AFTER)]
    if (Math.max(0, ...around) >= Math.min(BLIP, peaks[w] / 4)) continue
    a.fill(0, Math.max(0, (w - 1) * WINDOW), Math.min(a.length, (w + 2) * WINDOW))
    found++
  }
  if (found) console.log(`${id}: silenced ${found} blip${found > 1 ? 's' : ''}`)
  return spawnSync('ffmpeg', ['-v', 'error', '-f', 's16le', '-ac', '1', '-ar', String(RATE), '-i', 'pipe:0', '-f', 'wav', 'pipe:1'],
    { input: Buffer.from(a.buffer, a.byteOffset, a.byteLength), maxBuffer: 1 << 28 }).stdout
}

const durations = {}
for (const s of segments) {
  const response = await fetch('http://localhost:11434/v1/audio/speech', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: 'phonon', voice: VOICE, input: s.say ?? s.caption }),
  })
  if (!response.ok) throw new Error(`${s.id}: ${response.status} ${await response.text()}`)
  const file = join(OUT, `${s.id}.wav`)
  writeFileSync(file, declicked(Buffer.from(await response.arrayBuffer()), s.id))
  const probe = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file], { encoding: 'utf8' })
  durations[s.id] = Number(probe.stdout.trim())
  console.log(`${s.id}: ${durations[s.id].toFixed(1)} s`)
}
writeFileSync(join(OUT, 'durations.json'), JSON.stringify({ voice: VOICE, durations }, null, 2))
console.log('total', Object.values(durations).reduce((a, b) => a + b, 0).toFixed(1), 's')
