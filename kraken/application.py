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
from kraken.logging import APIHandler, WSGILogWrapper
from kraken.utilities import add_cors_to_response, make_json_error
from kraken.framework import register_frameworks

from flask import Flask
from flask_socketio import SocketIO
from werkzeug.exceptions import default_exceptions
import json

app = Flask(__name__)
socketio = SocketIO(app)


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


def run_daemon(environment, config_file, secrets_file,
               policies_file, debug):
    """Run the Kraken server daemon."""
    app.debug = debug or environment in ["dev", "vagrant"]
    app.config["SECRET_KEY"] = random_string()

    # Open and load configuraton
    config = arkos.init(config_file, secrets_file, policies_file,
                        app.debug, environment in ["dev", "vagrant"],
                        app.logger)
    storage.connect()
    logger.info("Init", "arkOS Kraken {0}".format(arkos.version))
    if environment in ["dev", "vagrant"]:
        logger.debug("Init", "*** TEST MODE ***")
    logger.info("Init", "Using config file at {0}".format(config.filename))
    app.conf = config

    arch = config.get("enviro", "arch", "Unknown")
    board = config.get("enviro", "board", "Unknown")
    platform = detect_platform()
    hwstr = "Detected architecture/hardware: {0}, {1}"
    logger.info("Init", hwstr.format(arch, board))
    logger.info("Init", "Detected platform: {0}".format(platform))
    logger.info("Init", "Environment: {0}".format(environment))
    config.set("enviro", "run", environment)

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
    app.register_blueprint(genesis.backend)
    try:
        genesis.backend.verify_genesis()
    except:
        errmsg = ("A compiled distribution of Genesis was not found. "
                  "Kraken will finish loading but you may not be able to "
                  "access the Web interface.")
        logger.warning("Init", errmsg)

    app.after_request(add_cors_to_response)
    logger.info("Init", "Server is up and ready")
    try:
        import eventlet
        pubsub = storage.redis.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(["arkos:notifications", "arkos:records:push",
                          "arkos:records:purge"])
        eventlet.spawn(handle_pubsub, pubsub, socketio)
        eventlet_socket = eventlet.listen(
            (config.get("genesis", "host"), config.get("genesis", "port"))
        )
        if config.get("genesis", "ssl", False):
            eventlet_socket = eventlet.wrap_ssl(
                eventlet_socket, certfile=config.get("genesis", "cert_file"),
                keyfile=config.get("genesis", "cert_key"),
                ssl_version=ssl.PROTOCOL_TLSv1_2, server_side=True)
        eventlet.wsgi.server(eventlet_socket, app, log=WSGILogWrapper(),
            log_format=('%(client_ip)s - "%(request_line)s" %(status_code)s '
                        '%(body_length)s %(wall_seconds).6f'))
    except KeyboardInterrupt:
        logger.info("Init", "Received interrupt")
        raise
