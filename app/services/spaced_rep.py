from datetime import datetime, timedelta

BUCKET_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def next_review_date(bucket: int, now: datetime | None = None) -> datetime:
    if now is None:
        now = datetime.now()
    days = BUCKET_INTERVALS.get(bucket, 1)
    return now + timedelta(days=days)


def update_bucket(current_bucket: int, correct: bool) -> int:
    if correct:
        return min(current_bucket + 1, 5)
    return 1
