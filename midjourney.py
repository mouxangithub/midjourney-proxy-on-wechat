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

def webp_to_png(webp_path):
    image_path = webp_path
    image_path = io.BytesIO()
    response = requests.get(webp_path)
    image = Image.open(io.BytesIO(response.content))
    image = image.convert("RGB")
    image.save(image_path, format="JPEG")
    return image_path

def read_file(path):
    with open(path, mode="r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4)
    return True

COMMANDS = {
    "mj_help": {
        "alias": ["mj_help", "帮助"],
        "desc": "说明文档",
    },
    "mj_admin_password": {
        "alias": ["mj_admin_password"],
        "args": ["口令"],
        "desc": "MJ管理员认证",
    }
}

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
    "clean_mj": {
        "alias": ["clean_mj", "清空MJ缓存"],
        "desc": "清空MJ缓存",
    },
}

@plugins.register(
    name="MidJourney",
    namecn="MJ绘画",
    desc="一款AI绘画工具",
    version="1.0.33",
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
            "mj_type": "all",
            "mj_groups": [],
            "mj_users": [],
            "mj_admin_users": [],
            "imagine_prefix": "[\"/i\", \"/mj\"]",
            "fetch_prefix": "[\"/f\"]",
            "up_prefix": "[\"/u\"]",
            "pad_prefix": "[\"/p\"]",
            "blend_prefix": "[\"/b\"]",
            "describe_prefix": "[\"/d\"]",
            "queue_prefix": "[\"/q\"]",
            "end_prefix": "[\"/e\"]"
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
                "mj_type": os.environ.get("using_type", "all"),
                "mj_groups": os.environ.get("group", []),
                "mj_users": [],
                "mj_admin_users": [],
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

        # 重新写入配置文件
        write_file(self.json_path, gconf)

        logger.info("[MJ] config={}".format(gconf))
        
        self.mj_url = gconf["mj_url"]
        self.mj_api_secret = gconf["mj_api_secret"]
        self.mj_tip = gconf["mj_tip"]
        self.mj_admin_password = gconf["mj_admin_password"]
        self.mj_type = gconf["mj_type"]
        self.mj_groups = gconf["mj_groups"]
        self.mj_users = gconf["mj_users"]
        self.mj_admin_users = gconf["mj_admin_users"]

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
            "mj_type": self.mj_type,
            "mj_groups": self.mj_groups,
            "mj_users": self.mj_users,
            "mj_admin_users": [],
            "imagine_prefix": self.imagine_prefix,
            "fetch_prefix": self.fetch_prefix,
            "up_prefix": self.up_prefix,
            "pad_prefix": self.pad_prefix,
            "blend_prefix": self.blend_prefix,
            "describe_prefix": self.describe_prefix,
            "queue_prefix": self.queue_prefix,
            "end_prefix": self.end_prefix
        }
        
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
        user = context["receiver"]
        isgroup = context.get("isgroup", False)
        # 判断管理员权限
        self.isadmin = False
        if user in self.mj_admin_users:
            self.isadmin = True
        # 写入用户信息
        userInfo = {
            "user_id": msg.from_user_id,
            "user_nickname": msg.from_user_nickname
        }
        if isgroup:
            userInfo["group_id"] = msg.from_user_id
            userInfo["user_id"] = msg.actual_user_id
            userInfo["group_name"] = msg.from_user_nickname
            userInfo["user_nickname"] = msg.actual_user_nickname
        self.mj.set_user(json.dumps(userInfo))

        reply = None

        if ContextType.TEXT == context.type and content.startswith(trigger_prefix):
            command_parts = content[1:].strip().split()
            cmd = command_parts[0]
            args = command_parts[1:]
            if cmd == "mj_help":
                reply = Reply(ReplyType.INFO, self.get_help_text(verbose=True))
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
                return
            elif cmd == "mj_admin_password":
                ok, result = self.authenticate(user, args, self.isadmin, isgroup)
                reply = Reply()
                if ok:
                    reply.type = ReplyType.INFO
                else:
                    reply.type = ReplyType.ERROR
                reply.content = result
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif cmd == "set_mj_admin_password":
                if self.isadmin == False:
                    reply = Reply(ReplyType.ERROR, f"[MJ] 您没有权限执行该操作,请先输入{trigger_prefix}mj_admin_password+密码进行认证")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                if len(args) < 1:
                    reply = Reply(ReplyType.ERROR, "[MJ] 请输入需要设置的密码")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                self.mj_admin_password = args[0]
                self.config["mj_admin_password"] = args[0]
                write_file(self.json_path, self.config)
                reply = Reply(ReplyType.INFO, "[MJ] 管理员口令设置成功")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif cmd == "set_mj_url" or cmd == "stop_mj" or cmd == "enable_mj" or cmd == "clean_mj":
                if self.isadmin == False:
                    reply = Reply(ReplyType.ERROR, f"[MJ] 您没有权限执行该操作,请先输入{trigger_prefix}mj_admin_password+密码进行认证")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
                if cmd == "stop_mj":
                    self.ismj = False
                    reply = Reply(ReplyType.INFO, "[MJ] 服务已暂停")
                elif cmd == "enable_mj":
                    self.ismj = True
                    reply = Reply(ReplyType.INFO, "[MJ] 服务已恢复")
                elif cmd == "clean_mj":
                    if sessionid in self.sessions:
                        self.sessions[sessionid].reset()
                        del self.sessions[sessionid]
                    reply = Reply(ReplyType.INFO, "[MJ] 缓存已清理")
                else:
                    if len(args) < 1:
                        reply = Reply(ReplyType.ERROR, "[MJ] 请输入需要设置的服务器地址")
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return
                    mj_url = args[0] if args[0] else ""
                    mj_api_secret = args[1] if len(args) > 1 else ""
                    self.mj.set_mj(mj_url, mj_api_secret)
                    self.mj_url = mj_url
                    self.mj_api_secret = mj_api_secret
                    self.config["mj_url"] = mj_url
                    self.config["mj_api_secret"] = mj_api_secret
                    write_file(self.json_path, self.config)
                    reply = Reply(ReplyType.INFO, "MJ服务设置成功\nmj_url={}\nmj_api_secret={}".format(mj_url, mj_api_secret))
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

        if not self.ismj:
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
            
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return


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
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif uprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                reply = self.up(uq, channel, context)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif pprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                if not pq:
                    reply = Reply(ReplyType.TEXT, "✨ 垫图模式\n✏ 请在指令后输入要绘制的描述文字")
                else:
                    self.sessions[sessionid] = _imgCache(sessionid, "imagine", pq)
                    reply = Reply(ReplyType.TEXT, "✨ 垫图模式\n✏ 请再发送一张图片")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif bprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                self.sessions[sessionid] = _imgCache(sessionid, "blend", bq)
                reply = Reply(ReplyType.TEXT, "✨ 混图模式\n✏ 请发送两张或多张图片，然后输入['{self.end_prefix[0]}']结束")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif dprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                self.sessions[sessionid] = _imgCache(sessionid, "describe", dq)
                reply = Reply(ReplyType.TEXT, "✨ 识图模式\n✏ 请发送一张图片")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif content.startswith("/re"):
                status = self.env_detection(e_context)
                if not status:
                    return
                id = content.replace("/re", "").strip()
                reply = self.reroll(id, channel, context)
                if sessionid in self.sessions:
                    self.sessions[sessionid].reset()
                    del self.sessions[sessionid]
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif eprefix == True:
                status = self.env_detection(e_context)
                if not status:
                    return
                # 从会话中获取缓存的图片
                img_cache = None
                if sessionid in self.sessions:
                    img_cache = self.sessions[sessionid].get_cache()
                if not img_cache:
                    reply = Reply(ReplyType.TEXT, "请先输入指令开启绘图模式")
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return
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
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
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
                            image_path = webp_to_png(imageUrl)
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
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
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
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

    def get_help_text(self, **kwargs):
        if kwargs.get("verbose") != True:
            return "这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。"
        else:
            trigger_prefix = conf().get("plugin_trigger_prefix", "$")
            help_text = self.mj.help_text()
            help_text += f"\n-----------------------------\n"
            help_text += "通用指令：\n"
            for cmd, info in COMMANDS.items():
                alias = [trigger_prefix + a for a in info["alias"][:1]]
                help_text += f"{','.join(alias)} "
                if "args" in info:
                    args = [a for a in info["args"]]
                    help_text += f"{' '.join(args)}"
                help_text += f": {info['desc']}\n"
            if ADMIN_COMMANDS and self.isadmin:
                help_text += f"-----------------------------\n"
                help_text += "管理员指令：\n"
                for cmd, info in ADMIN_COMMANDS.items():
                    alias = [trigger_prefix + a for a in info["alias"][:1]]
                    help_text += f"{','.join(alias)} "
                    if "args" in info:
                        args = [a for a in info["args"]]
                        help_text += f"{' '.join(args)}"
                    help_text += f": {info['desc']}\n"
            return help_text

    def authenticate(self, userid, args, isadmin, isgroup) -> Tuple[bool, str]:
        if isgroup:
            return False, "[MJ] 请勿在群聊中认证"

        if isadmin:
            return False, "[MJ] 管理员账号无需认证"

        if len(args) != 1:
            return False, "[MJ] 请输入密码"

        password = args[0]
        if password == self.mj_admin_password:
            self.mj_admin_users.append(userid)
            return True, "[MJ] 认证成功"
        elif password == self.temp_password:
            self.mj_admin_users.append(userid)
            return True, "[MJ] 认证成功，请尽快设置口令"
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
                    image_path = webp_to_png(imageUrl)
                    reply = Reply(ReplyType.IMAGE, image_path)
                else:
                    if types == "image":
                        image_path = webp_to_png(imageUrl)
                        reply = Reply(ReplyType.IMAGE, image_path)
                    else:
                        reply = Reply(ReplyType.TEXT, msg)
            else:
                reply = Reply(ReplyType.TEXT, msg)
        else:
            reply = Reply(ReplyType.ERROR, msg)
        return reply
    
    def sendMsg(self, msg, channel, context, types=ReplyType.TEXT):
        return channel._send_reply(context, channel._decorate_reply(context, Reply(types, msg)))
