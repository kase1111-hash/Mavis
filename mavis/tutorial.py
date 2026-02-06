"""Tutorial mode -- progressive lessons teaching Sheet Text and buffer management."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TutorialStep:
    """A single instruction step within a lesson."""

    instruction: str
    practice_text: str = ""
    hint: str = ""


@dataclass
class TutorialLesson:
    """A complete tutorial lesson with steps and practice text."""

    lesson_id: int
    title: str
    description: str
    sheet_text: str
    steps: List[TutorialStep] = field(default_factory=list)
    target_grade: str = "C"


# --- Predefined Lessons ---

LESSONS: List[TutorialLesson] = [
    TutorialLesson(
        lesson_id=1,
        title="Basic Typing",
        description="Learn to type text and watch the buffer fill.",
        sheet_text="hello world this is your voice",
        steps=[
            TutorialStep(
                instruction="Type the text shown on screen at a steady pace.",
                practice_text="hello world this is your voice",
                hint="Watch the output buffer bar -- keep it in the green zone.",
            ),
            TutorialStep(
                instruction="Try typing faster and slower. See how the buffer reacts.",
                practice_text="hello world this is your voice",
                hint="Too fast fills the buffer (yellow/red). Too slow empties it.",
            ),
        ],
        target_grade="D",
    ),
    TutorialLesson(
        lesson_id=2,
        title="Emphasis with CAPS",
        description="Use Shift/Caps Lock to add emphasis to words.",
        sheet_text="the SUN is BRIGHT today",
        steps=[
            TutorialStep(
                instruction="Type uppercase words with Shift held down for emphasis.",
                practice_text="the SUN is BRIGHT today",
                hint="CAPS words are louder and stronger. Hold Shift for the whole word.",
            ),
            TutorialStep(
                instruction="Practice alternating between normal and emphasized words.",
                practice_text="HELLO world GOODBYE world",
                hint="Notice the volume difference between loud and normal words.",
            ),
        ],
        target_grade="D",
    ),
    TutorialLesson(
        lesson_id=3,
        title="Soft Voice",
        description="Use _underscores_ to make words soft and breathy.",
        sheet_text="falling _gently_ to the _ground_",
        steps=[
            TutorialStep(
                instruction="Words between underscores become soft and breathy.",
                practice_text="falling _gently_ to the _ground_",
                hint="Type the underscores before and after the soft word.",
            ),
            TutorialStep(
                instruction="Combine soft and loud in the same phrase.",
                practice_text="the THUNDER _fades_ to _silence_",
                hint="Contrast loud CAPS words with _soft_ underscored words.",
            ),
        ],
        target_grade="D",
    ),
    TutorialLesson(
        lesson_id=4,
        title="Sustain and Vibrato",
        description="Use ... (ellipsis) to hold notes with vibrato.",
        sheet_text="hold... this... note... LONG...",
        steps=[
            TutorialStep(
                instruction="Three dots after a word add sustain (like holding a note).",
                practice_text="hold... this... note... LONG...",
                hint="The sustain bar shows how long the note is held.",
            ),
            TutorialStep(
                instruction="Try combining sustain with emphasis.",
                practice_text="the SUN... is _falling_... DOWN...",
                hint="Sustained loud notes get vibrato. Sustained soft notes fade out.",
            ),
        ],
        target_grade="D",
    ),
    TutorialLesson(
        lesson_id=5,
        title="Harmony with [Brackets]",
        description="Hold Ctrl and type [bracketed] words for harmony.",
        sheet_text="singing [together] as [one]",
        steps=[
            TutorialStep(
                instruction="Words in brackets trigger a harmony layer.",
                practice_text="singing [together] as [one]",
                hint="Hold Ctrl while typing the bracketed word for extra voices.",
            ),
            TutorialStep(
                instruction="Combine harmony with other markups.",
                practice_text="the CHOIR... sings [HALLELUJAH]...",
                hint="Harmony + sustain + emphasis = full vocal power.",
            ),
        ],
        target_grade="D",
    ),
    TutorialLesson(
        lesson_id=6,
        title="Buffer Management",
        description="Master the core skill: keeping your buffer in the optimal zone.",
        sheet_text="TWINKLE twinkle _little_ STAR... how I WONDER... what you ARE...",
        steps=[
            TutorialStep(
                instruction="Play through a song while keeping the buffer bar green.",
                practice_text="TWINKLE twinkle _little_ STAR... how I WONDER... what you ARE...",
                hint="Green = optimal. Yellow = warning. Red = you're losing points.",
            ),
            TutorialStep(
                instruction="If the buffer gets too full, pause briefly. If too empty, type faster.",
                practice_text="TWINKLE twinkle _little_ STAR... how I WONDER... what you ARE...",
                hint="Think of the buffer like breath control -- smooth and steady.",
            ),
        ],
        target_grade="C",
    ),
    TutorialLesson(
        lesson_id=7,
        title="Full Performance",
        description="Put it all together: emphasis, softness, sustain, harmony, and buffer control.",
        sheet_text="a _MAZING_... GRACE... how SWEET... the SOUND...\nthat SAVED... a _wretch_ like ME...\nI ONCE was LOST... but NOW am [FOUND]...",
        steps=[
            TutorialStep(
                instruction="Perform the full passage using everything you've learned.",
                practice_text=(
                    "a _MAZING_... GRACE... how SWEET... the SOUND...\n"
                    "that SAVED... a _wretch_ like ME...\n"
                    "I ONCE was LOST... but NOW am [FOUND]..."
                ),
                hint="Read 2-3 seconds ahead. Plan your emphasis before you type.",
            ),
        ],
        target_grade="B",
    ),
]


@dataclass
class TutorialProgress:
    """Track which lessons have been completed and at what grade."""

    completed: dict = field(default_factory=dict)  # lesson_id -> best grade

    def mark_completed(self, lesson_id: int, grade: str) -> None:
        """Record completion of a lesson with the achieved grade."""
        current = self.completed.get(lesson_id)
        if current is None or _grade_value(grade) > _grade_value(current):
            self.completed[lesson_id] = grade

    def is_completed(self, lesson_id: int) -> bool:
        """Check if a lesson has been completed at all."""
        return lesson_id in self.completed

    def best_grade(self, lesson_id: int) -> Optional[str]:
        """Return the best grade achieved for a lesson, or None."""
        return self.completed.get(lesson_id)

    def next_lesson(self) -> Optional[TutorialLesson]:
        """Return the next uncompleted lesson, or None if all done."""
        for lesson in LESSONS:
            if lesson.lesson_id not in self.completed:
                return lesson
        return None

    def completion_ratio(self) -> float:
        """Fraction of lessons completed (0.0-1.0)."""
        if not LESSONS:
            return 1.0
        return len(self.completed) / len(LESSONS)


def get_lesson(lesson_id: int) -> Optional[TutorialLesson]:
    """Look up a lesson by ID (1-based)."""
    for lesson in LESSONS:
        if lesson.lesson_id == lesson_id:
            return lesson
    return None


def format_lesson_list(progress: Optional[TutorialProgress] = None) -> str:
    """Format the lesson list for terminal display, with progress markers."""
    lines = []
    for lesson in LESSONS:
        marker = " "
        if progress is not None and progress.is_completed(lesson.lesson_id):
            grade = progress.best_grade(lesson.lesson_id)
            marker = f"[{grade}]"
        else:
            marker = "[ ]"
        lines.append(f"  {lesson.lesson_id}. {marker} {lesson.title} -- {lesson.description}")
    return "\n".join(lines)


def _grade_value(grade: str) -> int:
    """Convert a letter grade to a numeric value for comparison."""
    return {"S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "F": 1}.get(grade, 0)
