const App = {
    currentPage: 'login',
    currentLesson: null,
    currentSentenceIndex: 0,
    sentences: [],
    profile: null,

    showToast(msg, duration = 2000) {
        const toast = document.getElementById('toast');
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), duration);
    },

    async api(method, path, body) {
        const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
        if (body) opts.body = JSON.stringify(body);
        const resp = await fetch(path, opts);
        if (resp.status === 401 && path !== '/api/auth/login') { this.showPage('login'); return null; }
        return resp;
    },

    showPage(name) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const page = document.getElementById('page-' + name);
        if (page) page.classList.add('active');
        this.currentPage = name;
    },

    async init() {
        this._bindLogin();
        this._bindDashboard();
        this._bindLesson();
        this._bindVocabulary();
        this._bindSettings();
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                I18n.setLang(btn.dataset.lang);
            });
        });
        document.getElementById('modal-back-dashboard').addEventListener('click', () => {
            document.getElementById('lesson-complete-modal').style.display = 'none';
            this.loadDashboard();
        });
        const activeLang = document.querySelector('.lang-btn.active')?.dataset.lang || 'zh';
        I18n.setLang(activeLang);
    },

    _bindLogin() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('login-form').style.display = btn.dataset.tab === 'login' ? 'block' : 'none';
                document.getElementById('register-form').style.display = btn.dataset.tab === 'register' ? 'block' : 'none';
                document.getElementById('login-error').textContent = '';
                document.getElementById('reg-error').textContent = '';
                document.getElementById('login-success').style.display = 'none';
            });
        });
        document.getElementById('register-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            const lang = document.querySelector('.lang-btn.active')?.dataset.lang || 'zh';
            const resp = await this.api('POST', '/api/auth/register', {
                username: document.getElementById('reg-username').value,
                password: document.getElementById('reg-password').value,
                ui_language: lang,
            });
            btn.disabled = false;
            if (resp && resp.ok) {
                document.querySelector('[data-tab="login"]').click();
                document.getElementById('login-username').value = document.getElementById('reg-username').value;
                const msg = document.getElementById('login-success');
                msg.textContent = I18n.t('register_success');
                msg.style.display = 'block';
                document.getElementById('reg-error').textContent = '';
                document.getElementById('reg-password').value = '';
            } else {
                document.getElementById('reg-error').textContent = I18n.t('username_exists');
            }
        });
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type="submit"]');
            btn.disabled = true;
            document.getElementById('login-success').style.display = 'none';
            const resp = await this.api('POST', '/api/auth/login', {
                username: document.getElementById('login-username').value,
                password: document.getElementById('login-password').value,
            });
            btn.disabled = false;
            if (resp && resp.ok) {
                const selectedLang = document.querySelector('.lang-btn.active')?.dataset.lang || 'zh';
                await this.api('PUT', '/api/user/settings', { ui_language: selectedLang });
                await this.loadDashboard();
            }
            else { document.getElementById('login-error').textContent = I18n.t('invalid_credentials'); }
        });
    },

    async loadDashboard() {
        this.showPage('dashboard');
        const profileResp = await this.api('GET', '/api/user/profile');
        if (!profileResp) return;
        this.profile = await profileResp.json();
        I18n.setLang(this.profile.ui_language);
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b.dataset.lang === this.profile.ui_language));
        document.getElementById('dash-username').textContent = this.profile.username;
        document.getElementById('dash-streak').textContent = this.profile.streak_days;
        document.getElementById('dash-xp').textContent = this.profile.xp;
        document.getElementById('dash-today').textContent = this.profile.sentences_today;
        document.getElementById('dash-goal').textContent = this.profile.daily_goal;
        const pct = Math.min(100, Math.round((this.profile.sentences_today / this.profile.daily_goal) * 100));
        document.getElementById('progress-pct').textContent = pct + '%';
        const circle = document.getElementById('progress-ring-fill');
        const circumference = 2 * Math.PI * 42;
        circle.style.strokeDasharray = circumference;
        circle.style.strokeDashoffset = circumference - (pct / 100) * circumference;
        if (pct >= 100) {
            circle.style.stroke = 'var(--success)';
        } else {
            circle.style.stroke = 'var(--primary)';
        }
        const lessonsResp = await this.api('GET', '/api/lessons');
        if (!lessonsResp) return;
        const lessons = await lessonsResp.json();
        const grid = document.getElementById('lesson-grid');
        grid.innerHTML = '';
        const filterVal = document.getElementById('filter-difficulty').value;
        const filtered = lessons.filter(l => filterVal === 'all' || l.difficulty === filterVal);
        if (filtered.length === 0) {
            grid.innerHTML = '<div class="empty-state">' + I18n.t('no_lessons_found') + '</div>';
            return;
        }
        filtered.forEach(l => {
            const lang = this.profile.ui_language;
            const title = lang === 'vi' ? l.title_vi : l.title_zh;
            const pctDone = l.sentence_count > 0 ? Math.round((l.completed_count / l.sentence_count) * 100) : 0;
            const card = document.createElement('div');
            card.className = 'lesson-card';
            card.setAttribute('role', 'button');
            card.setAttribute('tabindex', '0');
            card.innerHTML = `
                <div class="lesson-card-header">
                    <span class="lesson-num">${I18n.t('lesson')} ${l.id}</span>
                    <span class="difficulty-badge badge-${l.difficulty}">${l.difficulty}</span>
                </div>
                <div class="lesson-card-title">${title}</div>
                <div class="lesson-card-subtitle">${l.title}</div>
                <div class="progress-bar-container"><div class="progress-bar-fill" style="width:${pctDone}%"></div></div>
                <span class="progress-label">${l.completed_count}/${l.sentence_count}</span>`;
            card.addEventListener('click', () => this.openLesson(l.id));
            card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.openLesson(l.id); } });
            grid.appendChild(card);
        });
    },

    _bindDashboard() {
        document.getElementById('btn-logout').addEventListener('click', async () => { await this.api('POST', '/api/auth/logout'); this.showPage('login'); });
        document.getElementById('btn-vocab').addEventListener('click', () => this.openVocabulary());
        document.getElementById('btn-settings').addEventListener('click', () => this.openSettings());
        document.getElementById('btn-review').addEventListener('click', () => this.openReview());
        document.getElementById('filter-difficulty').addEventListener('change', () => this.loadDashboard());
    },

    async openLesson(lessonId) {
        const resp = await this.api('GET', `/api/lessons/${lessonId}`);
        if (!resp) return;
        const lesson = await resp.json();
        this.currentLesson = lesson;
        this.sentences = lesson.sentences;
        this.currentSentenceIndex = 0;
        const lang = this.profile.ui_language;
        const title = lang === 'vi' ? lesson.title_vi : lesson.title_zh;
        document.getElementById('lesson-title').textContent = `${title} (${lesson.title})`;
        this.showPage('lesson');
        this.renderSentence();
    },

    renderSentence() {
        const s = this.sentences[this.currentSentenceIndex];
        if (!s) return;
        document.getElementById('sentence-counter').textContent = `${this.currentSentenceIndex + 1}/${this.sentences.length}`;
        document.getElementById('nav-counter').textContent = `${this.currentSentenceIndex + 1} / ${this.sentences.length}`;
        const mode = document.querySelector('.mode-tab.active').dataset.mode;
        const showAnnotations = mode !== 'dictation';
        Annotation.render(document.getElementById('annotation-area'), s, this.profile.ui_language, showAnnotations);
        document.getElementById('dictation-input').value = '';
        document.getElementById('dictation-result').style.display = 'none';
        document.getElementById('speech-result').style.display = 'none';
        if (Speech.listening) Speech.stop();
        if (mode === 'learn') TTS.speak(s.text);
    },

    _showLessonComplete() {
        const modal = document.getElementById('lesson-complete-modal');
        I18n.setLang(this.profile.ui_language);
        modal.style.display = 'flex';
    },

    _bindLesson() {
        document.getElementById('btn-back').addEventListener('click', () => this.loadDashboard());
        document.getElementById('btn-prev').addEventListener('click', () => { if (this.currentSentenceIndex > 0) { this.currentSentenceIndex--; this.renderSentence(); } });
        document.getElementById('btn-next').addEventListener('click', () => {
            if (this.currentSentenceIndex < this.sentences.length - 1) { this.currentSentenceIndex++; this.renderSentence(); }
            else { this._showLessonComplete(); }
        });
        document.getElementById('btn-play').addEventListener('click', () => { const s = this.sentences[this.currentSentenceIndex]; if (s) TTS.speak(s.text); });
        document.getElementById('btn-repeat').addEventListener('click', () => { const s = this.sentences[this.currentSentenceIndex]; if (s) TTS.speak(s.text); });
        document.getElementById('speed-slider').addEventListener('input', (e) => { const val = parseFloat(e.target.value); document.getElementById('speed-value').textContent = val.toFixed(1) + 'x'; TTS.setSpeed(val); });
        document.getElementById('btn-mic').addEventListener('click', () => {
            if (!Speech.supported) {
                this.showToast(I18n.t('speech_not_supported'));
                return;
            }
            if (Speech.listening) {
                Speech.stop();
                return;
            }
            const s = this.sentences[this.currentSentenceIndex];
            if (!s) return;
            Speech.start((transcript, confidence) => {
                const result = Speech.compare(transcript, s.text);
                Speech.showResult(result, this.profile.ui_language);
                const rating = result.score >= 0.7 ? 'good' : result.score >= 0.4 ? 'okay' : 'again';
                this.api('POST', '/api/practice/self-rate', { sentence_id: s.id, rating });
            });
        });
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
                const mode = tab.dataset.mode;
                const panelId = { learn: 'mode-learn', read_aloud: 'mode-read-aloud', dictation: 'mode-dictation' }[mode];
                document.getElementById(panelId).classList.add('active');
                this.renderSentence();
            });
        });
        document.querySelectorAll('.rate-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const s = this.sentences[this.currentSentenceIndex];
                await this.api('POST', '/api/practice/self-rate', { sentence_id: s.id, rating: btn.dataset.rating });
                this.showToast(I18n.t('rating_saved') + ' ✓');
                if (this.currentSentenceIndex < this.sentences.length - 1) {
                    this.currentSentenceIndex++;
                    this.renderSentence();
                } else {
                    this._showLessonComplete();
                }
            });
        });
        document.getElementById('btn-submit-dictation').addEventListener('click', async () => {
            const s = this.sentences[this.currentSentenceIndex];
            const typed = document.getElementById('dictation-input').value;
            if (!typed.trim()) return;
            const btn = document.getElementById('btn-submit-dictation');
            btn.disabled = true;
            const resp = await this.api('POST', '/api/practice/submit', { sentence_id: s.id, typed_text: typed });
            btn.disabled = false;
            if (!resp) return;
            const result = await resp.json();
            Dictation.showResult(result, this.profile.ui_language);
            Annotation.render(document.getElementById('annotation-area'), s, this.profile.ui_language, true);
        });
    },

    async openVocabulary() {
        this.showPage('vocabulary');
        const filter = document.getElementById('vocab-filter-select').value;
        const resp = await this.api('GET', `/api/vocabulary?filter=${filter}`);
        if (!resp) return;
        const words = await resp.json();
        const list = document.getElementById('vocab-list');
        list.innerHTML = '';
        if (words.length === 0) {
            list.innerHTML = '<div class="empty-state">' + I18n.t('no_vocabulary_yet') + '</div>';
            return;
        }
        words.forEach(w => {
            const item = document.createElement('div');
            item.className = 'vocab-item';
            item.innerHTML = `
                <span class="vocab-word">${w.word}</span>
                <span class="vocab-ipa">${w.ipa}</span>
                <span class="pos-badge pos-${w.pos}">${w.pos}</span>
                <span class="vocab-status status-${w.status}">${I18n.t(w.status)}</span>
                <span class="vocab-stats">${w.correct_count}/${w.seen_count}</span>`;
            list.appendChild(item);
        });
    },

    _bindVocabulary() {
        document.getElementById('vocab-back').addEventListener('click', () => this.loadDashboard());
        document.getElementById('vocab-filter-select').addEventListener('change', () => this.openVocabulary());
        document.getElementById('btn-flashcards').addEventListener('click', async () => {
            const resp = await this.api('GET', '/api/vocabulary/flashcards');
            if (!resp) return;
            const cards = await resp.json();
            Dictation.showFlashcards(cards, this.profile.ui_language);
        });
    },

    async openSettings() {
        this.showPage('settings');
        if (this.profile) {
            document.getElementById('setting-language').value = this.profile.ui_language;
            document.getElementById('setting-tts-speed').value = this.profile.tts_speed;
            document.getElementById('setting-speed-val').textContent = this.profile.tts_speed.toFixed(1) + 'x';
            document.getElementById('setting-daily-goal').value = this.profile.daily_goal;
        }
    },

    _bindSettings() {
        document.getElementById('settings-back').addEventListener('click', () => this.loadDashboard());
        document.getElementById('setting-tts-speed').addEventListener('input', (e) => { document.getElementById('setting-speed-val').textContent = parseFloat(e.target.value).toFixed(1) + 'x'; });
        document.getElementById('btn-save-settings').addEventListener('click', async () => {
            const btn = document.getElementById('btn-save-settings');
            btn.disabled = true;
            await this.api('PUT', '/api/user/settings', {
                ui_language: document.getElementById('setting-language').value,
                tts_speed: parseFloat(document.getElementById('setting-tts-speed').value),
                daily_goal: parseInt(document.getElementById('setting-daily-goal').value),
            });
            btn.disabled = false;
            const profileResp = await this.api('GET', '/api/user/profile');
            if (profileResp) { this.profile = await profileResp.json(); I18n.setLang(this.profile.ui_language); TTS.setSpeed(this.profile.tts_speed); }
            this.loadDashboard();
        });
    },

    async openReview() {
        const resp = await this.api('GET', '/api/review/due');
        if (!resp) return;
        const items = await resp.json();
        if (items.length === 0) {
            this.showToast(I18n.t('no_review_items'));
            return;
        }
        const first = items[0];
        const lessonId = parseInt(first.sentence_id.split('-')[0]);
        await this.openLesson(lessonId);
        const idx = this.sentences.findIndex(s => s.id === first.sentence_id);
        if (idx >= 0) { this.currentSentenceIndex = idx; this.renderSentence(); }
    },
};
document.addEventListener('DOMContentLoaded', () => App.init());
