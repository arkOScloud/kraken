import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos.system import users, groups, domains

backend = Blueprint("roles", __name__)


class UsersAPI(MethodView):
    def get(self, id):
        u = users.get(id)
        if not u:
            abort(404)
        if type(u) == list:
            return jsonify(users=[x.as_dict() for x in u])
        else:
            return jsonify(user=u.as_dict())
    
    def post(self):
        data = json.loads(request.body)["user"]
        u = users.User(id=data["id"], name=data["name"], first_name=data["first_name"], 
            last_name=data["last_name"], domain=data["domain"])
        u.add(data["passwd"])
        return jsonify(user=u.as_dict())
    
    def put(self, id):
        data = json.loads(request.body)["user"]
        u = users.get(id)
        if not u:
            abort(404)
        u.first_name = data["first_name"]
        u.last_name = data["last_name"]
        u.domain = data["domain"]
        u.admin = data["admin"]
        u.sudo = data["sudo"]
        u.update(data.get("passwd"))
        return jsonify(user=u.as_dict())
    
    def delete(self, id):
        u = users.get(id)
        if not u:
            abort(404)
        u.delete()
        return Response(status=204)


class GroupsAPI(MethodView):
    def get(self, id):
        g = groups.get(id)
        if not g:
            abort(404)
        if type(g) == list:
            return jsonify(groups=[x.as_dict() for x in g])
        else:
            return jsonify(group=g.as_dict())
    
    def post(self):
        data = json.loads(request.body)["group"]
        g = groups.Group(id=data["id"], name=data["name"])
        g.add()
        return jsonify(group=g.as_dict())
    
    def put(self, id):
        data = json.loads(request.body)["group"]
        g = groups.get(id)
        if not g:
            abort(404)
        g.name = data["name"]
        g.users = data["users"]
        g.update()
        return jsonify(group=g.as_dict())
    
    def delete(self, id):
        g = groups.get(id)
        if not g:
            abort(404)
        g.delete()
        return Response(status=204)


class DomainsAPI(MethodView):
    def get(self, id):
        d = domains.get(id)
        if not d:
            abort(404)
        if type(d) == list:
            return jsonify(domains=[x.as_dict() for x in d])
        else:
            return jsonify(domain=d.as_dict())
    
    def post(self):
        d = domains.Domain(name=id)
        d.add()
        return jsonify(domain=d.as_dict())
    
    def delete(self, id):
        d = domains.get(id)
        if not d:
            abort(404)
        d.remove()
        return Response(status=204)


users_view = UsersAPI.as_view('users_api')
backend.add_url_rule('/system/users/', defaults={'id': None}, 
    view_func=users_view, methods=['GET',])
backend.add_url_rule('/system/users/', view_func=users_view, methods=['POST',])
backend.add_url_rule('/system/users/<int:id>', view_func=users_view, 
    methods=['GET', 'PUT', 'DELETE'])

groups_view = GroupsAPI.as_view('groups_api')
backend.add_url_rule('/system/groups/', defaults={'id': None}, 
    view_func=groups_view, methods=['GET',])
backend.add_url_rule('/system/groups/', view_func=groups_view, methods=['POST',])
backend.add_url_rule('/system/groups/<int:id>', view_func=groups_view, 
    methods=['GET', 'PUT', 'DELETE'])

domains_view = DomainsAPI.as_view('domains_api')
backend.add_url_rule('/system/domains/', defaults={'id': None}, 
    view_func=domains_view, methods=['GET',])
backend.add_url_rule('/system/domains/<string:id>', view_func=domains_view, 
    methods=['GET', 'POST', 'DELETE'])
