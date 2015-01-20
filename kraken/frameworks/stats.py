from flask import Blueprint, jsonify

from arkos.system import stats

backend = Blueprint("stats", __name__)


@backend.route('/system/stats/all/')
def get_all():
    return jsonify(**stats.get_all())

@backend.route('/system/stats/load/')
def get_load():
    return jsonify(load=stats.get_load())

@backend.route('/system/stats/temp/')
def get_temp():
    return jsonify(temp=stats.get_temp())

@backend.route('/system/stats/ram/')
def get_ram():
    return jsonify(ram=stats.get_ram())

@backend.route('/system/stats/cpu/')
def get_cpu():
    return jsonify(cpu=stats.get_cpu())

@backend.route('/system/stats/swap/')
def get_swap():
    return jsonify(swap=stats.get_swap())

@backend.route('/system/stats/uptime/')
def get_uptime():
    return jsonify(uptime=stats.get_uptime())
