import uuid
from datetime import UTC, datetime

from app.models.srs import ReviewItem


def test_review_item_defaults():
    user_id = str(uuid.uuid4())
    question_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    item = ReviewItem(
        user_id=user_id,
        question_id=question_id,
        topic_tag="Backend Architecture",
    )

    assert item.user_id == user_id
    assert item.question_id == question_id
    assert item.topic_tag == "Backend Architecture"
    assert item.interval_days == 1
    assert item.repetitions == 0
    assert item.ease_factor == 2.5
    assert item.consecutive_correct == 0
    assert item.total_reviews == 0
    assert item.next_review_at >= now
    assert "interval=1d" in repr(item)

