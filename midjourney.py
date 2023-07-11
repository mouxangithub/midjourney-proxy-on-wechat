# encoding:utf-8
import requests
import os
import io
import json
import base64
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from common.expired_dict import ExpiredDict
from plugins import *
from PIL import Image
from .mjapi import _mjApi
from .mjcache import _imgCache
from channel.chat_message import ChatMessage
from config import conf
from typing import Tuple
from config import conf
from lib import itchat
from lib.itchat.content import *


def check_prefix(content, prefix_list):
    if not prefix_list:
        return False, None
    for prefix in prefix_list:
        if content.startswith(prefix):
            return True, content.replace(prefix, "").strip()
    return False, None


def image_to_base64(image_path):
    filename, extension = os.path.splitext(image_path)
    t = extension[1:]
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return f"data:image/{t};base64,{encoded_string.decode('utf-8')}"

# 下载图片，任何格式都转JPEG


def img_to_jpeg(image_url):
    image = io.BytesIO()
    res = requests.get(image_url)
    idata = Image.open(io.BytesIO(res.content))
    idata = idata.convert("RGB")
    idata.save(image, format="JPEG")
    return image


def read_file(path):
    with open(path, mode="r", encoding="utf-8") as f:
        return f.read()


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4)
    return True


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


@plugins.register(
    name="MidJourney",
    namecn="MJ绘画",
    desc="一款AI绘画工具",
    version="1.0.37",
    author="mouxan",
    desire_priority=0
)
class MidJourney(Plugin):
    def __init__(self):
        super().__init__()

        gconf = {
            "mj_url": "",
            "mj_api_secret": "",
            "mj_tip": True,
            "mj_admin_password": "",
            "mj_admin_users": [],
            "mj_users": [
                {
                    "user_id": "ALL_USER",
                    "user_nickname": "所有用户"
                }
            ],
            "mj_groups": [
                "ALL_GROUP"
            ],
            "imagine_prefix": [
                "/i",
                "/mj"
            ],
            "fetch_prefix": [
                "/f"
            ],
            "up_prefix": [
                "/u"
            ],
            "pad_prefix": [
                "/p"
            ],
            "blend_prefix": [
                "/b"
            ],
            "describe_prefix": [
                "/d"
            ],
            "queue_prefix": [
                "/q"
            ],
            "end_prefix": [
                "/e"
            ]
        }

        # 读取和写入配置文件
        curdir = os.path.dirname(__file__)
        self.json_path = os.path.join(curdir, "config.json")
        if not os.path.exists(self.json_path):
            config_path = os.path.join(curdir, "config.json.template")
        else:
            config_path = self.json_path
        if os.environ.get("mj_url", None):
            gconf = {
                "mj_url": os.environ.get("mj_url", ""),
                "mj_api_secret": os.environ.get("mj_api_secret", ""),
                "mj_tip": os.environ.get("mj_tip", True),
                "mj_admin_password": os.environ.get("mj_admin_password", ""),
                "mj_admin_users": [],
                "mj_groups": os.environ.get("mj_groups", ["ALL_GROUP"]),
                "mj_users": os.environ.get("mj_users", [
                    {
                        "user_id": "ALL_USER",
                        "user_nickname": "所有用户"
                    }
                ]),
                "imagine_prefix": os.environ.get("imagine_prefix", "[\"/i\", \"/mj\"]"),
                "fetch_prefix": os.environ.get("fetch_prefix", "[\"/f\"]"),
                "up_prefix": os.environ.get("up_prefix", "[\"/u\"]"),
                "pad_prefix": os.environ.get("pad_prefix", "[\"/p\"]"),
                "blend_prefix": os.environ.get("blend_prefix", "[\"/b\"]"),
                "describe_prefix": os.environ.get("describe_prefix", "[\"/d\"]"),
                "queue_prefix": os.environ.get("queue_prefix", "[\"/q\"]"),
                "end_prefix": os.environ.get("end_prefix", "[\"/e\"]")
            }
        else:
            gconf = {**gconf, **json.loads(read_file(config_path))}

        if gconf["mj_admin_password"] == "":
            self.temp_password = "123456"
            logger.info("[MJ] 因未设置管理员密码，本次的临时密码为%s。" % self.temp_password)
        else:
            self.temp_password = None

        if gconf["mj_url"] == "":
            logger.info("[MJ] 未设置[mj_url],请前往环境变量进行配置或在该插件目录下的config.json进行配置.")

        logger.info("[MJ] config={}".format(gconf))

        self.mj_url = gconf["mj_url"]
        self.mj_api_secret = gconf["mj_api_secret"]
        self.mj_tip = gconf["mj_tip"]
        self.mj_admin_password = gconf["mj_admin_password"]
        if not gconf["mj_users"]:
            self.mj_users = [{
                "user_id": "ALL_USER",
                "user_nickname": "ALL_USER"
            }]
        else:
            self.mj_users = eval(gconf["mj_users"]) if isinstance(gconf["mj_users"], str) else gconf["mj_users"]
        if not gconf["mj_admin_users"]:
            self.mj_admin_users = []
        else:
            self.mj_admin_users = eval(gconf["mj_admin_users"]) if isinstance(gconf["mj_admin_users"], str) else gconf["mj_admin_users"]
        if not gconf["mj_groups"]:
            self.mj_groups = ["ALL_GROUP"]
        else:
            self.mj_groups = eval(gconf["mj_groups"]) if isinstance(gconf["mj_groups"], str) else gconf["mj_groups"]
        if not gconf["imagine_prefix"]:
            self.imagine_prefix = ["/i", "/mj"]
        else:
            self.imagine_prefix = eval(gconf["imagine_prefix"]) if isinstance(gconf["imagine_prefix"], str) else gconf["imagine_prefix"]
        if not gconf["fetch_prefix"]:
            self.fetch_prefix = ["/f"]
        else:
            self.fetch_prefix = eval(gconf["fetch_prefix"]) if isinstance(gconf["fetch_prefix"], str) else gconf["fetch_prefix"]
        if not gconf["up_prefix"]:
            self.up_prefix = ["/u"]
        else:
            self.up_prefix = eval(gconf["up_prefix"]) if isinstance(gconf["up_prefix"], str) else gconf["up_prefix"]
        if not gconf["pad_prefix"]:
            self.pad_prefix = ["/p"]
        else:
            self.pad_prefix = eval(gconf["pad_prefix"]) if isinstance(gconf["pad_prefix"], str) else gconf["pad_prefix"]
        if not gconf["blend_prefix"]:
            self.blend_prefix = ["/b"]
        else:
            self.blend_prefix = eval(gconf["blend_prefix"]) if isinstance(gconf["blend_prefix"], str) else gconf["blend_prefix"]
        if not gconf["describe_prefix"]:
            self.describe_prefix = ["/d"]
        else:
            self.describe_prefix = eval(gconf["describe_prefix"]) if isinstance(gconf["describe_prefix"], str) else gconf["describe_prefix"]
        if not gconf["queue_prefix"]:
            self.queue_prefix = ["/q"]
        else:
            self.queue_prefix = eval(gconf["queue_prefix"]) if isinstance(gconf["queue_prefix"], str) else gconf["queue_prefix"]
        if not gconf["end_prefix"]:
            self.end_prefix = ["/e"]
        else:
            self.end_prefix = eval(gconf["end_prefix"]) if isinstance(gconf["end_prefix"], str) else gconf["end_prefix"]

        self.config = {
            "mj_url": self.mj_url,
            "mj_api_secret": self.mj_api_secret,
            "mj_tip": self.mj_tip,
            "mj_admin_password": self.mj_admin_password,
            "mj_groups": self.mj_groups,
            "mj_users": self.mj_users,
            "mj_admin_users": self.mj_admin_users,
            "imagine_prefix": self.imagine_prefix,
            "fetch_prefix": self.fetch_prefix,
            "up_prefix": self.up_prefix,
            "pad_prefix": self.pad_prefix,
            "blend_prefix": self.blend_prefix,
            "describe_prefix": self.describe_prefix,
            "queue_prefix": self.queue_prefix,
            "end_prefix": self.end_prefix
        }

        # 重新写入配置文件
        write_file(self.json_path, self.config)

        # 目前没有设计session过期事件，这里先暂时使用过期字典
        if conf().get("expires_in_seconds"):
            self.sessions = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            self.sessions = dict()

        self.ismj = True  # 机器人是否运行中

        self.mj = _mjApi(self.config)

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        logger.info("[MJ] inited")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.IMAGE,
        ]:
            return

        trigger_prefix = conf().get("plugin_trigger_prefix", "$")
        channel = e_context['channel']
        context = e_context['context']
        content = context.content
        msg: ChatMessage = context["msg"]
        sessionid = context["session_id"]
        isgroup = context.get("isgroup", False)
        reply = Reply()

        # 写入用户信息
        userInfo = {
            "user_id": msg.from_user_id,
            "user_nickname": msg.from_user_nickname,
            "isadmin": False,
            "isgroup": isgroup,
        }
        if isgroup:
            userInfo["group_id"] = msg.from_user_id
            userInfo["user_id"] = msg.actual_user_id
            userInfo["group_name"] = msg.from_user_nickname
            userInfo["user_nickname"] = msg.actual_user_nickname

        # 判断管理员权限
        self.isadmin = False

        # 判断是否是管理员
        if not isgroup and (userInfo["user_id"] in [user["user_id"] for user in self.mj_admin_users]):
            self.isadmin = True
            userInfo['isadmin'] = True

        self.mj.set_user(json.dumps(userInfo))

        if ContextType.TEXT == context.type and content.startswith(trigger_prefix):
            command_parts = content[1:].strip().split()
            cmd = command_parts[0]
            args = command_parts[1:]
            reply.type = ReplyType.INFO
            if cmd == "mj_help":
                reply.content = self.get_help_text(verbose=True)
                return self.send(reply, e_context)
            elif cmd == "mj_admin_password":
                ok, result = self.authenticate(userInfo, args)
                if not ok:
                    reply.type = ReplyType.ERROR
                reply.content = result
                return self.send(reply, e_context)
            elif cmd == "set_mj_admin_password":
                if self.isadmin == False:
                    return self.send("[MJ] 您没有权限执行该操作,进行管理员认证", e_context, ReplyType.ERROR)
                if len(args) < 1:
                    return self.send("[MJ] 请输入需要设置的密码", e_context, ReplyType.ERROR)
                password = args[0]
                if len(password) < 6:
                    return self.send("[MJ] 密码长度不能小于6位", e_context, ReplyType.ERROR)
                if password == self.temp_password:
                    return self.send("[MJ] 不能使用临时密码，请重新设置", e_context, ReplyType.ERROR)
                if password == self.mj_admin_password:
                    return self.send("[MJ] 新密码不能与旧密码相同", e_context, ReplyType.ERROR)
                self.mj_admin_password = password
                self.config["mj_admin_password"] = password
                write_file(self.json_path, self.config)
                reply.content = "[MJ] 管理员口令设置成功"
                return self.send(reply, e_context)
            elif cmd == "set_mj_url" or cmd == "stop_mj" or cmd == "enable_mj" or cmd == "clean_mj" or cmd == "mj_tip" or cmd == "s_wgroup" or cmd == "r_wgroup" or cmd == "g_wgroup" or cmd == "c_wgroup" or cmd == "s_wuser" or cmd == "r_wuser" or cmd == "g_wuser" or cmd == "c_wuser":
                if self.isadmin == False:
                    return self.send(f"[MJ] 您没有权限执行该操作,请先输入{trigger_prefix}mj_admin_password+密码进行认证", e_context, ReplyType.ERROR)
                if cmd == "mj_tip":
                    self.mj_tip = not self.mj_tip
                    self.config["mj_tip"] = self.mj_tip
                    write_file(self.json_path, self.config)
                    reply.content = f"[MJ] 提示功能已{'开启' if self.mj_tip else '关闭'}"
                elif cmd == "stop_mj":
                    self.ismj = False
                    reply.content = "[MJ] 服务已暂停"
                elif cmd == "enable_mj":
                    self.ismj = True
                    reply.content = "[MJ] 服务已启用"
                elif cmd == "clean_mj":
                    if sessionid in self.sessions:
                        self.sessions[sessionid].reset()
                        del self.sessions[sessionid]
                    reply.content = "[MJ] 缓存已清理"
                elif cmd == "g_wgroup" and not isgroup:
                    if "ALL_GROUP" in self.mj_groups:
                        reply.content = "[MJ] 白名单群组：所有群组"
                    elif len(self.mj_groups) == 0:
                        reply.content = "[MJ] 白名单群组：无"
                    else:
                        t = "\n"
                        reply.content = f"[MJ] 白名单群组\n{t.join(f'{index+1}. {group}' for index, group in enumerate(self.mj_groups))}"
                elif cmd == "c_wgroup":
                    self.mj_groups = ["ALL_GROUP"]
                    self.config["mj_groups"] = self.mj_groups
                    write_file(self.json_path, self.config)
                    reply.content = "[MJ] 白名单已清空，目前所有群组都可以使用MJ服务"
                elif cmd == "s_wgroup":
                    if not isgroup and len(args) < 1:
                        return self.send("[MJ] 请输入需要设置的群组名称", e_context, ReplyType.ERROR)
                    if isgroup:
                        group_name = userInfo["group_name"]
                    if args and args[0]:
                        group_name = args[0]
                    # 如果是设置所有群组，则清空其他群组
                    if group_name == "ALL_GROUP" or group_name == "all_group" or group_name == "所有群组":
                        self.mj_groups = ["ALL_GROUP"]
                        reply = Reply(ReplyType.INFO, f"[MJ] 白名单已清空，目前所有群组都可以使用MJ服务")
                    else:
                        if group_name in self.mj_groups:
                            return self.send(f"[MJ] 群组[{group_name}]已在白名单中", e_context, ReplyType.ERROR)
                        if "ALL_GROUP" in self.mj_groups:
                            self.mj_groups.remove("ALL_GROUP")
                        # 判断是否是itchat平台，并判断group_name是否在列表中
                        if conf().get("channel_type", "wx") == "wx":
                            isonin = itchat.search_chatrooms(name=group_name)
                            if len(isonin) == 0:
                                return self.send(f"[MJ] 群组[{group_name}]不存在", e_context, ReplyType.ERROR)
                        self.mj_groups.append(group_name)
                        reply.content = f"[MJ] 群组[{group_name}]已添加到白名单"
                    self.config["mj_groups"] = self.mj_groups
                    write_file(self.json_path, self.config)
                elif cmd == "r_wgroup":
                    if not isgroup and len(args) < 1:
                        return self.send("[MJ] 请输入需要移除的群组名称或序列号", e_context, ReplyType.ERROR)
                    if isgroup:
                        group_name = userInfo["group_name"]
                    if args and args[0]:
                        if args[0].isdigit():
                            index = int(args[0]) - 1
                            if index < 0 or index >= len(self.mj_groups):
                                return self.send(f"[MJ] 序列号[{args[0]}]不在白名单中", e_context, ReplyType.ERROR)
                            group_name = self.mj_groups[index]
                        else:
                            group_name = args[0]
                    if group_name in self.mj_groups:
                        self.mj_groups.remove(group_name)
                        if len(self.mj_groups) == 0:
                            self.mj_groups.append("ALL_GROUP")
                        self.config["mj_groups"] = self.mj_groups
                        write_file(self.json_path, self.config)
                        reply.content = f"[MJ] 群组[{group_name}]已从白名单中移除"
                    else:
                        return self.send(f"[MJ] 群组[{group_name}]不在白名单中", e_context, ReplyType.ERROR)
                elif cmd == "g_wuser" and not isgroup:
                    t = "\n"
                    if any(user["user_id"] == "ALL_USER" for user in self.mj_users):
                        reply.content = "[MJ] 白名单用户：所有用户"
                    elif len(self.mj_users) == 0:
                        reply.content = "[MJ] 白名单用户：无"
                    else:
                        lists = t.join(f'{index+1}. {data["user_nickname"]}' for index, data in enumerate(self.mj_users))
                        reply.content = f"[MJ] 白名单用户\n{lists}"
                elif cmd == "c_wuser":
                    self.mj_users = [{
                        "user_id": "ALL_USER",
                        "user_nickname": "所有用户"
                    }]
                    self.config["mj_users"] = self.mj_users
                    write_file(self.json_path, self.config)
                    reply.content = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
                elif cmd == "s_wuser":
                    user_name = args[0] if args and args[0] else ""
                    if not args or len(args) < 1:
                        return self.send("[MJ] 请输入需要设置的用户名称或ID", e_context, ReplyType.ERROR)
                    # 如果是设置所有用户，则清空白名单
                    if user_name == "ALL_USER" or user_name == "all_user" or user_name == "所有用户":
                        self.mj_users = [{
                            "user_id": "ALL_USER",
                            "user_nickname": "所有用户"
                        }]
                        reply.content = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
                    else:
                        index = -1
                        aind = -1
                        for i, user in enumerate(self.mj_users):
                            if user["user_id"] == user_name or user["user_nickname"] == user_name:
                                index = i
                                break
                            if user["user_id"] == "ALL_USER":
                                aind = i
                                break
                        if index >= 0:
                            return self.send(f"[MJ] 用户[{self.mj_users[index]['user_nickname']}]已在白名单中", e_context, ReplyType.ERROR)
                        if aind >= 0:
                            del self.mj_users[index]
                        userInfo = {
                            "user_id": user_name,
                            "user_nickname": user_name
                        }
                        # 判断是否是itchat平台
                        if conf().get("channel_type", "wx") == "wx":
                            userInfo = self.search_friends(user_name)
                            # 判断user_name是否在列表中
                            if not userInfo or not userInfo["user_id"]:
                                return self.send(f"[MJ] 用户[{user_name}]不存在通讯录中", e_context, ReplyType.ERROR)
                        self.mj_users.append(userInfo)
                        reply.content = f"[MJ] 用户[{userInfo['user_nickname']}]已添加到白名单"
                    self.config["mj_users"] = self.mj_users
                    write_file(self.json_path, self.config)
                elif cmd == "r_wuser":
                    if len(args) < 1:
                        return self.send("[MJ] 请输入需要移除的用户名称或ID或序列号", e_context, ReplyType.ERROR)
                    if args and args[0]:
                        if args[0].isdigit():
                            index = int(args[0]) - 1
                            if index < 0 or index >= len(self.mj_users):
                                return self.send(f"[MJ] 序列号[{args[0]}]不在白名单中", e_context, ReplyType.ERROR)
                            user_name = self.mj_users[index]['user_nickname']
                            user_id = self.mj_users[index]['user_id']
                            if user_id != "ALL_USER":
                                del self.mj_users[index]
                                self.config["mj_users"] = self.mj_users
                                write_file(self.json_path, self.config)
                                reply.content = f"[MJ] 用户[{user_name}]已从白名单中移除"
                            else:
                                reply.content = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
                            return self.send(reply, e_context)
                        else:
                            user_name = args[0]
                            index = -1
                            for i, user in enumerate(self.mj_users):
                                if user["user_nickname"] == user_name or user["user_id"] == user_name:
                                    index = i
                                    break
                            if index >= 0:
                                del self.mj_users[index]
                                if len(self.mj_users) == 0:
                                    self.mj_users = [{
                                        "user_id": "ALL_USER",
                                        "user_nickname": "所有用户"
                                    }]
                                    reply.content = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
                                else:
                                    reply.content = f"[MJ] 用户[{user_name}]已从白名单中移除"
                                self.config["mj_users"] = self.mj_users
                                write_file(self.json_path, self.config)
                                return self.send(reply, e_context)
                            else:
                                return self.send(f"[MJ] 用户[{user_name}]不在白名单中", e_context, ReplyType.ERROR)
                else:
                    if len(args) < 1:
                        return self.send("[MJ] 请输入需要设置的服务器地址", e_context, ReplyType.ERROR)
                    mj_url = args[0] if args[0] else ""
                    mj_api_secret = args[1] if len(args) > 1 else ""
                    self.mj.set_mj(mj_url, mj_api_secret)
                    self.mj_url = mj_url
                    self.mj_api_secret = mj_api_secret
                    self.config["mj_url"] = mj_url
                    self.config["mj_api_secret"] = mj_api_secret
                    write_file(self.json_path, self.config)
                    reply.content = "MJ服务设置成功\nmj_url={}\nmj_api_secret={}".format(mj_url, mj_api_secret)
                return self.send(reply, e_context)

        # 判断是否在运行中
        if not self.ismj:
            return

        # 判断群组是否在白名单中
        if isgroup and (userInfo["group_name"] not in self.mj_groups) and ("ALL_GROUP" not in self.mj_groups):
            return

        # 判断用户是否在白名单中，管理员可不在白名单中
        if not isgroup and (userInfo["user_id"] not in [user["user_id"] for user in self.mj_users]) and ("ALL_USER" not in [user["user_id"] for user in self.mj_users]) and (not self.isadmin):
            return

        # 图片
        if ContextType.IMAGE == context.type:
            # 需要调用准备函数下载图片，否则会出错
            msg.prepare()
            base64 = image_to_base64(content)
            img_cache = None
            if sessionid in self.sessions:
                img_cache = self.sessions[sessionid].get_cache()

            # 识别图片
            if (not isgroup and not img_cache) or (not isgroup and not img_cache["instruct"]) or (img_cache and img_cache["instruct"] == "describe"):
                status = self.env_detection(e_context)
                if not status:
                    return
                reply = self.describe(base64, channel, context)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]

            if img_cache and img_cache["instruct"] == "imagine":
                self.env_detection(e_context)
                prompt = img_cache["prompt"]
                reply = self.imagine(prompt, base64, channel, context)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]

            if img_cache and img_cache["instruct"] == "blend":
                self.env_detection(e_context)
                self.sessions[sessionid].action(base64)
                img_cache = self.sessions[sessionid].get_cache()
                length = len(img_cache["base64Array"])
                if length < 2:
                    reply = Reply(ReplyType.TEXT, f"✏  请再发送一张或多张图片")
                else:
                    reply = Reply(ReplyType.TEXT, f"✏  您已发送{length}张图片，可以发送更多图片或者发送['{self.end_prefix[0]}']开始合成")

            return self.send(reply, e_context)

        if ContextType.TEXT == context.type:
            # 判断是否是指令
            iprefix, iq = check_prefix(content, self.imagine_prefix)
            fprefix, fq = check_prefix(content, self.fetch_prefix)
            uprefix, uq = check_prefix(content, self.up_prefix)
            pprefix, pq = check_prefix(content, self.pad_prefix)
            bprefix, bq = check_prefix(content, self.blend_prefix)
            dprefix, dq = check_prefix(content, self.describe_prefix)
            qprefix, qq = check_prefix(content, self.queue_prefix)
            eprefix, eq = check_prefix(content, self.end_prefix)

            if iprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                reply = self.imagine(iq, "", channel, context)
                logger.info("[MJ] /imagine reply={}".format(reply))
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                return self.send(reply, e_context)
            elif uprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                reply = self.up(uq, channel, context)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                return self.send(reply, e_context)
            elif pprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                if not pq:
                    reply = Reply(ReplyType.TEXT, "✨ 垫图模式\n✏ 请在指令后输入要绘制的描述文字")
                else:
                    self.sessions[sessionid] = _imgCache(sessionid, "imagine", pq)
                    reply = Reply(ReplyType.TEXT, "✨ 垫图模式\n✏ 请再发送一张图片")
                return self.send(reply, e_context)
            elif bprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                self.sessions[sessionid] = _imgCache(sessionid, "blend", bq)
                reply = Reply(ReplyType.TEXT, "✨ 混图模式\n✏ 请发送两张或多张图片，然后输入['{self.end_prefix[0]}']结束")
                return self.send(reply, e_context)
            elif dprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                self.sessions[sessionid] = _imgCache(sessionid, "describe", dq)
                reply = Reply(ReplyType.TEXT, "✨ 识图模式\n✏ 请发送一张图片")
                return self.send(reply, e_context)
            elif content.startswith("/re"):
                status = self.env_detection(e_context)
                if not status:
                    return
                id = content.replace("/re", "").strip()
                reply = self.reroll(id, channel, context)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                return self.send(reply, e_context)
            elif eprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                # 从会话中获取缓存的图片
                img_cache = None
                if sessionid in self.sessions:
                    img_cache = self.sessions[sessionid].get_cache()
                if not img_cache:
                    return self.send("[MJ] 请先输入指令开启绘图模式", e_context, ReplyType.ERROR)
                base64Array = img_cache["base64Array"]
                prompt = img_cache["prompt"]
                length = len(base64Array)
                if length >= 2:
                    reply = self.blend(img_cache["base64Array"], prompt, channel, context)
                    if sessionid in self.sessions:
                        self.sessions[sessionid].reset()
                        del self.sessions[sessionid]
                elif length == 0:
                    reply = Reply(ReplyType.TEXT, "✨ 混图模式\n✏ 请发送两张或多张图片方可完成混图")
                else:
                    reply = Reply(ReplyType.TEXT, "✨ 混图模式\n✏ 请再发送一张图片方可完成混图")
                return self.send(reply, e_context)
            elif fprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                logger.debug("[MJ] /fetch id={}".format(fq))
                status, msg, imageUrl = self.mj.fetch(fq)
                if status:
                    if imageUrl:
                        if self.mj_tip:
                            self.sendMsg(msg, channel, context)
                            image_path = img_to_jpeg(imageUrl)
                            reply = Reply(ReplyType.IMAGE, image_path)
                        else:
                            reply = Reply(ReplyType.TEXT, msg)
                    else:
                        reply = Reply(ReplyType.TEXT, msg)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                return self.send(reply, e_context)
            elif qprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                status, msg = self.mj.task_queue()
                if status:
                    reply = Reply(ReplyType.TEXT, msg)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                return self.send(reply, e_context)

    def send(self, reply, e_context: EventContext, types=ReplyType.TEXT, action=EventAction.BREAK_PASS):
        if isinstance(reply, str):
            reply = Reply(types, reply)
        elif not reply.type and types:
            reply.type = types
        e_context["reply"] = reply
        e_context.action = action
        return

    def sendMsg(self, msg, channel, context, types=ReplyType.TEXT):
        return channel._send_reply(context, channel._decorate_reply(context, Reply(types, msg)))

    def search_friends(self, name):
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

    def authenticate(self, userInfo, args) -> Tuple[bool, str]:
        isgroup = userInfo["isgroup"]
        isadmin = userInfo["isadmin"]
        if isgroup:
            return False, "[MJ] 请勿在群聊中认证"

        if isadmin:
            return False, "[MJ] 管理员账号无需认证"

        if len(args) != 1:
            return False, "[MJ] 请输入密码"

        password = args[0]
        if password == self.mj_admin_password or password == self.temp_password:
            self.mj_admin_users.append({
                "user_id": userInfo["user_id"],
                "user_nickname": userInfo["user_nickname"]
            })
            self.config["mj_admin_users"] = self.mj_admin_users
            write_file(self.json_path, self.config)
            return True, f"[MJ] 认证成功 {'，请尽快设置口令' if password == self.temp_password else ''}"
        else:
            return False, "[MJ] 认证失败"

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

    def imagine(self, prompt, base64, channel, context):
        logger.debug("[MJ] /imagine prompt={} img={}".format(prompt, base64))
        reply = None
        status, msg, id = self.mj.imagine(prompt, base64)
        if status:
            if self.mj_tip:
                self.sendMsg(msg, channel, context)
            reply = self.get_f_img(id, channel, context)
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply

    def up(self, id, channel, context):
        logger.debug("[MJ] /up id={}".format(id))
        reply = None
        status, msg, id = self.mj.simpleChange(id)
        if status:
            if self.mj_tip:
                self.sendMsg(msg, channel, context)
            reply = self.get_f_img(id, channel, context)
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply

    def describe(self, base64, channel, context):
        logger.debug("[MJ] /describe img={}".format(base64))
        reply = None
        status, msg, id = self.mj.describe(base64)
        if status:
            if self.mj_tip:
                self.sendMsg(msg, channel, context)
                reply = self.get_f_img(id, channel, context)
            else:
                reply = self.get_f_img(id, channel, context, "text")
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply

    def blend(self, base64Array, dimensions, channel, context):
        logger.debug("[MJ] /blend imgList={} dimensions={}".format(base64Array, dimensions))
        reply = None
        status, msg, id = self.mj.blend(base64Array, dimensions)
        if status:
            if self.mj_tip:
                self.sendMsg(msg, channel, context)
            reply = self.get_f_img(id, channel, context)
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply

    def reroll(self, id, channel, context):
        logger.debug("[MJ] /reroll id={}".format(id))
        reply = None
        status, msg, id = self.mj.reroll(id)
        if status:
            if self.mj_tip:
                self.sendMsg(msg, channel, context)
            reply = self.get_f_img(id, channel, context)
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply

    def get_f_img(self, id, channel, context, types="image"):
        status2, msg, imageUrl = self.mj.get_f_img(id)
        if status2:
            if imageUrl:
                if self.mj_tip:
                    self.sendMsg(msg, channel, context)
                    image_path = img_to_jpeg(imageUrl)
                    reply = Reply(ReplyType.IMAGE, image_path)
                else:
                    if types == "image":
                        image_path = img_to_jpeg(imageUrl)
                        reply = Reply(ReplyType.IMAGE, image_path)
                    else:
                        reply = Reply(ReplyType.TEXT, msg)
            else:
                reply = Reply(ReplyType.TEXT, msg)
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply
