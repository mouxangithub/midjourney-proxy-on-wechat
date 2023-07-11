# encoding:utf-8
import os
import json
import plugins
from bridge.context import ContextType
from bridge.reply import ReplyType
from common.log import logger
from common.expired_dict import ExpiredDict
from plugins import *
from channel.chat_message import ChatMessage
from typing import Tuple
from config import conf
from lib import itchat
from lib.itchat.content import *

from .mjapi import _mjApi
from .mjcache import _imgCache
from .ctext import *


@plugins.register(
    name="MidJourney",
    namecn="MJ绘画",
    desc="一款AI绘画工具",
    version="1.0.38",
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

        self.trigger_prefix = conf().get("plugin_trigger_prefix", "$")

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

        logger.info("[MJ] inited")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.IMAGE,
        ]:
            return

        channel = e_context['channel']
        context = e_context['context']
        content = context.content
        msg: ChatMessage = context["msg"]
        self.channel = channel
        self.context = context
        self.sessionid = context["session_id"]
        self.isgroup = context.get("isgroup", False)
        self.isadmin = False
        # 写入用户信息
        self.userInfo = {
            "user_id": msg.from_user_id,
            "user_nickname": msg.from_user_nickname,
            "isadmin": False,
            "isgroup": self.isgroup,
        }
        if self.isgroup:
            self.userInfo["group_id"] = msg.from_user_id
            self.userInfo["user_id"] = msg.actual_user_id
            self.userInfo["group_name"] = msg.from_user_nickname
            self.userInfo["user_nickname"] = msg.actual_user_nickname
        # 判断是否是管理员
        if not self.isgroup and (self.userInfo["user_id"] in [user["user_id"] for user in self.mj_admin_users]):
            self.isadmin = True
            self.userInfo['isadmin'] = True

        self.mj.set_user(json.dumps(self.userInfo))

        if ContextType.TEXT == context.type and content.startswith(self.trigger_prefix):
            return self.handle_command(e_context)

        # 判断是否在运行中
        if not self.ismj:
            return

        # 判断群组是否在白名单中
        if self.isgroup and (self.userInfo["group_name"] not in self.mj_groups) and ("ALL_GROUP" not in self.mj_groups):
            return

        # 判断用户是否在白名单中，管理员可不在白名单中
        if not self.isgroup and (self.userInfo["user_id"] not in [user["user_id"] for user in self.mj_users]) and ("ALL_USER" not in [user["user_id"] for user in self.mj_users]) and (not self.isadmin):
            return

        # 图片
        if ContextType.IMAGE == context.type:
            # 需要调用准备函数下载图片，否则会出错
            msg.prepare()
            return self.handle_image(e_context)
        # 文字
        elif ContextType.TEXT == context.type:
            # 判断是否是指令
            return self.handle_text(e_context)

    def get_help_text(self, **kwargs):
        return get_help_text(self, **kwargs)

    def handle_text(self, e_context: EventContext):
        context = e_context['context']
        content = context.content
        if not context or not content:
            return
        # 判断指令渠道
        pn, prompt  = check_prefix_list(content, self.config)
        if pn:
            # 环境检测
            env = env_detection(self, e_context)
            if not env:
                return
        if pn == "imagine_prefix":
            if not prompt:
                return Info("[MJ] 请输入要绘制的描述文字", e_context)
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return self.imagine(prompt, "", e_context)
        elif pn == "up_prefix":
            if not prompt:
                return Info("[MJ] 请输入任务ID", e_context)
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return self.up(prompt, e_context)
        elif pn == "pad_prefix":
            if not prompt:
                return Info("[MJ] 请输入要绘制的描述文字", e_context)
            self.sessions[self.sessionid] = _imgCache(self.sessionid, "imagine", prompt)
            return Text(f"✨ 垫图模式\n✏ 请再发送一张图片", e_context)
        elif pn == "blend_prefix":
            self.sessions[self.sessionid] = _imgCache(self.sessionid, "blend", prompt)
            return Text(f"✨ 混图模式\n✏ 请发送两张或多张图片，然后输入['{self.end_prefix[0]}']结束", e_context)
        elif pn == "describe_prefix":
            self.sessions[self.sessionid] = _imgCache(self.sessionid, "describe", prompt)
            return Text(f"✨ 识图模式\n✏ 请发送一张图片", e_context)
        elif pn == "end_prefix":
            # 从会话中获取缓存的图片
            img_cache = None
            if self.sessionid in self.sessions:
                img_cache = self.sessions[self.sessionid].get_cache()
            if not img_cache:
                return Error("[MJ] 请先输入指令开启绘图模式", e_context)
            base64Array = img_cache["base64Array"]
            prompt = img_cache["prompt"]
            length = len(base64Array)
            if length >= 2:
                if self.sessionid in self.sessions:
                    self.sessions[self.sessionid].reset()
                    del self.sessions[self.sessionid]
                return self.blend(base64Array, prompt, e_context)
            elif length == 0:
                return Text(f"✨ 混图模式\n✏ 请发送两张或多张图片方可完成混图", e_context)
            else:
                return Text(f"✨ 混图模式\n✏ 请再发送一张图片方可完成混图", e_context)
        elif pn == "fetch_prefix":
            logger.debug("[MJ] /fetch id={}".format(prompt))
            status, msg, imageUrl = self.mj.fetch(prompt)
            rt = ReplyType.TEXT
            rc = msg
            if not status:
                rt = ReplyType.ERROR
            if status and imageUrl:
                if self.mj_tip:
                    send_reply(self, msg)
                    rt = ReplyType.IMAGE
                    rc = img_to_jpeg(imageUrl)
                    if not rc:
                        rt = ReplyType.ERROR
                        rc = "图片下载发送失败"
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return send(rc, e_context, rt)
        elif pn == "queue_prefix":
            status, msg = self.mj.task_queue()
            rc = msg
            rt = ReplyType.TEXT if status else ReplyType.ERROR
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return send(rc, e_context, rt)
        elif content.startswith("/re"):
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return self.reroll(content.replace("/re", "").strip(), e_context)

    # 识图
    def handle_image(self, e_context: EventContext):
        # 获取图片base64
        context = e_context['context']
        if not context or not context.content:
            return
        base64 = image_to_base64(context.content)

        # 从会话中获取缓存的图片
        img_cache = None
        if self.sessionid in self.sessions:
            img_cache = self.sessions[self.sessionid].get_cache()

        # 识图模式
        if (not self.isgroup and not img_cache) or (not self.isgroup and not img_cache["instruct"]) or (img_cache and img_cache["instruct"] == "describe"):
            # 环境检测
            env = env_detection(self, e_context)
            if not env:
                return
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return self.describe(base64, e_context)

        # 垫图模式
        if img_cache and img_cache["instruct"] == "imagine":
            # 环境检测
            env = env_detection(self, e_context)
            if not env:
                return
            prompt = img_cache["prompt"]
            if self.sessionid in self.sessions:
                self.sessions[self.sessionid].reset()
                del self.sessions[self.sessionid]
            return self.imagine(prompt, base64, e_context)

        # 混图模式
        if img_cache and img_cache["instruct"] == "blend":
            # 环境检测
            env = env_detection(self, e_context)
            if not env:
                return
            if self.sessionid not in self.sessions:
                return Info("[MJ] 请先输入指令开启绘图模式", e_context)
            self.sessions[self.sessionid].action(base64)
            img_cache = self.sessions[self.sessionid].get_cache()
            length = len(img_cache["base64Array"])
            if length < 2:
                return Text(f"✏  请再发送一张或多张图片", e_context)
            else:
                return Text(f"✏  您已发送{length}张图片，可以发送更多图片或者发送['{self.end_prefix[0]}']开始合成", e_context)

    # 指令处理
    def handle_command(self, e_context: EventContext):
        content = e_context['context'].content
        com = content[1:].strip().split()
        cmd = com[0]
        args = com[1:]

        if cmd == "mj_help":
            return Info(get_help_text(self, verbose=True), e_context)
        elif cmd == "mj_admin_password":
            ok, result = self.authenticate(self.userInfo, args)
            if not ok:
                return Error(result, e_context)
            else:
                return Info(result, e_context)
        elif cmd == "set_mj_admin_password":
            if self.isadmin == False:
                return Error("[MJ] 您没有权限执行该操作,进行管理员认证", e_context)
            if len(args) < 1:
                return Error("[MJ] 请输入需要设置的密码", e_context)
            password = args[0]
            if len(password) < 6:
                return Error("[MJ] 密码长度不能小于6位", e_context)
            if password == self.temp_password:
                return Error("[MJ] 不能使用临时密码，请重新设置", e_context)
            if password == self.mj_admin_password:
                return Error("[MJ] 新密码不能与旧密码相同", e_context)
            self.mj_admin_password = password
            self.config["mj_admin_password"] = password
            write_file(self.json_path, self.config)
            return Info("[MJ] 管理员口令设置成功", e_context)
        elif cmd == "set_mj_url" or cmd == "stop_mj" or cmd == "enable_mj" or cmd == "clean_mj" or cmd == "mj_tip" or cmd == "s_wgroup" or cmd == "r_wgroup" or cmd == "g_wgroup" or cmd == "c_wgroup" or cmd == "s_wuser" or cmd == "r_wuser" or cmd == "g_wuser" or cmd == "c_wuser":
            if self.isadmin == False:
                return Error("[MJ] 您没有权限执行该操作,进行管理员认证", e_context)
            if cmd == "mj_tip":
                self.mj_tip = not self.mj_tip
                self.config["mj_tip"] = self.mj_tip
                write_file(self.json_path, self.config)
                return Info(f"[MJ] 提示功能已{'开启' if self.mj_tip else '关闭'}", e_context)
            elif cmd == "stop_mj":
                self.ismj = False
                return Info("[MJ] 服务已暂停", e_context)
            elif cmd == "enable_mj":
                self.ismj = True
                return Info("[MJ] 服务已启用", e_context)
            elif cmd == "clean_mj":
                if self.sessionid in self.sessions:
                    self.sessions[self.sessionid].reset()
                    del self.sessions[self.sessionid]
                return Info("[MJ] 会话已清理", e_context)
            elif cmd == "g_wgroup" and not self.isgroup:
                text = ""
                if "ALL_GROUP" in self.mj_groups:
                    text = "[MJ] 白名单群组：所有群组"
                elif len(self.mj_groups) == 0:
                    text = "[MJ] 白名单群组：无"
                else:
                    t = "\n"
                    nameList = t.join(f'{index+1}. {group}' for index, group in enumerate(self.mj_groups))
                    text = f"[MJ] 白名单群组\n{nameList}"
                return Info(text, e_context)
            elif cmd == "c_wgroup":
                self.mj_groups = ["ALL_GROUP"]
                self.config["mj_groups"] = self.mj_groups
                write_file(self.json_path, self.config)
                return Info("[MJ] 白名单已清空，目前所有群组都可以使用MJ服务", e_context)
            elif cmd == "s_wgroup":
                text = ""
                if not self.isgroup and len(args) < 1:
                    return Error("[MJ] 请输入需要设置的群组名称", e_context)
                if self.isgroup:
                    group_name = self.userInfo["group_name"]
                if args and args[0]:
                    group_name = args[0]
                # 如果是设置所有群组，则清空其他群组
                if group_name == "ALL_GROUP" or group_name == "all_group" or group_name == "所有群组":
                    self.mj_groups = ["ALL_GROUP"]
                    text = "[MJ] 白名单已清空，目前所有群组都可以使用MJ服务"
                else:
                    if group_name in self.mj_groups:
                        return Error(f"[MJ] 群组[{group_name}]已在白名单中", e_context)
                    if "ALL_GROUP" in self.mj_groups:
                        self.mj_groups.remove("ALL_GROUP")
                    # 判断是否是itchat平台，并判断group_name是否在列表中
                    if conf().get("channel_type", "wx") == "wx":
                        chatrooms = itchat.search_chatrooms(name=group_name)
                        if len(chatrooms) == 0:
                            return Error(f"[MJ] 群组[{group_name}]不存在", e_context)
                    self.mj_groups.append(group_name)
                    text = f"[MJ] 群组[{group_name}]已添加到白名单"
                self.config["mj_groups"] = self.mj_groups
                write_file(self.json_path, self.config)
                return Info(text, e_context)
            elif cmd == "r_wgroup":
                if not self.isgroup and len(args) < 1:
                    return Error("[MJ] 请输入需要移除的群组名称或序列号", e_context)
                if self.isgroup:
                    group_name = self.userInfo["group_name"]
                if args and args[0]:
                    if args[0].isdigit():
                        index = int(args[0]) - 1
                        if index < 0 or index >= len(self.mj_groups):
                            return Error(f"[MJ] 序列号[{args[0]}]不在白名单中", e_context)
                        group_name = self.mj_groups[index]
                    else:
                        group_name = args[0]
                if group_name in self.mj_groups:
                    self.mj_groups.remove(group_name)
                    if len(self.mj_groups) == 0:
                        self.mj_groups.append("ALL_GROUP")
                    self.config["mj_groups"] = self.mj_groups
                    write_file(self.json_path, self.config)
                    return Info(f"[MJ] 群组[{group_name}]已从白名单中移除", e_context)
                else:
                    return Error(f"[MJ] 群组[{group_name}]不在白名单中", e_context)
            elif cmd == "g_wuser" and not self.isgroup:
                if any(user["user_id"] == "ALL_USER" for user in self.mj_users):
                    return Info("[MJ] 白名单用户：所有用户", e_context)
                elif len(self.mj_users) == 0:
                    return Info("[MJ] 白名单用户：无", e_context)
                else:
                    t = "\n"
                    nameList = t.join(f'{index+1}. {data["user_nickname"]}' for index, data in enumerate(self.mj_users))
                    return Info(f"[MJ] 白名单用户\n{nameList}", e_context)
            elif cmd == "c_wuser":
                self.mj_users = [{
                    "user_id": "ALL_USER",
                    "user_nickname": "所有用户"
                }]
                self.config["mj_users"] = self.mj_users
                write_file(self.json_path, self.config)
                return Info("[MJ] 白名单已清空，目前所有用户都可以使用MJ服务", e_context)
            elif cmd == "s_wuser":
                text = ""
                user_name = args[0] if args and args[0] else ""
                if not args or len(args) < 1:
                    return Error("[MJ] 请输入需要设置的用户名称或ID", e_context)
                # 如果是设置所有用户，则清空白名单
                if user_name == "ALL_USER" or user_name == "all_user" or user_name == "所有用户":
                    self.mj_users = [{
                        "user_id": "ALL_USER",
                        "user_nickname": "所有用户"
                    }]
                    text = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
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
                        return Error(f"[MJ] 用户[{self.mj_users[index]['user_nickname']}]已在白名单中", e_context)
                    if aind >= 0:
                        del self.mj_users[index]
                    userInfo = {
                        "user_id": user_name,
                        "user_nickname": user_name
                    }
                    # 判断是否是itchat平台
                    if conf().get("channel_type", "wx") == "wx":
                        userInfo = search_friends(user_name)
                        # 判断user_name是否在列表中
                        if not userInfo or not userInfo["user_id"]:
                            return Error(f"[MJ] 用户[{user_name}]不存在通讯录中", e_context)
                    self.mj_users.append(userInfo)
                    text = f"[MJ] 用户[{userInfo['user_nickname']}]已添加到白名单"
                self.config["mj_users"] = self.mj_users
                write_file(self.json_path, self.config)
                return Info(text, e_context)
            elif cmd == "r_wuser":
                text = ""
                if len(args) < 1:
                    return Error("[MJ] 请输入需要移除的用户名称或ID或序列号", e_context)
                if args and args[0]:
                    if args[0].isdigit():
                        index = int(args[0]) - 1
                        if index < 0 or index >= len(self.mj_users):
                            return Error(f"[MJ] 序列号[{args[0]}]不在白名单中", e_context)
                        user_name = self.mj_users[index]['user_nickname']
                        user_id = self.mj_users[index]['user_id']
                        if user_id != "ALL_USER":
                            del self.mj_users[index]
                            self.config["mj_users"] = self.mj_users
                            write_file(self.json_path, self.config)
                            text = f"[MJ] 用户[{user_name}]已从白名单中移除"
                        else:
                            text = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
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
                                text = "[MJ] 白名单已清空，目前所有用户都可以使用MJ服务"
                            else:
                                text = f"[MJ] 用户[{user_name}]已从白名单中移除"
                            self.config["mj_users"] = self.mj_users
                            write_file(self.json_path, self.config)
                        else:
                            return Error(f"[MJ] 用户[{user_name}]不在白名单中", e_context)
                return Info(text, e_context)
            else:
                if len(args) < 1:
                    return Error("[MJ] 请输入需要设置的服务器地址", e_context)
                mj_url = args[0] if args[0] else ""
                mj_api_secret = args[1] if len(args) > 1 else ""
                self.mj_url = mj_url
                self.mj_api_secret = mj_api_secret
                self.config["mj_url"] = mj_url
                self.config["mj_api_secret"] = mj_api_secret
                self.mj.set_mj(mj_url, mj_api_secret)
                write_file(self.json_path, self.config)
                return Info("MJ服务设置成功\nmj_url={}\nmj_api_secret={}".format(mj_url, mj_api_secret), e_context)

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

    def imagine(self, prompt, base64, e_context: EventContext):
        logger.info("[MJ] /imagine prompt={} img={}".format(prompt, base64))
        status, msg, id = self.mj.imagine(prompt, base64)
        return self._reply(status, msg, id, e_context)

    def up(self, id, e_context: EventContext):
        logger.debug("[MJ] /up id={}".format(id))
        status, msg, id = self.mj.simpleChange(id)
        return self._reply(status, msg, id, e_context)

    def describe(self, base64, e_context: EventContext):
        logger.debug("[MJ] /describe img={}".format(base64))
        status, msg, id = self.mj.describe(base64)
        return self._reply(status, msg, id, e_context, "text" if not self.mj_tip else "image")

    def blend(self, base64Array, dimensions, e_context: EventContext):
        logger.debug("[MJ] /blend imgList={} dimensions={}".format(base64Array, dimensions))
        status, msg, id = self.mj.blend(base64Array, dimensions)
        return self._reply(status, msg, id, e_context)

    def reroll(self, id, e_context: EventContext):
        logger.debug("[MJ] /reroll id={}".format(id))
        status, msg, id = self.mj.reroll(id)
        return self._reply(status, msg, id, e_context)

    def _reply(self, status, msg, id, e_context: EventContext, rtype="image"):
        if status:
            if self.mj_tip:
                send_reply(self, msg)
            rc, rt = get_f_img(self, id, rtype)
            return send(rc, e_context, rt)
        else:
            return Error(msg, e_context)
