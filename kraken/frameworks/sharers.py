"""
Endpoints for management of network file share services.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""


from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import sharers, logger
from arkos.utilities import errors

backend = Blueprint("sharers", __name__)


class SharesAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            sharers.scan_shares()
        shares = sharers.get_shares(id)
        if id and not shares:
            abort(404)
        if isinstance(shares, sharers.Share):
            return jsonify(shares=shares.serialized,
                           share_types=shares.manager.serialized)
        else:
            share_types = (x.manager.serialized for x in shares)
            share_types = list({v['id']: v for v in share_types}.values())
            return jsonify(shares=[x.serialized for x in shares],
                           share_types=share_types)

    @auth.required()
    def post(self):
        data = request.get_json()["share"]
        if not data.get("share_type"):
            abort(422)
        manager = sharers.get_sharers(data["share_type"])
        try:
            share = manager.add_share(
                data["id"], data["path"], data.get("comment", ""),
                data["valid_users"], data["read_only"]
            )
        except errors.InvalidConfigError as e:
            logger.error("Sharers", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(share=share.serialized)

    @auth.required()
    def delete(self, id):
        share = sharers.get_shares(id)
        if not id or not share:
            abort(404)
        try:
            share.remove()
        except errors.InvalidConfigError as e:
            logger.error("Sharers", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return Response(status=204)


class MountsAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            sharers.scan_mounts()
        mounts = sharers.get_mounts(id)
        if id and not mounts:
            abort(404)
        if isinstance(mounts, sharers.Mount):
            return jsonify(mounts=mounts.serialized,
                           share_types=mounts.manager.serialized)
        else:
            share_types = (x.manager.serialized for x in mounts)
            share_types = list({v['id']: v for v in share_types}.values())
            return jsonify(mounts=[x.serialized for x in mounts],
                           share_types=share_types)

    @auth.required()
    def post(self):
        data = request.get_json()["mount"]
        manager = sharers.get_sharers(data["share_type"])
        try:
            mount = manager.add_mount(
                data["path"], data["network_path"], data.get("username"),
                data.get("password"), data["read_only"]
            )
        except errors.InvalidConfigError as e:
            logger.error("Sharers", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return jsonify(mount=mount.serialized)

    @auth.required()
    def delete(self, id):
        mount = sharers.get_mounts(id)
        if not id or not mount:
            abort(404)
        try:
            mount.remove()
        except errors.InvalidConfigError as e:
            logger.error("Sharers", str(e))
            return jsonify(errors={"msg": str(e)}), 422
        return Response(status=204)


@backend.route('/api/share_types')
@auth.required()
def list_types():
    if request.args.get("rescan", None):
        sharers.scan_sharers()
    managers = sharers.get_sharers()
    return jsonify(share_types=[x.serialized for x in managers])


shares_view = SharesAPI.as_view('shares_api')
backend.add_url_rule('/api/shares', defaults={'id': None},
    view_func=shares_view, methods=['GET',])
backend.add_url_rule('/api/shares', view_func=shares_view, methods=['POST',])
backend.add_url_rule('/api/shares/<string:id>', view_func=shares_view,
    methods=['GET', 'DELETE'])

mounts_view = MountsAPI.as_view('mounts_api')
backend.add_url_rule('/api/mounts', defaults={'id': None},
    view_func=mounts_view, methods=['GET',])
backend.add_url_rule('/api/mounts', view_func=mounts_view, methods=['POST',])
backend.add_url_rule('/api/mounts/<string:id>', view_func=mounts_view,
    methods=['GET', 'DELETE'])
