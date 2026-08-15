# backend/app/celery/notification_merge.py

from app.schemas.notification import NotificationMetric, NotificationPayload


def merge_notification_payloads(operation: str, entries: list[tuple[str, NotificationPayload]], duration_seconds: float) -> NotificationPayload:
    """
    Combine N per-strategy NotificationPayloads into one Discord-bound payload.

    entries: (strategy_label, payload) pairs, one per strategy processed this run.
    A single-entry batch (today's common case — one strategy on this schedule row)
    passes through unchanged, with no label-prefixing noise.
    """
    if len(entries) == 1:
        _, only = entries[0]
        return only.model_copy(update={"operation": operation})

    statuses = {p.status for _, p in entries}
    status = "failed" if "failed" in statuses else "warning" if "warning" in statuses else "success"

    return NotificationPayload(
        operation=operation,
        status=status,
        duration_seconds=duration_seconds,
        summary="\n".join(f"**{label}** — {p.summary}" for label, p in entries),
        results=[NotificationMetric(label=f"{label} · {m.label}", value=m.value) for label, p in entries for m in p.results],
        warnings=[f"[{label}] {w}" for label, p in entries for w in p.warnings],
        action_required=[f"[{label}] {a}" for label, p in entries for a in p.action_required],
    )
