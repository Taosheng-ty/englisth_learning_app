const Speech = {
    recognition: null,
    listening: false,
    supported: false,

    init() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            this.supported = false;
            return;
        }
        this.supported = true;
        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'en-US';
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;
        this.recognition.continuous = false;
    },

    start(onResult) {
        if (!this.supported || this.listening) return;
        this.listening = true;
        const btn = document.getElementById('btn-mic');
        const status = document.getElementById('mic-status');
        btn.classList.add('mic-active');
        status.textContent = I18n.t('listening');

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const confidence = event.results[0][0].confidence;
            this.listening = false;
            btn.classList.remove('mic-active');
            status.textContent = I18n.t('tap_to_speak');
            if (onResult) onResult(transcript, confidence);
        };

        this.recognition.onerror = (event) => {
            this.listening = false;
            btn.classList.remove('mic-active');
            if (event.error === 'no-speech') {
                status.textContent = I18n.t('no_speech_detected');
            } else if (event.error === 'not-allowed') {
                status.textContent = I18n.t('mic_not_allowed');
            } else {
                status.textContent = I18n.t('tap_to_speak');
            }
        };

        this.recognition.onend = () => {
            this.listening = false;
            btn.classList.remove('mic-active');
        };

        this.recognition.start();
    },

    stop() {
        if (this.recognition && this.listening) {
            this.recognition.abort();
            this.listening = false;
            document.getElementById('btn-mic').classList.remove('mic-active');
            document.getElementById('mic-status').textContent = I18n.t('tap_to_speak');
        }
    },

    compare(spoken, expected) {
        const normalize = (s) => s.toLowerCase().replace(/[^\w\s']/g, '').split(/\s+/).filter(Boolean);
        const spokenWords = normalize(spoken);
        const expectedWords = normalize(expected);
        if (expectedWords.length === 0) return { score: 0, diffs: [], spokenText: spoken };

        const diffs = [];
        let matched = 0;
        let ei = 0;
        let si = 0;

        while (ei < expectedWords.length && si < spokenWords.length) {
            if (spokenWords[si] === expectedWords[ei]) {
                diffs.push({ word: expectedWords[ei], status: 'correct' });
                matched++;
                ei++;
                si++;
            } else if (si + 1 < spokenWords.length && spokenWords[si + 1] === expectedWords[ei]) {
                diffs.push({ word: spokenWords[si], status: 'extra' });
                si++;
            } else if (ei + 1 < expectedWords.length && spokenWords[si] === expectedWords[ei + 1]) {
                diffs.push({ word: expectedWords[ei], status: 'missing' });
                ei++;
            } else {
                const sim = this._similarity(spokenWords[si], expectedWords[ei]);
                if (sim > 0.5) {
                    diffs.push({ word: spokenWords[si], status: 'close', expected: expectedWords[ei] });
                    matched += 0.5;
                } else {
                    diffs.push({ word: spokenWords[si], status: 'incorrect', expected: expectedWords[ei] });
                }
                ei++;
                si++;
            }
        }
        while (ei < expectedWords.length) {
            diffs.push({ word: expectedWords[ei], status: 'missing' });
            ei++;
        }
        while (si < spokenWords.length) {
            diffs.push({ word: spokenWords[si], status: 'extra' });
            si++;
        }

        const score = Math.min(1, matched / expectedWords.length);
        return { score, diffs, spokenText: spoken };
    },

    _similarity(a, b) {
        if (a === b) return 1;
        const longer = a.length > b.length ? a : b;
        const shorter = a.length > b.length ? b : a;
        if (longer.length === 0) return 1;
        const dist = this._editDistance(longer, shorter);
        return (longer.length - dist) / longer.length;
    },

    _editDistance(a, b) {
        const matrix = [];
        for (let i = 0; i <= b.length; i++) matrix[i] = [i];
        for (let j = 0; j <= a.length; j++) matrix[0][j] = j;
        for (let i = 1; i <= b.length; i++) {
            for (let j = 1; j <= a.length; j++) {
                if (b[i - 1] === a[j - 1]) matrix[i][j] = matrix[i - 1][j - 1];
                else matrix[i][j] = Math.min(matrix[i - 1][j - 1] + 1, matrix[i][j - 1] + 1, matrix[i - 1][j] + 1);
            }
        }
        return matrix[b.length][a.length];
    },

    showResult(result, lang) {
        const container = document.getElementById('speech-result');
        container.style.display = 'block';
        container.innerHTML = '';

        const pct = Math.round(result.score * 100);
        const scoreLine = document.createElement('div');
        scoreLine.className = 'score-line';
        scoreLine.innerHTML = `<span class="score-label">${I18n.t('pronunciation_score')}:</span> <span class="score-value score-${pct >= 70 ? 'good' : pct >= 40 ? 'okay' : 'bad'}">${pct}%</span>`;
        container.appendChild(scoreLine);

        const spokenLine = document.createElement('div');
        spokenLine.className = 'spoken-line';
        spokenLine.innerHTML = `<strong>${I18n.t('you_said')}:</strong> "${result.spokenText}"`;
        container.appendChild(spokenLine);

        const diffLine = document.createElement('div');
        diffLine.className = 'diff-line';
        result.diffs.forEach(d => {
            const span = document.createElement('span');
            span.className = `diff-word diff-${d.status}`;
            span.textContent = d.word;
            if (d.status === 'close' && d.expected) span.title = `${I18n.t('close_match')}: ${d.expected}`;
            else if (d.status === 'missing') span.title = I18n.t('missing');
            else if (d.status === 'extra') span.title = I18n.t('extra');
            diffLine.appendChild(span);
            diffLine.appendChild(document.createTextNode(' '));
        });
        container.appendChild(diffLine);

        if (pct >= 70) {
            const msg = document.createElement('div');
            msg.className = 'speech-encouragement good';
            msg.textContent = I18n.t('great_pronunciation');
            container.appendChild(msg);
        } else if (pct >= 40) {
            const msg = document.createElement('div');
            msg.className = 'speech-encouragement okay';
            msg.textContent = I18n.t('keep_practicing');
            container.appendChild(msg);
        } else {
            const msg = document.createElement('div');
            msg.className = 'speech-encouragement bad';
            msg.textContent = I18n.t('try_again_speech');
            container.appendChild(msg);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => Speech.init());
