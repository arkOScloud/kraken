import json

from flask import Response, Blueprint, jsonify, request

from arkos.system import packages
from kraken.utilities import as_job, job_response

backend = Blueprint("packages", __name__)


@backend.route('/system/packages/install', methods=["POST",])
def install():
    data = json.loads(request.body)["packages"]
    id = as_job(_install, data)
    return job_response(id)

def _install(data):
    packages.install(data, query=True)

@backend.route('/system/packages/remove', methods=["POST",])
def remove():
    data = json.loads(request.body)["packages"]
    id = as_job(_install, data)
    return job_response(id)

def _remove(data):
    packages.remove(data)
