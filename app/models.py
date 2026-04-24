from pydantic import BaseModel
from typing import Optional


class RegisterRequest(BaseModel):
    username: str
    password: str
    ui_language: str = "zh"


class LoginRequest(BaseModel):
    username: str
    password: str


class SettingsUpdate(BaseModel):
    ui_language: Optional[str] = None
    daily_goal: Optional[int] = None
    tts_speed: Optional[float] = None


class DictationSubmit(BaseModel):
    sentence_id: str
    typed_text: str


class SelfRateRequest(BaseModel):
    sentence_id: str
    rating: str


class WordDiff(BaseModel):
    word: str
    status: str
    expected: Optional[str] = None


class DictationResult(BaseModel):
    score: float
    xp_earned: int
    diffs: list[WordDiff]
    expected_text: str


class UserProfile(BaseModel):
    username: str
    ui_language: str
    daily_goal: int
    tts_speed: float
    xp: int
    streak_days: int
    sentences_today: int


class LessonSummary(BaseModel):
    id: int
    title: str
    title_zh: str
    title_vi: str
    difficulty: str
    category: str
    sentence_count: int
    completed_count: int


class WordAnnotation(BaseModel):
    word: str
    ipa: str
    pos: str
    pos_zh: str
    pos_vi: str
    role: str
    role_zh: str
    role_vi: str
    group: int
    group_color: str


class Constituent(BaseModel):
    group: int
    label_en: str
    label_zh: str
    label_vi: str
    word_indices: list[int]
    color: str


class SentenceDetail(BaseModel):
    id: str
    lesson_id: int
    index: int
    text: str
    translation_zh: str
    translation_vi: str
    words: list[WordAnnotation]
    constituents: list[Constituent]


class VocabEntry(BaseModel):
    word: str
    ipa: str
    pos: str
    seen_count: int
    correct_count: int
    status: str


class StatsResponse(BaseModel):
    xp: int
    streak_days: int
    total_sentences_practiced: int
    total_words_learned: int
    accuracy_percent: float
    sentences_today: int
    daily_goal: int
