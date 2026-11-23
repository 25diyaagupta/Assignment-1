"""Orchestration: request -> model -> interpretation -> exact decision."""

from collections.abc import Sequence

from reminder_agent.calendar_facts import calendar_facts
from reminder_agent.guard import leaks
from reminder_agent.interpretation import Interpretation, parse_interpretation
from reminder_agent.output import DecisionOutput
from reminder_agent.ports import ModelClient
from reminder_agent.prompt import (
    RESPONSE_SCHEMA,
    build_user_message,
    load_system_prompt,
)
from reminder_agent.request import Request
from reminder_agent.resolve import format_due, resolve_due

ASK_GENERIC = "Could you tell me what to remind you about and when?"
ASK_TASK = "What should I remind you about?"
ASK_REFERENCE = "Which reminder do you mean? Please give its reference."
ASK_SNOOZE = "For how long should I snooze it?"


def _text(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _clarify(question: str | None, fallback: str) -> DecisionOutput:
    return DecisionOutput(decision="clarify", question=_text(question) or fallback)


def _snooze(interp: Interpretation) -> DecisionOutput:
    reference = _text(interp.reminder_ref)
    if reference is None:
        return _clarify(None, ASK_REFERENCE)
    if interp.snooze_minutes is None:
        return _clarify(None, ASK_SNOOZE)
    return DecisionOutput(
        decision="snooze", reminder_ref=reference, snooze_minutes=interp.snooze_minutes
    )


def _timed(interp: Interpretation, request: Request) -> DecisionOutput:
    task = _text(interp.task)
    reference = _text(interp.reminder_ref)
    if interp.decision == "create" and task is None:
        return _clarify(None, ASK_TASK)
    if interp.decision == "reschedule" and reference is None:
        return _clarify(None, ASK_REFERENCE)
    resolution = resolve_due(interp, request.now_local, request.zone)
    if resolution.due is None:
        return _clarify(resolution.question, ASK_GENERIC)
    due = format_due(resolution.due)
    if interp.decision == "create":
        return DecisionOutput(decision="create", task=task, due=due)
    return DecisionOutput(
        decision="reschedule", task=task, due=due, reminder_ref=reference
    )


def decide(interp: Interpretation, request: Request) -> DecisionOutput:
    """Map an interpretation to the final decision (data-model.md transitions)."""
    if interp.decision == "refuse":
        return DecisionOutput(decision="refuse", refusal_reason=interp.refusal_reason)
    if interp.decision == "clarify":
        return _clarify(interp.question, ASK_GENERIC)
    if interp.decision == "snooze":
        return _snooze(interp)
    return _timed(interp, request)


def handle_request(
    request: Request, client: ModelClient, *, secrets: Sequence[str] = ()
) -> DecisionOutput:
    """Interpret one validated request with exactly one model call."""
    system = load_system_prompt()
    user = build_user_message(request, calendar_facts(request))
    reply = client.generate(system, user, RESPONSE_SCHEMA)
    decision = decide(parse_interpretation(reply), request)
    texts = [decision.to_json()]
    texts += [value for value in decision.to_dict().values() if isinstance(value, str)]
    if leaks(texts, system, [secret for secret in secrets if secret]):
        return DecisionOutput(decision="refuse", refusal_reason="prompt_extraction")
    return decision
