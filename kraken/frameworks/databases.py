"""
Endpoints for management of arkOS databases.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import databases, logger
from arkos.utilities import errors

backend = Blueprint("databases", __name__)


class DatabasesAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            databases.scan()
        dbs = databases.get(id)
        if id and not dbs:
            abort(404)
        if id and request.args.get("download", None):
            data = dbs.dump()
            resp = Response(data, mimetype="application/octet-stream")
            resp.headers["Content-Length"] = str(len(data.encode('utf-8')))
            resp.headers["Content-Disposition"] = "attachment; filename={0}.sql".format(id)
            return resp
        if isinstance(dbs, databases.Database):
            return jsonify(database=dbs.serialized,
                           database_type=dbs.manager.serialized)
        else:
            db_types = (x.manager.serialized for x in dbs)
            db_types = list({v['id']: v for v in db_types}.values())
            return jsonify(databases=[x.serialized for x in dbs],
                           database_types=db_types)

    @auth.required()
    def post(self):
        data = request.get_json()["database"]
        manager = databases.get_managers(data["database_type"])
        try:
            db = manager.add_db(data["id"])
        except errors.InvalidConfigError as e:
            logger.error("Databases", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(database=db.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["database"]
        db = databases.get(id)
        if not id or not db:
            abort(404)
        elif not data.get("execute"):
            abort(400)
        try:
            result = db.execute(data["execute"])
        except Exception as e:
            result = str(e)
        return jsonify(database={"id": db.id, "result": result})

    @auth.required()
    def delete(self, id):
        db = databases.get(id)
        if not id or not db:
            abort(404)
        try:
            db.remove()
        except errors.InvalidConfigError as e:
            logger.error("Databases", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return Response(status=204)


class DatabaseUsersAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            databases.scan_users()
        u = databases.get_users(id)
        if id and not u:
            abort(404)
        if isinstance(u, databases.DatabaseUser):
            return jsonify(database_user=u.serialized,
                           database_type=u.manager.serialized)
        else:
            db_types = (x.manager.serialized for x in u)
            db_types = list({v['id']: v for v in db_types}.values())
            return jsonify(database_users=[x.serialized for x in u],
                           database_types=db_types)

    @auth.required()
    def post(self):
        data = request.get_json()["database_user"]
        manager = databases.get_managers(data["database_type"])
        try:
            u = manager.add_user(data["id"], data["passwd"])
        except errors.InvalidConfigError as e:
            logger.error("Databases", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(database_user=u.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["database_user"]
        u = databases.get_users(id)
        if not id or not u:
            abort(404)
        elif not data.get("operation"):
            abort(400)
        u.chperm(data["operation"], databases.get(data["database"]))
        return jsonify(database_user=u.serialized)

    @auth.required()
    def delete(self, id):
        u = databases.get_users(id)
        if not id or not u:
            abort(404)
        try:
            u.remove()
        except errors.InvalidConfigError as e:
            logger.error("Databases", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return Response(status=204)


@backend.route('/api/database_types')
@auth.required()
def list_types():
    if request.args.get("rescan", None):
        databases.scan_managers()
    dbs = databases.get_managers()
    return jsonify(database_types=[x.serialized for x in dbs])


dbs_view = DatabasesAPI.as_view('dbs_api')
backend.add_url_rule('/api/databases', defaults={'id': None},
    view_func=dbs_view, methods=['GET',])
backend.add_url_rule('/api/databases', view_func=dbs_view, methods=['POST',])
backend.add_url_rule('/api/databases/<string:id>', view_func=dbs_view,
    methods=['GET', 'PUT', 'DELETE'])

dbusers_view = DatabaseUsersAPI.as_view('db_users_api')
backend.add_url_rule('/api/database_users', defaults={'id': None},
    view_func=dbusers_view, methods=['GET',])
backend.add_url_rule('/api/database_users', view_func=dbusers_view, methods=['POST',])
backend.add_url_rule('/api/database_users/<string:id>', view_func=dbusers_view,
    methods=['GET', 'PUT', 'DELETE'])
