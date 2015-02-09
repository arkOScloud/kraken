import threading
import traceback

from flask import Response, jsonify

from kraken.application import app
from redis_storage import storage
from arkos.utilities import api, random_string
from arkos.utilities.errors import RequestError


class Job(threading.Thread):
    def __init__(self, id, func, *args, **kwargs):
        self._id = id
        self._func = func
        self._args = args
        self._kwargs = kwargs
        if "success_code" in kwargs:
            self._success_code = kwargs["success_code"]
            del kwargs["success_code"]
        else:
            self._success_code = 201
        threading.Thread.__init__(self)
    
    def run(self):
        storage.set("job:%s" % self._id, {"status": 200})
        storage.expire("job:%s" % self._id, 43200)
        try:
            self._func(*self._args, **self._kwargs)
        except RequestError, e:
            storage.set("job:%s" % self._id, {"status": 400})
        except Exception, e:
            app.logger.error("Job %s (%s) has run into exception %s: %s"%(self._id,
                self._func.__name__, e.__class__.__name__, str(e)))
            app.logger.error("Stacktrace is as follows:\n%s" % traceback.format_exc())
            storage.set("job:%s" % self._id, {"status": 500})
        finally:
            storage.set("job:%s" % self._id, {"status": self._success_code})
        storage.expire("job:%s" % self._id, 43200)


def as_job(func, *args, **kwargs):
    id = random_string()[0:16]
    j = Job(id, func, *args, **kwargs)
    j.start()
    return id

def job_response(id, data=None):
    if data:
        response = jsonify(**data)
        response.headers.add("Location", "/jobs/%s" % id)
        response.status_code = 202
        return response
    response = Response(status=202)
    response.headers.add("Location", "/jobs/%s" % id)
    return response
