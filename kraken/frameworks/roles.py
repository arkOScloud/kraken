import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos.system import users, groups, domains

backend = Blueprint("roles", __name__)


class UsersAPI(MethodView):
    @auth.required()
    def get(self, id):
        u = users.get(id)
        if id and not u:
            abort(404)
        if type(u) == list:
            return jsonify(users=[x.as_dict() for x in u])
        else:
            return jsonify(user=u.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["user"]
        try:
            u = users.User(name=data["name"], first_name=data["first_name"], 
                last_name=data["last_name"], domain=data["domain"],
                admin=data["admin"], sudo=data["sudo"])
            u.add(data["passwd"])
        except Exception, e:
            resp = jsonify(message="User couldn't be added: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(user=u.as_dict(), message="User %s added successfully" % str(u.name))
    
    @auth.required()
    def put(self, id):
        data = json.loads(request.data)["user"]
        u = users.get(id)
        if not u:
            abort(404)
        u.first_name = data["first_name"]
        u.last_name = data["last_name"]
        u.domain = data["domain"]
        u.admin = data["admin"]
        u.sudo = data["sudo"]
        try:
            u.update(data.get("passwd"))
        except Exception, e:
            resp = jsonify(message="User couldn't be updated: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(user=u.as_dict(), message="User %s updated successfully" % u.name)
    
    @auth.required()
    def delete(self, id):
        u = users.get(id)
        if not u:
            abort(404)
        try:
            u.delete()
        except Exception, e:
            resp = jsonify(message="User couldn't be deleted: %s" % str(e))
            resp.status_code = 422
            return resp
        return Response(status=204)


class GroupsAPI(MethodView):
    @auth.required()
    def get(self, id):
        g = groups.get(id)
        if id and not g:
            abort(404)
        if type(g) == list:
            return jsonify(groups=[x.as_dict() for x in g])
        else:
            return jsonify(group=g.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["group"]
        g = groups.Group(name=data["name"], users=data["users"])
        try:
            g.add()
        except Exception, e:
            resp = jsonify(message="Group couldn't be added: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(group=g.as_dict(), message="Group %s added successfully" % str(g.name))
    
    @auth.required()
    def put(self, id):
        data = json.loads(request.data)["group"]
        g = groups.get(id)
        if not g:
            abort(404)
        g.users = [str(u) for u in data["users"]]
        try:
            g.update()
        except Exception, e:
            resp = jsonify(message="Group couldn't be updated: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(group=g.as_dict(), message="Group %s updated successfully" % g.name)
    
    @auth.required()
    def delete(self, id):
        g = groups.get(id)
        if not g:
            abort(404)
        try:
            g.delete()
        except Exception, e:
            resp = jsonify(message="Group couldn't be deleted: %s" % str(e))
            resp.status_code = 422
            return resp
        return Response(status=204)


class DomainsAPI(MethodView):
    @auth.required()
    def get(self, id):
        d = domains.get(id)
        if id and not d:
            abort(404)
        if type(d) == list:
            return jsonify(domains=[x.as_dict() for x in d])
        else:
            return jsonify(domain=d.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["domain"]
        d = domains.Domain(name=data["id"])
        try:
            d.add()
        except Exception, e:
            resp = jsonify(message="Domain couldn't be added: %s" % str(e))
            resp.status_code = 422
            return resp
        return jsonify(domain=d.as_dict(), message="Domain %s added successfully" % str(d.name))
    
    @auth.required()
    def delete(self, id):
        d = domains.get(id)
        if not d:
            abort(404)
        try:
            d.remove()
        except Exception, e:
            resp = jsonify(message="Domain couldn't be deleted: %s" % str(e))
            resp.status_code = 422
            return resp
        return Response(status=204)


users_view = UsersAPI.as_view('users_api')
backend.add_url_rule('/api/system/users', defaults={'id': None}, 
    view_func=users_view, methods=['GET',])
backend.add_url_rule('/api/system/users', view_func=users_view, methods=['POST',])
backend.add_url_rule('/api/system/users/<int:id>', view_func=users_view, 
    methods=['GET', 'PUT', 'DELETE'])

groups_view = GroupsAPI.as_view('groups_api')
backend.add_url_rule('/api/system/groups', defaults={'id': None}, 
    view_func=groups_view, methods=['GET',])
backend.add_url_rule('/api/system/groups', view_func=groups_view, methods=['POST',])
backend.add_url_rule('/api/system/groups/<int:id>', view_func=groups_view, 
    methods=['GET', 'PUT', 'DELETE'])

domains_view = DomainsAPI.as_view('domains_api')
backend.add_url_rule('/api/system/domains', defaults={'id': None}, 
    view_func=domains_view, methods=['GET',])
backend.add_url_rule('/api/system/domains', view_func=domains_view, methods=['POST',])
backend.add_url_rule('/api/system/domains/<string:id>', view_func=domains_view, 
    methods=['GET', 'DELETE'])
