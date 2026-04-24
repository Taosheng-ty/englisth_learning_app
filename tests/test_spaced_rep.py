from datetime import datetime, timedelta
from app.services.spaced_rep import next_review_date, update_bucket


def test_next_review_bucket_1():
    now = datetime(2026, 4, 24, 12, 0)
    result = next_review_date(bucket=1, now=now)
    assert result == now + timedelta(days=1)


def test_next_review_bucket_5():
    now = datetime(2026, 4, 24, 12, 0)
    result = next_review_date(bucket=5, now=now)
    assert result == now + timedelta(days=30)


def test_update_bucket_correct_promotes():
    assert update_bucket(current_bucket=1, correct=True) == 2
    assert update_bucket(current_bucket=4, correct=True) == 5


def test_update_bucket_correct_max():
    assert update_bucket(current_bucket=5, correct=True) == 5


def test_update_bucket_incorrect_resets():
    assert update_bucket(current_bucket=3, correct=False) == 1
    assert update_bucket(current_bucket=5, correct=False) == 1


def test_update_bucket_incorrect_already_1():
    assert update_bucket(current_bucket=1, correct=False) == 1
