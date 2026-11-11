"""Create and answer shared exercises; choice items first."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.config import Settings, get_settings
from vocab.drills.select import select_group
from vocab.events import ExerciseAnsweredPayload, record_event
from vocab.exercises.grading import grade_choice
from vocab.exercises.models import Exercise, ExerciseAttempt
from vocab.exercises.schemas import (
    ChoiceAnswer,
    ChoiceAnswerCandidate,
    ChoiceGenOutput,
    ChoicePrompt,
    ChoicePromptCandidate,
    ChoiceResponse,
)
from vocab.lexicon.models import PrecisionGroup
from vocab.llm.graphs import run_structured_role
from vocab.llm.models import LlmCall
from vocab.practice.models import SrsCard
from vocab.practice.srs import review_card


def _group_payload(group: PrecisionGroup) -> dict[str, object]:
    return {
        "id": group.id,
        "head_lemma": group.head_lemma,
        "pos": group.pos,
        "sense_gloss": group.sense_gloss,
        "options": [
            {
                "id": opt.id,
                "word": opt.word,
                "distinction": opt.distinction,
            }
            for opt in group.options
            if opt.status == "approved"
        ],
    }


def _latest_call_id(session: Session, user_id: str, role: str) -> str | None:
    call = session.scalars(
        select(LlmCall)
        .where(LlmCall.user_id == user_id, LlmCall.role == role)
        .order_by(LlmCall.created_at.desc())
    ).first()
    return call.id if call else None


def _validate_choice_ids(group: PrecisionGroup, output: ChoiceGenOutput) -> dict[str, str]:
    """Reject unknown option IDs; return option_id -> word for the prompt."""
    known = {
        opt.id: opt.word
        for opt in group.options
        if opt.status == "approved"
    }
    words: dict[str, str] = {}
    for candidate in output.candidates:
        word = known.get(candidate.option_id)
        if word is None:
            raise ValueError(f"unknown option_id in choice_gen output: {candidate.option_id}")
        words[candidate.option_id] = word
    return words


def _choice_prompt_and_answer(
    output: ChoiceGenOutput, words: dict[str, str]
) -> tuple[ChoicePrompt, ChoiceAnswer]:
    best = next(c for c in output.candidates if c.best)
    prompt = ChoicePrompt(
        situation=output.situation.strip(),
        sentence=output.sentence.strip(),
        candidates=[
            ChoicePromptCandidate(option_id=c.option_id, word=words[c.option_id])
            for c in output.candidates
        ],
    )
    answer = ChoiceAnswer(
        best_option_id=best.option_id,
        candidates=[
            ChoiceAnswerCandidate(
                option_id=c.option_id,
                fit=c.fit,
                reason=c.reason,
                best=c.best,
            )
            for c in output.candidates
        ],
    )
    return prompt, answer


async def create_choice(
    session: Session,
    *,
    user_id: str,
    settings: Settings | None = None,
) -> Exercise:
    """Select a group, generate a choice item, persist prompt and answer."""
    settings = settings or get_settings()
    group = select_group(session, user_id)
    result = await run_structured_role(
        "choice_gen",
        {"group": _group_payload(group)},
        user_id=user_id,
        output_model=ChoiceGenOutput,
        session=session,
        settings=settings,
    )
    assert isinstance(result, ChoiceGenOutput)
    words = _validate_choice_ids(group, result)
    prompt, answer = _choice_prompt_and_answer(result, words)
    exercise = Exercise(
        user_id=user_id,
        group_id=group.id,
        item_type="choice",
        prompt=prompt.model_dump(),
        answer=answer.model_dump(),
        llm_call_id=_latest_call_id(session, user_id, "choice_gen"),
    )
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


def answer_exercise(
    session: Session,
    *,
    exercise: Exercise,
    user_id: str,
    response: ChoiceResponse,
) -> ExerciseAttempt:
    """Grade a choice response, record the event, and maybe review an SRS card."""
    if exercise.item_type != "choice":
        raise ValueError(f"unsupported item_type for answer_exercise: {exercise.item_type}")
    answer = ChoiceAnswer.model_validate(exercise.answer)
    grade = grade_choice(answer, response)
    attempt = ExerciseAttempt(
        exercise_id=exercise.id,
        user_id=user_id,
        response=response.model_dump(),
        correct=grade.correct,
        feedback=grade.feedback.model_dump(),
    )
    session.add(attempt)
    session.flush()
    record_event(
        session,
        user_id=user_id,
        type="exercise_answered",
        subject_type="exercise_attempt",
        subject_id=attempt.id,
        payload=ExerciseAnsweredPayload(
            item_type=exercise.item_type,
            correct=grade.correct,
            option_id=answer.best_option_id,
        ),
    )
    session.commit()
    session.refresh(attempt)

    if grade.correct:
        card = session.scalars(
            select(SrsCard).where(
                SrsCard.user_id == user_id,
                SrsCard.option_id == answer.best_option_id,
            )
        ).first()
        if card is not None:
            review_card(
                session,
                user_id=user_id,
                option_id=answer.best_option_id,
                rating="Good",
                source="exercise",
            )
    return attempt
