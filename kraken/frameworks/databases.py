import base64
import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import applications, databases
from kraken.messages import Message

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
        message = Message()
        manager = databases.get_managers(data["type"])
        try:
            db = manager.add_db(data["name"])
            message.complete("success", "%s created successfully" % data["name"])
            return jsonify(database=db.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be created: %s" % (data["name"], str(e)))
            raise
    
    def put(self, id):
        data = json.loads(request.data)["database"]
        db = databases.get(id)
        if not id or not db:
            abort(404)
        elif not data.get("execute"):
            abort(400)
        else:
            result = db.execute(data["execute"])
            return jsonify(database={"id": db.id, "result": result})
    
    def delete(self, id):
        message = Message()
        db = databases.get(id)
        if not id or not db:
            abort(404)
        try:
            db.remove()
            message.complete("success", "%s removed successfully" % db.name)
            return Response(status=204)
        except Exception, e:
            message.complete("error", "%s could not be removed: %s" % (db.name, str(e)))
            raise


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
        message = Message()
        app = applications.get(data["type"])
        u = app.modules["database"]["user"]
        u = u(data["id"], data["name"], app.modules["database"]["manager"])
        try:
            u.add(data["passwd"])
            message.complete("success", "%s created successfully" % u.name)
            return jsonify(database_user=u.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be created: %s" % (u.name, str(e)))
            raise
    
    def put(self, id):
        data = json.loads(request.data)["database_user"]
        u = databases.get_user(data["id"])
        if not id or not u:
            abort(404)
        elif not data.get("operation"):
            abort(400)
        else:
            u.chperm(data["operation"], databases.get(data["database_name"]))
            return Response(status=201)
    
    def delete(self, id):
        message = Message()
        u = databases.get_user(id)
        if not id or not u:
            abort(404)
        try:
            u.remove()
            message.complete("success", "%s removed successfully" % u.name)
            return Response(status=204)
        except Exception, e:
            message.complete("error", "%s could not be removed: %s" % (u.name, str(e)))
            raise


@backend.route('/database_types')
def list_types():
    if request.args.get("rescan", None):
        databases.scan_managers()
    return jsonify(database_types=[x.as_dict() for x in databases.get_managers()])


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
