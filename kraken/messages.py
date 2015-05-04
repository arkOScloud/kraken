import json

from kraken import auth
from flask import Blueprint, jsonify, abort
from arkos.utilities import random_string
from redis_storage import storage

backend = Blueprint("messages", __name__)


class Message:
    def __init__(self, cls="", msg="", head=None):
        self.id = random_string()[0:10]
        if cls and msg:
            data = {"id": self.id, "class": cls, "message": msg, "headline": head,
                "complete": True}
        else:
            data = {"id": self.id, "class": "info", "headline": None,
                "message": "Please wait...", "complete": False}
        storage.append("genesis:messages", data)

    def update(self, cls, msg, head=None):
        data = {"id": self.id, "class": cls, "message": msg, "headline": head,
            "complete": False}
        storage.append("genesis:messages", data)

    def complete(self, cls, msg, head=None):
        data = {"id": self.id, "class": cls, "message": msg, "headline": head,
            "complete": True}
        storage.append("genesis:messages", data)


@backend.route('/api/genesis')
@auth.required()
def get_messages():
    messages = storage.get_list("genesis:messages")
    _pushes = storage.get_list("genesis:pushes")
    purges = storage.get_list("genesis:purges")
    storage.delete("genesis:messages")
    storage.delete("genesis:pushes")
    storage.delete("genesis:purges")
    pushes = {}
    for x in _pushes:
        if not pushes.has_key(x["model"]):
            pushes[x["model"]] = []
        pushes[x["model"]].append(x["record"])
    return jsonify(messages=messages, pushes=pushes, purges=purges)

@backend.route('/api/jobs')
@auth.required()
def get_jobs():
    jobs = []
    for x in storage.scan("job"):
        jobs.append("/api/jobs/%s" % x.split("arkos:job")[1])
    return jsonify(jobs=jobs)

@backend.route('/api/jobs/<string:id>')
@auth.required()
def get_job(id):
    job = storage.get_all("job:%s" % id)
    if not job:
        abort(404)
    return Response(status=job["status"])

def push_record(name, model):
    storage.append("genesis:pushes", {"model": name, "record": model})

def remove_record(name, id):
    storage.append("genesis:purges", {"model": name, "id": id})
