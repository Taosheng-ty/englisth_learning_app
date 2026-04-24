const TTS = {
    speed: 1.0,
    audio: null,
    wordSpans: [],
    playing: false,

    setSpeed(rate) { this.speed = Math.max(0.5, Math.min(2.0, rate)); },

    _rateParam() {
        const pct = Math.round((this.speed - 1.0) * 100);
        return (pct >= 0 ? '+' : '') + pct + '%';
    },

    speak(text) {
        this.stop();
        const url = '/api/tts?text=' + encodeURIComponent(text) + '&rate=' + encodeURIComponent(this._rateParam());
        this.audio = new Audio(url);
        this.wordSpans = document.querySelectorAll('.word-text');
        this.playing = true;

        const words = text.replace(/[^\w\s']/g, '').split(/\s+/);
        const totalWords = words.length;

        this.audio.addEventListener('timeupdate', () => {
            if (!this.playing || !this.audio.duration) return;
            const progress = this.audio.currentTime / this.audio.duration;
            const wordIdx = Math.min(Math.floor(progress * totalWords), totalWords - 1);
            this._clearHighlights();
            if (this.wordSpans[wordIdx]) this.wordSpans[wordIdx].classList.add('tts-highlight');
        });

        this.audio.addEventListener('ended', () => {
            this.playing = false;
            this._clearHighlights();
        });

        this.audio.addEventListener('error', () => {
            this.playing = false;
            this._clearHighlights();
        });

        this.audio.play();
    },

    stop() {
        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.audio = null;
        }
        this.playing = false;
        this._clearHighlights();
    },

    _clearHighlights() {
        this.wordSpans.forEach(span => span.classList.remove('tts-highlight'));
    }
};
