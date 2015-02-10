import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import certificates
from kraken.messages import Message, push_record
from kraken.utilities import as_job, job_response

backend = Blueprint("certs", __name__)


class CertificatesAPI(MethodView):
    def get(self, id):
        if request.args.get("rescan", None):
            certificates.scan()
        certs = certificates.get(id)
        if id and not certs:
            abort(404)
        if type(certs) == list:
            return jsonify(certs=[x.as_dict() for x in certs])
        else:
            return jsonify(cert=certs.as_dict())
    
    def post(self):
        if request.headers.get('Content-Type').startswith("application/json"):
            data = json.loads(request.data)["cert"]
            id = as_job(self._generate, data)
            return job_response(id, data={"cert": {"id": data["id"]}})
        elif request.headers.get('Content-Type').startswith("multipart/form-data"):
            name = request.form.get("id")
            files = [request.files.get("file[0]").read(), request.files.get("file[1]").read(),
                request.files.get("file[2]").read() if request.files.get("file[2]") else None]
            id = as_job(self._upload, name, files)
            return job_response(id)
        else:
            abort(400)
    
    def _generate(self, data):
        message = Message()
        message.update("info", "Generating certificate...")
        try:
            cert = certificates.generate_certificate(data["id"], data["domain"], 
                data["country"], data["state"], data["locale"], data["email"], 
                data["keytype"], data["keylength"])
            message.complete("success", "Certificate generated successfully")
            push_record("certs", cert.as_dict())
        except Exception, e:
            message.complete("error", "Certificate could not be generated: %s" % str(e))
            raise
    
    def _upload(self, name, files):
        message = Message()
        message.update("info", "Uploading certificate...")
        try:
            cert = certificates.upload_certificate(name, files[0], files[1], files[2])
            message.complete("success", "Certificate uploaded successfully")
            push_record("certs", cert.as_dict())
        except Exception, e:
            message.complete("error", "Certificate could not be uploaded: %s" % str(e))
            raise
    
    def put(self, id):
        data = json.loads(request.data)["cert"]
        cert = certificates.get(id)
        if not id or not cert:
            abort(404)
        for x in cert.assign:
            if not x in data["assign"]:
                cert.unassign(x["type"], x["name"])
        for x in data["assign"]:
            if not x in cert.assign:
                cert.assign(x["type"], x["name"])
        return Response(status=201)
    
    def delete(self, id):
        cert = certificates.get(id)
        if not id or not cert:
            abort(404)
        cert.remove()
        return Response(status=204)


class CertificateAuthoritiesAPI(MethodView):
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
            resp.headers["Content-Disposition"] = "attachment; filename=%s.pem" % id
            return resp
        if type(certs) == list:
            return jsonify(certauths=[x.as_dict() for x in certs])
        else:
            return jsonify(certauth=certs.as_dict())
    
    def delete(self, id):
        cert = certificates.get_authorities(id)
        if not id or not cert:
            abort(404)
        cert.remove()
        return Response(status=204)


certs_view = CertificatesAPI.as_view('certs_api')
backend.add_url_rule('/certs', defaults={'id': None}, 
    view_func=certs_view, methods=['GET',])
backend.add_url_rule('/certs', view_func=certs_view, methods=['POST',])
backend.add_url_rule('/certs/<string:id>', view_func=certs_view, 
    methods=['GET', 'PUT', 'DELETE'])

certauth_view = CertificateAuthoritiesAPI.as_view('cert_auths_api')
backend.add_url_rule('/certauths', defaults={'id': None}, 
    view_func=certauth_view, methods=['GET',])
backend.add_url_rule('/certauths/<string:id>', view_func=certauth_view, 
    methods=['GET', 'DELETE'])
