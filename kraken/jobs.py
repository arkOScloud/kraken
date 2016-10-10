"""
Classes and functions to manage threaded long-running processes.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import threading

from flask import jsonify, Response

from arkos.utilities import random_string

from kraken.redis_storage import storage


class Job(threading.Thread):
    """
    A Job is a long-running process isolated to run in its own thread.

    Jobs exist to free up the web server to continue handling requests, and to
    improve performance for the user during long-running operations. It is
    configured to communicate its running and ending status via specific
    tracking headers and endpoints.
    """

    def __init__(self, id, func, *args, **kwargs):
        """
        Initialize. In code, this should be done by ``as_job()``.

        If the job should return a code other than 201 when it finishes
        successfully, send it as the ``success_code`` keyword argument.

        :param str id: Job ID
        :param function func: Function to execute
        :param args: Additional arguments to pass to executable function
        :param kwargs: Keyword arguments to pass to executable function
        """
        threading.Thread.__init__(self)
        self.id = id
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self.status_code = 200
        if "success_code" in kwargs:
            self._success_code = kwargs["success_code"]
            del kwargs["success_code"]
        else:
            self._success_code = 201

    def run(self):
        """Execute the job's function."""
        storage.set("job:{0}".format(self.id), self.status_code)
        try:
            self._func(self, *self._args, **self._kwargs)
        except Exception as e:
            self.status_code = 500
            storage.set("job:{0}".format(self.id), self.status_code)
            raise
        else:
            storage.set("job:{0}".format(self.id), self._success_code)
        storage.expire("job:{0}".format(self.id), 43200)


def as_job(func, *args, **kwargs):
    """
    Create and execute a Job.

    :param function func: Function to execute
    :param args: Additional arguments to pass to executable function
    :param kwargs: Keyword arguments to pass to executable function
    """
    id = random_string(16)
    j = Job(id, func, *args, **kwargs)
    j.start()
    return id


def job_response(id, data=None):
    """
    Respond to a request with job tracking information.

    :param str id: Job ID
    :param dict data: Additional data to return as response
    """
    if data:
        response = jsonify(**data)
        response.headers.add("Location", "/api/jobs/{0}".format(id))
        response.status_code = 202
        return response
    response = Response(status=202)
    response.headers.add("Location", "/api/jobs/{0}".format(id))
    return response
