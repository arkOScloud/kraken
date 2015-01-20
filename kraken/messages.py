import json

from flask import Blueprint, jsonify
from arkos.utilities import random_string

backend = Blueprint("messages", __name__)
backend.messages = []
backend.updates = []


class Message:
    def __init__(self, cls="", msg=""):
        self.id = random_string()[0:10]
        if cls and msg:
            data = {"id": self.id, "class": cls, "message": msg, "complete": True}
        else:
            data = {"id": self.id, "class": "info", "message": "Please wait...", 
                "complete": False}
        backend.messages.append(data)
    
    def update(self, cls, msg):
        data = {"id": self.id, "class": cls, "message": msg, "complete": False}
        backend.messages.append(data)
    
    def complete(self, cls, msg):
        data = {"id": self.id, "class": cls, "message": msg, "complete": True}
        backend.messages.append(data)


@backend.route('/messages/')
def get_messages(data):
    msg = jsonify(messages=backend.messages)
    backend.messages = []
    return msg

@backend.route('/record_updates/')
def get_updates(data):
    upd = jsonify(updates=backend.updates)
    backend.updates = []
    return upd

def update_model(name, model):
    backend.updates.append({name: model})
