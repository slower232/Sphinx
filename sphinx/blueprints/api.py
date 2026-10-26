from flask import Blueprint, jsonify, request

from ..i18n import t
from ..services import tutor
from ..services.owner import get_owner

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.post("/tutor")
def tutor_chat():
    data = request.get_json(silent=True) or {}
    if not tutor.available():
        return jsonify(ok=False, error=t("tutor.err_off")), 503
    owner = get_owner(create=True)
    lesson_id = data.get("lesson_id") if isinstance(data.get("lesson_id"), int) else None
    result = tutor.ask(owner, data.get("message"), lesson_id, data.get("history"))
    if result["ok"]:
        return jsonify(ok=True, text=result["text"])
    status = 429 if result["error"] in ("tutor.err_rate", "tutor.err_daily") else 502
    return jsonify(ok=False, error=t(result["error"])), status
