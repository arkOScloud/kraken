import json

from flask import Blueprint, jsonify, abort
from arkos.utilities import random_string
from redis_storage import storage

backend = Blueprint("messages", __name__)


class Message:
    def __init__(self, cls="", msg=""):
        self.id = random_string()[0:10]
        if cls and msg:
            data = {"id": self.id, "class": cls, "message": msg, "complete": True}
        else:
            data = {"id": self.id, "class": "info", "message": "Please wait...", 
                "complete": False}
        storage.append("messages", data)
    
    def update(self, cls, msg):
        data = {"id": self.id, "class": cls, "message": msg, "complete": False}
        storage.append("messages", data)
    
    def complete(self, cls, msg):
        data = {"id": self.id, "class": cls, "message": msg, "complete": True}
        storage.append("messages", data)


@backend.route('/messages')
def get_messages():
    messages = storage.get_list("messages")
    updates = storage.get_list("record_updates")
    storage.delete("messages")
    storage.delete("record_updates")
    return jsonify(messages=messages, models=updates)

@backend.route('/job')
def get_jobs():
    jobs = []
    for x in storage.scan("job"):
        jobs.append("/job/%s" % x.split("arkos:job")[1])
    return jsonify(jobs=jobs)

@backend.route('/job/<string:id>')
def get_job(id):
    job = storage.get_all("job:%s" % id)
    if not job:
        abort(404)
    return Response(status=job["status"])

def update_model(name, model):
    storage.append("record_updates", {name: model})
