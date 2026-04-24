const Annotation = {
    POS_COLORS: {
        noun: '#2196F3', verb: '#F44336', pronoun: '#9C27B0',
        adjective: '#FF9800', adverb: '#4CAF50', preposition: '#607D8B',
        particle: '#00BCD4', interjection: '#795548', determiner: '#3F51B5',
        conjunction: '#E91E63',
    },
    render(container, sentence, lang, showAnnotations) {
        container.innerHTML = '';
        if (!sentence || !sentence.words) return;
        if (showAnnotations) {
            const wordsRow = document.createElement('div');
            wordsRow.className = 'words-row';
            let charOffset = 0;
            sentence.words.forEach((w) => {
                const unit = document.createElement('div');
                unit.className = 'word-unit';
                const ipa = document.createElement('span');
                ipa.className = 'word-ipa';
                ipa.textContent = w.ipa;
                const posKey = `pos_${lang}`;
                const posBadge = document.createElement('span');
                posBadge.className = 'pos-badge';
                posBadge.style.backgroundColor = this.POS_COLORS[w.pos] || '#757575';
                posBadge.textContent = w[posKey] || w.pos;
                const wordSpan = document.createElement('span');
                wordSpan.className = 'word-text';
                wordSpan.textContent = w.word;
                wordSpan.dataset.charOffset = charOffset;
                wordSpan.dataset.group = w.group;
                wordSpan.style.cursor = 'pointer';
                wordSpan.addEventListener('click', () => {
                    TTS.speak(w.word);
                });
                unit.appendChild(ipa);
                unit.appendChild(posBadge);
                unit.appendChild(wordSpan);
                wordsRow.appendChild(unit);
                charOffset += w.word.length + 1;
            });
            container.appendChild(wordsRow);
            if (sentence.constituents && sentence.constituents.length > 0) {
                const bracketsDiv = document.createElement('div');
                bracketsDiv.className = 'constituents-row';
                sentence.constituents.forEach(c => {
                    const group = document.createElement('div');
                    group.className = 'constituent-group';
                    group.style.borderColor = c.color;
                    const labelKey = `label_${lang}`;
                    const label = document.createElement('span');
                    label.className = 'constituent-label';
                    label.style.color = c.color;
                    label.textContent = c[labelKey] || c.label_en;
                    const wordsInGroup = c.word_indices.map(idx => sentence.words[idx]?.word || '').join(' ');
                    const bracket = document.createElement('span');
                    bracket.className = 'constituent-bracket';
                    bracket.style.borderBottomColor = c.color;
                    bracket.textContent = wordsInGroup;
                    group.appendChild(bracket);
                    group.appendChild(label);
                    bracketsDiv.appendChild(group);
                });
                container.appendChild(bracketsDiv);
            }
            const translationKey = `translation_${lang}`;
            const translation = document.createElement('div');
            translation.className = 'translation';
            translation.textContent = sentence[translationKey] || '';
            container.appendChild(translation);
        } else {
            const hidden = document.createElement('div');
            hidden.className = 'dictation-mode-text';
            hidden.innerHTML = '<span class="listen-icon">&#128266;</span> <span class="listen-text">' + I18n.t('dictation_hint') + '</span>';
            container.appendChild(hidden);
        }
    }
};
