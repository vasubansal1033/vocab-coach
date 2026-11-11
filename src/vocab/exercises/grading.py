"""Pure grading for choose-the-word, compare, and idiom select responses."""

from __future__ import annotations

from dataclasses import dataclass

from vocab.exercises.schemas import (
    ChoiceAnswer,
    ChoiceFeedback,
    ChoiceFeedbackCandidate,
    ChoiceResponse,
    CompareMisuseAnswer,
    CompareMisuseFeedback,
    CompareMisuseResponse,
    CompareOrderAnswer,
    CompareOrderFeedback,
    CompareOrderResponse,
    ComparePairAnswer,
    ComparePairFeedback,
    ComparePairResponse,
    IdiomSelectAnswer,
    IdiomSelectFeedback,
    IdiomSelectResponse,
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


@dataclass(frozen=True)
class ComparePairGradeResult:
    correct: bool
    feedback: ComparePairFeedback


def grade_compare_pair(
    answer: ComparePairAnswer, response: ComparePairResponse
) -> ComparePairGradeResult:
    """Correct when each sentence is assigned its fitting option."""
    feedback = ComparePairFeedback(
        fits_option_ids=list(answer.fits_option_ids),
        user_fits_option_ids=list(response.fits_option_ids),
    )
    return ComparePairGradeResult(
        correct=list(response.fits_option_ids) == list(answer.fits_option_ids),
        feedback=feedback,
    )


@dataclass(frozen=True)
class CompareMisuseGradeResult:
    correct: bool
    feedback: CompareMisuseFeedback


def grade_compare_misuse(
    answer: CompareMisuseAnswer, response: CompareMisuseResponse
) -> CompareMisuseGradeResult:
    """Correct when both the misused word and its replacement match."""
    feedback = CompareMisuseFeedback(
        misused_option_id=answer.misused_option_id,
        replacement_option_id=answer.replacement_option_id,
        user_misused_option_id=response.misused_option_id,
        user_replacement_option_id=response.replacement_option_id,
        reason=answer.reason,
    )
    correct = (
        response.misused_option_id == answer.misused_option_id
        and response.replacement_option_id == answer.replacement_option_id
    )
    return CompareMisuseGradeResult(correct=correct, feedback=feedback)


@dataclass(frozen=True)
class CompareOrderGradeResult:
    correct: bool
    feedback: CompareOrderFeedback


def grade_compare_order(
    answer: CompareOrderAnswer, response: CompareOrderResponse
) -> CompareOrderGradeResult:
    """Correct when the user order matches strength order weakest to strongest."""
    feedback = CompareOrderFeedback(
        ordered_option_ids=list(answer.ordered_option_ids),
        user_ordered_option_ids=list(response.ordered_option_ids),
    )
    return CompareOrderGradeResult(
        correct=list(response.ordered_option_ids) == list(answer.ordered_option_ids),
        feedback=feedback,
    )


@dataclass(frozen=True)
class IdiomSelectGradeResult:
    correct: bool
    feedback: IdiomSelectFeedback


def grade_idiom_select(
    answer: IdiomSelectAnswer, response: IdiomSelectResponse
) -> IdiomSelectGradeResult:
    """Correct when the selected choice id matches the stored answer."""
    feedback = IdiomSelectFeedback(
        correct_id=answer.correct_id,
        selected_id=response.selected_id,
        option_id=answer.option_id,
    )
    return IdiomSelectGradeResult(
        correct=response.selected_id == answer.correct_id,
        feedback=feedback,
    )
