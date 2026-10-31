import re

from flask import Blueprint, jsonify, request, session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..models.user import User
from ..services.database import SessionLocal


auth_api = Blueprint("auth_api", __name__)


@auth_api.get("/auth/session")
def get_session():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None})
    return jsonify({"user": {"user_id": user_id, "username": session.get("username")}})


@auth_api.post("/auth/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Enter your username and password."}), 400

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Enter your username and password."}), 400

    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.username == username.strip()))
        valid = user is not None and check_password_hash(user.password_hash, password)
        if not valid:
            return jsonify({"error": "The username or password is incorrect."}), 401
        session.clear()
        session.permanent = True
        session["user_id"] = user.user_id
        session["username"] = user.username
        return jsonify({"user": {"user_id": user.user_id, "username": user.username}})


@auth_api.post("/auth/register")
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Enter a username and password."}), 400

    username = data.get("username")
    password = data.get("password")
    confirmation = data.get("confirm_password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "Enter a username and password."}), 400

    username = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", username):
        return jsonify({
            "error": "Username must be 3–80 characters using letters, numbers, dots, underscores, or hyphens."
        }), 400
    if len(password) < 12:
        return jsonify({"error": "Password must contain at least 12 characters."}), 400
    if password != confirmation:
        return jsonify({"error": "The passwords do not match."}), 400

    user = User(username=username, password_hash=generate_password_hash(password))
    with SessionLocal() as database:
        database.add(user)
        try:
            database.commit()
        except IntegrityError:
            database.rollback()
            return jsonify({"error": "That username is already registered."}), 409
        database.refresh(user)
        session.clear()
        session.permanent = True
        session["user_id"] = user.user_id
        session["username"] = user.username
        return jsonify({"user": {"user_id": user.user_id, "username": user.username}}), 201


@auth_api.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "Signed out."})
