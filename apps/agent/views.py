import bleach
import httpx
import markdown
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.core import ai_client

SESSION_CONVERSATION_KEY = "agent_conversation_id"
MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "nl2br", "sane_lists"]

# The assistant's reply can be influenced by untrusted content (uploaded
# files, RAG documents) via prompt injection, so its rendered HTML is treated
# as untrusted and sanitized before being sent to the browser — Markdown
# itself passes raw HTML straight through, it does not escape it.
ALLOWED_TAGS = [
    "p", "br", "strong", "em", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td", "hr",
]
ALLOWED_ATTRS = {"a": ["href", "title"]}


def _render_markdown(text: str) -> str:
    html = markdown.markdown(text, extensions=MARKDOWN_EXTENSIONS)
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


@login_required
def chat_page(request):
    conversation_id = request.session.get(SESSION_CONVERSATION_KEY)
    history = []
    if conversation_id:
        try:
            messages = ai_client.get_messages(conversation_id)
            history = [{"role": m["role"], "html": _render_markdown(m["content"])} for m in messages]
        except httpx.HTTPError:
            request.session.pop(SESSION_CONVERSATION_KEY, None)
    return render(request, "agent/chat.html", {"history": history})


@login_required
@require_POST
def new_conversation(request):
    request.session.pop(SESSION_CONVERSATION_KEY, None)
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def send_message(request):
    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse({"error": _("Сообщение не может быть пустым.")}, status=400)

    conversation_id = request.session.get(SESSION_CONVERSATION_KEY)
    files = request.FILES.getlist("files")

    try:
        result = ai_client.chat(
            external_user_id=request.user.get_username(),
            message=message,
            conversation_id=conversation_id,
            files=files,
        )
    except httpx.HTTPError:
        return JsonResponse({"error": _("AI-ассистент временно недоступен. Попробуйте позже.")}, status=502)

    request.session[SESSION_CONVERSATION_KEY] = result["conversation_id"]

    return JsonResponse(
        {
            "conversation_id": result["conversation_id"],
            "reply_html": _render_markdown(result["reply"]),
        }
    )
