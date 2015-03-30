from flask import Blueprint, jsonify

from kraken import auth
from arkos.system import stats

backend = Blueprint("stats", __name__)


@backend.route('/system/stats/all')
@auth.required()
def get_all():
    return jsonify(**stats.get_all())

@backend.route('/system/stats/load')
@auth.required()
def get_load():
    return jsonify(load=stats.get_load())

@backend.route('/system/stats/temp')
@auth.required()
def get_temp():
    return jsonify(temp=stats.get_temp())

@backend.route('/system/stats/ram')
@auth.required()
def get_ram():
    return jsonify(ram=stats.get_ram())

@backend.route('/system/stats/cpu')
@auth.required()
def get_cpu():
    return jsonify(cpu=stats.get_cpu())

@backend.route('/system/stats/swap')
@auth.required()
def get_swap():
    return jsonify(swap=stats.get_swap())

@backend.route('/system/stats/uptime')
@auth.required()
def get_uptime():
    return jsonify(uptime=stats.get_uptime())
