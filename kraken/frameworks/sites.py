import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import applications, websites, certificates
from kraken.messages import Message, update_model
from kraken.utilities import as_job, job_response

backend = Blueprint("websites", __name__)


class WebsitesAPI(MethodView):
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
    
    def post(self):
        data = json.loads(request.data)["website"]
        id = as_job(self._post, data)
        return job_response(id)
    
    def _post(self, data):
        message = Message()
        app = applications.get(data["type"])
        site = app._website
        site = site(data["id"], data["name"], data["addr"], data["port"])
        try:
            specialmsg = site.install(app, data["data"], True, message)
            message.complete("success", "%s site installed successfully" % site.meta.name)
            if specialmsg:
                Message("info", specialmsg)
            update_model("website", site.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be installed: %s" % (site.name, str(e)))
            raise
    
    def put(self, id):
        data = json.loads(request.data)["website"]
        site = websites.get(id)
        if not site:
            abort(404)
        if data.get("operation") == "enable":
            site.enable()
        elif data.get("operation") == "disable":
            site.disable()
        elif data.get("operation") == "enable_ssl":
            cert = certificates.get(data["cert"])
            cert.assign("website", site.name)
        elif data.get("operation") == "disable_ssl":
            site.cert.unassign("website", site.name)
        elif data.get("operation") == "update":
            site.update()
        else:
            message = Message()
            message.update("info", "Editing site...")
            site.name = data["name"]
            site.addr = data["addr"]
            site.port = data["port"]
            site.edit(data.get("old_name"))
            message.complete("success", "Site edited successfully")
        return jsonify(website=site.as_dict())
    
    def delete(self, id):
        id = as_job(_delete, id, success_code=204)
        return job_response(id)
    
    def _delete(self, id):
        message = Message()
        site = websites.get(id)
        try:
            site.remove(message)
            site.installed = False
            message.complete("success", "%s site removed successfully" % site.meta.name)
        except Exception, e:
            site.installed = True
            message.complete("error", "%s could not be removed: %s" % (site.name, str(e)))
            raise


sites_view = WebsitesAPI.as_view('sites_api')
backend.add_url_rule('/websites', defaults={'id': None}, 
    view_func=sites_view, methods=['GET',])
backend.add_url_rule('/websites', view_func=sites_view, methods=['POST',])
backend.add_url_rule('/websites/<int:id>', view_func=sites_view, 
    methods=['GET', 'PUT', 'DELETE'])
