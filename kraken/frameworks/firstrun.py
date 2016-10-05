"""
Endpoints for management of arkOS backups.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import os

from flask import Blueprint, request, jsonify

from kraken import auth
from kraken.jobs import as_job
from kraken.records import push_record

from arkos import applications, config, security
from arkos.messages import Notification, NotificationThread
from arkos.utilities import shell, random_string
from arkos.system import filesystems

backend = Blueprint("firstrun", __name__)


def install(job, to_install):
    errors = False
    nthread = NotificationThread(id=job.id)
    nthread.title = "Setting up your server..."

    for x in to_install:
        a = applications.get(x)
        msg = "Installing {0}...".format(x)
        nthread.update(Notification("info", "FirstRun", msg))
        try:
            a.install()
            push_record("app", a.serialized)
        except:
            errors = True

    if to_install:
        if errors:
            msg = ("One or more applications failed to install. "
                   "Check the App Store pane for more information.")
            nthread.complete(Notification("warning", "FirstRun", msg))
        else:
            msg = ("You may need to restart your device before "
                   "changes will take effect.")
            nthread.complete(Notification("success", "FirstRun", msg))


@backend.route('/api/firstrun', methods=["POST"])
@auth.required()
def firstrun():
    data = request.get_json()
    resize_boards = ["Raspberry Pi", "Raspberry Pi 2", "Raspberry Pi 3",
                     "Cubieboard2", "Cubietruck", "BeagleBone Black",
                     "ODROID-U"]
    if data.get("resize_sd_card", None)\
            and config.get("enviro", "board") in resize_boards:
        part = 1 if config.get("enviro", "board").startswith("Cubie") else 2
        p1str = 'd\nn\np\n1\n\n\nw\n'
        p2str = 'd\n2\nn\np\n2\n\n\nw\n'
        shell('fdisk /dev/mmcblk0', stdin=(p1str if part == 1 else p2str))
        if not os.path.exists('/etc/cron.d'):
            os.mkdir('/etc/cron.d')
        with open('/etc/cron.d/resize', 'w') as f:
            f.write('@reboot root e2fsck -fy /dev/mmcblk0p{0}\n'.format(part))
            f.write('@reboot root resize2fs /dev/mmcblk0p{0}\n'.format(part))
            f.write('@reboot root rm /etc/cron.d/resize\n')
            f.close()
    if data.get("use_gpu_mem", None) \
            and config.get("enviro", "board").startswith("Raspberry"):
        f = filesystems.get("mmcblk0p1")
        if not f.is_mounted():
            f.mountpoint = "/boot"
            f.mount()
        cfgdata = []
        if os.path.exists('/boot/config.txt'):
            with open("/boot/config.txt", "r") as f:
                for x in f.readlines():
                    if x.startswith("gpu_mem"):
                        x = "gpu_mem=16\n"
                    cfgdata.append(x)
                if "gpu_mem=16\n" not in cfgdata:
                    cfgdata.append("gpu_mem=16\n")
            with open("/boot/config.txt", "w") as f:
                f.writelines(cfgdata)
        else:
            with open("/boot/config.txt", "w") as f:
                f.write("gpu_mem=16\n")
    if data.get("cubie_mac", None) \
            and config.get("enviro", "board").startswith("Cubie"):
        if config.get("enviro", "board") == "Cubieboard2":
            with open('/boot/uEnv.txt', 'w') as f:
                opt_str = 'extraargs=mac_addr={0}\n'
                f.write(opt_str.format(data.get("cubie_mac")))
        elif config.get("enviro", "board") == "Cubietruck":
            with open('/etc/modprobe.d/gmac.conf', 'w') as f:
                opt_str = 'options sunxi_gmac mac_str="{0}"\n'
                f.write(opt_str.format(data.get("cubie_mac")))
    if data.get("install"):
        as_job(install, data["install"])
    rootpwd = ""
    if data.get("protectRoot"):
        rootpwd = random_string(16)
        shell("passwd root", stdin="{0}\n{0}\n".format(rootpwd))
    security.initialize_firewall()
    return jsonify(rootpwd=rootpwd)
