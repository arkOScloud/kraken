import logging
import sys

from arkos import config
from arkos.utilities.logs import ConsoleHandler
from arkos.utilities import *
from kraken.framework import register_frameworks

from flask import Flask, jsonify, request
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

def run_daemon(log_level, config_file):
    create_app(app, log_level, config_file, True)
    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    # Load framework blueprints
    app.logger.info("Loading frameworks...")
    register_frameworks(app)
    
    app.logger.info("Server is up and ready")
    try:
        app.run(host="0.0.0.0", port=8765)
    except KeyboardInterrupt:
        app.logger.info("Received interrupt")

def make_json_error(err):
    if hasattr(err, "description"):
        response = jsonify(message=err.description)
    else:
        response = jsonify(message=str(err))
    response.status_code = err.code if isinstance(err, HTTPException) else 500
    return response


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
