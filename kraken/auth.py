from itsdangerous import TimedJSONWebSignatureSerializer, SignatureExpired, BadSignature
from functools import wraps

from arkos import config
from arkos.system import users, systemtime
from flask import current_app, Blueprint, request, jsonify

backend = Blueprint("auth", __name__)


class AnonymousUser:
    def __init__(self):
        self.name = "anonymous"
        self.first_name = "Anonymous"
        self.last_name = ""
        self.admin = True

    def verify_passwd(self, passwd):
        return True


def create_token(user):
    iat = systemtime.get_unix_time()
    try:
        offset = systemtime.get_offset()
        if offset < -3600 or offset > 3600:
            systemtime.set_datetime()
            iat = systemtime.get_unix_time()
    except:
        current_app.logger.warning("System time is not accurate or could not be verified. Access tokens will not expire.")
        iat = None
    payload = {
        "uid": user.name,
        "ufn": user.first_name,
        "uln": user.last_name,
    }
    if iat:
        payload["iat"] = iat
        payload["exp"] = iat + config.get("genesis", "token_valid_for", 3600)
    tjwss = TimedJSONWebSignatureSerializer(secret_key=current_app.config["SECRET_KEY"],
        expires_in=config.get("genesis", "token_valid_for", 3600),
        algorithm_name="HS256")
    return tjwss.dumps(payload).decode("utf-8")

def verify(token=None):
    if config.get("genesis", "anonymous"):
        return

    if request.headers.get("X-API-Key", None):
        api_key = request.headers.get("X-API-Key")
        data = config.get_all("api-keys")
        for u in data:
            for key in data[u]:
                if key == api_key:
                    user = users.get(name=u)
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
        tjwss = TimedJSONWebSignatureSerializer(secret_key=current_app.config["SECRET_KEY"],
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
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            v = verify()
            if v:
                return v
            return func(*args, **kwargs)
        return decorator
    return wrapper

@backend.route("/api/token", methods=["POST"])
def get_token():
    data = request.get_json()
    user, pwd = data.get("username"), data.get("password")
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
    token = request.get_json().get("token", None)
    if not token:
        resp = jsonify(message="Authorization required")
        resp.status_code = 401
        return resp
    v = verify(token)
    if v: return v
    if config.get("genesis", "anonymous"):
        user = AnonymousUser()
    else:
        tjwss = TimedJSONWebSignatureSerializer(secret_key=current_app.config["SECRET_KEY"],
            expires_in=3600, algorithm_name="HS256")
        payload = tjwss.loads(token)
        user = users.get(name=payload["uid"])
    return jsonify(token=create_token(user))
