"""
Endpoints for management of arkOS certificates.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import certificates, websites, applications
from arkos.messages import NotificationThread

from kraken import auth
from kraken.messages import push_record
from kraken.jobs import as_job, job_response

backend = Blueprint("certs", __name__)


class CertificatesAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            certificates.scan()
        certs = certificates.get(id)
        if id and not certs:
            abort(404)
        if type(certs) == list:
            return jsonify(certs=[x.serialized for x in certs])
        else:
            return jsonify(cert=certs.serialized)

    @auth.required()
    def post(self):
        head = request.headers
        if head.get('Content-Type').startswith("application/json"):
            data = request.get_json()["cert"]
            id = as_job(self._generate, data)
            return job_response(id, data={"cert": {"id": data["id"]}})
        elif head.get('Content-Type').startswith("multipart/form-data"):
            name = request.form.get("id")
            files = [
                request.files.get("file[0]").read(),
                request.files.get("file[1]").read(),
                request.files.get("file[2]").read()
                if request.files.get("file[2]") else None]
            id = as_job(self._upload, name, files)
            return job_response(id)
        else:
            abort(400)

    def _generate(self, job, data):
        nthread = NotificationThread(id=job.id)
        cert = certificates.generate_certificate(
            data["id"], data["domain"], data["country"], data["state"],
            data["locale"], data["email"], data["keytype"],
            data["keylength"], nthread)
        push_record("certs", cert.serialized)

    def _upload(self, job, name, files):
        nthread = NotificationThread(id=job.id)
        cert = certificates.upload_certificate(
            name, files[0], files[1], files[2], nthread)
        push_record("certs", cert.serialized)

    @auth.required()
    def put(self, id):
        data = request.get_json()["cert"]
        cert = certificates.get(id)
        other_certs = [x for x in certificates.get() if x.id != id]
        if not id or not cert:
            abort(404)
        for x in other_certs:
            for y in data["assigns"]:
                if y in x.assigns:
                    x.unassign(y)
                    push_record("certs", x.serialized)
        for x in cert.assigns:
            if x not in data["assigns"]:
                cert.unassign(x)
        for x in data["assigns"]:
            if x not in cert.assigns:
                cert.assign(x)
        return jsonify(cert=cert.serialized,
                       message="Certificate updated successfully")

    @auth.required()
    def delete(self, id):
        cert = certificates.get(id)
        if not id or not cert:
            abort(404)
        cert.remove()
        return Response(status=204)


class CertificateAuthoritiesAPI(MethodView):
    @auth.required()
    def get(self, id):
        if request.args.get("rescan", None):
            certificates.get_authorities()
        certs = certificates.get_authorities(id)
        if id and not certs:
            abort(404)
        if id and request.args.get("download", None):
            with open(certs.cert_path, "r") as f:
                data = f.read()
            resp = Response(data, mimetype="application/octet-stream")
            resp.headers["Content-Length"] = str(len(data.encode('utf-8')))
            aname = "attachment; filename={0}.pem".format(id)
            resp.headers["Content-Disposition"] = aname
            return resp
        if type(certs) == list:
            return jsonify(certauths=[x.serialized for x in certs])
        else:
            return jsonify(certauth=certs.serialized)

    @auth.required()
    def delete(self, id):
        cert = certificates.get_authorities(id)
        if not id or not cert:
            abort(404)
        cert.remove()
        return Response(status=204)


@backend.route('/api/certassigns')
@auth.required()
def ssl_able():
    assigns = []
    assigns.append({"type": "genesis", "id": "genesis",
                    "name": "arkOS Genesis/API"})
    for x in websites.get():
        assigns.append({"type": "website", "id": x.id,
                        "name": x.id if x.meta else x.name})
    for x in applications.get(installed=True):
        if x.type == "app" and x.uses_ssl:
            for y in x.get_ssl_able():
                assigns.append(y)
    return jsonify(certassigns=assigns)


certs_view = CertificatesAPI.as_view('certs_api')
backend.add_url_rule('/api/certs', defaults={'id': None},
                     view_func=certs_view, methods=['GET', ])
backend.add_url_rule('/api/certs', view_func=certs_view, methods=['POST', ])
backend.add_url_rule('/api/certs/<string:id>', view_func=certs_view,
                     methods=['GET', 'PUT', 'DELETE'])

certauth_view = CertificateAuthoritiesAPI.as_view('cert_auths_api')
backend.add_url_rule('/api/certauths', defaults={'id': None},
                     view_func=certauth_view, methods=['GET', ])
backend.add_url_rule('/api/certauths/<string:id>', view_func=certauth_view,
                     methods=['GET', 'DELETE'])
