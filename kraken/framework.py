"""
Function for accepting and importing API endpoint sets.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import imp
import os


def register_frameworks(app):
    """
    Register an API framework (set of endpoints) with the server.

    :param Flask app: Flask app
    """
    fmwkdir = os.path.join(os.path.dirname(__file__), "frameworks")
    for x in os.listdir(fmwkdir):
        if x.startswith(".") or x == "__init__.py"\
                or x.endswith((".pyc", ".pyo")):
            continue
        x = x.split(".py")[0]
        mod = imp.load_module(x, *imp.find_module(x, [fmwkdir]))
        app.logger.debug(" *** Registering {0}...".format(x))
        app.register_blueprint(mod.backend)
