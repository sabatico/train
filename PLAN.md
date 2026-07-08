# "Spell Quest" — Adaptive Spelling Trainer for a Dyslexic Learner

A Flask + file-database web app that teaches spelling to a 7-year-old with dyslexia,
dysgraphia and ADHD, driven by an AI teacher-agent (DeepSeek API) with persistent memory,
a per-skill mastery model ("rose of winds"), and a gamified, distraction-free kid UI.

> Built in **one continuous phase, AI wired in from the start** (the DeepSeek key is
> connected once the UI + backend exist; until then the agent module runs mocked —
> see ADR-002). Process/decision docs live in `CLAUDE.md` + `docs/`.

---

## 1. The pedagogy first — why she spells the way she does

Everything in this app follows from understanding her errors correctly:

**"love → luv" is not a random mistake — it's a *good* error.** It proves her
phoneme–grapheme mapping works: `luv` is a phonetically perfect spelling. What she's
missing is **orthographic pattern knowledge** — the rule layer of English ("English
words never end in *v*, so we add a silent *e*"). This is teachable, rule by rule.

**"behind → dehainb" shows three classic dyslexic mechanisms at once:**
1. **b/d mirror reversal** — the brain is *correct* to treat mirror images as the same
   object (a chair is a chair from either side); literacy requires unlearning this for
   letters. It needs explicit, isolated discrimination training, never "just practice".
2. **Sequencing / working-memory overload** — the end of the word falls apart because
   holding a 6-phoneme sequence while writing exceeds her buffer. Fix: segment-then-write
   routines (say it, tap the sounds, write sound by sound), not whole-word memorization.
3. **Phonetically plausible vowel substitution** (`ai` for the /ai/ sound she hears).

**Core principles the whole system must obey (Orton-Gillingham / structured literacy):**

- **Explicit & systematic**: teach ONE pattern at a time, in a defined sequence, to
  mastery. Never "here are 10 random words".
- **Cumulative with spiral review**: mastered patterns keep reappearing forever
  (spaced repetition), because dyslexic mastery decays without review.
- **Multisensory**: hear it, say it, see it, tap/build it, type it. Every dictation
  answer routine = *say the word → segment the sounds aloud → write while naming letters
  → read it back* (Simultaneous Oral Spelling).
- **Regular words vs "heart words"**: ~85% of English is decodable by rules. The rest
  (*love, said, was, of*) have an irregular part that must be memorized "by heart" —
  the app visually marks the tricky letters with a ❤️ and treats these as a separate
  skill track. `love` is a heart word; teaching it as "sound it out" would be wrong.
- **Never let a wrong spelling linger on screen.** Dyslexic visual memory is sticky
  for errors. On a mistake: brief gentle signal → show the *correct* form large →
  have her rebuild/retype it correctly. The error itself is only stored in the log.
- **~80% success rate** is the motivational sweet spot for ADHD. The adaptive engine
  targets it: too many wins → harder; two misses in a row → step down, end on a win.
- **Short sessions**: 10–15 minutes, 8–12 items, always finish with a reward screen.
  Better daily 10 minutes than weekly 60.

---

## 2. The "Rose of Winds" — skill model

Per-skill mastery is the heart of the adaptive engine. ~14 skills in 4 strands,
each tracked 0–100 with time-decay:

**Strand A — Letters & sounds (foundation)**
1. `letter_orientation` — b/d, p/q, m/w discrimination
2. `phoneme_segmentation` — breaking a spoken word into sounds
3. `short_vowels` — CVC words (cat, bed, pig, hot, sun)
4. `blends` — st-, cr-, -mp, -nd (holding 2 consonants in sequence)

**Strand B — Patterns & rules (where "luv" gets fixed)**
5. `digraphs` — sh, ch, th, ck, wh
6. `magic_e` — silent-e long vowels (hop→hope), incl. the "no word ends in v" rule
7. `vowel_teams` — ai, ay, ee, ea, oa, igh
8. `r_controlled` — ar, or, er, ir, ur
9. `doubling_endings` — -ff/-ll/-ss, hop→hopping

**Strand C — Words (memory track)**
10. `heart_words` — irregular high-frequency words (Dolch/Fry lists)
11. `suffixes` — -s, -ed, -ing, -er

**Strand D — Composition (sequencing under load)**
12. `word_sequencing` — spelling stays intact in longer words (where *behind* broke)
13. `phrase_dictation` — 2–4 word dictated phrases
14. `sentence_writing` — capitals, spaces, end punctuation, free writing

Each skill record:

```json
{
  "id": "magic_e",
  "mastery": 42,            // 0-100, EMA-updated from results
  "last_practiced": "2026-07-06",
  "exposures": 31,
  "streak": 2,
  "introduced": true,        // gated: prerequisites must be >60 first
  "decay_per_day": 0.8       // mastery drains if unpracticed → forces spiral review
}
```

**Adaptive selection rule (deterministic core, agent can override):**
- 60% of items → the lowest-mastery *introduced* skill (the session's "focus pattern")
- 30% → spiral review of skills whose decayed mastery dropped most
- 10% → a stretch item from the next locked skill (teaser)
- Prerequisite gates: e.g. `magic_e` doesn't unlock until `short_vowels` > 60.
- Two consecutive misses → automatic step-down to an easier exercise type on the
  same word; session always ends on a success.

The parent dashboard renders this literally as a **radar/rose chart** — you'll see the
shape of her abilities and watch it grow outward evenly.

---

## 3. Exercise types (the agent's toolbox)

Each is a frontend component with a JSON contract; the backend (rule engine or agent)
just emits `{type, payload}` and the UI renders it. Ordered roughly by scaffolding
level — the engine steps down/up this ladder:

| # | Type | What it looks like | Trains | Scaffolding |
|---|------|--------------------|--------|-------------|
| 1 | `word_builder` | Word spoken + picture; letter **tiles to tap** (correct letters + 2–3 distractors) into sound boxes | segmentation, patterns | High (recognition, near-errorless — used to *introduce* a pattern) |
| 2 | `letter_boxes` | Word spoken; one **input box per letter**, phoneme groups color-joined (sh = one box pair) | segmentation, sequencing | Medium — your "per-letter inputs" |
| 3 | `missing_letters` | `l _ v e` with the pattern letters blanked | the focus pattern in isolation | Medium |
| 4 | `bd_ninja` | Quick game: letters fly by, tap only the *b*s. "Bat before ball" mnemonic card first | letter_orientation | Game (this is the ONLY timed exercise — reversals respond to speeded discrimination) |
| 5 | `word_sort` | Drag words into buckets: "magic-e 🪄" vs "no magic-e" | pattern *recognition* before production | Medium |
| 6 | `heart_word_spotlight` | Word shown, tricky letters pulse with ❤️; look → cover → type from memory | heart_words | Look-Cover-Write-Check routine |
| 7 | `echo_dictation` | TTS speaks word (replayable 🔊), single free input | full recall | Low |
| 8 | `phrase_dictation` | TTS speaks phrase, one input per word | phrase_dictation, working memory | Low |
| 9 | `sentence_scribe` | TTS or picture prompt → she types 1–2 sentences → AI reviews | sentence_writing | Lowest |
| 10 | `beat_yesterday` | Spelling-bee sprint on *mastered* words only — beat her own star record | review + her competitive streak | Game |

**Correction routine (every exercise, non-negotiable):** wrong answer → soft "almost!"
→ her attempt disappears → correct word appears large with the relevant part
highlighted → one-line kid-voice why ("*love* ends in a silent e because English words
never end in v — the e is v's bodyguard 🛡️") → she retypes it correctly → ✅ and move on.
The retype-it-right step is what writes it into memory.

---

## 4. Error classifier — turning mistakes into skill signals

A deterministic Python module (no AI needed, so it's fast and free) compares
`attempt` vs `target` letter-by-letter with alignment, and tags:

| Error tag | Example | Skill hit |
|---|---|---|
| `reversal` | dehind/behind | letter_orientation |
| `transposition` | freind/friend | word_sequencing |
| `omission` / `insertion` | behin/behind, behaind | word_sequencing, segmentation |
| `phonetic_plausible` | luv/love | the pattern skill of the target word (magic_e) |
| `vowel_substitution` | pit/pet | short_vowels or vowel_teams |
| `pattern_violation` | luvv, chik | doubling_endings, digraphs |
| `heart_word_miss` | sed/said | heart_words |

Every attempt is logged with its tags; tags drive mastery updates
(`mastery += k * (result - expected)`, EMA). This log is also the agent's raw material —
it can spot things the rules can't (e.g. "she only reverses b/d at the *start* of words").

---

## 5. Architecture

```
train/
├── app.py                      # Flask app + routes
├── engine/
│   ├── skills.py               # mastery model, decay, prerequisite gates
│   ├── selector.py             # deterministic adaptive item picker (60/30/10)
│   ├── classifier.py           # error alignment & tagging
│   ├── session.py              # session builder: warmup → teach → practice → challenge
│   └── rewards.py              # stars, streaks, levels, badge unlock logic
├── agent/
│   ├── teacher.py              # DeepSeek API calls (tool-use), graceful no-op if offline
│   ├── prompts/                # system prompt: age, profile, teaching rules
│   └── tools.py                # exercise schemas exposed to the agent as tools
├── data/                       # THE FILE DATABASE (all JSON/MD, human-readable)
│   ├── profile.json            # name, age, avatar, settings (font size, voice rate)
│   ├── skills.json             # the rose of winds — live mastery state
│   ├── word_bank/              # curated lists per pattern:
│   │   ├── short_vowels.json   #   {word, phonemes, pattern, phrase, sentence, emoji}
│   │   ├── magic_e.json
│   │   ├── heart_words.json    #   + "tricky_letters" field for the ❤️ highlight
│   │   └── ...
│   ├── sessions/2026-07-08.json  # full item-by-item log, attempts, tags, stars
│   ├── memory.md               # the agent's persistent teacher notebook
│   └── rewards.json            # stars total, level, badges, streak
├── static/  + templates/       # kid UI (vanilla JS component per exercise type)
└── PLAN.md
```

**Why file-based works well here:** one student, low write volume, and every file is
human-readable — you can open `memory.md` and read the teacher's notes, or hand-edit
a word list. Write via atomic tmp-file+rename to avoid corruption.

**The AI agent (DeepSeek API — ADR-002) sits at three points, and the app degrades gracefully
without it** (the deterministic engine can always run a session — practice is never
blocked by an outage or API cost):

1. **Session planning** (1 call/session): reads `skills.json` + `memory.md` + last
   sessions → picks focus pattern, theme, specific words, and writes the session plan.
   It uses tool-use: each exercise type is a tool schema, so its output is guaranteed
   renderable JSON.
2. **Rich feedback** (1 call per *wrong* answer, or batched): turns the classifier's
   tag into a 7-year-old-friendly explanation, referencing HER specific error and the
   rule. The deterministic engine has canned per-rule fallback lines.
3. **Sentence review + weekly notes**: for `sentence_scribe` free writing (gentle,
   praise-first review, max 2 corrections per text — never bleed red ink over
   everything), and a weekly parent summary appended to `memory.md`
   ("Reversals down 40% this week; magic-e is clicking; next: vowel teams").

**`memory.md` (agent memory) holds what the numbers can't:** "gets frustrated after
2 misses in a row — insert an easy win", "loves animal-themed words", "b/d reversals
worse when tired/evening sessions", "responded well to the 'bodyguard e' story".
The agent reads it every session and appends dated observations.

**TTS for dictation:** browser `speechSynthesis` API — free, offline, replayable,
rate-adjustable (set slightly slow). Good enough for v1; upgradeable to pre-generated
natural audio later.

---

## 6. Kid UI — design rules (dyslexia + ADHD specific)

- **One thing on screen at a time.** No sidebars, no menus, no counters flashing.
  A single big card: prompt, input, one button. ADHD design = remove, remove, remove.
- **Typography:** Lexend or OpenDyslexic, ≥28px, letter-spacing ~0.05em, line-height 1.8.
- **Cream background (#FAF6EE), near-black text** — pure white causes visual glare/
  swimming for many dyslexics. High contrast, no text over images.
- **Lowercase-first presentation** (that's what she reads/writes most; b/d confusion
  lives in lowercase).
- **Big 🔊 replay button on every audio item** — unlimited replays, never penalized.
- **No visible timers or countdowns** except inside `bd_ninja`/`beat_yesterday` games
  she chooses to enter. Timers + ADHD + a struggling skill = anxiety, not motivation.
- **Progress within session as a simple path**: 8 dots that fill with stars, so the
  end is always visible ("only 3 left!") — crucial for ADHD stamina.
- **Input forgiveness:** case-insensitive; trailing spaces ignored.

**Gamification (built for a kid who "likes to be first"):**
- ⭐ Stars per item (2 = first try, 1 = after correction — corrections still *earn*),
  session chest at the end.
- **Levels with names she climbs** (Word Sprout 🌱 → Word Wizard 🧙), level-up
  celebration screen with confetti.
- **A collection**: each mastered pattern hatches a creature/sticker for her shelf —
  mastery made visible and collectible.
- **Beat-yourself records** (`beat_yesterday`): competition against her own best, which
  is the safe version of "being first" — she can always win eventually.
- **Streak flame** for daily practice (with a "freeze" token so one missed day doesn't
  burn her out — losing a long streak is devastating for ADHD kids).
- Reward *effort and completion*, not only correctness. A hard session finished = chest.

---

## 7. The learning loop (one 10–15 min session)

```
1. WELCOME    avatar greets her by name, shows streak flame, today's "mission"
2. WARM-UP    2 easy items from mastered skills → guaranteed early stars
3. TEACH      focus-pattern card: rule shown as a tiny story + 2 examples,
              she taps through it (agent-written or canned)
4. PRACTICE   6–8 items, mixed exercise types, ladder up:
              word_builder → letter_boxes → missing_letters → echo_dictation
              (every miss → correction routine → retype right)
5. CHALLENGE  1 phrase dictation or 1 sentence (only if energy is there —
              skippable without penalty)
6. REWARD     chest opens: stars counted, progress bar to next level,
              maybe a sticker hatches; "see you tomorrow!"
── after ──   engine updates skills.json, writes session log;
              agent appends observation to memory.md
```

---

## 8. Build order (ONE phase — AI from the start)

One continuous build; the live tracker is `docs/runner.md`, the queue is
`docs/backlog-tickets.md`. The internal ordering (what gets built before what):

1. **Design first:** `DESIGN_BRIEF.md` → Claude Design mockups → token-lock
   (`tokens.css` + primitives, per `docs/sops/mockup-implementation.md`).
2. **Skeleton:** Flask app, atomic file storage, 14-skill mastery model, 60/30/10
   selector, error classifier, session builder, rewards — the deterministic core,
   heavily unit-tested.
3. **First playable:** UI shell + `word_builder`, `letter_boxes`, `echo_dictation`
   + browser TTS + curated word banks (`short_vowels`, `digraphs`, `heart_words`,
   ~120 words) + stars & session chest.
4. **The AI teacher, wired from day one:** `agent/teacher.py` against the DeepSeek
   API (mocked until the owner provides the key — `STUB:DEEPSEEK`): session planning
   via tool schemas, personalized kid-voice corrections, `memory.md` notebook.
   The deterministic engine remains the always-working fallback (ADR-002).
5. **Breadth:** remaining exercise types (`missing_letters`, `bd_ninja`, `word_sort`,
   `heart_word_spotlight`, `phrase_dictation`, `beat_yesterday`, `sentence_scribe`
   with gentle AI review), parent dashboard with the rose-of-winds radar + error log,
   weekly agent notes, richer word banks, streak/levels/collection polish.

---

## 9. Honest notes for you (the parent)

- **Typing is a legitimate and recommended accommodation for dysgraphia** — this app
  trains *orthographic knowledge* (knowing which letters), which transfers to
  handwriting. Optionally add a "paper mode": she writes on paper first, then types
  what she wrote — best of both.
- This app is a **practice multiplier, not a replacement** for structured literacy
  instruction/tutoring if she has access to it — it's the daily reps between lessons.
- Expect the rose of winds to be spiky and progress to be nonlinear — decay and
  regression are normal in dyslexia; the spiral review exists precisely for that.
- Sit with her the first weeks: your reaction to her mistakes inside the app teaches
  her whether mistakes are safe here. The app treats every error as information,
  never as failure — that framing is the most therapeutic feature of the whole plan.
