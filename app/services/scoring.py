import re


def levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _normalize(text: str) -> list[str]:
    text = re.sub(r"[^\w\s]", "", text.lower().strip())
    return text.split()


def score_dictation(expected: str, typed: str) -> dict:
    expected_words = _normalize(expected)
    typed_words = _normalize(typed)

    if not typed_words:
        diffs = [{"word": w, "status": "missing", "expected": None} for w in expected_words]
        return {"score": 0.0, "xp": 0, "diffs": diffs, "expected_text": expected}

    diffs = []
    e_idx = 0
    t_idx = 0

    while e_idx < len(expected_words) and t_idx < len(typed_words):
        ew = expected_words[e_idx]
        tw = typed_words[t_idx]

        if ew == tw:
            diffs.append({"word": tw, "status": "correct", "expected": None})
            e_idx += 1
            t_idx += 1
        elif levenshtein(ew, tw) <= 2:
            diffs.append({"word": tw, "status": "close", "expected": ew})
            e_idx += 1
            t_idx += 1
        else:
            if e_idx + 1 < len(expected_words) and expected_words[e_idx + 1] == tw:
                diffs.append({"word": ew, "status": "missing", "expected": None})
                e_idx += 1
            elif t_idx + 1 < len(typed_words) and typed_words[t_idx + 1] == ew:
                diffs.append({"word": tw, "status": "extra", "expected": None})
                t_idx += 1
            else:
                diffs.append({"word": tw, "status": "incorrect", "expected": ew})
                e_idx += 1
                t_idx += 1

    while e_idx < len(expected_words):
        diffs.append({"word": expected_words[e_idx], "status": "missing", "expected": None})
        e_idx += 1

    while t_idx < len(typed_words):
        diffs.append({"word": typed_words[t_idx], "status": "extra", "expected": None})
        t_idx += 1

    correct = sum(1 for d in diffs if d["status"] == "correct")
    close = sum(1 for d in diffs if d["status"] == "close")
    total_expected = len(expected_words)
    score = (correct + close * 0.8) / total_expected if total_expected > 0 else 0.0
    score = round(min(score, 1.0), 2)

    if score >= 0.95:
        xp = 10
    elif score >= 0.7:
        xp = 5
    else:
        xp = 0

    return {"score": score, "xp": xp, "diffs": diffs, "expected_text": expected}
