"""Flask review dashboard.

This is the manual approval surface: generated photos land here as ``pending``
and nothing is sent to Facebook until a human approves it *and* presses publish.
"""

from __future__ import annotations

import base64
import hmac
import secrets

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from app import config, generator, prompts, providers, publisher
from app import storage as storage_module
from app.facebook import FacebookError, FacebookGraphClient


def _authorised(settings) -> bool:
    password = settings.dashboard_password
    if not password:
        return True
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:]).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return False
    _user, _, supplied = decoded.partition(":")
    return hmac.compare_digest(supplied, password)


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _check_csrf() -> None:
    expected = session.get("csrf_token", "")
    supplied = request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, supplied):
        abort(400, description="Invalid or missing CSRF token. Reload the page and try again.")


def create_app(settings=None) -> Flask:
    settings = settings or config.load_settings()
    store = storage_module.Storage(settings.database_path, settings.media_dir)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.dashboard_password or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

    @app.before_request
    def _guard():
        if request.path in ("/healthz",):
            return None
        if not _authorised(settings):
            return Response(
                "Authentication required.",
                401,
                {"WWW-Authenticate": 'Basic realm="AI Photo Studio"'},
            )
        return None

    @app.context_processor
    def _inject():
        return {
            "csrf_token": _csrf_token(),
            "config_status": settings.public_status(),
            "categories": prompts.CATEGORY_LABELS,
        }

    # -- pages -----------------------------------------------------------
    @app.get("/")
    def index():
        status = request.args.get("status", "pending")
        if status not in (*storage_module.STATUSES, "all"):
            status = "pending"
        posts = store.list_posts(status=status, limit=48)
        return render_template(
            "index.html",
            posts=posts,
            status=status,
            counts=store.counts(),
            events=store.list_events(limit=15),
            providers=providers.provider_status(settings),
            statuses=storage_module.STATUSES,
        )

    @app.get("/posts/<post_id>")
    def post_detail(post_id: str):
        post = store.get_post(post_id)
        if post is None:
            abort(404)
        return render_template("detail.html", post=post, events=store.list_events(limit=50))

    # -- actions ---------------------------------------------------------
    @app.post("/generate")
    def generate():
        _check_csrf()
        try:
            count = max(1, min(5, int(request.form.get("count", "1"))))
        except ValueError:
            count = 1
        category = request.form.get("category") or None
        provider = request.form.get("provider") or None
        if category and category not in prompts.CATEGORY_LABELS:
            abort(400)

        outcome = generator.generate_batch(
            store, settings, count=count, category=category, provider_name=provider
        )
        if outcome.created:
            flash(f"Generated {len(outcome.created)} photo(s) and queued them for review.", "success")
        for error in outcome.errors:
            flash(f"Generation error: {error}", "error")
        return redirect(url_for("index", status="pending"))

    @app.post("/posts/<post_id>/approve")
    def approve(post_id: str):
        _check_csrf()
        try:
            publisher.approve_post(store, post_id)
            flash("Photo approved. It will only be published when you press Publish.", "success")
        except publisher.PublishBlocked as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("post_detail", post_id=post_id))

    @app.post("/posts/<post_id>/reject")
    def reject(post_id: str):
        _check_csrf()
        try:
            publisher.reject_post(store, post_id, request.form.get("reason", ""))
            flash("Photo rejected. Nothing will be published.", "success")
        except publisher.PublishBlocked as exc:
            flash(str(exc), "error")
        return redirect(request.referrer or url_for("post_detail", post_id=post_id))

    @app.post("/posts/<post_id>/publish")
    def publish(post_id: str):
        _check_csrf()
        try:
            post = publisher.publish_post(store, settings, post_id)
            flash(f"Published to Facebook: {post.get('permalink') or post.get('facebook_post_id')}", "success")
        except publisher.PublishBlocked as exc:
            flash(f"Publishing blocked: {exc}", "error")
        except FacebookError as exc:
            flash(f"Facebook error: {exc}", "error")
        return redirect(request.referrer or url_for("post_detail", post_id=post_id))

    @app.post("/posts/<post_id>/edit")
    def edit(post_id: str):
        _check_csrf()
        hashtags_raw = request.form.get("hashtags")
        hashtags = None
        if hashtags_raw is not None:
            hashtags = [tag for tag in hashtags_raw.replace(",", " ").split() if tag.startswith("#")]
        try:
            publisher.update_post_content(
                store,
                post_id,
                title=request.form.get("title"),
                caption=request.form.get("caption"),
                hashtags=hashtags,
            )
            flash("Copy updated.", "success")
        except publisher.PublishBlocked as exc:
            flash(str(exc), "error")
        return redirect(url_for("post_detail", post_id=post_id))

    @app.post("/posts/<post_id>/delete")
    def delete(post_id: str):
        _check_csrf()
        store.delete_post(post_id)
        flash("Photo deleted from the queue.", "success")
        return redirect(url_for("index", status="all"))

    @app.post("/verify-facebook")
    def verify_facebook():
        _check_csrf()
        try:
            page = FacebookGraphClient(settings).verify_page()
            flash(f"Connected to Page: {page.get('name')} (id {page.get('id')})", "success")
        except FacebookError as exc:
            flash(f"Facebook check failed: {exc}", "error")
        return redirect(url_for("index", status="all"))

    # -- static media + API ---------------------------------------------
    @app.get("/media/<path:filename>")
    def media(filename: str):
        if "/" in filename or "\\" in filename or filename.startswith("."):
            abort(404)
        return send_from_directory(str(store.media_dir), filename)

    @app.get("/api/status")
    def api_status():
        return jsonify(
            {
                "counts": store.counts(),
                "config": settings.public_status(),
                "providers": providers.provider_status(settings),
                "categories": prompts.CATEGORY_LABELS,
            }
        )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", message="That page or photo does not exist."), 404

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", message=getattr(error, "description", "Bad request.")), 400

    return app


def main() -> None:
    settings = config.load_settings()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port, debug=False)


if __name__ == "__main__":
    main()
