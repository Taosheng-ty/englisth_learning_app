const Dictation = {
    isComposing: false,
    init() {
        const input = document.getElementById('dictation-input');
        if (!input) return;
        input.addEventListener('compositionstart', () => { this.isComposing = true; });
        input.addEventListener('compositionend', () => { this.isComposing = false; });
    },
    showResult(result, lang) {
        const container = document.getElementById('dictation-result');
        container.style.display = 'block';
        container.innerHTML = '';
        const scoreLine = document.createElement('div');
        scoreLine.className = 'score-line';
        const pct = Math.round(result.score * 100);
        scoreLine.innerHTML = `<span class="score-label">${I18n.t('score')}:</span> <span class="score-value score-${pct >= 70 ? 'good' : pct >= 40 ? 'okay' : 'bad'}">${pct}%</span>`;
        if (result.xp_earned > 0) scoreLine.innerHTML += ` <span class="xp-earned">+${result.xp_earned} XP</span>`;
        container.appendChild(scoreLine);
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
        const expectedLine = document.createElement('div');
        expectedLine.className = 'expected-line';
        expectedLine.innerHTML = `<strong>${I18n.t('correct')}:</strong> ${result.expected_text}`;
        container.appendChild(expectedLine);
    },
    showFlashcards(cards, lang) {
        const area = document.getElementById('flashcard-area');
        area.style.display = 'block';
        area.innerHTML = '';
        if (cards.length === 0) { area.innerHTML = '<p class="empty-state">' + I18n.t('no_flashcards') + '</p>'; return; }
        let idx = 0;
        const renderCard = () => {
            if (idx >= cards.length) { area.innerHTML = '<p class="empty-state">' + I18n.t('all_cards_reviewed') + ' 🎉</p>'; return; }
            const c = cards[idx];
            const translationKey = `translation_${lang}`;
            area.innerHTML = `
                <div class="flashcard">
                    <div class="flashcard-front">
                        <span class="fc-word">${c.word}</span>
                        <span class="fc-ipa">${c.ipa}</span>
                        <span class="fc-pos">${c.pos}</span>
                    </div>
                    <div class="flashcard-back" style="display:none">
                        <span class="fc-example">${c.example_sentence}</span>
                        <span class="fc-translation">${c[translationKey] || ''}</span>
                    </div>
                    <div class="flashcard-actions">
                        <button class="btn-flip btn-primary">${I18n.t('flip')}</button>
                        <button class="btn-next-card btn-primary" style="display:none">${I18n.t('next_card')}</button>
                    </div>
                </div>`;
            area.querySelector('.btn-flip').addEventListener('click', () => {
                area.querySelector('.flashcard-back').style.display = 'block';
                area.querySelector('.btn-flip').style.display = 'none';
                area.querySelector('.btn-next-card').style.display = 'inline-block';
            });
            area.querySelector('.btn-next-card').addEventListener('click', () => { idx++; renderCard(); });
        };
        renderCard();
    }
};
document.addEventListener('DOMContentLoaded', () => Dictation.init());
