import base64
import json

from flask import Response, Blueprint, abort, jsonify, request
from flask.views import MethodView

from arkos import certificates
from kraken.messages import Message, update_model
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
            return jsonify(certificates=[x.as_dict() for x in certs])
        else:
            return jsonify(certificate=certs.as_dict())
    
    def post(self):
        data = json.loads(request.body)["certificate"]
        if data["operation"] == "generate":
            id = as_job(_post, self, data)
            return job_response(id)
        elif data["operation"] == "upload":
            id = as_job(_post, self, data)
            return job_response(id)
        else:
            abort(400)
    
    def _post(self, data):
        if data["operation"] == "generate":
            message = Message()
            message.update("info", "Generating certificate...")
            try:
                cert = certificates.generate_certificate(data["id"], data["name"], data["domain"], 
                    data["country"], data["state"], data["locale"], data["email"], 
                    data["keytype"], data["keylength"])
                message.complete("success", "Certificate generated successfully")
                update_model("certificate", cert.as_dict())
            except Exception, e:
                message.complete("error", "Certificate could not be generated: %s" % str(e))
                raise
        elif data["operation"] == "upload":
            try:
                cert = certificates.upload_certificate(data["id"], data["name"], 
                    base64.b64decode(data["cert"]), base64.b64decode(data["key"]), 
                    base64.b64decode(data["chain"]) if data.get("chain") else None)
                message.complete("success", "Certificate uploaded successfully")
                update_model("certificate", cert.as_dict())
            except Exception, e:
                message.complete("error", "Certificate could not be uploaded: %s" % str(e))
                raise
    
    def put(self, id):
        data = json.loads(request.body)["certificate"]
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
                certfile = base64.b64encode(f.read())
            return jsonify(certificate_authority={"name": "%s.crt"%certs.name, 
                "cert": certfile})
        if type(certs) == list:
            return jsonify(certificate_authorities=[x.as_dict() for x in certs])
        else:
            return jsonify(certificate_authority=certs.as_dict())
    
    def delete(self, id):
        cert = certificates.get_authorities(id)
        if not id or not cert:
            abort(404)
        cert.remove()
        return Response(status=204)


certs_view = CertificatesAPI.as_view('certs_api')
backend.add_url_rule('/certs/', defaults={'id': None}, 
    view_func=certs_view, methods=['GET',])
backend.add_url_rule('/certs/', view_func=certs_view, methods=['POST',])
backend.add_url_rule('/certs/<int:id>', view_func=certs_view, 
    methods=['GET', 'PUT', 'DELETE'])

certauth_view = CertificateAuthoritiesAPI.as_view('cert_auths_api')
backend.add_url_rule('/cert_auths/', defaults={'id': None}, 
    view_func=certauth_view, methods=['GET',])
backend.add_url_rule('/cert_auths/<int:id>', view_func=certauth_view, 
    methods=['GET', 'DELETE'])
