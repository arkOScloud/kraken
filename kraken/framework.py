import imp
import os
import sys


def register_frameworks(app):
    fmwkdir = os.path.join(os.path.dirname(__file__), "frameworks")
    for x in os.listdir(fmwkdir):
        if x.startswith(".") or x == "__init__.py" or x.endswith((".pyc", ".pyo")):
            continue
        x = x.split(".py")[0]
        mod = imp.load_module(x, *imp.find_module(x, [fmwkdir]))
        app.logger.debug(" *** Registering %s..." % x)
        app.register_blueprint(mod.backend)
