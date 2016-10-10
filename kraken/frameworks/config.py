"""
Endpoints for management of arkOS configuration.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

from flask import Blueprint, jsonify, request

from kraken import auth
from arkos import config
from arkos.system import sysconfig, systemtime

backend = Blueprint("config", __name__)


@backend.route('/api/config', methods=["GET", "PUT", "PATCH"])
@auth.required()
def arkos_config():
    if request.method == "PUT":
        data = request.get_json()
        if data.get("config"):
            config.config = data["config"]
            config.save()
        if data.get("hostname"):
            sysconfig.set_hostname(data["hostname"])
        if data.get("timezone"):
            sysconfig.set_timezone(**data["timezone"])
    elif request.method == "PATCH":
        data = request.get_json()
        for x in data.get("config"):
            if type(data["config"][x]) == str:
                config.config[x] = data["config"][x]
            else:
                for y in data["config"][x]:
                    config.config[x][y] = data["config"][x][y]
        config.save()
    return jsonify(config=config.config, hostname=sysconfig.get_hostname(),
        timezone=sysconfig.get_timezone())

@backend.route('/api/config/datetime', methods=["GET", "PUT"])
@auth.required()
def datetime():
    if request.method == "PUT":
        systemtime.set_datetime()
    return jsonify(datetime={"datetime": systemtime.get_iso_time(),
        "offset": systemtime.verify_time(False, False)})

@backend.route('/api/system/shutdown', methods=["POST",])
@auth.required()
def shutdown():
    sysconfig.shutdown()
    return jsonify(), 200

@backend.route('/api/system/reload', methods=["POST",])
@auth.required()
def reload():
    sysconfig.reload()
    return jsonify(), 200

@backend.route('/api/system/reboot', methods=["POST",])
@auth.required()
def reboot():
    sysconfig.reboot()
    return jsonify(), 200
