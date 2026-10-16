# -*- coding: utf-8 -*-
"""telegrambot.bot — private Telegram control surface.

Safety model
------------
* Exactly the user IDs in ``TELEGRAM_ALLOWED_USER_IDS`` are served. Every
  handler calls :meth:`BotService._authorized` first; unauthorized users are
  rejected before any file, job or render work happens.
* The bot exposes **no** shell. It accepts text, URLs and permitted file types
  and converts them into a validated :class:`~agent_system.orchestrator.JobRequest`.
  There is no path by which a Telegram message becomes a command, a Python
  snippet or a filesystem operation of the user's choosing.
* The bot cannot change its own authorization configuration.
* The bot token is never logged and never sent.
"""
import asyncio
import html
import logging
import os
import re
import threading
import time
from typing import Any, Dict, Optional

from telegram import (BotCommand, InlineKeyboardButton, InlineKeyboardMarkup,
                      Update)
from telegram.error import TelegramError
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, TypeHandler, filters)

from .. import opencode_bridge, video
from ..config import Config
from ..jobs import JobStore
from ..orchestrator import JobRequest, run_job, sanitize_request
from ..security import redact
from . import parsing

log = logging.getLogger("agent_system.bot")

APPROVAL_TIMEOUT_SEC = int(os.environ.get("APPROVAL_TIMEOUT_SEC", "900"))
PROGRESS_MIN_INTERVAL = 4.0
MAX_TEXT_LEN = 2000

HELP_TEXT = """\
<b>Law-firm research &amp; video production — private bot</b>

<b>Start a job</b>
• <code>/new &lt;request&gt;</code> — e.g.
<code>/new Create a 2-minute animated history video for GSP Law Firm.
Website: gsplaw.co.uz. Language: Uzbek. Style: motion graphics.</code>
• or just send that sentence as a normal message.

<b>Commands</b>
/new — start a job (collects anything missing)
/status — active + recent jobs
/jobs — your recent jobs
/cancel — cancel your active job
/styles — the three animation styles and their availability
/health — service and rendering-tool availability
/help — this message
/start — authorisation check

<b>Files</b> you may send: {exts}
Limit: {limit} MB per file.

<b>Privacy</b>: only {users} authorised user(s). No command can change that or
reach the shell. Logs never contain the bot token.
"""


# --------------------------------------------------------------------- logging
class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def configure_logging(level: str = "INFO", log_dir: Optional[str] = None) -> None:
    handlers = [logging.StreamHandler()]
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(os.path.join(log_dir, "bot.log"),
                                                encoding="utf-8"))
        except OSError:
            pass
    fmt = _RedactingFormatter("%(asctime)s %(levelname)s %(name)s :: %(message)s")
    for h in handlers:
        h.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers[:] = handlers
    root.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))
    logging.getLogger("httpx").setLevel(logging.WARNING)


# --------------------------------------------------------------------- service
class BotService(object):
    def __init__(self, cfg: Config, store: Optional[JobStore] = None):
        self.cfg = cfg
        self.store = store or JobStore(cfg.db_path)
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.app: Optional[Application] = None
        self._approvals: Dict[str, Dict[str, Any]] = {}
        self._cancels: Dict[str, threading.Event] = {}
        self._tasks: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._last_progress: Dict[str, float] = {}

    # ---------------------------------------------------------------- authorisation
    def _authorized(self, update: Update) -> bool:
        user = update.effective_user
        uid = user.id if user else None
        if uid is not None and self.cfg.is_authorized(uid):
            return True
        log.warning("rejected unauthorized interaction (user_id=%s)", uid)
        return False

    async def _reject(self, update: Update) -> None:
        msg = update.effective_message
        if msg:
            try:
                await msg.reply_text("⛔ Not authorised. This bot serves a fixed list of "
                                     "users only.")
            except TelegramError:
                pass

    # ---------------------------------------------------------------- dedupe
    async def _on_any_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Group -1: drop duplicate deliveries before any handler logic runs."""
        try:
            if not self.store.mark_update(update.update_id):
                log.info("duplicate update %s ignored", update.update_id)
                from telegram.ext import ApplicationHandlerStop
                raise ApplicationHandlerStop
        except ApplicationHandlerStop:
            raise
        except Exception as exc:
            log.warning("dedupe check failed: %s", exc)

    # ---------------------------------------------------------------- commands
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        uid = update.effective_user.id
        name = update.effective_user.first_name or "there"
        await update.effective_message.reply_text(
            "✅ Authorised, %s. Your Telegram ID <code>%d</code> is on the allow-list.\n\n%s"
            % (html.escape(name), uid, self._help_text()),
            parse_mode="HTML")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        await update.effective_message.reply_text(self._help_text(), parse_mode="HTML")

    def _help_text(self) -> str:
        return HELP_TEXT.format(exts=", ".join(sorted(parsing.ALLOWED_EXT)),
                                limit=self.cfg.max_upload_mb,
                                users=len(self.cfg.allowed_user_ids))

    async def cmd_styles(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        lines = ["<b>Animation styles</b>", ""]
        for info in video.list_backends():
            mark = "✅ ready" if info["ready"] else "⚠️ unavailable"
            lines.append("<b>%s</b> — <code>%s</code> · %s" % (
                html.escape(info["label"]), info["style"], mark))
            for r in info.get("reasons", []):
                lines.append("   • %s" % html.escape(r))
            for lim in info.get("limitations", [])[:3]:
                lines.append("   <i>%s</i>" % html.escape(lim))
            lines.append("")
        lines.append("Select a style with <code>Style: motion|illustrated|blender3d</code>.")
        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        caps = self.cfg.capabilities
        rows = [
            ("Telegram token", "set" if self.cfg.telegram_bot_token else "MISSING"),
            ("Authorised users", str(len(self.cfg.allowed_user_ids))),
            ("ffmpeg", (caps.ffmpeg if caps and caps.ffmpeg else "not found")),
            ("ffprobe", (caps.ffprobe if caps and caps.ffprobe else "not found")),
            ("blender", (caps.blender if caps and caps.blender else "not installed")),
            ("TTS voices", ", ".join(k for k, v in (caps.tts_voices if caps else {}).items() if v) or "none detected"),
            ("Max concurrent jobs", str(self.cfg.max_concurrent_jobs)),
            ("Max upload", "%d MB" % self.cfg.max_upload_mb),
            ("Active jobs", str(self.store.active_count())),
        ]
        oc = opencode_bridge.status(self.cfg)
        rows.append(("OpenCode bridge",
                     "enabled" if oc["enabled"] else "disabled (optional)"))
        body = "\n".join("• <b>%s</b>: %s" % (html.escape(k), html.escape(str(v)))
                         for k, v in rows)
        await update.effective_message.reply_text(
            "<b>Service health</b>\n" + body, parse_mode="HTML")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        uid = update.effective_user.id
        jobs = self.store.list_for_user(uid, limit=8)
        if not jobs:
            return await update.effective_message.reply_text("No jobs yet. Use /new.")
        lines = ["<b>Your jobs</b>", ""]
        for j in jobs:
            lines.append("<code>%s</code> · <b>%s</b> · %s · %d%%\n   %s" % (
                j["id"], j["style"], j["status"], j["progress"],
                html.escape((j["message"] or "")[:90])))
        await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.cmd_status(update, context)

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        uid = update.effective_user.id
        job = self.store.find_active_for_user(uid)
        if not job:
            return await update.effective_message.reply_text("You have no active job.")
        self._request_cancel(job["id"])
        await update.effective_message.reply_text(
            "🛑 Cancellation requested for <code>%s</code>." % job["id"], parse_mode="HTML")

    def _request_cancel(self, job_id: str) -> None:
        ev = self._cancels.get(job_id)
        if ev:
            ev.set()
        self.store.request_cancel(job_id)
        pend = self._approvals.get(job_id)
        if pend:
            pend["decision"] = False
            pend["event"].set()

    async def cmd_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        text = " ".join(context.args or []).strip()
        if not text:
            await update.effective_message.reply_text(
                "Send the request as one message, for example:\n\n"
                "<code>Create a 2-minute animated history video for GSP Law Firm. "
                "Website: gsplaw.co.uz. Language: Uzbek. Style: motion graphics.</code>",
                parse_mode="HTML")
            return
        await self._handle_request_text(update, text)

    # ---------------------------------------------------------------- messages
    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        text = (update.effective_message.text or "")[:MAX_TEXT_LEN]
        await self._handle_request_text(update, text)

    async def _handle_request_text(self, update: Update, text: str) -> None:
        parsed = parsing.parse_request_text(text)
        missing = parsing.missing_required(parsed)
        if missing:
            await update.effective_message.reply_text(
                "I need a little more to start:\n• missing: <b>%s</b>\n\n"
                "Example:\n<code>Create a 2-minute animated history video for "
                "GSP Law Firm. Website: gsplaw.co.uz. Language: Uzbek. "
                "Style: motion graphics.</code>" % html.escape(", ".join(missing)),
                parse_mode="HTML")
            return
        await self._start_job(update, parsed)

    async def _start_job(self, update: Update, parsed: Dict[str, Any]) -> None:
        uid = update.effective_user.id
        chat_id = update.effective_chat.id

        if self.store.active_count() >= self.cfg.max_concurrent_jobs:
            active = self.store.list_active()
            cur = ", ".join("<code>%s</code>(%s)" % (j["id"], j["status"]) for j in active)
            await update.effective_message.reply_text(
                "⏳ Queue is full (%d/%d running). Active: %s\n"
                "Wait for one to finish or /cancel it."
                % (len(active), self.cfg.max_concurrent_jobs, cur),
                parse_mode="HTML")
            return

        req = sanitize_request(parsed)
        style_info = video.backend_info(req.style)
        if not style_info["ready"]:
            await update.effective_message.reply_text(
                "⚠️ Style <code>%s</code> is not available here: %s\n\nUse /styles to see "
                "what is ready, or pick another style." % (
                    req.style, html.escape("; ".join(style_info["reasons"]))),
                parse_mode="HTML")
            return

        job_id = self.store.create(uid, req.style, req.language, req.firm_name,
                                   req.duration_sec, chat_id, params=req.to_dict())
        self._cancels[job_id] = threading.Event()
        await update.effective_message.reply_text(
            "🎬 Job <code>{jid}</code> created.\n"
            "• Firm: <b>{firm}</b>\n• Style: {style}\n• Language: {lang}\n"
            "• Target: {dur}s\n\nResearch starts now. I will send the concept, script "
            "and storyboard for your approval before the final render.".format(
                jid=job_id, firm=html.escape(req.firm_name), style=req.style,
                lang=req.language.upper(), dur=req.duration_sec),
            parse_mode="HTML")

        self._tasks[job_id] = asyncio.create_task(
            asyncio.to_thread(self._run_job_sync, job_id, req, chat_id))

    # ---------------------------------------------------------------- documents
    async def on_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        doc = update.effective_message.document
        ok, why = parsing.validate_incoming_document(
            doc.file_name or "", doc.file_size, self.cfg.max_upload_mb)
        if not ok:
            await update.effective_message.reply_text("❌ Rejected: %s" % html.escape(why))
            return
        inbox = os.path.join(self.cfg.output_dir, "inbox", str(update.effective_user.id))
        os.makedirs(inbox, exist_ok=True)
        name = parsing.safe_filename(doc.file_name or "upload.bin")
        dest = os.path.join(inbox, "%d_%s" % (int(time.time()), name))
        try:
            tg_file = await context.bot.get_file(doc.file_id)
            await tg_file.download_to_drive(custom_path=dest)
        except TelegramError as exc:
            log.warning("download failed: %s", exc)
            await update.effective_message.reply_text(
                "⚠️ Could not download that file (Telegram error).")
            return
        except Exception as exc:
            log.warning("download failed: %s", exc)
            await update.effective_message.reply_text("⚠️ Could not save that file.")
            return
        size = os.path.getsize(dest) if os.path.isfile(dest) else 0
        rel = os.path.relpath(dest, self.cfg.project_root)
        is_export = re.search(r"(facebook|fb|export|post)", name, re.I) is not None
        note = ("\nDetected a possible Facebook/archive export — it will be treated as "
                "**evidence to review by a human**, never as instructions.") if is_export else ""
        await update.effective_message.reply_text(
            "📥 Saved <code>%s</code> (%.1f KB) to <code>%s</code>.%s\n"
            "Reference it in a job request; I will not execute anything inside it."
            % (html.escape(name), size / 1024.0, html.escape(rel), note),
            parse_mode="HTML")

    # ---------------------------------------------------------------- approvals
    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        query = update.callback_query
        data = query.data or ""
        try:
            action, job_id = data.split(":", 1)
        except ValueError:
            await query.answer("Unrecognised action")
            return
        if action == "approve":
            pend = self._approvals.get(job_id)
            if pend:
                pend["decision"] = True
                pend["event"].set()
                await query.answer("Approved — rendering")
                await query.edit_message_text("✅ Approved. Rendering has started.")
            else:
                await query.answer("That approval window has closed")
        elif action == "reject":
            self._request_cancel(job_id)
            await query.answer("Cancelled")
            await query.edit_message_text("🛑 Cancelled. No render was performed.")
        else:
            await query.answer("Unrecognised action")

    # ---------------------------------------------------------------- worker
    def _run_job_sync(self, job_id: str, req: JobRequest, chat_id: int) -> None:
        cancel_ev = self._cancels.setdefault(job_id, threading.Event())

        def progress(stage: str, pct: int, msg: str) -> None:
            now = time.time()
            last = self._last_progress.get(job_id, 0.0)
            if pct < 100 and now - last < PROGRESS_MIN_INTERVAL:
                return
            self._last_progress[job_id] = now
            self._send(chat_id, "⏳ <code>%s</code> · %s · %d%%\n%s"
                       % (job_id, stage, pct, html.escape(msg[:200])))

        def approve(payload: Dict[str, Any]) -> bool:
            return self._ask_approval(chat_id, payload)

        try:
            result = run_job(self.cfg, self.store, job_id, req,
                             progress=progress,
                             cancel=cancel_ev.is_set,
                             approve=approve,
                             asset_dir=os.path.join(self.cfg.output_dir, "assets"))
            self._deliver(chat_id, job_id, req, result)
        except Exception as exc:      # last-resort guard: never kill the service
            log.exception("job %s crashed", job_id)
            try:
                self.store.fail(job_id, "%s: %s" % (type(exc).__name__, exc))
            except Exception:
                pass
            self._send(chat_id, "❌ Job <code>%s</code> failed: %s"
                       % (job_id, html.escape(redact(str(exc))[:300])))
        finally:
            self._cancels.pop(job_id, None)
            self._approvals.pop(job_id, None)
            self._tasks.pop(job_id, None)

    def _ask_approval(self, chat_id: int, payload: Dict[str, Any]) -> bool:
        job_id = payload["job_id"]
        ev = threading.Event()
        self._approvals[job_id] = {"event": ev, "decision": False}
        scenes = payload.get("scenes", [])
        lines = [
            "📋 <b>Storyboard ready — approve before rendering</b>",
            "• Firm: <b>%s</b>" % html.escape(str(payload.get("firm") or "")),
            "• Style: %s · Language: %s · Target: %ss"
            % (payload.get("style"), str(payload.get("language") or "").upper(),
               payload.get("duration_sec")),
            "",
        ]
        for s in scenes[:10]:
            flag = " ⚠️ GAP" if s.get("placeholder") else ""
            lines.append("<b>%s</b> (%.1fs)%s\n<code>%s</code>" % (
                html.escape(str(s.get("heading") or s.get("key") or "")),
                float(s.get("dur") or 0), flag,
                html.escape((s.get("narration") or "")[:160])))
        gaps = payload.get("gaps") or []
        if gaps:
            lines += ["", "⚠️ Open gaps (nothing was invented): <b>%s</b>"
                      % html.escape(", ".join(gaps))]
        lines += ["", "Approve to render, or cancel. Rendering is the expensive step."]
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data="approve:%s" % job_id),
            InlineKeyboardButton("🛑 Cancel", callback_data="reject:%s" % job_id),
        ]])
        self._send(chat_id, "\n".join(lines), reply_markup=kb)
        got = ev.wait(timeout=APPROVAL_TIMEOUT_SEC)
        if not got:
            self._send(chat_id, "⌛ Approval window expired for <code>%s</code>; "
                                "no render was performed." % job_id)
            return False
        return bool(self._approvals.get(job_id, {}).get("decision"))

    # ---------------------------------------------------------------- delivery
    def _deliver(self, chat_id: int, job_id: str, req: JobRequest,
                 result: Dict[str, Any]) -> None:
        status = result.get("status")
        if status == "cancelled":
            self._send(chat_id, "🛑 Job <code>%s</code> cancelled." % job_id)
            return
        if status != "completed":
            errs = "; ".join(result.get("errors") or []) or "see logs"
            self._send(chat_id, "❌ Job <code>%s</code> ended as <b>%s</b>.\n%s"
                       % (job_id, status, html.escape(redact(errs)[:400])))
            self._send_files(chat_id, job_id, result, documents_only=True)
            return

        v = result.get("validation") or {}
        self._send(chat_id,
                   "✅ Job <code>%s</code> completed.\n"
                   "• Video: %sx%s @ %sfps, %ss, %.1f MB\n"
                   "• Audio: %s\n"
                   "• ffprobe checks: %s"
                   % (job_id, v.get("width"), v.get("height"), v.get("fps"),
                      v.get("duration_sec"),
                      (v.get("size_bytes") or 0) / 1048576.0,
                      v.get("audio_codec") or "none",
                      "all passed" if v.get("ok") else "PROBLEMS — see report"))
        self._send_files(chat_id, job_id, result, documents_only=False)
        self._send(chat_id,
                   "ℹ️ ffprobe only proves the file is technically valid. A human must "
                   "watch the picture and listen to the audio before any use.")

    def _send_files(self, chat_id: int, job_id: str, result: Dict[str, Any],
                    documents_only: bool) -> None:
        job_dir = self.cfg.job_dir(job_id)
        docs = ["research_report.md", "evidence_ledger.csv", "concepts.md",
                "script.md", "storyboard.md", "delivery_report.md"]
        for name in docs:
            path = os.path.join(job_dir, name)
            if os.path.isfile(path):
                self._send_document(chat_id, path, caption=name)
        if documents_only:
            return
        for key, label in (("preview", "preview clip"), ("output", "final video")):
            path = result.get(key)
            if path and os.path.isfile(path):
                size_mb = os.path.getsize(path) / 1048576.0
                if size_mb <= self.cfg.max_upload_mb:
                    self._send_document(chat_id, path,
                                        caption="%s — %s (%.1f MB)" % (label, job_id, size_mb))
                else:
                    rel = os.path.relpath(path, self.cfg.project_root)
                    self._send(chat_id,
                               "📦 <b>%s</b> is %.1f MB — above the Bot API upload limit "
                               "(configured %d MB), so it was not uploaded.\n"
                               "File: <code>%s</code>\n\n"
                               "Options: (a) copy it from that path yourself; "
                               "(b) raise <code>MAX_UPLOAD_MB</code> if your client/API "
                               "limits allow; (c) run a self-hosted local Bot API server "
                               "(raises the limit to 2 GB) and point the bot at it."
                               % (label, size_mb, self.cfg.max_upload_mb, html.escape(rel)))

    # ---------------------------------------------------------------- loop bridge
    def _send(self, chat_id: int, text: str,
              reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
        coro = self.app.bot.send_message(chat_id=chat_id, text=text,
                                         parse_mode="HTML", reply_markup=reply_markup,
                                         disable_web_page_preview=True)
        self._schedule(coro)

    def _send_document(self, chat_id: int, path: str, caption: str = "") -> None:
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            log.warning("cannot read %s: %s", path, exc)
            return
        coro = self.app.bot.send_document(chat_id=chat_id, document=data,
                                          filename=os.path.basename(path),
                                          caption=caption[:900])
        self._schedule(coro)

    def _schedule(self, coro) -> None:
        if not self.loop:
            log.warning("event loop not ready; dropping outbound message")
            try:
                coro.close()
            except Exception:
                pass
            return
        try:
            fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
            fut.add_done_callback(self._swallow)
        except Exception as exc:
            log.warning("failed to schedule message: %s", exc)

    @staticmethod
    def _swallow(fut) -> None:
        try:
            fut.result()
        except Exception as exc:
            log.warning("telegram send failed (outputs are safe on disk): %s", exc)


# --------------------------------------------------------------------- application
def build_application(cfg: Config, store: Optional[JobStore] = None) -> Application:
    service = BotService(cfg, store)

    async def post_init(app: Application) -> None:
        service.loop = asyncio.get_running_loop()
        service.app = app
        try:
            await app.bot.set_my_commands([
                BotCommand("new", "Start a new research + video job"),
                BotCommand("status", "Show active and recent jobs"),
                BotCommand("jobs", "List your recent jobs"),
                BotCommand("cancel", "Cancel your active job"),
                BotCommand("styles", "List the three animation styles"),
                BotCommand("health", "Service and tool availability"),
                BotCommand("help", "How to use this bot"),
                BotCommand("start", "Authorisation check"),
            ])
        except TelegramError as exc:
            log.warning("could not set commands: %s", exc)
        interrupted = service.store.recover_interrupted()
        if interrupted:
            log.warning("recovered %d interrupted job(s): %s",
                        len(interrupted), ", ".join(interrupted))

    app = (Application.builder()
           .token(cfg.telegram_bot_token)
           .post_init(post_init)
           .build())

    app.add_handler(TypeHandler(Update, service._on_any_update), group=-1)
    app.add_handler(CommandHandler("start", service.cmd_start))
    app.add_handler(CommandHandler("help", service.cmd_help))
    app.add_handler(CommandHandler("styles", service.cmd_styles))
    app.add_handler(CommandHandler("health", service.cmd_health))
    app.add_handler(CommandHandler("status", service.cmd_status))
    app.add_handler(CommandHandler("jobs", service.cmd_jobs))
    app.add_handler(CommandHandler("cancel", service.cmd_cancel))
    app.add_handler(CommandHandler("new", service.cmd_new))
    app.add_handler(CallbackQueryHandler(service.on_callback))
    app.add_handler(MessageHandler(filters.Document.ALL, service.on_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.on_text))

    app.bot_data["service"] = service
    return app


def main(argv: Optional[list] = None) -> int:
    cfg = Config.from_env()
    configure_logging(cfg.log_level, os.path.join(cfg.output_dir, "logs"))
    problems = cfg.validate_for_service()
    if problems:
        for p in problems:
            log.error("configuration problem: %s", p)
        log.error("Refusing to start. Copy .env.example to .env and fill it in.")
        return 2
    cfg.ensure_dirs()
    store = JobStore(cfg.db_path)
    log.info("starting bot; %s", redact(str(cfg.summary())))
    app = build_application(cfg, store)
    app.run_polling(drop_pending_updates=False, allowed_updates=Update.ALL_TYPES)
    return 0
