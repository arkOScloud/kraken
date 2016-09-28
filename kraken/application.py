"""
Functions to initialize the arkOS Kraken server.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import eventlet
import logging
import ssl

from kraken import auth, genesis

import arkos
from arkos import logger
from arkos.utilities import random_string, detect_platform, NotificationFilter

from kraken.redis_storage import storage
from kraken.logging import APIHandler
from kraken.utilities import add_cors_to_response, make_json_error
from kraken.framework import register_frameworks

from flask import Flask
from flask_socketio import SocketIO
from werkzeug.exceptions import default_exceptions
import json

app = Flask(__name__)
socketio = SocketIO(app, logger=True)


def handle_pubsub(ps, sio):
    while True:
        msg = ps.get_message()
        if msg and msg["channel"] == b"arkos:notifications":
            sio.emit("sendNotification", json.loads(msg["data"].decode()))
        elif msg and msg["channel"] == b"arkos:records:push":
            sio.emit("modelPush", json.loads(msg["data"].decode()))
        elif msg and msg["channel"] == b"arkos:records:purge":
            sio.emit("modelPurge", json.loads(msg["data"].decode()))
        eventlet.sleep(0.1)


def run_daemon(environment, log_level, config_file, secrets_file,
               policies_file):
    """Run the Kraken server daemon."""
    app.debug = environment in ["dev", "vagrant"]
    app.config["SECRET_KEY"] = random_string()

    # Open and load configuraton
    config = arkos.init(config_file, secrets_file, policies_file,
                        app.debug, app.logger)
    logger.info("Init", "arkOS Kraken {0}".format(arkos.version))
    logger.debug("Init", "*** DEBUG MODE ***")
    logger.info("Init", "Using config file at {0}".format(config.filename))
    app.conf = config

    arch = app.conf.get("enviro", "arch", "Unknown")
    board = app.conf.get("enviro", "board", "Unknown")
    platform = detect_platform()
    hwstr = "Detected architecture/hardware: {0}, {1}"
    logger.info("Init", hwstr.format(arch, board))
    logger.info("Init", "Detected platform: {0}".format(platform))
    app.conf.set("enviro", "run", environment)
    logger.info("Init", "Environment: {0}".format(environment))

    apihdlr = APIHandler()
    apihdlr.setLevel(logging.DEBUG if app.debug else logging.INFO)
    apihdlr.addFilter(NotificationFilter())
    logger.logger.addHandler(apihdlr)

    for code in list(default_exceptions.keys()):
        app.register_error_handler(code, make_json_error)

    app.register_blueprint(auth.backend)

    logger.info("Init", "Loading applications and scanning system...")
    arkos.initial_scans()

    # Load framework blueprints
    logger.info("Init", "Loading frameworks...")
    register_frameworks(app)

    logger.info("Init", "Initializing Genesis (if present)...")
    genesis.DEBUG = app.debug
    try:
        app.register_blueprint(genesis.backend)
    except:
        errmsg = ("Genesis failed to build. Kraken will finish loading"
                  " but you may not be able to access the Web interface.")
        logger.error("Init", errmsg)

    app.after_request(add_cors_to_response)
    logger.info("Init", "Server is up and ready")
    try:
        import eventlet
        pubsub = storage.redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(["arkos:notifications", "arkos:records:push",
                          "arkos:records:purge"])
        eventlet.spawn(handle_pubsub, pubsub, socketio)
        eventlet_socket = eventlet.listen(
            (app.conf.get("genesis", "host"), app.conf.get("genesis", "port"))
        )
        if app.conf.get("genesis", "ssl", False):
            sslctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            sslctx.load_cert_chain(app.conf.get("genesis", "cert_file"),
                                   app.conf.get("genesis", "cert_key"))
            socketio.run(app=app,
                         host=app.conf.get("genesis", "host"),
                         port=app.conf.get("genesis", "port"),
                         ssl_context=sslctx)
        else:
            eventlet.wsgi.server(eventlet_socket, app)
    except KeyboardInterrupt:
        logger.info("Init", "Received interrupt")
        raise
