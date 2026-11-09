"""Dashboard routes and approval actions."""

from __future__ import annotations

import base64
import dataclasses

from app import web


def _client(settings):
    return web.create_app(settings).test_client()


def _token(client) -> str:
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_dashboard_renders_empty_queue(settings):
    client = _client(settings)
    response = client.get("/")
    assert response.status_code == 200
    assert b"Photo review queue" in response.data
    assert client.get("/healthz").get_json() == {"status": "ok"}
    assert client.get("/api/status").get_json()["counts"]["total"] == 0


def test_generate_requires_csrf(settings):
    client = _client(settings)
    assert client.post("/generate", data={"count": "1"}).status_code == 400


def test_generate_approve_and_blocked_publish(settings, store):
    client = _client(settings)
    token = _token(client)

    response = client.post(
        "/generate",
        data={"count": "2", "category": "food", "provider": "placeholder", "csrf_token": token},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert store.counts()["pending"] == 2

    post = store.list_posts(status="pending")[0]
    detail = client.get(f"/posts/{post['id']}")
    assert detail.status_code == 200
    assert post["title"].encode() in detail.data

    client.post(f"/posts/{post['id']}/approve", data={"csrf_token": token}, follow_redirects=True)
    assert store.get_post(post["id"])["status"] == "approved"

    blocked = client.post(
        f"/posts/{post['id']}/publish", data={"csrf_token": token}, follow_redirects=True
    )
    assert b"Publishing blocked" in blocked.data
    assert store.get_post(post["id"])["status"] == "approved"


def test_media_route_serves_generated_photo(settings, store):
    import random

    from app import generator

    post = generator.generate_post(store, settings, rng=random.Random(1))
    client = _client(settings)
    response = client.get(f"/media/{post['image_file']}")
    assert response.status_code == 200
    assert response.mimetype == "image/jpeg"
    assert client.get("/media/../app/config.py").status_code == 404


def test_reject_and_edit_actions(settings, store):
    import random

    from app import generator

    post = generator.generate_post(store, settings, rng=random.Random(2))
    client = _client(settings)
    token = _token(client)

    client.post(
        f"/posts/{post['id']}/edit",
        data={"csrf_token": token, "title": "Hand-written title", "caption": "Hand-written caption",
              "hashtags": "#studio #manual"},
        follow_redirects=True,
    )
    edited = store.get_post(post["id"])
    assert edited["title"] == "Hand-written title"
    assert edited["hashtags"] == ["#studio", "#manual"]

    client.post(f"/posts/{post['id']}/reject", data={"csrf_token": token}, follow_redirects=True)
    assert store.get_post(post["id"])["status"] == "rejected"


def test_password_protection_when_configured(settings):
    secured = dataclasses.replace(settings, dashboard_password="s3cret")
    client = _client(secured)
    assert client.get("/").status_code == 401

    header = {"Authorization": "Basic " + base64.b64encode(b"admin:s3cret").decode()}
    assert client.get("/", headers=header).status_code == 200

    wrong = {"Authorization": "Basic " + base64.b64encode(b"admin:nope").decode()}
    assert client.get("/", headers=wrong).status_code == 401


def test_unknown_post_returns_404(settings):
    client = _client(settings)
    assert client.get("/posts/does-not-exist").status_code == 404
