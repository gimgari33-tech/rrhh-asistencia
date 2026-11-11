"""Serve only the public frontend entry point and static assets."""

from flask import Blueprint, abort, current_app, send_from_directory


web = Blueprint("web", __name__)
PUBLIC_ASSETS = frozenset({
    "static/css/styles.css",
    "static/js/app.js",
    "static/js/firebase-config.js",
})


@web.get("/")
def index():
    return send_from_directory(current_app.config["PROJECT_ROOT"], "index.html")


@web.get("/<path:asset>")
def public_asset(asset):
    if asset not in PUBLIC_ASSETS:
        abort(404)
    return send_from_directory(current_app.config["PROJECT_ROOT"], asset)
