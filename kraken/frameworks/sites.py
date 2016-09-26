"""
Endpoints for management of arkOS websites.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import applications, certificates, websites
from arkos.messages import Notification, NotificationThread

from kraken import auth
from kraken.messages import push_record, remove_record
from kraken.jobs import as_job, job_response

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
            return jsonify(websites=[x.serialized for x in sites])
        else:
            return jsonify(website=sites.serialized)

    @auth.required()
    def post(self):
        data = request.get_json()["website"]
        id = as_job(self._post, data)
        return job_response(id)

    def _post(self, job, data):
        nthread = NotificationThread(id=job.id)
        sapp = applications.get(data["app"])
        site = sapp._website
        site = site(sapp, data["id"], data["domain"], data["port"])
        try:
            specialmsg = site.install(data["extra_data"], True, nthread)
            if specialmsg:
                Notification("info", "Websites", specialmsg).send()
            push_record("website", site.serialized)
        except Exception as e:
            remove_record("website", data["id"])
            raise

    @auth.required()
    def put(self, id):
        data = request.get_json()["website"]
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
            site.domain = data["domain"]
            site.port = data["port"]
            site.edit(data.get("new_name"))
        push_record("website", site.serialized)
        remove_record("website", id)
        return jsonify(message="Site edited successfully")

    @auth.required()
    def delete(self, id):
        id = as_job(self._delete, id, success_code=204)
        return job_response(id)

    def _delete(self, job, id):
        nthread = NotificationThread(id=job.id)
        site = websites.get(id)
        site.remove(nthread)
        remove_record("website", id)
        remove_record("policy", id)


@backend.route('/api/websites/actions/<string:id>/<string:action>',
               methods=["POST", ])
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
    except Exception as e:
        resp = jsonify(message=str(e))
        resp.status_code = 500
        return resp
    finally:
        return Response(status=200)


sites_view = WebsitesAPI.as_view('sites_api')
backend.add_url_rule('/api/websites', defaults={'id': None},
                     view_func=sites_view, methods=['GET', ])
backend.add_url_rule('/api/websites', view_func=sites_view, methods=['POST', ])
backend.add_url_rule('/api/websites/<string:id>', view_func=sites_view,
                     methods=['GET', 'PUT', 'DELETE'])
