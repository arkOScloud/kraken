import imp
import os
import sys

import messages


def register_frameworks(app):
    for x in os.listdir(os.path.join(sys.path[0], "kraken/frameworks")):
        if x.startswith(".") or x == "__init__.py" or x.endswith(".pyc"):
            continue
        x = x.split(".py")[0]
        mod = imp.load_module(x, *imp.find_module(x, [os.path.join(sys.path[0], "kraken/frameworks")]))
        app.logger.debug(" *** Registering %s..." % x)
        app.register_blueprint(mod.backend)
    app.register_blueprint(messages.backend)
