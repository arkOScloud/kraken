"""
Classes and functions to manage API authentication and authorization.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from itsdangerous import TimedJSONWebSignatureSerializer, SignatureExpired
from itsdangerous import BadSignature
from functools import wraps

from arkos import config, secrets, logger
from arkos.system import users, systemtime
from flask import current_app, Blueprint, request, jsonify

backend = Blueprint("auth", __name__)


class AnonymousUser:
    """Dummy class to represent an anonymous user of the API."""

    def __init__(self):
        """Initialize."""
        self.name = "anonymous"
        self.first_name = "Anonymous"
        self.last_name = ""
        self.admin = True

    def verify_passwd(self, passwd):
        """Verify password. Always true since anonymous."""
        return True


def create_token(user):
    """
    Create a JSON Web Token (JWT) for the specified user.

    :param User user: an arkOS user
    :returns: JSON Web Token (JWT)
    :rtype: str
    """
    iat = systemtime.get_unix_time()
    try:
        offset = systemtime.get_offset()
        if offset < -3600 or offset > 3600:
            systemtime.set_datetime()
            iat = systemtime.get_unix_time()
    except:
        twarn = ("System time is not accurate or could not be verified."
                 " Access tokens will not expire.")
        logger.warning("System", twarn)
        iat = None
    payload = {
        "uid": user.name,
        "ufn": user.first_name,
        "uln": user.last_name,
    }
    if iat:
        payload["iat"] = iat
        payload["exp"] = iat + config.get("genesis", "token_valid_for", 3600)
    tjwss = TimedJSONWebSignatureSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            expires_in=config.get("genesis", "token_valid_for", 3600),
            algorithm_name="HS256")
    return tjwss.dumps(payload).decode("utf-8")


def verify(token=None):
    """
    Verify a provided JSON Web Token (JWT) for authentication.

    :param str token: JSON Web Token (JWT)
    :returns: True if valid, False if not
    """
    if config.get("genesis", "anonymous"):
        return

    if request.headers.get("X-API-Key", None):
        api_key = request.headers.get("X-API-Key")
        data = secrets.get_all("api-keys")
        for x in data:
            if x["key"] == api_key:
                user = users.get(name=x["user"])
                if not user or not user.admin:
                    resp = jsonify(message="Authorization required")
                    resp.status_code = 401
                    return resp
                else:
                    return

    if not token:
        token = request.headers.get("Authorization", None)
        if not token:
            resp = jsonify(message="Authorization required")
            resp.status_code = 401
            return resp

        token = token.split()
        if token[0] != "Bearer" or len(token) > 2:
            resp = jsonify(message="Malformed token")
            resp.status_code = 400
            return resp
        token = token[1]

    try:
        tjwss = TimedJSONWebSignatureSerializer(
                secret_key=current_app.config["SECRET_KEY"],
                expires_in=3600, algorithm_name="HS256")
        payload = tjwss.loads(token)
    except SignatureExpired:
        resp = jsonify(message="Token expired")
        resp.status_code = 401
        return resp
    except BadSignature:
        resp = jsonify(message="Malformed token signature")
        resp.status_code = 401
        return resp
    user = users.get(name=payload["uid"])
    if not user or not user.admin:
        resp = jsonify(message="Authorization required")
        resp.status_code = 401
        return resp


def required():
    """Decorator function. Wraps API endpoints to require authentication."""
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            v = verify()
            if v:
                return v
            return func(*args, **kwargs)
        return decorator
    return wrapper


@backend.route("/api/ping")
def ping():
    """Simple endpoint to check API up status."""
    return jsonify(ping="pong")


@backend.route("/api/token", methods=["POST"])
def get_token():
    """Get a new API token."""
    data = request.get_json()
    user, pwd = data.get("username", ""), data.get("password", "")
    if config.get("genesis", "anonymous"):
        user = AnonymousUser()
    else:
        user = users.get(name=user)
    if user and not user.admin:
        resp = jsonify(message="Not an admin user")
        resp.status_code = 401
        return resp
    elif user and user.verify_passwd(pwd):
        return jsonify(token=create_token(user))
    else:
        resp = jsonify(message="Invalid credentials")
        resp.status_code = 401
        return resp


@backend.route("/api/token/refresh", methods=["POST"])
def get_refresh_token():
    """Refresh an existing API token."""
    token = request.get_json().get("token", None)
    if not token:
        resp = jsonify(message="Authorization required")
        resp.status_code = 401
        return resp
    v = verify(token)
    if v:
        return v
    if config.get("genesis", "anonymous"):
        user = AnonymousUser()
    else:
        tjwss = TimedJSONWebSignatureSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            expires_in=3600, algorithm_name="HS256")
        payload = tjwss.loads(token)
        user = users.get(name=payload["uid"])
    return jsonify(token=create_token(user))
