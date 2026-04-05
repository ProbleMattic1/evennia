"""
JSON API for contrib systems: mail, dice rolls, in-game reports (player + staff).

Patterns match ``views.py`` (session auth, ``JsonResponse``, CSRF-exempt POST).
"""

from __future__ import annotations

import json
import re
from typing import Any

from django.conf import settings
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from evennia import AccountDB, ObjectDB
from evennia.comms.models import Msg
from evennia.contrib.rpg import dice as dice_contrib
from evennia.utils import create, logger
from evennia.utils.utils import is_iter, make_iter

from .views import _json_body, _resolve_character_for_web

# --- Mail -----------------------------------------------------------------

_PREVIEW_LEN = 280


def _mail_sender_label(msg: Msg) -> str:
    senders = msg.senders
    if not senders:
        return "?"
    s0 = senders[0]
    if isinstance(s0, str):
        return s0
    key = getattr(s0, "key", None)
    if key:
        return str(key)
    un = getattr(s0, "username", None)
    if un:
        return str(un)
    return str(s0)


def _mail_qs_for_owner(account, scope: str, character):
    base = Msg.objects.get_by_tag(category="mail")
    if scope == "account":
        return base.filter(db_receivers_accounts=account).order_by("db_date_created")
    if scope == "character":
        if character is None:
            return None
        return base.filter(db_receivers_objects=character).order_by("db_date_created")
    return None


def _mail_has_new_tag(msg: Msg) -> bool:
    for key, cat in msg.tags.all(return_key_and_category=True):
        if key == "new" and (cat or "").lower() == "mail":
            return True
    return False


def _serialize_mail_row(msg: Msg, *, full_body: bool) -> dict[str, Any]:
    body = msg.message or ""
    row: dict[str, Any] = {
        "id": msg.id,
        "header": msg.header or "",
        "dateCreated": msg.date_created.isoformat() if msg.date_created else None,
        "sender": _mail_sender_label(msg),
        "hasNewTag": _mail_has_new_tag(msg),
    }
    if full_body:
        row["body"] = body
    else:
        row["bodyPreview"] = body if len(body) <= _PREVIEW_LEN else body[:_PREVIEW_LEN] + "…"
    return row


def _mail_search_targets(scope: str, namelist, account, character):
    nameregex = r"|".join(r"^%s$" % re.escape(name) for name in make_iter(namelist))
    if scope == "account":
        return AccountDB.objects.filter(username__iregex=nameregex)
    if scope == "character":
        if character is None:
            return ObjectDB.objects.none()
        return ObjectDB.objects.filter(db_key__iregex=nameregex)
    return ObjectDB.objects.none()


@require_GET
def ui_mail_list(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)

    scope = (request.GET.get("scope") or "account").strip().lower()
    if scope not in ("account", "character"):
        return JsonResponse({"ok": False, "message": "Invalid scope; use account or character."}, status=400)

    character = None
    if scope == "character":
        character, err = _resolve_character_for_web(request.user)
        if character is None:
            return JsonResponse({"ok": False, "message": err or "No character."}, status=400)

    qs = _mail_qs_for_owner(request.user, scope, character)
    if qs is None:
        return JsonResponse({"ok": False, "message": "Invalid mail scope."}, status=400)

    full_id = request.GET.get("fullMessageId")
    selected = None
    if full_id is not None and str(full_id).strip() != "":
        try:
            mid = int(full_id)
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "message": "Invalid fullMessageId."}, status=400)
        try:
            m = qs.get(id=mid)
        except Msg.DoesNotExist:
            return JsonResponse({"ok": False, "message": "Message not found."}, status=404)
        selected = _serialize_mail_row(m, full_body=True)

    messages = [_serialize_mail_row(m, full_body=False) for m in qs]
    out: dict[str, Any] = {"ok": True, "mode": scope, "messages": messages}
    if selected is not None:
        out["selectedMessage"] = selected
    return JsonResponse(out)


@csrf_exempt
@require_POST
def ui_mail_send(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)
    body = _json_body(request)
    scope = str(body.get("scope") or "account").strip().lower()
    if scope not in ("account", "character"):
        return JsonResponse({"ok": False, "message": "Invalid scope; use account or character."}, status=400)

    character = None
    if scope == "character":
        character, err = _resolve_character_for_web(request.user)
        if character is None:
            return JsonResponse({"ok": False, "message": err or "No character."}, status=400)

    raw_names = body.get("recipientNames") or body.get("recipients")
    if not isinstance(raw_names, list) or not raw_names:
        return JsonResponse({"ok": False, "message": "recipientNames must be a non-empty list."}, status=400)
    names = [str(n).strip() for n in raw_names if str(n).strip()]
    if not names:
        return JsonResponse({"ok": False, "message": "No recipient names given."}, status=400)

    subject = str(body.get("subject") or "").strip()
    msg_body = str(body.get("body") or "").strip()
    if not subject:
        return JsonResponse({"ok": False, "message": "subject is required."}, status=400)
    if not msg_body:
        return JsonResponse({"ok": False, "message": "body is required."}, status=400)

    sender = request.user if scope == "account" else character
    targets = _mail_search_targets(scope, names, request.user, character)
    recipients = list(targets)
    if not recipients:
        return JsonResponse({"ok": False, "message": "No valid target(s) found."}, status=400)

    for recipient in recipients:
        recipient.msg("You have received a new @mail from %s" % sender)
        new_message = create.create_message(sender, msg_body, receivers=recipient, header=subject)
        new_message.tags.add("new", category="mail")

    return JsonResponse({"ok": True, "message": "You sent your message.", "sentCount": len(recipients)})


@csrf_exempt
@require_POST
def ui_mail_delete(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)
    body = _json_body(request)
    scope = str(body.get("scope") or "account").strip().lower()
    if scope not in ("account", "character"):
        return JsonResponse({"ok": False, "message": "Invalid scope; use account or character."}, status=400)

    character = None
    if scope == "character":
        character, err = _resolve_character_for_web(request.user)
        if character is None:
            return JsonResponse({"ok": False, "message": err or "No character."}, status=400)

    raw_id = body.get("messageId")
    try:
        mid = int(raw_id)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "messageId required."}, status=400)

    qs = _mail_qs_for_owner(request.user, scope, character)
    if qs is None:
        return JsonResponse({"ok": False, "message": "Invalid mail scope."}, status=400)
    try:
        m = qs.get(id=mid)
    except Msg.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Message not found or not in your mailbox."}, status=404)

    m.delete()
    return JsonResponse({"ok": True, "message": "Message deleted."})


# --- Dice -----------------------------------------------------------------


@csrf_exempt
@require_POST
def ui_play_roll(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)
    body = _json_body(request)
    expr = str(body.get("expression") or "").strip()
    if not expr:
        return JsonResponse({"ok": False, "message": "expression is required."}, status=400)
    visibility = str(body.get("visibility") or "secret").strip().lower()
    if visibility not in ("public", "secret"):
        return JsonResponse({"ok": False, "message": "visibility must be public or secret."}, status=400)

    char, err = _resolve_character_for_web(request.user)
    if char is None:
        return JsonResponse({"ok": False, "message": err or "No character."}, status=400)

    try:
        total = dice_contrib.roll(expr)
    except (TypeError, ValueError) as e:
        return JsonResponse({"ok": False, "message": str(e)}, status=400)

    line = f"{char.key} rolls {expr}: |w{total}|n"
    if visibility == "public" and char.location:
        char.location.msg_contents(line, exclude=char)
        char.msg(line)
    else:
        char.msg(line)

    return JsonResponse({"ok": True, "result": total, "expression": expr, "visibility": visibility})


# --- In-game reports ------------------------------------------------------

def _report_status_tags() -> tuple[str, ...]:
    tags: tuple[str, ...] = ("in progress", "rejected")
    if hasattr(settings, "INGAME_REPORT_STATUS_TAGS"):
        if is_iter(settings.INGAME_REPORT_STATUS_TAGS):
            tags = tuple(settings.INGAME_REPORT_STATUS_TAGS)
        else:
            logger.log_warn(
                "The 'INGAME_REPORT_STATUS_TAGS' setting must be an iterable of strings; falling back to defaults."
            )
            tags = ("in progress", "rejected")
    closed = _("closed").lower()
    if closed not in tags:
        tags = tags + (closed,)
    return tags


def _get_report_hub(singular_type: str):
    """Same hub keys as ``evennia.contrib.base_systems.ingame_reports.reports``."""
    hub_key = f"{singular_type}_reports"
    from evennia import GLOBAL_SCRIPTS

    if not (hub := GLOBAL_SCRIPTS.get(hub_key)):
        hub = create.create_script(key=hub_key)
    return hub


def _hub_script_for_staff_query_param(report_type: str):
    """Map ?type= bugs|ideas|players → script key bug_reports / idea_reports / player_reports."""
    t = report_type.strip().lower()
    if t == "bugs":
        return _get_report_hub("bug")
    if t == "ideas":
        return _get_report_hub("idea")
    if t == "players":
        return _get_report_hub("player")
    return None


def _web_search_report_target(searchterm: str):
    """Approximate ``ReportCmdBase.target_search`` for web (account caller)."""
    term = (searchterm or "").strip()
    if not term:
        return None
    acc = AccountDB.objects.filter(username__iexact=term).first()
    if acc:
        return acc
    return ObjectDB.objects.filter(db_key__iexact=term).first()


def account_may_manage_ingame_reports_web(account) -> bool:
    """Matches ``CmdManageReports`` lock ``pperm(Admin)`` (plus superuser)."""
    if bool(getattr(account, "is_superuser", False)):
        return True
    try:
        return bool(account.check_permstring("Admin"))
    except Exception:
        return False


@csrf_exempt
@require_POST
def ui_reports_bug(request):
    return _ui_reports_file(request, hub_singular="bug", locks="read:pperm(Developer)", require_target=False)


@csrf_exempt
@require_POST
def ui_reports_idea(request):
    return _ui_reports_file(request, hub_singular="idea", locks="read:pperm(Builder)", require_target=False)


@csrf_exempt
@require_POST
def ui_reports_player(request):
    return _ui_reports_file(request, hub_singular="player", locks="read:pperm(Admin)", require_target=True)


def _ui_reports_file(request, *, hub_singular: str, locks: str, require_target: bool):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)
    body = _json_body(request)
    message = str(body.get("message") or "").strip()
    if not message:
        return JsonResponse({"ok": False, "message": "message is required."}, status=400)

    target = None
    target_str = str(body.get("target") or "").strip()
    if target_str:
        target = _web_search_report_target(target_str)
        if target is None:
            return JsonResponse({"ok": False, "message": "Target not found."}, status=400)
    elif require_target:
        return JsonResponse({"ok": False, "message": "target is required."}, status=400)

    hub = _get_report_hub(hub_singular)
    if not hub:
        return JsonResponse({"ok": False, "message": "Report hub unavailable."}, status=500)

    receivers = [hub]
    if target:
        receivers.append(target)

    ok = create.create_message(
        request.user,
        message,
        receivers=receivers,
        locks=locks,
        tags=["report"],
    )
    if not ok:
        return JsonResponse({"ok": False, "message": "Could not create report."}, status=500)

    return JsonResponse({"ok": True, "message": "Your report has been filed."})


@require_GET
def ui_staff_reports_list(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)
    if not account_may_manage_ingame_reports_web(request.user):
        return JsonResponse({"ok": False, "message": "Forbidden."}, status=403)

    t = (request.GET.get("type") or "").strip().lower()
    hub = _hub_script_for_staff_query_param(t)
    if hub is None:
        return JsonResponse({"ok": False, "message": "type must be bugs, ideas, or players."}, status=400)

    include_closed = str(request.GET.get("includeClosed") or "").lower() in ("1", "true", "yes")
    closed_tag = _("closed").lower()
    qs = Msg.objects.search_message(receiver=hub).order_by("-db_date_created")
    if not include_closed:
        qs = qs.exclude(db_tags__db_key=closed_tag)

    rows = []
    for msg in qs:
        if not msg.access(request.user, "read"):
            continue
        tags = list(msg.tags.all())
        rows.append(
            {
                "id": msg.id,
                "dateCreated": msg.date_created.isoformat() if msg.date_created else None,
                "message": msg.message or "",
                "tags": tags,
                "senders": [str(s) for s in msg.senders],
            }
        )

    return JsonResponse(
        {
            "ok": True,
            "type": t,
            "reports": rows,
            "allowedStatusTags": list(_report_status_tags()),
        }
    )


@csrf_exempt
@require_POST
def ui_staff_reports_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=401)
    if not account_may_manage_ingame_reports_web(request.user):
        return JsonResponse({"ok": False, "message": "Forbidden."}, status=403)

    body = _json_body(request)
    try:
        mid = int(body.get("messageId"))
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "messageId required."}, status=400)
    tag = str(body.get("tag") or "").strip()
    allowed = set(_report_status_tags())
    if tag not in allowed:
        return JsonResponse({"ok": False, "message": "Invalid status tag."}, status=400)
    add = body.get("add")
    if not isinstance(add, bool):
        return JsonResponse({"ok": False, "message": "add must be a boolean."}, status=400)

    try:
        msg = Msg.objects.get(id=mid)
    except Msg.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Message not found."}, status=404)

    if not msg.access(request.user, "read"):
        return JsonResponse({"ok": False, "message": "Forbidden."}, status=403)
    if "report" not in msg.tags.all():
        return JsonResponse({"ok": False, "message": "Not a report message."}, status=400)

    receivers = msg.receivers
    hub_keys = {f"{s}_reports" for s in ("bug", "idea", "player")}
    if not any(getattr(r, "key", None) in hub_keys for r in receivers):
        return JsonResponse({"ok": False, "message": "Report hub mismatch."}, status=400)

    if add:
        msg.tags.add(tag)
    else:
        msg.tags.remove(tag)

    return JsonResponse({"ok": True, "message": "Status updated.", "tags": list(msg.tags.all())})
