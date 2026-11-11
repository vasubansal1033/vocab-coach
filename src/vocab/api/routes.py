"""JSON endpoints consumed by the React SPA under /api."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from vocab.account.service import delete_user, export_user
from vocab.api.schemas import (
    AcceptIn,
    AccountLimitsOut,
    AccountOut,
    CompareCardOut,
    CompareGroupListItemOut,
    CompareOptionOut,
    ConversationCreateIn,
    ConversationListOut,
    ConversationOut,
    DashboardOut,
    DrillAnswerIn,
    DrillAttemptOut,
    DrillDisputeIn,
    DrillHintOut,
    DrillOut,
    DrillSummaryOut,
    DrillWeekOut,
    ExerciseAttemptIn,
    ExerciseAttemptOut,
    ExerciseCreateCompareIn,
    ExerciseOut,
    FeedbackOut,
    LemmaDetailOut,
    LemmaOptionOut,
    MessageIn,
    MessageOut,
    MetricWeekOut,
    OveruseGroupOut,
    OveruseRowOut,
    RecapCrutchOut,
    RecapOut,
    RecapWordOut,
    RetryIn,
    RetryOut,
    ReviewDueOut,
    ReviewIn,
    ReviewOptionOut,
    StatusOut,
    SuggestionActionOut,
    SuggestionOptionOut,
    SuggestionOut,
    UserOut,
)
from vocab.auth.authorize import authorize
from vocab.auth.deps import SESSION_KEY, current_user
from vocab.auth.models import User
from vocab.config import Settings, get_settings
from vocab.conversation import service
from vocab.conversation.feedback import ensure_message_feedback
from vocab.conversation.models import Conversation, Message
from vocab.db import get_session
from vocab.drills.models import Drill, DrillAttempt
from vocab.drills.service import (
    create_drill,
    dispute_attempt,
    grade_attempt,
    hint_for,
    intended_distinction,
    summarize_attempts,
)
from vocab.editor.models import Suggestion, SuggestionOption
from vocab.exercises.models import Exercise, ExerciseAttempt
from vocab.exercises.schemas import (
    ChoiceResponse,
    CompareMisuseResponse,
    CompareOrderResponse,
    ComparePairResponse,
)
from vocab.exercises.service import (
    answer_exercise,
    compare_card,
    create_choice,
    create_compare,
    list_compare_groups,
)
from vocab.lexicon.models import PrecisionGroup
from vocab.llm.models import LlmCall
from vocab.metrics.queries import (
    acceptance_rate,
    crutch_rate,
    crutch_rate_weekly,
    default_window,
    drill_score_weekly,
    lemma_detail,
    lexical_diversity,
    misuse_rate,
    overuse_lift,
    spontaneous_correct_use,
)
from vocab.practice.srs import due_options, review_card

logger = logging.getLogger(__name__)


def _cloze(example: str, word: str) -> str:
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    return pattern.sub("____", example, count=1)


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, display_name=user.display_name, email=user.email)


def _message_out(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat() if message.created_at else None,
    )


def _conversation_out(
    conversation: Conversation, *, with_messages: bool = False
) -> ConversationOut:
    return ConversationOut(
        id=conversation.id,
        title=conversation.title,
        feedback_expectations=conversation.feedback_expectations,
        flow_mode=bool(conversation.flow_mode),
        allow_idioms=bool(conversation.allow_idioms),
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
        messages=[_message_out(m) for m in conversation.messages] if with_messages else None,
    )


def _suggestion_out(suggestion: Suggestion, *, why: str | None = None) -> SuggestionOut:
    return SuggestionOut(
        id=suggestion.id,
        original_text=suggestion.original_text,
        span_start=suggestion.span_start,
        span_end=suggestion.span_end,
        question=suggestion.question,
        why=why,
        options=[
            SuggestionOptionOut(id=opt.id, word=opt.word, meaning=opt.meaning)
            for opt in suggestion.options
        ],
    )


def _suggestion_in_conversation(
    session: Session, conversation_id: str, suggestion: Suggestion
) -> bool:
    message = session.get(Message, suggestion.message_id)
    return message is not None and message.conversation_id == conversation_id


def _account_limits(session: Session, user_id: str, settings: Settings) -> AccountLimitsOut:
    since = datetime.now(UTC) - timedelta(days=1)
    calls = int(
        session.scalar(
            select(func.count())
            .select_from(LlmCall)
            .where(LlmCall.user_id == user_id, LlmCall.created_at >= since)
        )
        or 0
    )
    cost = float(
        session.scalar(
            select(func.coalesce(func.sum(LlmCall.cost_usd), 0.0)).where(
                LlmCall.user_id == user_id, LlmCall.created_at >= since
            )
        )
        or 0.0
    )
    return AccountLimitsOut(
        llm_calls_24h=calls,
        llm_call_limit_per_day=settings.llm_rate_limit_per_day,
        llm_cost_usd_24h=cost,
        llm_cost_limit_usd_per_day=settings.llm_cost_limit_usd_per_day,
    )


def build_router(settings: Settings | None = None) -> APIRouter:
    settings = settings or get_settings()
    router = APIRouter(prefix="/api")

    def _owned_conversation(session: Session, conversation_id: str, user: User) -> Conversation:
        conversation = service.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", conversation)
        return conversation

    @router.get("/me", response_model=UserOut)
    def me(user: User = Depends(current_user)) -> UserOut:
        return _user_out(user)

    @router.get("/account", response_model=AccountOut)
    def account(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> AccountOut:
        return AccountOut(
            user=_user_out(user),
            limits=_account_limits(session, user.id, settings),
            privacy_note=settings.llm_privacy_note,
        )

    @router.get("/account/export")
    def account_export(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        return JSONResponse(
            export_user(session, user.id),
            headers={"Content-Disposition": 'attachment; filename="vocab-export.json"'},
        )

    @router.post("/account/delete", status_code=204)
    def account_delete(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> None:
        delete_user(session, user.id)
        request.session.clear()
        request.session.pop(SESSION_KEY, None)

    @router.get("/conversations", response_model=ConversationListOut)
    def list_conversations(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ConversationListOut:
        items = service.list_conversations(session, user.id)
        return ConversationListOut(conversations=[_conversation_out(c) for c in items])

    @router.post("/conversations", response_model=ConversationOut)
    def create_conversation(
        body: ConversationCreateIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ConversationOut:
        conversation = service.create_conversation(
            session,
            user.id,
            body.resolved_name(),
            feedback_expectations=body.feedback_expectations,
            flow_mode=body.flow_mode,
            allow_idioms=body.allow_idioms,
        )
        return _conversation_out(conversation)

    @router.get("/conversations/{conversation_id}", response_model=ConversationOut)
    def get_conversation(
        conversation_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ConversationOut:
        conversation = _owned_conversation(session, conversation_id, user)
        return _conversation_out(conversation, with_messages=True)

    @router.delete("/conversations/{conversation_id}", status_code=204)
    def delete_conversation(
        conversation_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> None:
        conversation = service.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "delete", conversation)
        service.delete_conversation(session, conversation)

    @router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
    async def post_message(
        conversation_id: str,
        body: MessageIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> MessageOut:
        conversation = _owned_conversation(session, conversation_id, user)
        message = service.post_user_message(
            session, conversation=conversation, user_id=user.id, content=body.content
        )
        from vocab.practice.usage import process_message_usage

        await process_message_usage(
            session,
            user_id=user.id,
            conversation_id=conversation.id,
            message=message,
            settings=settings,
        )
        return _message_out(message)

    @router.get("/conversations/{conversation_id}/messages/{message_id}/partner")
    async def partner_sse(
        conversation_id: str,
        message_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> EventSourceResponse:
        conversation = _owned_conversation(session, conversation_id, user)
        message = session.get(Message, message_id)
        if message is None or message.conversation_id != conversation.id:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", message)

        history = service.chat_history(session, conversation.id)
        topic = conversation.title
        from vocab.practice.srs import due_words as due_word_list

        due = due_word_list(session, user.id, limit=3)
        conv_id = conversation.id
        uid = user.id

        async def event_gen():  # noqa: ANN202
            from vocab.llm.graphs import run_partner_stream

            chunks: list[str] = []
            try:
                async for chunk in run_partner_stream(
                    {"topic": topic, "due_words": due},
                    user_id=uid,
                    history=history,
                    session=session,
                    settings=settings,
                ):
                    chunks.append(chunk)
                    yield ServerSentEvent(data=chunk, event="token")
                full = "".join(chunks).strip() or "(no reply)"
                service.save_partner_message(
                    session,
                    conversation_id=conv_id,
                    user_id=uid,
                    content=full,
                )
                yield ServerSentEvent(data=full, event="done")
            except Exception as exc:
                logger.exception("partner stream failed")
                yield ServerSentEvent(data=f"Partner reply failed: {exc}", event="error")

        return EventSourceResponse(event_gen())

    @router.get(
        "/conversations/{conversation_id}/messages/{message_id}/feedback",
        response_model=FeedbackOut,
    )
    async def feedback(
        conversation_id: str,
        message_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> FeedbackOut:
        conversation = _owned_conversation(session, conversation_id, user)
        message = session.get(Message, message_id)
        if message is None or message.conversation_id != conversation.id:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", message)

        result = await ensure_message_feedback(
            session,
            conversation=conversation,
            message=message,
            user_id=user.id,
            settings=settings,
        )
        if result.failed:
            return FeedbackOut(failed=True, content=result.content)
        return FeedbackOut(
            failed=False,
            content=result.content,
            overview=result.overview,
            highlighted_html=result.highlighted_html,
            keep=result.keep,
            suggestions=[
                _suggestion_out(s, why=result.why_by_original.get(s.original_text))
                for s in result.suggestions
            ],
        )

    @router.post(
        "/conversations/{conversation_id}/suggestions/{suggestion_id}/accept",
        response_model=SuggestionActionOut,
    )
    def accept_suggestion(
        conversation_id: str,
        suggestion_id: str,
        body: AcceptIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> SuggestionActionOut:
        _owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if (
            suggestion is None
            or suggestion.user_id != user.id
            or not _suggestion_in_conversation(session, conversation_id, suggestion)
        ):
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        option = session.get(SuggestionOption, body.option_id)
        if option is None or option.suggestion_id != suggestion.id:
            raise HTTPException(status_code=404, detail="Not found")
        service.accept_suggestion(session, suggestion=suggestion, option=option, user_id=user.id)
        return SuggestionActionOut(
            dismissed=False,
            accepted_word=option.word,
            original_text=suggestion.original_text,
        )

    @router.post(
        "/conversations/{conversation_id}/suggestions/{suggestion_id}/dismiss",
        response_model=SuggestionActionOut,
    )
    def dismiss_suggestion(
        conversation_id: str,
        suggestion_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> SuggestionActionOut:
        _owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if (
            suggestion is None
            or suggestion.user_id != user.id
            or not _suggestion_in_conversation(session, conversation_id, suggestion)
        ):
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        service.dismiss_suggestion(session, suggestion=suggestion, user_id=user.id)
        return SuggestionActionOut(
            dismissed=True,
            accepted_word=None,
            original_text=suggestion.original_text,
        )

    @router.post(
        "/conversations/{conversation_id}/suggestions/{suggestion_id}/retry",
        response_model=RetryOut,
    )
    def retry_suggestion(
        conversation_id: str,
        suggestion_id: str,
        body: RetryIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RetryOut:
        _owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if (
            suggestion is None
            or suggestion.user_id != user.id
            or not _suggestion_in_conversation(session, conversation_id, suggestion)
        ):
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        option = session.get(SuggestionOption, body.option_id)
        if option is None or option.suggestion_id != suggestion.id:
            raise HTTPException(status_code=404, detail="Not found")
        text = service.retry_suggestion(
            session, suggestion=suggestion, option=option, user_id=user.id
        )
        return RetryOut(text=text)

    @router.get("/conversations/{conversation_id}/recap", response_model=RecapOut)
    async def conversation_recap(
        conversation_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RecapOut:
        conversation = _owned_conversation(session, conversation_id, user)
        recap = await service.conversation_recap(
            session, conversation=conversation, user_id=user.id, settings=settings
        )
        return RecapOut(
            words_to_keep=[
                RecapWordOut(word=w.word, option_id=w.option_id, source=w.source)
                for w in recap.words_to_keep
            ],
            crutch_words=[
                RecapCrutchOut(lemma=c.lemma, count=c.count) for c in recap.crutch_words
            ],
            rewrite_sentence=recap.rewrite_sentence,
        )

    @router.get("/dashboard", response_model=DashboardOut)
    def dashboard(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
        prompt_version: int | None = None,
        model: str | None = None,
    ) -> DashboardOut:
        start, end = default_window()
        weekly = crutch_rate_weekly(session, user.id, start, end)
        drills = drill_score_weekly(session, user.id, start, end)
        overuse = overuse_lift(session, user.id, start, end)
        return DashboardOut(
            window_start=start.isoformat(),
            window_end=end.isoformat(),
            crutch_rate=crutch_rate(session, user.id, start, end),
            weekly=[MetricWeekOut(label=w.label, rate=w.rate) for w in weekly],
            overuse=[
                OveruseRowOut(
                    word=row.word,
                    uses=row.uses,
                    lift=row.lift,
                    groups=[
                        OveruseGroupOut(id=g.id, sense_gloss=g.sense_gloss) for g in row.groups
                    ],
                )
                for row in overuse
            ],
            acceptance=acceptance_rate(
                session,
                user.id,
                start,
                end,
                prompt_version=prompt_version,
                model=model,
            ),
            spontaneous=spontaneous_correct_use(session, user.id, start, end),
            misuse=misuse_rate(session, user.id, start, end),
            drill_weeks=[DrillWeekOut(label=w.label, score=w.score) for w in drills],
            mtld=lexical_diversity(session, user.id, start, end),
        )

    @router.get("/dashboard/lemma/{lemma}", response_model=LemmaDetailOut)
    def dashboard_lemma(
        lemma: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> LemmaDetailOut:
        start, end = default_window()
        detail = lemma_detail(session, user.id, start, end, lemma)
        return LemmaDetailOut(
            lemma=detail.lemma,
            weekly=[MetricWeekOut(label=w.label, rate=w.rate) for w in detail.weekly],
            options=[
                LemmaOptionOut(
                    option_id=o.option_id,
                    word=o.word,
                    uses=o.uses,
                    correct_uses=o.correct_uses,
                )
                for o in detail.options
            ],
        )

    @router.get("/review", response_model=ReviewDueOut)
    def review_due(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ReviewDueOut:
        options = due_options(session, user.id, limit=1)
        if not options:
            return ReviewDueOut(option=None)
        option = options[0]
        return ReviewDueOut(
            option=ReviewOptionOut(
                id=option.id,
                word=option.word,
                distinction=option.distinction,
                example=option.example,
                cloze=_cloze(option.example, option.word),
            )
        )

    @router.post("/review/{option_id}", response_model=StatusOut)
    def review_submit(
        option_id: str,
        body: ReviewIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> StatusOut:
        review_card(
            session,
            user_id=user.id,
            option_id=option_id,
            rating=body.rating,
            source="review_page",
        )
        return StatusOut(status="ok")

    def _drill_out(session: Session, drill: Drill) -> DrillOut:
        return DrillOut(
            id=drill.id,
            vague_sentence=drill.vague_sentence,
            intended_word=drill.intended_word,
            context=drill.context,
            intended_distinction=intended_distinction(session, drill),
        )

    @router.post("/drills", response_model=DrillOut)
    async def drills_create(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> DrillOut:
        drill = await create_drill(session, user_id=user.id, settings=settings)
        return _drill_out(session, drill)

    @router.get("/drills/summary", response_model=DrillSummaryOut)
    def drills_summary(
        attempt_ids: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> DrillSummaryOut:
        ids = [part.strip() for part in attempt_ids.split(",") if part.strip()]
        if not ids:
            raise HTTPException(status_code=400, detail="attempt_ids required")
        attempts = list(
            session.scalars(
                select(DrillAttempt)
                .where(DrillAttempt.user_id == user.id, DrillAttempt.id.in_(ids))
                .options(selectinload(DrillAttempt.drill))
            )
        )
        by_id = {a.id: a for a in attempts}
        ordered = [by_id[i] for i in ids if i in by_id]
        summary = summarize_attempts(ordered)
        return DrillSummaryOut(
            mean_score=summary.mean_score,
            words_practised=summary.words_practised,
            total_hints_used=summary.total_hints_used,
        )

    @router.post("/drills/attempts/{attempt_id}/dispute", response_model=StatusOut)
    def drills_dispute(
        attempt_id: str,
        body: DrillDisputeIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> StatusOut:
        attempt = session.get(DrillAttempt, attempt_id)
        if attempt is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", attempt)
        dispute_attempt(
            session,
            attempt=attempt,
            user_id=user.id,
            note=body.note,
        )
        return StatusOut(status="ok")

    @router.get("/drills/{drill_id}", response_model=DrillOut)
    def drills_get(
        drill_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> DrillOut:
        drill = session.get(Drill, drill_id)
        if drill is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", drill)
        return _drill_out(session, drill)

    @router.get("/drills/{drill_id}/hint", response_model=DrillHintOut)
    def drills_hint(
        drill_id: str,
        level: int,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> DrillHintOut:
        if level not in (1, 2, 3):
            raise HTTPException(status_code=400, detail="level must be 1, 2 or 3")
        drill = session.get(Drill, drill_id)
        if drill is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", drill)
        return DrillHintOut(level=level, text=hint_for(session, drill, level))

    @router.post("/drills/{drill_id}/attempt", response_model=DrillAttemptOut)
    async def drills_attempt(
        drill_id: str,
        body: DrillAnswerIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> DrillAttemptOut:
        drill = session.get(Drill, drill_id)
        if drill is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", drill)
        attempt = await grade_attempt(
            session,
            drill=drill,
            user_id=user.id,
            answer=body.answer,
            hints_used=body.hints_used,
            settings=settings,
        )
        grade = attempt.grade if isinstance(attempt.grade, dict) else None
        return DrillAttemptOut(
            id=attempt.id,
            answer=attempt.answer,
            score=attempt.score,
            grade=grade,
            hints_used=attempt.hints_used,
        )

    def _exercise_out(exercise: Exercise) -> ExerciseOut:
        prompt = exercise.prompt if isinstance(exercise.prompt, dict) else {}
        return ExerciseOut(
            id=exercise.id,
            item_type=exercise.item_type,
            prompt=prompt,
        )

    def _attempt_out(attempt: ExerciseAttempt) -> ExerciseAttemptOut:
        feedback = attempt.feedback if isinstance(attempt.feedback, dict) else {}
        return ExerciseAttemptOut(
            id=attempt.id,
            correct=bool(attempt.correct),
            feedback=feedback,
        )

    def _has_strength_order(group: PrecisionGroup) -> bool:
        approved = [o for o in group.options if o.status == "approved"]
        if len(approved) < 2:
            return False
        return all(
            isinstance((o.details or {}).get("strength"), int) for o in approved
        )

    def _compare_card_out(group: PrecisionGroup) -> CompareCardOut:
        options: list[CompareOptionOut] = []
        for opt in group.options:
            if opt.status != "approved":
                continue
            details = opt.details or {}
            strength = details.get("strength")
            options.append(
                CompareOptionOut(
                    id=opt.id,
                    word=opt.word,
                    distinction=opt.distinction,
                    example=opt.example,
                    speech_register=opt.register,
                    collocations=list(details.get("collocations") or []),
                    connotation=details.get("connotation"),
                    strength=int(strength) if isinstance(strength, int) else None,
                )
            )
        options.sort(
            key=lambda o: (o.strength is None, o.strength if o.strength is not None else 0, o.word)
        )
        return CompareCardOut(
            id=group.id,
            kind=group.kind,
            sense_gloss=group.sense_gloss,
            pos=group.pos,
            options=options,
            has_strength_order=_has_strength_order(group),
        )

    def _response_for_attempt(
        exercise: Exercise, body: ExerciseAttemptIn
    ) -> (
        ChoiceResponse
        | ComparePairResponse
        | CompareMisuseResponse
        | CompareOrderResponse
    ):
        if exercise.item_type == "choice":
            if not body.best_option_id:
                raise HTTPException(status_code=422, detail="best_option_id is required")
            return ChoiceResponse(
                best_option_id=body.best_option_id,
                marked_option_ids=body.marked_option_ids,
            )
        if exercise.item_type == "compare_pair":
            if not body.fits_option_ids or len(body.fits_option_ids) != 2:
                raise HTTPException(status_code=422, detail="fits_option_ids needs two ids")
            return ComparePairResponse(fits_option_ids=body.fits_option_ids)
        if exercise.item_type == "compare_misuse":
            if not body.misused_option_id or not body.replacement_option_id:
                raise HTTPException(
                    status_code=422,
                    detail="misused_option_id and replacement_option_id are required",
                )
            return CompareMisuseResponse(
                misused_option_id=body.misused_option_id,
                replacement_option_id=body.replacement_option_id,
            )
        if exercise.item_type == "compare_order":
            if not body.ordered_option_ids:
                raise HTTPException(status_code=422, detail="ordered_option_ids is required")
            return CompareOrderResponse(ordered_option_ids=body.ordered_option_ids)
        raise HTTPException(status_code=400, detail=f"unsupported item_type: {exercise.item_type}")

    @router.get("/compare", response_model=list[CompareGroupListItemOut])
    def compare_list(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> list[CompareGroupListItemOut]:
        del user  # auth only
        rows: list[CompareGroupListItemOut] = []
        for group in list_compare_groups(session):
            words = [o.word for o in group.options if o.status == "approved"]
            rows.append(
                CompareGroupListItemOut(
                    id=group.id,
                    kind=group.kind,
                    sense_gloss=group.sense_gloss,
                    words=words,
                    has_strength_order=_has_strength_order(group),
                )
            )
        return rows

    @router.get("/compare/{group_id}", response_model=CompareCardOut)
    def compare_get(
        group_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> CompareCardOut:
        del user  # auth only; lexicon is shared
        try:
            group = compare_card(session, group_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        return _compare_card_out(group)

    @router.post("/exercises/choice", response_model=ExerciseOut)
    async def exercises_choice_create(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ExerciseOut:
        exercise = await create_choice(session, user_id=user.id, settings=settings)
        return _exercise_out(exercise)

    @router.post("/exercises/compare", response_model=ExerciseOut)
    async def exercises_compare_create(
        body: ExerciseCreateCompareIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ExerciseOut:
        try:
            exercise = await create_compare(
                session,
                user_id=user.id,
                group_id=body.group_id,
                item_type=body.item_type,
                settings=settings,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _exercise_out(exercise)

    @router.get("/exercises/{exercise_id}", response_model=ExerciseOut)
    def exercises_get(
        exercise_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ExerciseOut:
        exercise = session.get(Exercise, exercise_id)
        if exercise is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", exercise)
        return _exercise_out(exercise)

    @router.post("/exercises/{exercise_id}/attempt", response_model=ExerciseAttemptOut)
    def exercises_attempt(
        exercise_id: str,
        body: ExerciseAttemptIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> ExerciseAttemptOut:
        exercise = session.get(Exercise, exercise_id)
        if exercise is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", exercise)
        response = _response_for_attempt(exercise, body)
        attempt = answer_exercise(
            session,
            exercise=exercise,
            user_id=user.id,
            response=response,
        )
        return _attempt_out(attempt)

    return router
