"""Create and answer shared exercises: choice, compare, and idiom items."""

from __future__ import annotations

import random
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.config import Settings, get_settings
from vocab.drills.select import select_group
from vocab.events import ExerciseAnsweredPayload, record_event
from vocab.exercises.grading import (
    grade_choice,
    grade_compare_misuse,
    grade_compare_order,
    grade_compare_pair,
    grade_idiom_select,
)
from vocab.exercises.models import Exercise, ExerciseAttempt
from vocab.exercises.schemas import (
    ChoiceAnswer,
    ChoiceAnswerCandidate,
    ChoiceGenOutput,
    ChoicePrompt,
    ChoicePromptCandidate,
    ChoiceResponse,
    CompareItemType,
    CompareMisuseAnswer,
    CompareMisuseGenOutput,
    CompareMisusePrompt,
    CompareMisuseResponse,
    CompareOrderAnswer,
    CompareOrderPrompt,
    CompareOrderResponse,
    ComparePairAnswer,
    ComparePairGenOutput,
    ComparePairPrompt,
    ComparePairResponse,
    IdiomItemType,
    IdiomLlmItemType,
    IdiomMeaningGenOutput,
    IdiomRecogniseGenOutput,
    IdiomSelectAnswer,
    IdiomSelectPrompt,
    IdiomSelectResponse,
    IdiomSituationGenOutput,
    IdiomWriteAnswer,
    IdiomWriteFeedback,
    IdiomWritePrompt,
    IdiomWriteResponse,
)
from vocab.lexicon.models import PrecisionGroup, PrecisionOption
from vocab.llm.graphs import run_structured_role
from vocab.llm.models import LlmCall
from vocab.practice.judge import judge_usage
from vocab.practice.models import SrsCard
from vocab.practice.srs import review_card


def _group_payload(group: PrecisionGroup) -> dict[str, object]:
    return {
        "id": group.id,
        "kind": group.kind,
        "head_lemma": group.head_lemma,
        "pos": group.pos,
        "sense_gloss": group.sense_gloss,
        "options": [
            {
                "id": opt.id,
                "word": opt.word,
                "distinction": opt.distinction,
                "example": opt.example,
                "register": opt.register,
                "details": opt.details or {},
            }
            for opt in group.options
            if opt.status == "approved"
        ],
    }


def _approved_options(group: PrecisionGroup) -> list[PrecisionOption]:
    return [opt for opt in group.options if opt.status == "approved"]


def _option_words(group: PrecisionGroup) -> dict[str, str]:
    return {opt.id: opt.word for opt in _approved_options(group)}


def _prompt_options(group: PrecisionGroup) -> list[ChoicePromptCandidate]:
    return [
        ChoicePromptCandidate(option_id=opt.id, word=opt.word)
        for opt in _approved_options(group)
    ]


def _latest_call_id(session: Session, user_id: str, role: str) -> str | None:
    call = session.scalars(
        select(LlmCall)
        .where(LlmCall.user_id == user_id, LlmCall.role == role)
        .order_by(LlmCall.created_at.desc())
    ).first()
    return call.id if call else None


def _load_group(session: Session, group_id: str) -> PrecisionGroup:
    group = session.scalars(
        select(PrecisionGroup)
        .where(PrecisionGroup.id == group_id)
        .options(selectinload(PrecisionGroup.options))
    ).first()
    if group is None or group.status != "approved":
        raise ValueError(f"unknown or unapproved group: {group_id}")
    if not _approved_options(group):
        raise ValueError(f"group has no approved options: {group_id}")
    return group


def _validate_choice_ids(group: PrecisionGroup, output: ChoiceGenOutput) -> dict[str, str]:
    """Reject unknown option IDs; return option_id -> word for the prompt."""
    known = _option_words(group)
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


def _require_known_ids(known: dict[str, str], *option_ids: str, role: str) -> None:
    for option_id in option_ids:
        if option_id not in known:
            raise ValueError(f"unknown option_id in {role} output: {option_id}")


def _create_compare_order(session: Session, *, user_id: str, group: PrecisionGroup) -> Exercise:
    """Build an order item from details.strength; no LLM call."""
    scored: list[tuple[int, PrecisionOption]] = []
    for opt in _approved_options(group):
        details = opt.details or {}
        strength = details.get("strength")
        if strength is None:
            raise ValueError(f"compare_order requires strength on every option: {group.id}")
        scored.append((int(strength), opt))
    scored.sort(key=lambda row: row[0])
    ordered = [opt for _, opt in scored]
    prompt_opts = [ChoicePromptCandidate(option_id=opt.id, word=opt.word) for opt in ordered]
    random.shuffle(prompt_opts)
    prompt = CompareOrderPrompt(options=prompt_opts)
    answer = CompareOrderAnswer(ordered_option_ids=[opt.id for opt in ordered])
    exercise = Exercise(
        user_id=user_id,
        group_id=group.id,
        item_type="compare_order",
        prompt=prompt.model_dump(),
        answer=answer.model_dump(),
        llm_call_id=None,
    )
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


async def create_compare(
    session: Session,
    *,
    user_id: str,
    group_id: str,
    item_type: CompareItemType,
    settings: Settings | None = None,
) -> Exercise:
    """Create a compare exercise for a group; order items need no LLM."""
    settings = settings or get_settings()
    group = _load_group(session, group_id)
    if item_type == "compare_order":
        return _create_compare_order(session, user_id=user_id, group=group)

    known = _option_words(group)
    variables = {"group": _group_payload(group), "item_type": item_type}

    if item_type == "compare_pair":
        result = await run_structured_role(
            "compare_gen",
            variables,
            user_id=user_id,
            output_model=ComparePairGenOutput,
            session=session,
            settings=settings,
        )
        assert isinstance(result, ComparePairGenOutput)
        for sentence in result.sentences:
            _require_known_ids(known, sentence.fits_option_id, role="compare_gen")
        prompt = ComparePairPrompt(
            sentences=[s.text.strip() for s in result.sentences],
            options=_prompt_options(group),
        )
        answer = ComparePairAnswer(
            fits_option_ids=[s.fits_option_id for s in result.sentences],
        )
    elif item_type == "compare_misuse":
        result = await run_structured_role(
            "compare_gen",
            variables,
            user_id=user_id,
            output_model=CompareMisuseGenOutput,
            session=session,
            settings=settings,
        )
        assert isinstance(result, CompareMisuseGenOutput)
        _require_known_ids(
            known,
            result.misused_option_id,
            result.replacement_option_id,
            role="compare_gen",
        )
        prompt = CompareMisusePrompt(
            sentence=result.sentence.strip(),
            options=_prompt_options(group),
        )
        answer = CompareMisuseAnswer(
            misused_option_id=result.misused_option_id,
            replacement_option_id=result.replacement_option_id,
            reason=result.reason.strip(),
        )
    else:
        raise ValueError(f"unsupported compare item_type: {item_type}")

    exercise = Exercise(
        user_id=user_id,
        group_id=group.id,
        item_type=item_type,
        prompt=prompt.model_dump(),
        answer=answer.model_dump(),
        llm_call_id=_latest_call_id(session, user_id, "compare_gen"),
    )
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


def _review_options(session: Session, *, user_id: str, option_ids: list[str]) -> None:
    """Review each carded option with Good / exercise after a correct attempt."""
    for option_id in option_ids:
        card = session.scalars(
            select(SrsCard).where(
                SrsCard.user_id == user_id,
                SrsCard.option_id == option_id,
            )
        ).first()
        if card is not None:
            review_card(
                session,
                user_id=user_id,
                option_id=option_id,
                rating="Good",
                source="exercise",
            )


def answer_exercise(
    session: Session,
    *,
    exercise: Exercise,
    user_id: str,
    response: (
        ChoiceResponse
        | ComparePairResponse
        | CompareMisuseResponse
        | CompareOrderResponse
        | IdiomSelectResponse
    ),
) -> ExerciseAttempt:
    """Grade a response, record exercise_answered, and maybe review SRS cards."""
    item_type = exercise.item_type
    event_option_id: str | None = None
    review_ids: list[str] = []
    response_dump: dict[str, Any]
    feedback_dump: dict[str, Any]
    correct: bool

    if item_type == "choice":
        if not isinstance(response, ChoiceResponse):
            raise ValueError("choice exercises require ChoiceResponse")
        answer = ChoiceAnswer.model_validate(exercise.answer)
        grade = grade_choice(answer, response)
        correct = grade.correct
        response_dump = response.model_dump()
        feedback_dump = grade.feedback.model_dump()
        event_option_id = answer.best_option_id
        if correct:
            review_ids = [answer.best_option_id]
    elif item_type == "compare_pair":
        if not isinstance(response, ComparePairResponse):
            raise ValueError("compare_pair exercises require ComparePairResponse")
        answer = ComparePairAnswer.model_validate(exercise.answer)
        grade = grade_compare_pair(answer, response)
        correct = grade.correct
        response_dump = response.model_dump()
        feedback_dump = grade.feedback.model_dump()
        event_option_id = answer.fits_option_ids[0] if answer.fits_option_ids else None
        if correct:
            review_ids = list(answer.fits_option_ids)
    elif item_type == "compare_misuse":
        if not isinstance(response, CompareMisuseResponse):
            raise ValueError("compare_misuse exercises require CompareMisuseResponse")
        answer = CompareMisuseAnswer.model_validate(exercise.answer)
        grade = grade_compare_misuse(answer, response)
        correct = grade.correct
        response_dump = response.model_dump()
        feedback_dump = grade.feedback.model_dump()
        event_option_id = answer.replacement_option_id
        if correct:
            review_ids = [answer.replacement_option_id]
    elif item_type == "compare_order":
        if not isinstance(response, CompareOrderResponse):
            raise ValueError("compare_order exercises require CompareOrderResponse")
        answer = CompareOrderAnswer.model_validate(exercise.answer)
        grade = grade_compare_order(answer, response)
        correct = grade.correct
        response_dump = response.model_dump()
        feedback_dump = grade.feedback.model_dump()
        event_option_id = None
        if correct:
            review_ids = list(answer.ordered_option_ids)
    elif item_type in ("idiom_recognise", "idiom_meaning", "idiom_situation"):
        if not isinstance(response, IdiomSelectResponse):
            raise ValueError(f"{item_type} exercises require IdiomSelectResponse")
        answer = IdiomSelectAnswer.model_validate(exercise.answer)
        grade = grade_idiom_select(answer, response)
        correct = grade.correct
        response_dump = response.model_dump()
        feedback_dump = grade.feedback.model_dump()
        event_option_id = answer.option_id
        if correct:
            review_ids = [answer.option_id]
    else:
        raise ValueError(f"unsupported item_type for answer_exercise: {item_type}")

    attempt = ExerciseAttempt(
        exercise_id=exercise.id,
        user_id=user_id,
        response=response_dump,
        correct=correct,
        feedback=feedback_dump,
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
            item_type=item_type,
            correct=correct,
            option_id=event_option_id,
        ),
    )
    session.commit()
    session.refresh(attempt)

    if correct and review_ids:
        _review_options(session, user_id=user_id, option_ids=review_ids)
    return attempt


def _load_idiom_group(session: Session, group_id: str) -> PrecisionGroup:
    group = _load_group(session, group_id)
    if group.kind != "idiom":
        raise ValueError(f"group is not an idiom set: {group_id}")
    return group


def _load_option(session: Session, option_id: str) -> PrecisionOption:
    opt = session.get(PrecisionOption, option_id)
    if opt is None or opt.status != "approved":
        raise ValueError(f"unknown or unapproved option: {option_id}")
    return opt


def _idiom_word(group: PrecisionGroup, option_id: str) -> str:
    known = _option_words(group)
    word = known.get(option_id)
    if word is None:
        raise ValueError(f"unknown option_id in idiom group: {option_id}")
    return word


def create_idiom_write(
    session: Session,
    *,
    user_id: str,
    option_id: str,
) -> Exercise:
    """Step 4: prompt the user to write a sentence; graded later by usage_judge."""
    opt = _load_option(session, option_id)
    group = session.get(PrecisionGroup, opt.group_id)
    if group is None or group.kind != "idiom" or group.status != "approved":
        raise ValueError(f"option is not on an approved idiom group: {option_id}")
    details = opt.details or {}
    meaning = str(details.get("meaning") or opt.distinction).strip()
    avoid_when = str(details.get("avoid_when") or "").strip()
    if not meaning:
        raise ValueError(f"idiom option missing meaning: {option_id}")
    prompt = IdiomWritePrompt(
        option_id=opt.id,
        word=opt.word,
        meaning=meaning,
        avoid_when=avoid_when,
    )
    answer = IdiomWriteAnswer(option_id=opt.id, word=opt.word, meaning=meaning)
    exercise = Exercise(
        user_id=user_id,
        group_id=group.id,
        item_type="idiom_write",
        prompt=prompt.model_dump(),
        answer=answer.model_dump(),
        llm_call_id=None,
    )
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


async def create_idiom(
    session: Session,
    *,
    user_id: str,
    group_id: str,
    item_type: IdiomItemType,
    option_id: str | None = None,
    settings: Settings | None = None,
) -> Exercise:
    """Create an idiom exercise; write items need no LLM, others use compare_gen."""
    settings = settings or get_settings()
    if item_type == "idiom_write":
        if not option_id:
            group = _load_idiom_group(session, group_id)
            approved = _approved_options(group)
            option_id = approved[0].id
        return create_idiom_write(session, user_id=user_id, option_id=option_id)

    group = _load_idiom_group(session, group_id)
    known = _option_words(group)
    llm_type: IdiomLlmItemType = item_type  # type: ignore[assignment]
    variables = {"group": _group_payload(group), "item_type": llm_type}

    if item_type == "idiom_recognise":
        result = await run_structured_role(
            "compare_gen",
            variables,
            user_id=user_id,
            output_model=IdiomRecogniseGenOutput,
            session=session,
            settings=settings,
        )
        assert isinstance(result, IdiomRecogniseGenOutput)
        _require_known_ids(known, result.option_id, role="compare_gen")
        prompt = IdiomSelectPrompt(
            stem=result.paragraph.strip(),
            word=None,
            choices=list(result.choices),
        )
        answer = IdiomSelectAnswer(correct_id=result.option_id, option_id=result.option_id)
    elif item_type == "idiom_meaning":
        result = await run_structured_role(
            "compare_gen",
            variables,
            user_id=user_id,
            output_model=IdiomMeaningGenOutput,
            session=session,
            settings=settings,
        )
        assert isinstance(result, IdiomMeaningGenOutput)
        _require_known_ids(known, result.option_id, role="compare_gen")
        word = _idiom_word(group, result.option_id)
        prompt = IdiomSelectPrompt(
            stem="Which meaning fits this idiom?",
            word=word,
            choices=list(result.choices),
        )
        answer = IdiomSelectAnswer(correct_id=result.correct_id, option_id=result.option_id)
    elif item_type == "idiom_situation":
        result = await run_structured_role(
            "compare_gen",
            variables,
            user_id=user_id,
            output_model=IdiomSituationGenOutput,
            session=session,
            settings=settings,
        )
        assert isinstance(result, IdiomSituationGenOutput)
        _require_known_ids(known, result.option_id, role="compare_gen")
        word = _idiom_word(group, result.option_id)
        prompt = IdiomSelectPrompt(
            stem="Which situation fits this idiom best?",
            word=word,
            choices=list(result.choices),
        )
        answer = IdiomSelectAnswer(correct_id=result.correct_id, option_id=result.option_id)
    else:
        raise ValueError(f"unsupported idiom item_type: {item_type}")

    exercise = Exercise(
        user_id=user_id,
        group_id=group.id,
        item_type=item_type,
        prompt=prompt.model_dump(),
        answer=answer.model_dump(),
        llm_call_id=_latest_call_id(session, user_id, "compare_gen"),
    )
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


async def answer_idiom_write(
    session: Session,
    *,
    exercise: Exercise,
    user_id: str,
    response: IdiomWriteResponse,
    settings: Settings | None = None,
) -> ExerciseAttempt:
    """Grade a written sentence with usage_judge using the idiom meaning."""
    if exercise.item_type != "idiom_write":
        raise ValueError("answer_idiom_write requires idiom_write")
    settings = settings or get_settings()
    answer = IdiomWriteAnswer.model_validate(exercise.answer)
    sentence = response.sentence.strip()
    if not sentence:
        raise ValueError("sentence must not be empty")
    judge, _call_id = await judge_usage(
        session,
        user_id=user_id,
        sentence=sentence,
        word=answer.word,
        distinction=answer.meaning,
        settings=settings,
    )
    correct = bool(judge.correct)
    feedback = IdiomWriteFeedback(
        correct=correct,
        explanation=judge.explanation,
        option_id=answer.option_id,
        word=answer.word,
    )
    attempt = ExerciseAttempt(
        exercise_id=exercise.id,
        user_id=user_id,
        response=response.model_dump(),
        correct=correct,
        feedback=feedback.model_dump(),
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
            item_type="idiom_write",
            correct=correct,
            option_id=answer.option_id,
        ),
    )
    session.commit()
    session.refresh(attempt)
    if correct:
        _review_options(session, user_id=user_id, option_ids=[answer.option_id])
    return attempt


def list_compare_groups(session: Session) -> list[PrecisionGroup]:
    """Approved confusable and precision sets available as compare cards."""
    return list(
        session.scalars(
            select(PrecisionGroup)
            .where(
                PrecisionGroup.status == "approved",
                PrecisionGroup.kind.in_(("confusable", "precision")),
            )
            .order_by(PrecisionGroup.id)
            .options(selectinload(PrecisionGroup.options))
        ).all()
    )


def list_idiom_groups(session: Session) -> list[PrecisionGroup]:
    """Approved idiom sets for the idioms page."""
    return list(
        session.scalars(
            select(PrecisionGroup)
            .where(
                PrecisionGroup.status == "approved",
                PrecisionGroup.kind == "idiom",
            )
            .order_by(PrecisionGroup.id)
            .options(selectinload(PrecisionGroup.options))
        ).all()
    )


def compare_card(session: Session, group_id: str) -> PrecisionGroup:
    """Load one approved group for a compare card page."""
    return _load_group(session, group_id)


def idiom_card(session: Session, group_id: str) -> PrecisionGroup:
    """Load one approved idiom group for the idiom card page."""
    return _load_idiom_group(session, group_id)
