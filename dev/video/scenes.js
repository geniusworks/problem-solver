// The scene engine shared by the Problem Solver video pages (intro.html, overview.html). Each page
// defines its sections and a global `scenes` object: one draw function per script segment,
// (t seconds into the segment, seg). record.mjs calls setup(timeline) once, then render(t) per frame.
const LEAD = 0.25 // the narration starts this long after its scene (assemble.mjs)
const FADE = 0.7 // the old scene fades out over the first half, the new one in over the second
let T = []
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x))
const ease = (x) => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2 }
// 0 → 1 over `len` seconds from `at`
const prog = (t, at, len = 0.6) => ease((t - at) / len)
const $ = (id) => document.getElementById(id)
function show(el, p, dy = 24) { el.style.opacity = p; el.style.transform = `translateY(${(1 - p) * dy}px)` }
// seconds into the segment at which the narration says `phrase`
function cue(seg, phrase) {
  const at = seg.say.toLowerCase().indexOf(phrase.toLowerCase())
  if (at < 0) throw new Error(`${seg.id}: the narration does not say "${phrase}"`)
  return LEAD + (at / seg.say.length) * seg.spoken
}


function setup(data) {
  T = data
  return T.filter((s) => !scenes[s.id]).map((s) => s.id)
}

function draw(seg, t, opacity, z) {
  const el = $(seg.id)
  el.style.opacity = opacity
  el.style.zIndex = z
  scenes[seg.id](t, seg)
}

function render(time) {
  const k = Math.max(0, T.findIndex((s) => time < s.end) === -1 ? T.length - 1 : T.findIndex((s) => time < s.end))
  for (const s of T) $(s.id).style.opacity = 0
  const seg = T[k]
  const local = time - seg.start
  if (k > 0 && local < FADE / 2) {
    const prev = T[k - 1]
    draw(prev, prev.end - prev.start, 1 - ease(local / (FADE / 2)), 1)
  }
  draw(seg, local, k === 0 ? 1 : ease((local - FADE / 2) / (FADE / 2)), 2)
  return true
}
