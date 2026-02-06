"""Tests for mavis.tutorial."""

from mavis.tutorial import (
    LESSONS,
    TutorialLesson,
    TutorialProgress,
    TutorialStep,
    format_lesson_list,
    get_lesson,
)


def test_lesson_count():
    assert len(LESSONS) == 7


def test_lesson_ids_sequential():
    ids = [l.lesson_id for l in LESSONS]
    assert ids == list(range(1, 8))


def test_each_lesson_has_steps():
    for lesson in LESSONS:
        assert len(lesson.steps) > 0
        assert lesson.title
        assert lesson.description
        assert lesson.sheet_text


def test_get_lesson_by_id():
    lesson = get_lesson(1)
    assert lesson is not None
    assert lesson.title == "Basic Typing"


def test_get_lesson_nonexistent():
    assert get_lesson(99) is None


def test_get_lesson_last():
    lesson = get_lesson(7)
    assert lesson is not None
    assert "Full Performance" in lesson.title


def test_progress_empty():
    p = TutorialProgress()
    assert p.completion_ratio() == 0.0
    assert not p.is_completed(1)
    assert p.best_grade(1) is None
    assert p.next_lesson() is not None
    assert p.next_lesson().lesson_id == 1


def test_progress_mark_completed():
    p = TutorialProgress()
    p.mark_completed(1, "B")
    assert p.is_completed(1)
    assert p.best_grade(1) == "B"
    assert p.next_lesson().lesson_id == 2


def test_progress_best_grade_upgrade():
    p = TutorialProgress()
    p.mark_completed(1, "C")
    assert p.best_grade(1) == "C"
    p.mark_completed(1, "A")
    assert p.best_grade(1) == "A"


def test_progress_best_grade_no_downgrade():
    p = TutorialProgress()
    p.mark_completed(1, "A")
    p.mark_completed(1, "C")  # should not downgrade
    assert p.best_grade(1) == "A"


def test_progress_completion_ratio():
    p = TutorialProgress()
    for i in range(1, 4):
        p.mark_completed(i, "B")
    assert 0.4 < p.completion_ratio() < 0.5  # 3/7


def test_progress_all_complete():
    p = TutorialProgress()
    for lesson in LESSONS:
        p.mark_completed(lesson.lesson_id, "S")
    assert p.completion_ratio() == 1.0
    assert p.next_lesson() is None


def test_format_lesson_list():
    text = format_lesson_list()
    assert "1." in text
    assert "7." in text
    assert "Basic Typing" in text


def test_format_lesson_list_with_progress():
    p = TutorialProgress()
    p.mark_completed(1, "A")
    text = format_lesson_list(p)
    assert "[A]" in text
    assert "[ ]" in text  # uncompleted lessons


def test_tutorial_step_fields():
    step = TutorialStep(
        instruction="Do the thing",
        practice_text="hello world",
        hint="Try harder",
    )
    assert step.instruction
    assert step.practice_text
    assert step.hint
