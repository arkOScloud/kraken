"""
Endpoints for management of arkOS users, groups and domains.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos.system import users, groups, domains
from arkos.utilities import errors

backend = Blueprint("roles", __name__)


class UsersAPI(MethodView):
    @auth.required()
    def get(self, id):
        u = users.get(id)
        if id and not u:
            abort(404)
        if isinstance(u, users.User):
            return jsonify(user=u.serialized)
        else:
            return jsonify(users=[x.serialized for x in u])

    @auth.required()
    def post(self):
        data = request.get_json()["user"]
        try:
            u = users.User(name=data["name"], first_name=data["first_name"],
                           last_name=data["last_name"], domain=data["domain"],
                           admin=data["admin"], sudo=data["sudo"])
            u.add(data["passwd"])
        except KeyError as e:
            raise errors.InvalidConfigError(str(e) if e else "Value not found")
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(user=u.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["user"]
        u = users.get(id)
        if not u:
            abort(404)
        try:
            u.first_name = data["first_name"]
            u.last_name = data["last_name"]
            u.domain = data["domain"]
            u.admin = data["admin"]
            u.sudo = data["sudo"]
            u.mail = [str(x) for x in data["mail_addresses"]]
            u.update(data.get("passwd"))
        except KeyError as e:
            raise errors.InvalidConfigError(str(e))
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(user=u.serialized)

    @auth.required()
    def delete(self, id):
        u = users.get(id)
        if not u:
            abort(404)
        try:
            u.delete()
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return Response(status=204)


class GroupsAPI(MethodView):
    @auth.required()
    def get(self, id):
        g = groups.get(id)
        if id and not g:
            abort(404)
        if isinstance(g, groups.Group):
            return jsonify(group=g.serialized)
        else:
            return jsonify(groups=[x.serialized for x in g])

    @auth.required()
    def post(self):
        data = request.get_json()["group"]
        g = groups.Group(name=data["name"], users=data.get("users", []))
        try:
            g.add()
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(group=g.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["group"]
        g = groups.get(id)
        if not g:
            abort(404)
        g.users = [str(u) for u in data["users"]]
        try:
            g.update()
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(group=g.serialized)

    @auth.required()
    def delete(self, id):
        g = groups.get(id)
        if not g:
            abort(404)
        try:
            g.delete()
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return Response(status=204)


class DomainsAPI(MethodView):
    @auth.required()
    def get(self, id):
        d = domains.get(id)
        if id and not d:
            abort(404)
        if isinstance(d, domains.Domain):
            return jsonify(domain=d.serialized)
        else:
            return jsonify(domains=[x.serialized for x in d])

    @auth.required()
    def post(self):
        data = request.get_json()["domain"]
        d = domains.Domain(name=data["id"])
        try:
            d.add()
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(domain=d.serialized)

    @auth.required()
    def delete(self, id):
        d = domains.get(id)
        if not d:
            abort(404)
        try:
            d.remove()
        except errors.InvalidConfigError as e:
            return jsonify(errors={"msg": str(e)}), 422
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
