from flask import Blueprint, request, Response, current_app

from kraken import auth, genesis
from kraken.utilities import as_job
from kraken.messages import Message, push_record

from arkos import config, applications
from arkos.utilities import shell
from arkos.system import filesystems

backend = Blueprint("firstrun", __name__)


def install(to_install):
    errors = False
    for x in to_install:
        a = applications.get(x)
        try:
            a.install()
        except:
            errors = True
    if to_install:
        try:
            genesis.genesis_build()
        except:
            Message("error", "Genesis rebuild failed. Please try to manually rebuild.")
        if errors:
            Message("warning", "One or more applications failed to install. Check the App Store pane for more information.")
        else:
            Message("success", "You will need to refresh this page before changes will take effect.", head="Applications installed successfully")


@backend.route('/api/firstrun', methods=["POST"])
@auth.required()
def firstrun():
    data = request.get_json()
    if data.get("resize_sd_card", None) \
    and config.get("enviro", "board") in ["Raspberry Pi", "Raspberry Pi 2", 
    "Cubieboard2", "Cubietruck", "BeagleBone Black", "ODROID-U"]:
        part = 1 if config.get("enviro", "board").startswith("Cubie") else 2
        if part == 1:
            shell('fdisk /dev/mmcblk0', 
                stdin=('d\nn\np\n1\n\n\nw\n' if part == 1 else 'd\n2\nn\np\n2\n\n\nw\n'))
        if not os.path.exists('/etc/cron.d'):
            os.mkdir('/etc/cron.d')
        with open('/etc/cron.d/resize', 'w') as f:
            f.write('@reboot root resize2fs /dev/mmcblk0p%s\n'%part)
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
                if not "gpu_mem=16\n" in cfgdata:
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
                f.write('extraargs=mac_addr=%s\n' % data.get("cubie_mac"))
        elif config.get("enviro", "board") == "Cubietruck":
            with open('/etc/modprobe.d/gmac.conf', 'w') as f:
                f.write('options sunxi_gmac mac_str="%s"\n' % data.get("cubie_mac"))
    if data.get("install"):
        as_job(install, data["install"])
    return Response(status=200)
