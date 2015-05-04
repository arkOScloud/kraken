import platform
import threading
import traceback

from flask import current_app, Response, jsonify, request

from arkos import config, version
from arkos import storage as arkos_storage
from redis_storage import storage
from arkos.utilities import api, shell, random_string
from arkos.utilities.errors import RequestError
from werkzeug.exceptions import default_exceptions, HTTPException


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
            current_app.logger.error("Job %s (%s) has run into exception %s: %s"%(self._id,
                self._func.__name__, e.__class__.__name__, str(e)))
            current_app.logger.error("Stacktrace is as follows:\n%s" % traceback.format_exc())
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
        response.headers.add("Location", "/api/jobs/%s" % id)
        response.status_code = 202
        return response
    response = Response(status=202)
    response.headers.add("Location", "/api/jobs/%s" % id)
    return response

def make_json_error(err):
    if hasattr(err, "description"):
        message = err.description
    else:
        message = str(err)
    if (isinstance(err, HTTPException) and err.code == 500) \
    or not isinstance(err, HTTPException):
        apps = [x.id for x in arkos_storage.apps.get("applications") if x.installed]
        stacktrace = traceback.format_exc()
        report = "arkOS %s Crash Report\n" % version
        report += "--------------------\n\n"
        report += "Running in %s\n" % config.get("enviro", "run")
        report += "System: %s\n" % shell("uname -a")["stdout"]
        report += "Platform: %s %s\n" % (config.get("enviro", "arch"), config.get("enviro", "board"))
        report += "Python version %s\n" % '.'.join([str(x) for x in platform.python_version_tuple()])
        report += "Config path: %s\n\n" % config.filename
        report += "Loaded applicatons: \n%s\n\n" % "\n".join(apps)
        report += "Request: %s %s\n\n" % (request.method, request.path)
        report += stacktrace
        response = jsonify(message=message, stacktrace=stacktrace,
            report=report, version=version, arch=config.get("enviro", "arch"))
    else:
        response = jsonify(message=message)
    response.status_code = err.code if isinstance(err, HTTPException) else 500
    return add_cors_to_response(response)

def add_cors_to_response(resp):
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin','*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'PATCH, PUT, POST, OPTIONS, GET, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Origin, X-Requested-With, Accept, DNT, Cache-Control, Accept-Encoding, Content-Type'
    return resp
