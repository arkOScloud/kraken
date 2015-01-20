import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import applications, websites, certificates
from kraken.messages import Message

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
        data = json.loads(request.body)["website"]
        message = Message()
        site = applications.get(data["type"]).modules["website"]
        site = site(data["id"], data["name"], data["addr"], data["port"])
        try:
            specialmsg = site.install(data["data"], True, message)
            message.complete("success", "%s site installed successfully" % site.meta.name)
            if specialmsg:
                Message("info", specialmsg)
            return jsonify(website=site.as_dict())
        except Exception, e:
            message.complete("error", "%s could not be installed: %s" % (site.name, str(e)))
            abort(500)
    
    def put(self, id):
        data = json.loads(request.body)["website"]
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
        message = Message()
        site = websites.get(id)
        try:
            site.remove(message)
            site.installed = False
            message.complete("success", "%s site removed successfully" % site.meta.name)
            return Response(status=201)
        except Exception, e:
            site.installed = True
            message.complete("error", "%s could not be removed: %s" % (site.name, str(e)))
            abort(500)


sites_view = WebsitesAPI.as_view('sites_api')
backend.add_url_rule('/sites/', defaults={'id': None}, 
    view_func=sites_view, methods=['GET',])
backend.add_url_rule('/sites/', view_func=sites_view, methods=['POST',])
backend.add_url_rule('/sites/<int:id>', view_func=sites_view, 
    methods=['GET', 'PUT', 'DELETE'])
