import json
import logging
import os
import sys

from arkos import config, applications
from arkos.utilities.logs import ConsoleHandler
from arkos.utilities import *
from kraken.framework import register_frameworks

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import default_exceptions, HTTPException


def create_app(app, log_level, config_file, debug=False):
    app.debug = debug
    app.config["SECRET_KEY"] = random_string()
    
    # Customize logging format
    if not debug:
        stdout = ConsoleHandler(sys.stdout, debug)
        stdout.setLevel(logging.INFO)
        dformatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s')
        stdout.setFormatter(dformatter)
        app.logger.setLevel(logging.INFO)
        app.logger.addHandler(stdout)
    
    app.logger.info('arkOS Kraken %s' % version())
    
    # Open and load configuration
    app.logger.info("Using config file at %s" % config_file)
    app.conf = config
    app.conf.load(config_file)
    
    arch = detect_architecture()
    platform = detect_platform()
    app.logger.info('Detected architecture/hardware: %s, %s' % arch)
    app.logger.info('Detected platform: %s' % platform)
    app.conf.set("enviro", "arch", arch[0])
    app.conf.set("enviro", "board", arch[1])
    
    return app

def run_daemon(environment, log_level, config_file):
    create_app(app, log_level, config_file, True)
    app.logger.info('Environment: %s' % environment)
    
    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    # Load framework blueprints
    app.logger.info("Loading frameworks...")
    app.add_url_rule('/', defaults={'path': None}, view_func=genesis, 
        methods=['GET',])
    app.add_url_rule('/<path:path>', view_func=genesis, methods=['GET',])
    register_frameworks(app)
    
    app.conf.set("enviro", "run", environment)
    genesis_init()
    app.logger.info("Server is up and ready")
    try:
        app.run(host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        app.logger.info("Received interrupt")

def make_json_error(err):
    if hasattr(err, "description"):
        response = jsonify(message=err.description)
    else:
        response = jsonify(message=str(err))
    response.status_code = err.code if isinstance(err, HTTPException) else 500
    return response

def genesis_init():
    path = ""
    apps = applications.get()
    if config.get("enviro", "run") == "vagrant":
        path = '/home/vagrant/genesis'
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.abspath(os.path.join(sdir, '../../genesis'))
    elif os.path.exists('/var/lib/arkos/genesis'):
        path = '/var/lib/arkos/genesis'
    if not os.path.exists(path):
        return
    for x in os.listdir(os.path.join(path, 'lib')):
        if os.path.islink(os.path.join(path, 'lib', x)):
            os.unlink(os.path.join(path, 'lib', x))
    libpaths = []
    for x in apps:
        genpath = "/var/lib/arkos/applications/%s/genesis" % x.id
        if x.type == "app" and os.path.exists(genpath):
            libpaths.append("lib/%s"%x.id)
            os.symlink(genpath, os.path.join(path, 'lib', x.id))
    if libpaths:
        with open(os.path.join(path, 'package.json'), 'r') as f:
            data = json.loads(f.read())
        data["ember-addon"] = {"paths": libpaths}
        with open(os.path.join(path, 'package.json'), 'w') as f:
            f.write(json.dumps(data, sort_keys=True, 
                indent=2, separators=(',', ': ')))
    s = shell("ember build")
    if s["code"] != 0:
        raise Exception("Genesis rebuild process failed")
    
def genesis(path):
    if config.get("enviro", "run") == "vagrant":
        if os.path.exists('/home/vagrant/genesis/dist'):
            return send_from_directory('/home/vagrant/genesis/dist', path or 'index.html')
    elif config.get("enviro", "run") == "dev":
        sdir = os.path.dirname(os.path.realpath(__file__))
        sdir = os.path.abspath(os.path.join(sdir, '../../genesis/dist'))
        return send_from_directory(sdir, path or 'index.html')
    elif os.path.exists('/var/lib/arkos/genesis/dist'):
        return send_from_directory('/var/lib/arkos/genesis/dist', path or 'index.html')
    else:
        resp = jsonify(message="Genesis does not appear to be installed.")
        resp.status_code = 500
        return resp


app = Flask(__name__)

@app.after_request
def add_cors(resp):
    """ Ensure all responses have the CORS headers. This ensures any failures are also accessible
        by the client. """
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin','*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'PUT, POST, OPTIONS, GET, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Accept, DNT, Cache-Control, Accept-Encoding, Content-Type'
    # set low for debugging
    if app.debug:
        resp.headers['Access-Control-Max-Age'] = '1'
    return resp
