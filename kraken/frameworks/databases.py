import base64
import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import databases
from kraken.messages import update_model

backend = Blueprint("databases", __name__)


class DatabasesAPI(MethodView):
    def get(self, id):
        if request.args.get("rescan", None):
            databases.scan()
        dbs = databases.get(id)
        if id and not dbs:
            abort(404)
        if id and request.args.get("download", None):
            result = base64.b64encode(dbs.dump())
            return jsonify(database={"name": "%s.sql"%dbs.name, 
                "db": result})
        if type(dbs) == list:
            return jsonify(databases=[x.as_dict() for x in dbs])
        else:
            return jsonify(database=dbs.as_dict())
    
    def post(self):
        data = json.loads(request.data)["database"]
        manager = databases.get_managers(data["type"])
        try:
            db = manager.add_db(data["name"])
        except Exception, e:
            resp = jsonify(message="Database couldn't be added: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(database=db.as_dict(), message="Database %s added successfully" % str(db.name))
    
    def put(self, id):
        data = json.loads(request.data)["database"]
        db = databases.get(id)
        if not id or not db:
            abort(404)
        elif not data.get("execute"):
            abort(400)
        try:
            result = db.execute(data["execute"])
        except Exception, e:
            result = str(e)
        return jsonify(database={"id": db.id, "result": result})
    
    def delete(self, id):
        db = databases.get(id)
        if not id or not db:
            abort(404)
        try:
            db.remove()
        except Exception, e:
            resp = jsonify(message="Database couldn't be deleted: %s" % str(e))
            resp.status_code = 422
            return resp
        return Response(status=204)


class DatabaseUsersAPI(MethodView):
    def get(self, id):
        if request.args.get("rescan", None):
            databases.scan_users()
        u = databases.get_user(id)
        if id and not u:
            abort(404)
        if type(u) == list:
            return jsonify(database_users=[x.as_dict() for x in u])
        else:
            return jsonify(database_user=u.as_dict())
    
    def post(self):
        data = json.loads(request.data)["database_user"]
        manager = databases.get_managers(data["type"])
        try:
            u = manager.add_user(data["name"], data["passwd"])
        except Exception, e:
            resp = jsonify(message="Database user couldn't be added: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(database_user=u.as_dict(), message="Database user %s added successfully" % str(u.name))
    
    def put(self, id):
        data = json.loads(request.data)["database_user"]
        u = databases.get_user(id)
        if not id or not u:
            abort(404)
        elif not data.get("operation"):
            abort(400)
        u.chperm(data["operation"], databases.get(data["database"]))
        update_model("database_users", u.as_dict())
        return Response(status=201)
    
    def delete(self, id):
        u = databases.get_user(id)
        if not id or not u:
            abort(404)
        try:
            u.remove()
        except Exception, e:
            resp = jsonify(message="Database user couldn't be deleted: %s" % str(e))
            resp.status_code = 422
            return resp
        return Response(status=204)


@backend.route('/database_types')
def list_types():
    dbs = databases.get_managers()
    if request.args.get("rescan", None):
        dbs = databases.scan_managers()
    return jsonify(database_types=[x.as_dict() for x in dbs])


dbs_view = DatabasesAPI.as_view('dbs_api')
backend.add_url_rule('/databases', defaults={'id': None}, 
    view_func=dbs_view, methods=['GET',])
backend.add_url_rule('/databases', view_func=dbs_view, methods=['POST',])
backend.add_url_rule('/databases/<string:id>', view_func=dbs_view, 
    methods=['GET', 'PUT', 'DELETE'])

dbusers_view = DatabaseUsersAPI.as_view('db_users_api')
backend.add_url_rule('/database_users', defaults={'id': None}, 
    view_func=dbusers_view, methods=['GET',])
backend.add_url_rule('/database_users', view_func=dbusers_view, methods=['POST',])
backend.add_url_rule('/database_users/<string:id>', view_func=dbusers_view, 
    methods=['GET', 'PUT', 'DELETE'])
