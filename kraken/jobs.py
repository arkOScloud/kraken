import threading
import traceback

from flask import jsonify, Response

from arkos.utilities.errors import RequestError

from kraken.application import app
from kraken.utilities import random_string
from redis_storage import storage


class Job(threading.Thread):
    def __init__(self, id, func, *args, **kwargs):
        self._id = id
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.status_code = 200
        if "success_code" in kwargs:
            self._success_code = kwargs["success_code"]
            del kwargs["success_code"]
        else:
            self._success_code = 201
        threading.Thread.__init__(self)

    def run(self):
        storage.set("job:%s" % self._id, {"status": self.status_code, "message": None,
            "class": None, "headline": None})
        try:
            self._func(self, *self._args, **self._kwargs)
        except RequestError, e:
            self.status_code = 400
            storage.set("job:%s" % self._id, {"status": self.status_code})
        except Exception, e:
            self.status_code = 500
            app.logger.error("Job %s (%s) has run into exception %s: %s"%(self._id,
                self._func.__name__, e.__class__.__name__, str(e)))
            app.logger.error("Stacktrace is as follows:\n%s" % traceback.format_exc())
            storage.set("job:%s" % self._id, {"status": self.status_code})
        else:
            storage.set("job:%s" % self._id, {"status": self._success_code})
        storage.expire("job:%s" % self._id, 43200)

    def update_message(self, cls="", msg="", head=None):
        storage.set("job:%s" % self._id, {"status": self.status_code, "message": msg,
            "class": cls, "headline": head})


def as_job(func, *args, **kwargs):
    id = random_string()[0:16]
    j = Job(id, func, *args, **kwargs)
    j.start()
    return id

def job_response(id, data=None):
    if data:
        response = jsonify(**data)
        response.headers.add("Location", "/api/jobs/%s" % id)
        response.status_code = 202
        return response
    response = Response(status=202)
    response.headers.add("Location", "/api/jobs/%s" % id)
    return response
