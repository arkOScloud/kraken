"""
Functions to initialize the arkOS Kraken server.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import logging
import sys
import ssl

from kraken import auth, genesis, messages

import arkos
from arkos.utilities import *
from arkos.utilities.logs import ConsoleHandler
from kraken.utilities import add_cors_to_response, make_json_error
from kraken.framework import register_frameworks

from flask import Flask
from werkzeug.exceptions import default_exceptions


app = Flask(__name__)


def run_daemon(environment, log_level, config_file, secrets_file,
               policies_file):
    """Run the Kraken server daemon."""
    app.debug = environment in ["dev", "vagrant"]
    app.config["SECRET_KEY"] = random_string()

    # Customize logging format
    if not app.debug:
        stdout = ConsoleHandler(sys.stdout, app.debug)
        stdout.setLevel(log_level)
        fmt_str = '%(asctime)s [%(levelname)s] %(module)s: %(message)s'
        dformatter = logging.Formatter(fmt_str)
        stdout.setFormatter(dformatter)
        app.logger.addHandler(stdout)
    app.logger.setLevel(log_level)

    # Open and load configuraton
    config = arkos.init(config_file, secrets_file, policies_file, app.logger)
    app.logger.info('arkOS Kraken {0}'.format(arkos.version))
    app.logger.info("Using config file at {0}".format(config.filename))
    app.conf = config

    arch = app.conf.get("enviro", "arch", "Unknown")
    board = app.conf.get("enviro", "board", "Unknown")
    platform = detect_platform()
    hwstr = 'Detected architecture/hardware: {0}, {1}'
    app.logger.info(hwstr.format(arch, board))
    app.logger.info('Detected platform: {0}'.format(platform))
    app.conf.set("enviro", "run", environment)
    app.logger.info('Environment: {0}'.format(environment))

    for code in list(default_exceptions.keys()):
        app.register_error_handler(code, make_json_error)

    app.register_blueprint(auth.backend)
    app.register_blueprint(messages.backend)

    app.logger.info("Loading applications and scanning system...")
    arkos.initial_scans()

    # Load framework blueprints
    app.logger.info("Loading frameworks...")
    register_frameworks(app)

    app.logger.info("Initializing Genesis (if present)...")
    genesis.DEBUG = app.debug
    try:
        app.register_blueprint(genesis.backend)
    except:
        warnmsg = ("Genesis failed to rebuild. If you can access Genesis,"
                   " you may not be able to see recently installed apps."
                   " See the logs for more information.")
        errmsg = ("Genesis failed to build. Kraken will finish loading"
                  " but you may not be able to access the Web interface.")
        messages.Message("warn", warnmsg, head="Warning")
        app.logger.error(errmsg)

    app.after_request(add_cors_to_response)
    app.logger.info("Server is up and ready")
    try:
        if app.conf.get("genesis", "ssl", False):
            sslctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            sslctx.load_cert_chain(app.conf.get("genesis", "cert_file"),
                                   app.conf.get("genesis", "cert_key"))
            app.run(host=app.conf.get("genesis", "host"),
                    port=app.conf.get("genesis", "port"),
                    ssl_context=sslctx)
        else:
            app.run(host=app.conf.get("genesis", "host"),
                    port=app.conf.get("genesis", "port"))
    except KeyboardInterrupt:
        app.logger.info("Received interrupt")
        raise
