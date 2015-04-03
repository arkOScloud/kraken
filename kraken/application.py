import logging
import platform
import sys
import traceback

import auth
import genesis
import messages

import arkos
from arkos import config, applications, tracked_services
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
    
    arkos.logger.active_logger = app.logger
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
    app.conf.set("enviro", "run", environment)
    app.logger.info('Environment: %s' % environment)
    
    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error
    
    app.register_blueprint(auth.backend)
    app.register_blueprint(messages.backend)
    
    app.logger.info("Loading applications...")
    applications.get()

    # Load framework blueprints
    app.logger.info("Loading frameworks...")
    register_frameworks(app)

    app.logger.info("Initializing Genesis (if present)...")
    app.register_blueprint(genesis.backend)
    
    tracked_services.initialize()
    app.logger.info("Server is up and ready")
    try:
        app.run(host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        app.logger.info("Received interrupt")

def make_json_error(err):
    if hasattr(err, "description"):
        message = err.description
    else:
        message = str(err)
    if traceback.format_exc():
        stacktrace = traceback.format_exc()
        report = "arkOS %s Crash Report\n" % version()
        report += "--------------------\n\n"
        report += "Running in %s\n" % config.get("enviro", "run")
        report += "System: %s\n" % shell("uname -a")["stdout"]
        report += "Platform: %s %s\n" % (config.get("enviro", "arch"), config.get("enviro", "board"))
        report += "Python version %s\n" % '.'.join([str(x) for x in platform.python_version_tuple()])
        report += "Config path: %s\n\n" % config.filename
        report += "Loaded applicatons: \n%s\n\n" % "\n".join([x.id for x in applications.get()])
        report += "Request: %s %s\n\n" % (request.method, request.path)
        report += stacktrace
        response = jsonify(message=message, stacktrace=stacktrace, 
            report=report, version=version(), arch=config.get("enviro", "arch"))
    else:
        response = jsonify(message=message)
    response.status_code = err.code if isinstance(err, HTTPException) else 500
    return add_cors(response)


app = Flask(__name__)

@app.after_request
def add_cors(resp):
    """ Ensure all responses have the CORS headers. This ensures any failures are also accessible
        by the client. """
    resp.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin','*')
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'PUT, POST, OPTIONS, GET, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'Authorization, Origin, X-Requested-With, Accept, DNT, Cache-Control, Accept-Encoding, Content-Type'
    # set low for debugging
    if app.debug:
        resp.headers['Access-Control-Max-Age'] = '1'
    return resp
