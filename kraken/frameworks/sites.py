import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from kraken import auth
from arkos import applications, websites, certificates
from kraken.messages import Message, push_record, remove_record
from kraken.utilities import as_job, job_response

backend = Blueprint("websites", __name__)


class WebsitesAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            websites.scan()
        sites = websites.get(id)
        if id and not sites:
            abort(404)
        if type(sites) == list:
            return jsonify(websites=[x.as_dict() for x in sites])
        else:
            return jsonify(website=sites.as_dict())
    
    @auth.required()
    def post(self):
        data = json.loads(request.data)["website"]
        id = as_job(self._post, data)
        return job_response(id)
    
    def _post(self, data):
        message = Message()
        app = applications.get(data["site_type"])
        site = app._website
        site = site(data["id"], data["addr"], data["port"])
        try:
            specialmsg = site.install(app, data["extra_data"], True, message)
            message.complete("success", "%s site installed successfully" % site.meta.name)
            if specialmsg:
                Message("info", specialmsg)
            push_record("website", site.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be installed: %s" % (data["id"], str(e)))
            remove_record("website", data["id"])
            raise
    
    @auth.required()
    def put(self, id):
        data = json.loads(request.data)["website"]
        site = websites.get(id)
        if not site:
            abort(404)
        if data.get("operation") == "enable":
            site.nginx_enable()
        elif data.get("operation") == "disable":
            site.nginx_disable()
        elif data.get("operation") == "enable_ssl":
            cert = certificates.get(data["cert"])
            cert.assign("website", site.id)
        elif data.get("operation") == "disable_ssl":
            site.cert.unassign("website", site.id)
        elif data.get("operation") == "update":
            site.update()
        else:
            site.addr = data["addr"]
            site.port = data["port"]
            site.edit(data.get("new_name"))
        push_record("website", site.as_dict())
        remove_record("website", id)
        return jsonify(message="Site edited successfully")
    
    @auth.required()
    def delete(self, id):
        id = as_job(self._delete, id, success_code=204)
        return job_response(id)
    
    def _delete(self, id):
        message = Message()
        site = websites.get(id)
        try:
            site.remove(message)
            message.complete("success", "%s site removed successfully" % site.meta.name)
            remove_record("website", id)
        except Exception, e:
            message.complete("error", "%s could not be removed: %s" % (id, str(e)))
            raise


@backend.route('/websites/actions/<string:id>/<string:action>', methods=["POST",])
@auth.required()
def perform_action(id, action):
    w = websites.get(id)
    if not w:
        abort(404)
    if not hasattr(w, action):
        abort(422)
    actionfunc = getattr(w, action)
    try:
        actionfunc()
    except Exception, e:
        resp = jsonify(message=str(e))
        resp.status_code = 500
        return resp
    finally:
        return Response(status=200)


sites_view = WebsitesAPI.as_view('sites_api')
backend.add_url_rule('/websites', defaults={'id': None}, 
    view_func=sites_view, methods=['GET',])
backend.add_url_rule('/websites', view_func=sites_view, methods=['POST',])
backend.add_url_rule('/websites/<string:id>', view_func=sites_view, 
    methods=['GET', 'PUT', 'DELETE'])
