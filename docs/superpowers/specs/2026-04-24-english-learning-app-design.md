# English Learning App for Chinese/Vietnamese Learners

## Overview

A complete web application for learning English, targeting Chinese and Vietnamese speakers. The app presents English sentences with rich annotations (IPA phonetics, part-of-speech tags, sentence structure analysis, native language translations) and provides typing/dictation practice with submit-then-check feedback and diff highlighting.

Inspired by Chinese English learning apps like 每日英语听力 and 扇贝听力.

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Backend | Python FastAPI | NLP capabilities, clean REST API, async support |
| Database | SQLite | Zero config, single file, sufficient for single-user/small-group use |
| Frontend | Vanilla JS + CSS | No framework dependency, fast, lightweight |
| TTS | Web Speech API | Free, built-in, word-by-word highlighting via boundary events |
| NLP (authoring) | eng-to-ipa, spaCy, Claude/GPT | Pre-compute IPA, POS, sentence structure at content creation time |
| NLP (runtime) | compromise.js (345KB) | Client-side POS tagging for user-submitted text |
| Auth | Session-based (cookie) | Simple username + password, bcrypt hashing |

## Pages

### 1. Landing/Login Page
- Bilingual welcome: "English Learning / 英语学习 / Hoc tieng Anh"
- Language selector toggle (中文 / Tieng Viet) at top right
- Login form + "Create Account" tab
- Motivational tagline and brief feature overview

### 2. Dashboard Page
- Top bar: user avatar, streak flame + day count, XP total, settings gear
- Progress card: today's goal (e.g., "5 sentences"), circular progress ring
- Lesson grid: cards with lesson number, title (in selected language), difficulty badge (A1/A2/B1...), completion percentage bar
- Quick review button: jump to spaced repetition queue
- Filter by: difficulty level, category (daily conversation, travel, business, etc.)

### 3. Lesson View Page (Core)

The main learning interface with 3 learning modes accessible via tabs.

**Layout:**
- Header: back arrow, lesson title + sentence counter (e.g., "Lesson 126 (2/16)"), play controls
- Annotation area: IPA phonetics above each word, POS color badges, main sentence in large font, constituent bracket groupings with structure labels below, native translation
- Audio controls: timer, repeat button, speed selector (0.5x-2.0x)
- Mode tabs: Learn / Read Aloud / Dictation
- Mode-specific content area
- Sentence navigation: prev/next arrows, sentence counter

**Learning Modes:**

1. **Learn (学习/Hoc):** Full annotations visible, TTS plays automatically, user studies the sentence structure. No input required.

2. **Read Aloud (朗读/Doc):** Annotations visible, TTS plays, user self-rates pronunciation (Good/Okay/Again). Self-assessment drives spaced repetition scheduling.

3. **Dictation (听写/Nghe viet):** Annotations HIDDEN, TTS plays audio only, user types what they heard. On submit: score displayed, annotations revealed, diff highlighting shows correct/incorrect/missing words.

### 4. Vocabulary Page
- Searchable word list from all encountered words
- Each entry: word, IPA, POS badge, example sentence, translation
- Filter by: mastered / learning / weak
- Flashcard mode: show word, user recalls meaning, flip to reveal

### 5. Settings Page
- UI language: 中文 / Tieng Viet
- TTS voice selector + speed slider (0.5x-2.0x)
- Daily goal (sentences per day)
- Difficulty preference (A1-C2)
- Reset progress option

## Data Model

### Database Schema

**users:**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| username | TEXT UNIQUE | Login name |
| password_hash | TEXT | bcrypt hash |
| ui_language | TEXT | "zh" or "vi" |
| daily_goal | INTEGER | Sentences per day, default 5 |
| tts_speed | REAL | 0.5-2.0, default 1.0 |
| created_at | TIMESTAMP | Registration time |

**lessons:**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Lesson number |
| title | TEXT | English title |
| title_zh | TEXT | Chinese title |
| title_vi | TEXT | Vietnamese title |
| difficulty | TEXT | CEFR level (A1-C2) |
| category | TEXT | Topic category |
| sentence_count | INTEGER | Total sentences in lesson |

**sentences:**
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PK | Format: "126-02" |
| lesson_id | INTEGER FK | References lessons.id |
| index | INTEGER | Position in lesson (1-based) |
| text | TEXT | English sentence |
| translation_zh | TEXT | Chinese translation |
| translation_vi | TEXT | Vietnamese translation |
| words_json | TEXT | JSON array of word annotations |
| constituents_json | TEXT | JSON array of constituent groups |

**user_progress:**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | References users.id |
| sentence_id | TEXT FK | References sentences.id |
| mode | TEXT | "learn", "read_aloud", "dictation" |
| score | REAL | 0.0-1.0 |
| attempts | INTEGER | Total attempts |
| last_attempt | TIMESTAMP | Last practice time |
| next_review | TIMESTAMP | Spaced repetition next date |
| leitner_bucket | INTEGER | 1-5, drives review intervals |

**vocabulary:**
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | References users.id |
| word | TEXT | English word |
| ipa | TEXT | IPA transcription |
| pos | TEXT | Part of speech |
| seen_count | INTEGER | Times encountered |
| correct_count | INTEGER | Times correct in dictation |
| next_review | TIMESTAMP | Spaced repetition next date |

### Word Annotation JSON Structure

```json
{
  "word": "immediately",
  "ipa": "/ɪˌmiːdi.ətli/",
  "pos": "adverb",
  "pos_zh": "副词",
  "pos_vi": "trang tu",
  "role": "time_adverbial",
  "role_zh": "时间状语",
  "role_vi": "trang ngu thoi gian",
  "group": 3,
  "group_color": "#FF9800"
}
```

### Constituent JSON Structure

```json
{
  "group": 2,
  "label_en": "predicate",
  "label_zh": "谓语",
  "label_vi": "vi ngu",
  "word_indices": [2, 3, 4],
  "color": "#4CAF50"
}
```

## Sentence Annotation UI

### Word Display
- Flexbox column layout for each word: IPA above, word in middle, POS badge below
- `flex-wrap: wrap` for responsive line breaking
- Each word wrapped in a `<span>` with data attributes for TTS highlighting

### POS Color Scheme
| POS | Chinese | Vietnamese | Color | Hex |
|-----|---------|------------|-------|-----|
| Noun | 名词 | danh tu | Blue | #2196F3 |
| Verb | 动词 | dong tu | Red | #F44336 |
| Pronoun | 代词 | dai tu | Purple | #9C27B0 |
| Adjective | 形容词 | tinh tu | Orange | #FF9800 |
| Adverb | 副词 | trang tu | Green | #4CAF50 |
| Preposition | 介词 | gioi tu | Gray | #607D8B |
| Particle | 小品词 | tieu tu | Teal | #00BCD4 |
| Interjection | 感叹词 | than tu | Brown | #795548 |
| Determiner | 限定词 | han dinh tu | Indigo | #3F51B5 |
| Conjunction | 连词 | lien tu | Pink | #E91E63 |

### Constituent Brackets
- SVG overlay positioned below the word row
- Curved bracket paths using quadratic Bezier curves
- Labels centered under each bracket group
- x-positions calculated from word elements' getBoundingClientRect()

## Text-to-Speech

### Implementation
- Primary: Web Speech API (SpeechSynthesis)
- Voice selection: prefer "Google US English" or "Google UK English" on Chrome; filter for "enhanced"/"premium" en-US voices on other browsers
- Speed control via `SpeechSynthesisUtterance.rate` (0.5-2.0)
- Repeat: cancel current and call `speechSynthesis.speak()` again

### Word-by-Word Highlighting
1. Wrap each word in `<span data-char-offset="N">`
2. Listen to `SpeechSynthesisUtterance.onboundary` event
3. Match `event.charIndex` to word spans
4. Toggle CSS `.highlight` class for karaoke effect

## Dictation / Typing Practice

### Input Handling
- Submit-then-check validation (not real-time) for IME compatibility
- Track `compositionstart`/`compositionend` events to set `isComposing` flag
- Skip all validation while `isComposing === true`

### Scoring
- Use jsdiff `diffWords()` for comparison
- Green = correct word, Red = missing word, Orange = extra word
- Yellow = "almost correct" (Levenshtein distance <= 2)
- Case insensitive comparison
- Punctuation ignored
- Score = correct words / total expected words

### Fuzzy Matching
- Per-word Levenshtein distance <= 2 = accepted with gentle correction
- Whole-sentence Sorensen-Dice coefficient > 0.85 = "almost correct"

## Gamification & Progress

### XP System
- 10 XP per correct sentence
- 5 XP per "almost correct" sentence
- 0 XP per incorrect sentence
- Bonus: 5 XP for first-try accuracy

### Streaks
- Consecutive days with >= 1 completed sentence
- Displayed as flame icon + day count on dashboard

### Spaced Repetition (Leitner System)
- 5 buckets with review intervals: 1, 3, 7, 14, 30 days
- Correct answer: promote to next bucket
- Incorrect answer: return to bucket 1
- Due sentences appear in "Quick Review" on dashboard

## Content Generation Pipeline

### Authoring Workflow
1. Define lesson: CEFR level, topic, sentence count
2. Generate with Claude/GPT using prompt template
3. Validate IPA with `eng-to-ipa` Python library
4. Human review translations
5. Export as JSON seed file
6. Import script loads into SQLite

### Starter Content
- 10 lessons across A1-B1 difficulty
- Topics: greetings, daily routines, travel, food, shopping, directions, weather, emotions, work, health
- ~16 sentences per lesson = ~160 sentences total

## Project Structure

```
englisht_turorial/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # App configuration
│   ├── database.py          # SQLite connection, schema init
│   ├── models.py            # Pydantic models
│   ├── routers/
│   │   ├── auth.py          # Login, register, session
│   │   ├── lessons.py       # Lesson CRUD, listing
│   │   ├── practice.py      # Dictation scoring, progress
│   │   └── vocabulary.py    # Word bank, flashcards
│   ├── services/
│   │   ├── scoring.py       # Diff, Levenshtein, scoring logic
│   │   ├── spaced_rep.py    # Leitner bucket management
│   │   └── tts_prep.py      # Pre-compute TTS metadata
│   └── static/
│       ├── css/
│       │   ├── main.css     # Global styles
│       │   ├── lesson.css   # Annotation layout styles
│       │   └── dashboard.css
│       ├── js/
│       │   ├── app.js       # Router, global state
│       │   ├── tts.js       # Web Speech API wrapper
│       │   ├── dictation.js # Typing practice logic
│       │   ├── annotation.js # Sentence annotation renderer
│       │   └── i18n.js      # Chinese/Vietnamese translations
│       └── index.html       # SPA shell
├── tools/
│   ├── generate_lesson.py   # Claude/GPT lesson generator
│   ├── validate_ipa.py      # IPA validation with eng-to-ipa
│   └── import_lessons.py    # JSON to SQLite importer
├── data/
│   └── lessons/             # JSON seed files
├── requirements.txt
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/register | Create account |
| POST | /api/auth/login | Login, set session cookie |
| POST | /api/auth/logout | Clear session |
| GET | /api/user/profile | Get user profile + stats |
| PUT | /api/user/settings | Update preferences |
| GET | /api/lessons | List lessons with progress |
| GET | /api/lessons/{id} | Get lesson with all sentences |
| GET | /api/lessons/{id}/sentences/{index} | Get single sentence with annotations |
| POST | /api/practice/submit | Submit dictation attempt, get score |
| POST | /api/practice/self-rate | Submit read-aloud self-rating |
| GET | /api/review/due | Get sentences due for review |
| GET | /api/vocabulary | Get user word bank |
| GET | /api/vocabulary/flashcards | Get flashcard review set |
| GET | /api/stats | Get user statistics |

## Testing Strategy

- **Backend:** pytest for API endpoints, scoring logic, spaced repetition calculations
- **Frontend:** Manual browser testing for TTS, IME handling, responsive layout
- **Content:** Validation script ensures all sentences have complete annotations (IPA, POS, translations for every word)
