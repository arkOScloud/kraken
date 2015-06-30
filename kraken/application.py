import logging
import sys
import ssl

import auth
import genesis
import messages

import arkos
from arkos.utilities import *
from arkos.utilities.logs import ConsoleHandler
from kraken.utilities import add_cors_to_response, make_json_error
from kraken.framework import register_frameworks

from flask import Flask, jsonify, request
from werkzeug.exceptions import default_exceptions


app = Flask(__name__)

def run_daemon(environment, log_level, config_file, secrets_file, policies_file):
    app.debug = environment in ["dev", "vagrant"]
    app.config["SECRET_KEY"] = random_string()

    # Customize logging format
    if not app.debug:
        stdout = ConsoleHandler(sys.stdout, app.debug)
        stdout.setLevel(log_level)
        dformatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s')
        stdout.setFormatter(dformatter)
        app.logger.addHandler(stdout)
    app.logger.setLevel(log_level)

    # Open and load configuraton
    config = arkos.init(config_file, secrets_file, policies_file, app.logger)
    app.logger.info('arkOS Kraken %s' % arkos.version)
    app.logger.info("Using config file at %s" % config.filename)
    app.conf = config

    arch = detect_architecture()
    platform = detect_platform()
    app.logger.info('Detected architecture/hardware: %s, %s' % arch)
    app.logger.info('Detected platform: %s' % platform)
    app.conf.set("enviro", "arch", arch[0])
    app.conf.set("enviro", "board", arch[1])
    app.conf.set("enviro", "run", environment)
    app.logger.info('Environment: %s' % environment)

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    app.register_blueprint(auth.backend)
    app.register_blueprint(messages.backend)

    app.logger.info("Loading applications and scanning system...")
    arkos.initial_scans()

    # Load framework blueprints
    app.logger.info("Loading frameworks...")
    register_frameworks(app)

    app.logger.info("Initializing Genesis (if present)...")
    genesis.DEBUG = app.debug
    app.register_blueprint(genesis.backend)

    app.after_request(add_cors_to_response)
    app.logger.info("Server is up and ready")
    try:
        if app.conf.get("genesis", "ssl", False):
            sslctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            sslctx.load_cert_chain(app.conf.get("genesis", "cert_file"),
                app.conf.get("genesis", "cert_key"))
            app.run(host=app.conf.get("genesis", "host"), port=app.conf.get("genesis", "port"),
                ssl_context=sslctx)
        else:
            app.run(host=app.conf.get("genesis", "host"), port=app.conf.get("genesis", "port"))
    except KeyboardInterrupt:
        app.logger.info("Received interrupt")
        raise
