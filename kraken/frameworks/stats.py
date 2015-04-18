from flask import Blueprint, jsonify

from kraken import auth
from arkos.system import stats

backend = Blueprint("stats", __name__)


@backend.route('/api/system/stats/all')
@auth.required()
def get_all():
    return jsonify(**stats.get_all())

@backend.route('/api/system/stats/load')
@auth.required()
def get_load():
    return jsonify(load=stats.get_load())

@backend.route('/api/system/stats/temp')
@auth.required()
def get_temp():
    return jsonify(temp=stats.get_temp())

@backend.route('/api/system/stats/ram')
@auth.required()
def get_ram():
    return jsonify(ram=stats.get_ram())

@backend.route('/api/system/stats/cpu')
@auth.required()
def get_cpu():
    return jsonify(cpu=stats.get_cpu())

@backend.route('/api/system/stats/swap')
@auth.required()
def get_swap():
    return jsonify(swap=stats.get_swap())

@backend.route('/api/system/stats/uptime')
@auth.required()
def get_uptime():
    return jsonify(uptime=stats.get_uptime())
