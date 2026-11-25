// Puts the rendered frames, the narration clips and the captions together into one MP4.
// Usage: node assemble.mjs <script.json> <title> <frames-dir> <timeline.json> <audio-dir> <out-base>
// Writes <out-base>.mp4 (captions burned in, chapters), <out-base>.srt and <out-base>-chapters.txt.
import { readFileSync, writeFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { join, resolve } from 'node:path'

const [SCRIPT, TITLE, FRAMES, TIMELINE, AUDIO, OUT] = process.argv.slice(2)
const segments = JSON.parse(readFileSync(SCRIPT, 'utf8'))
const timeline = JSON.parse(readFileSync(TIMELINE, 'utf8'))
const { durations } = JSON.parse(readFileSync(join(AUDIO, 'durations.json'), 'utf8'))
const byId = Object.fromEntries(segments.map((s) => [s.id, s]))
const FPS = 30
const LEAD = 0.25 // the narration starts a moment after its scene does
const end = timeline.at(-1).end

function run(args) {
  const r = spawnSync('ffmpeg', ['-v', 'error', '-y', ...args], { encoding: 'utf8', maxBuffer: 1 << 26 })
  if (r.status !== 0) throw new Error(r.stderr)
}

// ---- captions: each segment split into short lines, timed by their share of its characters ----
function chunks(text) {
  // a sentence ends only where the mark is followed by a space, so "6.2" stays whole
  const parts = text.split(/(?<=[.;!?])\s+/).map((s) => s.trim()).filter(Boolean)
  const out = []
  for (const p of parts) {
    if (p.length <= 95) out.push(p)
    else {
      // a long sentence is split at the comma or colon nearest its middle
      const breaks = [...p.matchAll(/[,:] /g)].map((m) => m.index)
      const mid = p.length / 2
      const at = breaks.sort((a, b) => Math.abs(a - mid) - Math.abs(b - mid))[0]
      if (at === undefined) out.push(p)
      else out.push(p.slice(0, at + 1), p.slice(at + 2))
    }
  }
  return out
}
const stamp = (t) => {
  const ms = Math.round(t * 1000)
  const h = String(Math.floor(ms / 3600000)).padStart(2, '0')
  const m = String(Math.floor((ms % 3600000) / 60000)).padStart(2, '0')
  const s = String(Math.floor((ms % 60000) / 1000)).padStart(2, '0')
  return `${h}:${m}:${s},${String(ms % 1000).padStart(3, '0')}`
}
const srt = []
for (const t of timeline) {
  const lines = chunks(byId[t.id].caption)
  const total = lines.reduce((a, l) => a + l.length, 0)
  let at = t.start + LEAD
  for (const line of lines) {
    const length = (durations[t.id] * line.length) / total
    srt.push(`${srt.length + 1}\n${stamp(at)} --> ${stamp(at + length - 0.001)}\n${line}\n`)
    at += length
  }
}
writeFileSync(`${OUT}.srt`, srt.join('\n'))

// ---- chapters ----
const chapters = timeline.filter((t) => byId[t.id].chapter).map((t) => ({ title: byId[t.id].chapter, start: t.start }))
const meta = [';FFMETADATA1', `title=${TITLE}`]
chapters.forEach((c, i) => {
  const until = i + 1 < chapters.length ? chapters[i + 1].start : end
  meta.push('[CHAPTER]', 'TIMEBASE=1/1000', `START=${Math.round(c.start * 1000)}`, `END=${Math.round(until * 1000)}`, `title=${c.title}`)
})
writeFileSync(`${OUT}-meta.txt`, meta.join('\n') + '\n')
const mmss = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`
writeFileSync(`${OUT}-chapters.txt`, chapters.map((c) => `${mmss(c.start)} ${c.title}`).join('\n') + '\n')

// ---- narration track: every clip at its scene's start, its edges faded to silence ----
const inputs = []
const filters = []
timeline.forEach((t, i) => {
  inputs.push('-i', join(AUDIO, `${t.id}.wav`))
  filters.push(`[${i}:a]aresample=48000,afade=t=in:d=0.01,afade=t=out:st=${(durations[t.id] - 0.02).toFixed(3)}:d=0.02,` +
    `adelay=${Math.round((t.start + LEAD) * 1000)}:all=1[a${i}]`)
})
filters.push(`${timeline.map((_, i) => `[a${i}]`).join('')}amix=inputs=${timeline.length}:normalize=0:dropout_transition=0,apad=whole_dur=${end},loudnorm=I=-16:TP=-1.5:LRA=11[out]`)
run([...inputs, '-filter_complex', filters.join(';'), '-map', '[out]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', `${OUT}-narration.wav`])

// ---- picture with captions burned in, joined with the narration and chapters ----
const style = 'FontName=Helvetica Neue,FontSize=12,PrimaryColour=&H00FFFFFF,BackColour=&H66221B17,BorderStyle=4,Outline=0,Shadow=0,MarginV=20,MarginL=40,MarginR=40'
const srtPath = `${resolve(OUT)}.srt`.replace(/\\/g, '/').replace(/:/g, '\\:').replace(/'/g, "\\'")
run([
  '-framerate', String(FPS), '-i', join(FRAMES, '%06d.jpg'), '-i', `${OUT}-narration.wav`, '-i', `${OUT}-meta.txt`,
  '-map_metadata', '2', '-map_chapters', '2',
  '-filter_complex', `[0:v]format=yuv420p,subtitles='${srtPath}':force_style='${style}'[v]`,
  '-map', '[v]', '-map', '1:a', '-t', String(end),
  '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart',
  `${OUT}.mp4`,
])
console.log('wrote', `${OUT}.mp4`, `(${mmss(end)})`, `${srt.length} captions`, `${chapters.length} chapters`)
