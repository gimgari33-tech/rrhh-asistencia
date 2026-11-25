"""Serve only the public frontend entry point and static assets."""

from flask import Blueprint, abort, current_app, send_from_directory

web = Blueprint("web", __name__)


@web.get("/")
def index():
    return send_from_directory(current_app.config["PROJECT_ROOT"], "index.html")


@web.get("/<path:asset>")
def public_asset(asset):
    if not asset.startswith("static/"):
        abort(404)
    return send_from_directory(current_app.config["PROJECT_ROOT"], asset)
