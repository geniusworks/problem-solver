// Renders a script's scenes (scenes.html) to frames in headless Chrome, one screenshot per frame.
// The page draws each frame from a time value rather than playing animations, so the picture is
// exact and the same on every run. Talks to Chrome over its DevTools protocol with Node's own
// WebSocket, so nothing needs installing.
// Usage: node record.mjs <script.json> <durations.json> <frames-dir> <timeline.json>
// Writes <frames-dir>/NNNNNN.jpg (30 per second) and <timeline.json> ([{id, start, end}]).
import { readFileSync, writeFileSync, mkdirSync, mkdtempSync, rmSync, existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const [SCRIPT, DURATIONS, OUT, TIMELINE] = process.argv.slice(2)
const here = dirname(fileURLToPath(import.meta.url))
const segments = JSON.parse(readFileSync(SCRIPT, 'utf8'))
const { durations } = JSON.parse(readFileSync(DURATIONS, 'utf8'))
const FPS = 30
const GAP = 0.8 // a pause after each segment's narration
const TAIL = 2.5 // the last scene holds after the narration ends
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// ---- the timeline: each segment lasts its narration plus a pause ----
let at = 0
const timeline = segments.map((s, i) => {
  const length = durations[s.id] + (i + 1 === segments.length ? TAIL : GAP)
  const t = { id: s.id, start: at, end: at + length, spoken: durations[s.id] }
  at += length
  return t
})
writeFileSync(TIMELINE, JSON.stringify(timeline, null, 2))

// ---- Chrome ----
const profile = mkdtempSync(join(tmpdir(), 'problem-solver-video-'))
const chrome = spawn(CHROME, [
  '--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--hide-scrollbars',
  '--force-color-profile=srgb', '--no-first-run', '--no-default-browser-check', 'about:blank',
], { stdio: 'ignore' })
// Chrome is stopped and its profile removed once it has exited (it writes to the profile until then).
let stopped = false
async function stop() {
  if (stopped) return
  stopped = true
  const exited = new Promise((resolve) => chrome.once('exit', resolve))
  chrome.kill()
  await exited
  rmSync(profile, { recursive: true, force: true, maxRetries: 5 })
}
process.on('exit', () => { if (!stopped) chrome.kill() })

let port
for (let i = 0; i < 100 && !port; i++) {
  const file = join(profile, 'DevToolsActivePort')
  if (existsSync(file)) port = readFileSync(file, 'utf8').split('\n')[0]
  else await sleep(100)
}
if (!port) throw new Error('Chrome did not start')
const target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page')
const socket = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
let nextId = 0
const pending = new Map()
const errors = []
socket.onmessage = (event) => {
  const message = JSON.parse(event.data)
  if (message.id !== undefined) {
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    message.error ? reject(new Error(message.error.message)) : resolve(message.result)
  } else if (message.method === 'Runtime.exceptionThrown') {
    errors.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text)
  }
}
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const id = ++nextId
  pending.set(id, { resolve, reject })
  socket.send(JSON.stringify({ id, method, params }))
})
async function evaluate(expression) {
  const { result, exceptionDetails } = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (exceptionDetails) throw new Error(exceptionDetails.exception?.description ?? exceptionDetails.text)
  return result.value
}

await send('Runtime.enable')
await send('Page.enable')
await send('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false })
await send('Page.navigate', { url: pathToFileURL(join(here, 'scenes.html')).href })
for (let i = 0; i < 100; i++) {
  if (await evaluate('document.readyState === "complete" && typeof window.setup === "function"')) break
  await sleep(100)
}
await evaluate('document.fonts.ready.then(() => true)')
const data = timeline.map((t) => ({ ...t, say: (segments.find((s) => s.id === t.id).say ?? segments.find((s) => s.id === t.id).caption) }))
const missing = await evaluate(`setup(${JSON.stringify(data)})`)
if (missing.length) throw new Error(`scenes.html has no scene for: ${missing.join(', ')}`)

// ---- frames ----
rmSync(OUT, { recursive: true, force: true })
mkdirSync(OUT, { recursive: true })
// STILLS="idea@0.9,finding@1" renders only those moments (a share of each segment) as PNGs, for
// checking the layout without rendering every frame.
if (process.env.STILLS) {
  for (const spec of process.env.STILLS.split(',')) {
    const [id, share] = spec.split('@')
    const t = timeline.find((s) => s.id === id)
    if (!t) throw new Error(`no segment ${id}`)
    await evaluate(`render(${t.start + Number(share) * (t.end - t.start - 0.001)})`)
    const { data: png } = await send('Page.captureScreenshot', { format: 'png' })
    writeFileSync(join(OUT, `${id}@${share}.png`), Buffer.from(png, 'base64'))
  }
  if (errors.length) throw new Error(`errors in the page:\n${errors.join('\n')}`)
  socket.close()
  await stop()
  process.exit(0)
}
const total = Math.ceil(at * FPS)
const started = Date.now()
for (let n = 0; n < total; n++) {
  await evaluate(`render(${n / FPS})`)
  const { data: jpeg } = await send('Page.captureScreenshot', { format: 'jpeg', quality: 92 })
  writeFileSync(join(OUT, `${String(n).padStart(6, '0')}.jpg`), Buffer.from(jpeg, 'base64'))
  if (n % (FPS * 10) === 0) process.stdout.write(`\r${(n / FPS).toFixed(0)} of ${at.toFixed(0)} s`)
}
process.stdout.write(`\r${total} frames, ${at.toFixed(1)} s of video, in ${((Date.now() - started) / 1000).toFixed(0)} s\n`)
if (errors.length) throw new Error(`errors in the page:\n${errors.join('\n')}`)
socket.close()
await stop()
process.exit(0)
