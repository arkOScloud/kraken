import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import security, tracked_services
from kraken.messages import Message

backend = Blueprint("security", __name__)


class PolicyAPI(MethodView):
    def get(self, id):
        svcs = tracked_services.get(id)
        if id and not svcs:
            abort(404)
        if type(svcs) == list:
            return jsonify(policies=[x.as_dict() for x in svcs])
        else:
            return jsonify(policy=svcs.as_dict())
    
    def put(self, id):
        data = json.loads(request.body)["policy"]
        policy = tracked_services.get(id)
        if not id or not policy:
            abort(404)
        policy.policy = data["level"]
        policy.save()
        return jsonify(policy=policy.as_dict())


class DefenceAPI(MethodView):
    def get(self, id):
        return jsonify(jails=security.get_defense_rules())
    
    def put(self, id):
        data = json.loads(request.body)["jail"]
        if data["operation"] == "enable":
            security.enable_all_def(data["name"])
        else:
            security.disable_all_def(data["name"])


policy_view = PolicyAPI.as_view('policy_api')
backend.add_url_rule('/system/policy/', defaults={'id': None}, 
    view_func=policy_view, methods=['GET',])
backend.add_url_rule('/system/policy/<int:id>', view_func=policy_view, methods=['GET', 'PUT'])

defence_view = DefenceAPI.as_view('defence_api')
backend.add_url_rule('/system/defence/', defaults={'id': None}, 
    view_func=defence_view, methods=['GET',])
backend.add_url_rule('/system/defence/<int:id>', view_func=defence_view, methods=['GET', 'PUT'])
