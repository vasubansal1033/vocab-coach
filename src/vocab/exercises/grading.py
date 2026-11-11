"""Pure grading for choose-the-word responses."""

from __future__ import annotations

from dataclasses import dataclass

from vocab.exercises.schemas import (
    ChoiceAnswer,
    ChoiceFeedback,
    ChoiceFeedbackCandidate,
    ChoiceResponse,
)


@dataclass(frozen=True)
class ChoiceGradeResult:
    correct: bool
    feedback: ChoiceFeedback


def grade_choice(answer: ChoiceAnswer, response: ChoiceResponse) -> ChoiceGradeResult:
    """Correct when the best pick matches; extra marks are feedback only."""
    marked = set(response.marked_option_ids)
    feedback = ChoiceFeedback(
        best_option_id=answer.best_option_id,
        user_best_option_id=response.best_option_id,
        candidates=[
            ChoiceFeedbackCandidate(
                option_id=c.option_id,
                fit=c.fit,
                reason=c.reason,
                best=c.best,
                user_marked=c.option_id in marked,
            )
            for c in answer.candidates
        ],
    )
    return ChoiceGradeResult(
        correct=response.best_option_id == answer.best_option_id,
        feedback=feedback,
    )
