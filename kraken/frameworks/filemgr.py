import grp
import json
import mimetypes
import os
import pwd
import shutil
import stat

from arkos.utilities import b64_to_path, path_to_b64, compress, extract, str_fperms

from flask import Response, Blueprint, jsonify, request, abort
from flask.views import MethodView
from kraken.utilities import as_job, job_response

backend = Blueprint("filemgr", __name__)


class FileManagerAPI(MethodView):
    def get(self, path):
        path = b64_to_path(path)
        if not path or not os.path.exists(path):
            abort(404)
        if request.args.get("download", None):
            if os.path.isdir(path):
                apath = compress(path, format="zip")
                with open(apath, "r") as f:
                    data = f.read()
                resp = Response(data, mimetype="application/octet-stream")
                resp.headers["Content-Length"] = os.path.getsize(apath)
                resp.headers["Content-Disposition"] = "attachment; filename=%s" % os.path.basename(apath)
                return resp
            else: 
                with open(path, "r") as f:
                    data = f.read()
                resp = Response(data, mimetype="application/octet-stream")
                resp.headers["Content-Length"] = str(len(data.encode('utf-8')))
                resp.headers["Content-Disposition"] = "attachment; filename=%s" % os.path.basename(path)
                return resp
        if os.path.isdir(path):
            data = []
            for x in os.listdir(path):
                data.append(as_dict(os.path.join(path, x)))
            return jsonify(files=data)
        else:
            return jsonify(file=as_dict(path))
    
    def post(self, path):
        path = b64_to_path(path)
        if not os.path.exists(path):
            abort(404)
        if not os.path.isdir(path):
            resp = jsonify(message="Can only upload into folders")
            resp.status_code = 422
            return resp
        if request.headers.get('Content-Type').startswith("multipart/form-data"):
            f = request.files.get("file")
            if type(f) == list:
                for x in f:
                    filename = secure_filename(x.filename)
                    x.save(os.path.join(path, filename))
            else:
                filename = secure_filename(f.filename)
                f.save(os.path.join(path, filename))
            results = []
            for x in os.listdir(path):
                results.append(as_dict(os.path.join(path, x)))
        else:
            data = json.loads(request.data)["file"]
            if not os.path.exists(path):
                abort(404)
            if not os.path.isdir(path):
                resp = jsonify(message="Can only create into folders")
                resp.status_code = 422
                return resp
            if data["folder"]:
                os.makedirs(os.path.join(path, data["name"]))
            else:
                with open(os.path.join(path, data["name"]), 'w') as f:
                    f.write("")
            return jsonify(file=as_dict(os.path.join(path, data["name"])))
    
    def put(self, path):
        data = json.loads(request.data)["file"]
        if not os.path.exists(data["path"]):
            abort(404)
        if data["operation"] == "copy":
            if os.path.exists(os.path.join(data["newdir"], data["name"])):
                data["name"] = data["name"]+"-copy"
            if os.path.isdir(data["path"]):
                shutil.copytree(data["path"], os.path.join(data["newdir"], data["name"]))
            else:
                shutil.copy2(data["path"], os.path.join(data["newdir"], data["name"]))
            return jsonify(file=as_dict(os.path.join(data["newdir"], data["name"])))
        elif data["operation"] == "rename":
            shutil.move(data["path"], os.path.join(os.path.split(join(data["path"]))[0], data["name"]))
        elif data["operation"] == "edit":
            with open(data["path"], "w") as f:
                f.write(data["data"])
        else:
            abort(422)
    
    def delete(self, path):
        path = b64_to_path(path)
        if not os.path.exists(path):
            abort(404)
        try:
            if os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
            return Response(status=204)
        except:
            abort(404)


def as_dict(path):
    name = os.path.basename(path)
    data = {"id": path_to_b64(path), "name": name, "path": path, "folder": False, 
        "hidden": name.startswith(".")}
    fstat = os.lstat(path)
    mode = fstat[stat.ST_MODE]
    
    if os.path.ismount(path):
        data["type"] = "mount"
        data["folder"] = True
        data["icon"] = "fa-hdd-o"
    elif stat.S_ISLNK(mode):
        data["type"] = "link"
        data["realpath"] = os.path.realpath(path)
        data["folder"] = os.path.isdir(data["realpath"])
        data["icon"] = "fa-link"
    elif stat.S_ISDIR(mode):
        data["type"] = "folder"
        data["folder"] = True
        data["icon"] = "fa-folder"
    elif stat.S_ISSOCK(mode):
        data["type"] = "socket"
        data["icon"] = "fa-plug"
    elif stat.S_ISBLK(mode):
        data["type"] = "block"
        data["icon"] = "fa-hdd-o"
    elif stat.S_ISREG(mode):
        data["type"] = "file"
        data["icon"] = guess_file_icon(name)
    else:
        data["type"] = "unknown"
        data["icon"] = "fa-question-circle"
    try:
        data["perms"] = {"oct": oct(stat.S_IMODE(mode)), "str": str_fperms(mode)}
        data["size"] = fstat[stat.ST_SIZE]
    except:
        return
    try:
        data["user"] = pwd.getpwuid(fstat[stat.ST_UID])[0]
    except:
        data["user"] = str(fstat[stat.ST_UID])
    try:
        data["group"] = grp.getgrgid(fstat[stat.ST_GID])[0]
    except:
        data["group"] = str(fstat[stat.ST_GID])
    if data["type"] == "file":
        tc = "".join(map(chr, [7,8,9,10,12,13,27] + range(0x20, 0x100)))
        ibs = lambda b: bool(b.translate(None, tc))
        with open(path, 'r') as f:
            try:
                data["binary"] = ibs(f.read(1024))
            except:
                data["binary"] = True
    else:
        data["binary"] = False
    data["mimetype"] = mimetypes.guess_type(path)[0]
    data["selected"] = False
    return data

def guess_file_icon(name):
    if name.endswith((".xls", ".xlsx", ".ods")):
        return "fa-file-excel-o"
    elif name.endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac")):
        return "fa-file-audio-o"
    elif name.endswith((".mkv", ".avi", ".mov", ".wmv", ".mp4", ".m4v", ".mpg")):
        return "fa-file-video-o"
    elif name.endswith(".pdf"):
        return "fa-file-pdf-o"
    elif name.endswith((".ppt", ".pptx", ".odp")):
        return "fa-file-powerpoint-o"
    elif name.endswith((".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".bmp")):
        return "fa-file-image-o"
    elif name.endswith((".zip", ".tar", ".gz", ".bz2", ".rar")):
        return "fa-file-archive-o"
    elif name.endswith((".doc", ".docx", ".odt")):
        return "fa-file-word-o"
    elif name.endswith((".php", ".js", ".py", ".sh", ".html", ".xml", ".rb")):
        return "fa-file-code-o"
    else:
        return "fa-file-o"


filemgr_view = FileManagerAPI.as_view('filemgr_api')
backend.add_url_rule('/files/<string:path>', view_func=filemgr_view, 
    methods=['GET', 'POST', 'PUT', 'DELETE'])
