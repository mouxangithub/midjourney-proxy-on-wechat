# encoding:utf-8
import os
import io
import json
import base64
import requests
from PIL import Image
from plugins import *
from lib import itchat
from lib.itchat.content import *
from bridge.reply import Reply, ReplyType
from config import conf
from common.log import logger


ADMIN_COMMANDS = {
    "set_mj_url": {
        "alias": ["set_mj_url", "设置MJ服务地址"],
        "args": ["服务器地址", "请求头参数"],
        "desc": "设置MJ服务地址",
    },
    "set_mj_admin_password": {
        "alias": ["set_mj_admin_password"],
        "args": ["口令"],
        "desc": "修改MJ管理员认证口令",
    },
    "stop_mj": {
        "alias": ["stop_mj", "暂停MJ服务"],
        "desc": "暂停MJ服务",
    },
    "enable_mj": {
        "alias": ["enable_mj", "启用MJ服务"],
        "desc": "启用MJ服务",
    },
    "mj_tip": {
        "alias": ["mj_tip", "MJ提示"],
        "desc": "启用/关闭MJ提示",
    },
    "clean_mj": {
        "alias": ["clean_mj", "清空MJ缓存"],
        "desc": "清空MJ缓存",
    },
    "g_wgroup": {
        "alias": ["g_wgroup", "查询白名单群组"],
        "desc": "查询白名单群组",
    },
    "s_wgroup": {
        "alias": ["s_wgroup", "设置白名单群组"],
        "args": ["群组名称"],
        "desc": "设置白名单群组",
    },
    "r_wgroup": {
        "alias": ["r_wgroup", "移除白名单群组"],
        "args": ["群组名称或序列号"],
        "desc": "移除白名单群组",
    },
    "c_wgroup": {
        "alias": ["c_wgroup", "清空白名单群组"],
        "desc": "清空白名单群组",
    },
    "g_wuser": {
        "alias": ["g_wuser", "查询白名单用户"],
        "desc": "查询白名单用户",
    },
    "s_wuser": {
        "alias": ["s_wuser", "设置白名单用户"],
        "args": ["用户ID或昵称"],
        "desc": "设置白名单用户",
    },
    "r_wuser": {
        "alias": ["r_wuser", "移除白名单用户"],
        "args": ["用户ID或昵称或序列号"],
        "desc": "移除白名单用户",
    },
    "c_wuser": {
        "alias": ["c_wuser", "清空白名单用户"],
        "desc": "清空白名单用户",
    }
}


def check_prefix_list(content, config):
    for key, value in config.items():
        if key.endswith("_prefix"):
            status, data = check_prefix(content, value)
            if status:
                return key, data
    return False, ""


def check_prefix(content, prefix_list):
    if not prefix_list:
        return False, ""
    for prefix in prefix_list:
        if content.startswith(prefix):
            return True, content.replace(prefix, "").strip()
    return False, ""


def image_to_base64(image_path):
    filename, extension = os.path.splitext(image_path)
    t = extension[1:]
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return f"data:image/{t};base64,{encoded_string.decode('utf-8')}"


def read_file(path):
    with open(path, mode="r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4)
    return True


def img_to_jpeg(image_url):
    image = io.BytesIO()
    res = requests.get(image_url)
    idata = Image.open(io.BytesIO(res.content))
    idata = idata.convert("RGB")
    idata.save(image, format="JPEG")
    return image


def Text(msg, e_context: EventContext):
    return send(msg, e_context, ReplyType.TEXT)


def Image(msg, e_context: EventContext):
    return send(msg, e_context, ReplyType.IMAGE)


def Image_url(msg, e_context: EventContext):
    return send(msg, e_context, ReplyType.IMAGE_URL)


def Info(msg, e_context: EventContext):
    return send(msg, e_context, ReplyType.INFO)


def Error(msg, e_context: EventContext):
    return send(msg, e_context, ReplyType.ERROR)


def send(reply, e_context: EventContext, types=ReplyType.TEXT, action=EventAction.BREAK_PASS):
    if isinstance(reply, str):
        reply = Reply(types, reply)
    elif not reply.type and types:
        reply.type = types
    e_context["reply"] = reply
    e_context.action = action
    return


def send_reply(self, msg="", types=ReplyType.TEXT):
    context = self.context
    channel = self.channel
    reply = channel._decorate_reply(context, Reply(types, msg))
    return channel._send_reply(context, reply)


def get_f_img(self, id, types="image"):
    status, msg, imageUrl = self.mj.get_f_img(id)
    rt = ReplyType.TEXT
    rc = msg
    if not status:
        rt = ReplyType.ERROR
    if status and imageUrl:
        if self.mj_tip:
            send_reply(self, msg)
            rt = ReplyType.IMAGE
            rc = img_to_jpeg(imageUrl)
        elif types == "image":
            rt = ReplyType.IMAGE
            rc = img_to_jpeg(imageUrl)
    return rc, rt


def search_friends(name):
    userInfo = {
        "user_id": "",
        "user_nickname": ""
    }
    # 判断是id还是昵称
    if name.startswith("@"):
        friends = itchat.search_friends(userName=name)
    else:
        friends = itchat.search_friends(name=name)
    if friends and len(friends) > 0:
        if isinstance(friends, list):
            userInfo["user_id"] = friends[0]["UserName"]
            userInfo["user_nickname"] = friends[0]["NickName"]
        else:
            userInfo["user_id"] = friends["UserName"]
            userInfo["user_nickname"] = friends["NickName"]
    return userInfo


def env_detection(self, e_context: EventContext):
    trigger_prefix = conf().get("plugin_trigger_prefix", "$")
    if not self.mj_url:
        if self.isadmin:
            reply = Reply(ReplyType.ERROR, f"未设置[mj_url]，请输入{trigger_prefix}set_mj_url+服务器地址+请求头参数进行设置。")
        else:
            reply = Reply(ReplyType.ERROR, "未设置[mj_url]，请联系管理员进行设置。")
        e_context["reply"] = reply
        e_context.action = EventAction.BREAK_PASS
        return False
    return True


def get_help_text(self, **kwargs):
    if kwargs.get("verbose") != True:
        return "这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。"
    else:
        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        help_text = self.mj.help_text()
        if ADMIN_COMMANDS and self.isadmin:
            help_text += f"\n-----------------------------\n"
            help_text += "管理员指令：\n"
            for cmd, info in ADMIN_COMMANDS.items():
                alias = [trigger_prefix + a for a in info["alias"][:1]]
                help_text += f"{','.join(alias)} "
                if "args" in info:
                    args = [a for a in info["args"]]
                    help_text += f"{' '.join(args)}"
                help_text += f": {info['desc']}\n"
        return help_text
