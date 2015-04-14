import json

from flask import Blueprint, jsonify, request

from kraken import auth
from arkos import config
from arkos.system import sysconfig, systemtime

backend = Blueprint("config", __name__)


@backend.route('/config', methods=["GET", "PUT"])
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
    return jsonify(config=config.config, hostname=sysconfig.get_hostname(),
        timezone=sysconfig.get_timezone())

@backend.route('/config/datetime', methods=["GET", "PUT"])
@auth.required()
def datetime():
    if request.method == "PUT":
        systemtime.set_datetime()
    return jsonify(datetime={"datetime": systemtime.get_iso_time(), "offset": systemtime.get_offset()})

@backend.route('/system/shutdown', methods=["POST",])
@auth.required()
def shutdown():
    sysconfig.shutdown()

@backend.route('/system/reboot', methods=["POST",])
@auth.required()
def reboot():
    sysconfig.reboot()
