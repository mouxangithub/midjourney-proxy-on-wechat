# encoding:utf-8
import requests
import os
import io
import json
import base64
import plugins
from bridge.bridge import Bridge
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common import const
from common.log import logger
from common.expired_dict import ExpiredDict
from plugins import *
from PIL import Image
from .mjapi import _mjApi, _imgCache
from channel.chat_message import ChatMessage
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
    if(".webp" in webp_path):
        image_path = io.BytesIO()
        response = requests.get(webp_path)
        image = Image.open(io.BytesIO(response.content))
        image = image.convert("RGB")
        image.save(image_path, format="JPEG")
        return ReplyType.IMAGE, image_path
    else:
        return ReplyType.IMAGE_URL, image_path

@plugins.register(
    name="MidJourney",
    namecn="MJ绘画",
    desc="一款AI绘画工具",
    version="1.0.28",
    author="mouxan",
    desire_priority=0
)
class MidJourney(Plugin):
    def __init__(self):
        super().__init__()

        gconf = {
            "mj_url": "",
            "mj_api_secret": "",
            "imagine_prefix": "[\"/i\", \"/mj\", \"/imagine\", \"/img\"]",
            "fetch_prefix": "[\"/f\", \"/fetch\"]",
            "up_prefix": "[\"/u\", \"/up\"]",
            "pad_prefix": "[\"/p\", \"/pad\"]",
            "blend_prefix": "[\"/b\", \"/blend\"]",
            "describe_prefix": "[\"/d\", \"/describe\"]"
        }

        # 读取和写入配置文件
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        config_template_path = os.path.join(curdir, "config.json.template")
        if os.environ.get("mj_url", None):
            logger.info("使用的是环境变量配置:mj_url={} mj_api_secret={} imagine_prefix={} fetch_prefix={}".format(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix))
            gconf = {
                "mj_url": os.environ.get("mj_url", ""),
                "mj_api_secret": os.environ.get("mj_api_secret", ""),
                "imagine_prefix": os.environ.get("imagine_prefix", "[\"/i\", \"/mj\", \"/imagine\", \"/img\"]"),
                "fetch_prefix": os.environ.get("fetch_prefix", "[\"/f\", \"/fetch\"]"),
                "up_prefix": os.environ.get("up_prefix", "[\"/u\", \"/up\"]"),
                "pad_prefix": os.environ.get("pad_prefix", "[\"/p\", \"/pad\"]"),
                "blend_prefix": os.environ.get("blend_prefix", "[\"/b\", \"/blend\"]"),
                "describe_prefix": os.environ.get("describe_prefix", "[\"/d\", \"/describe\"]")
            }
        elif os.path.exists(config_path):
            logger.info(f"使用的是插件目录下的config.json配置：{config_path}")
            with open(config_path, "r", encoding="utf-8") as f:
                z = json.load(f)
                gconf = {**gconf, **z}
        elif os.path.exists(config_template_path):
            logger.info(f"使用的是插件目录下的config.json.template配置：{config_template_path}")
            with open(config_template_path, "r", encoding="utf-8") as f:
                z = json.load(f)
                gconf = {**gconf, **z}
        else:
            logger.info("使用的是默认配置")

        if gconf["mj_url"] == "":
            logger.info("[MJ] 未设置[mj_url]，请前往环境变量进行配置或在该插件目录下的config.json进行配置。")

        # 重新写入配置文件
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(gconf, f, indent=4)
        
        self.mj_url = gconf["mj_url"]
        self.mj_api_secret = gconf["mj_api_secret"]

        if not gconf["imagine_prefix"]:
            self.imagine_prefix = ["/mj", "/imagine", "/img"]
        else:
            self.imagine_prefix = eval(gconf["imagine_prefix"])
        if not gconf["fetch_prefix"]:
            self.fetch_prefix = ["/ft", "/fetch"]
        else:
            self.fetch_prefix = eval(gconf["fetch_prefix"])
        if not gconf["up_prefix"]:
            self.up_prefix = ["/u", "/up"]
        else:
            self.up_prefix = eval(gconf["up_prefix"])
        if not gconf["pad_prefix"]:
            self.pad_prefix = ["/p", "/pad"]
        else:
            self.pad_prefix = eval(gconf["pad_prefix"])
        if not gconf["blend_prefix"]:
            self.blend_prefix = ["/b", "/blend"]
        else:
            self.blend_prefix = eval(gconf["blend_prefix"])
        if not gconf["describe_prefix"]:
            self.describe_prefix = ["/d", "/describe"]
        else:
            self.describe_prefix = eval(gconf["describe_prefix"])
        
        self.mj = _mjApi(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix, self.up_prefix, self.pad_prefix, self.blend_prefix, self.describe_prefix)

        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        
        # 目前没有设计session过期事件，这里先暂时使用过期字典
        if conf().get("expires_in_seconds"):
            self.sessions = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            self.sessions = dict()

        logger.info("[MJ] inited. mj_url={} mj_api_secret={} imagine_prefix={} fetch_prefix={}".format(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix))

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
        sessionid = context["session_id"]
        bot = Bridge().get_bot("chat")

        # 图片
        if ContextType.IMAGE == context.type:
            self.env_detection(e_context)
            msg.prepare()
            reply = None
            base64_string = image_to_base64(content)
            img_cache = None
            if sessionid in self.sessions:
                img_cache = self.sessions[sessionid].get_cache()
            # 私聊模式并且没有指令
            if not context["isgroup"] and (not img_cache["instruct"] or not img_cache):
                status, msg, id = self.mj.describe(base64_string)
                if status:
                    self.sendMsg(channel, context, ReplyType.TEXT, msg)
                    status2, msgs, imageUrl = self.mj.get_f_img(id)
                    if status2:
                        if imageUrl:
                            self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                            reply_type, image_path = webp_to_png(imageUrl)
                            reply = Reply(reply_type, image_path)
                        else:
                            reply = Reply(ReplyType.TEXT, msgs)
                    else:
                        reply = Reply(ReplyType.ERROR, msgs)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            
            if img_cache and img_cache["instruct"] == "pad":
                status, msg, id = self.mj.imagine(img_cache["prompt"], base64_string)
                if status:
                    self.sendMsg(channel, context, ReplyType.TEXT, msg)
                    status2, msgs, imageUrl = self.mj.get_f_img(id)
                    if status2:
                        if imageUrl:
                            self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                            reply_type, image_path = webp_to_png(imageUrl)
                            reply = Reply(reply_type, image_path)
                        else:
                            reply = Reply(ReplyType.TEXT, msgs)
                    else:
                        reply = Reply(ReplyType.ERROR, msgs)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                self.sessions[sessionid].reset()
                del self.sessions[sessionid]
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            
            if img_cache and img_cache["instruct"] == "blend":
                self.sessions[sessionid].action(base64_string)
                img_cache = self.sessions[sessionid].get_cache()
                length = len(img_cache["base64Array"])
                if length < 2:
                    reply = Reply(ReplyType.TEXT, "请再发送一张或多张图片")
                else:
                    reply = Reply(ReplyType.TEXT, f"您已发送{length}张图片，可以发送更多图片或者发送[/end]开始合成")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

            if img_cache and img_cache["instruct"] == "describe":
                status, msg, id = self.mj.describe(base64_string)
                if status:
                    self.sendMsg(channel, context, ReplyType.TEXT, msg)
                    status2, msgs, imageUrl = self.mj.get_f_img(id)
                    if status2:
                        if imageUrl:
                            self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                            reply_type, image_path = webp_to_png(imageUrl)
                            reply = Reply(reply_type, image_path)
                        else:
                            reply = Reply(ReplyType.TEXT, msgs)
                    else:
                        reply = Reply(ReplyType.ERROR, msgs)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                self.sessions[sessionid].reset()
                del self.sessions[sessionid]
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

            reply = None
            if content == "/mjhp" or content == "/mjhelp" or content == "/mj-help":
                reply = Reply(ReplyType.INFO, self.mj.help_text())
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
                return
            elif iprefix == True:
                self.env_detection(e_context)
                logger.debug("[MJ] /imagine iprefix={} iq={}".format(iprefix,iq))
                status, msg, id = self.mj.imagine(iq)
                if status:
                    self.sendMsg(channel, context, ReplyType.TEXT, msg)
                    status2, msgs, imageUrl = self.mj.get_f_img(id)
                    if status2:
                        if imageUrl:
                            self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                            reply_type, image_path = webp_to_png(imageUrl)
                            reply = Reply(reply_type, image_path)
                        else:
                            reply = Reply(ReplyType.TEXT, msgs)
                    else:
                        reply = Reply(ReplyType.ERROR, msgs)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif uprefix == True:
                self.env_detection(e_context)
                logger.debug("[MJ] /up uprefix={} uq={}".format(iprefix,iq))
                status, msg, id = self.mj.simpleChange(uq)
                if status:
                    self.sendMsg(channel, context, ReplyType.TEXT, msg)
                    status2, msgs, imageUrl = self.mj.get_f_img(id)
                    if status2:
                        if imageUrl:
                            self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                            reply_type, image_path = webp_to_png(imageUrl)
                            reply = Reply(reply_type, image_path)
                        else:
                            reply = Reply(ReplyType.TEXT, msgs)
                    else:
                        reply = Reply(ReplyType.ERROR, msgs)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif fprefix == True:
                self.env_detection(e_context)
                logger.debug("[MJ] /fetch fprefix={} fq={}".format(fprefix,fq))
                status, msg, imageUrl = self.mj.fetch(fq)
                if status:
                    if imageUrl:
                        self.sendMsg(channel, context, ReplyType.TEXT, msg)
                        reply_type, image_path = webp_to_png(imageUrl)
                        reply = Reply(reply_type, image_path)
                    else:
                        reply = Reply(ReplyType.TEXT, msg)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif pprefix == True:
                self.env_detection(e_context)
                logger.debug("[MJ] /pad pprefix={} pq={}".format(pprefix,pq))
                if not pq:
                    reply = Reply(ReplyType.TEXT, "请输入要绘制的文字后发送图片")
                else:
                    self.sessions[sessionid] = _imgCache(bot, sessionid, "pad", pq)
                    reply = Reply(ReplyType.TEXT, "请再发送一张图片")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif bprefix == True:
                self.env_detection(e_context)
                logger.debug("[MJ] /blend bprefix={} bq={}".format(bprefix,bq))
                self.sessions[sessionid] = _imgCache(bot, sessionid, "blend", bq)
                reply = Reply(ReplyType.TEXT, "请发送两张以上的图片，然后输入['/end']结束")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif dprefix == True:
                self.env_detection(e_context)
                logger.debug("[MJ] /describe dprefix={} dq={}".format(dprefix,dq))
                self.sessions[sessionid] = _imgCache(bot, sessionid, "describe", dq)
                reply = Reply(ReplyType.TEXT, "请发送一张图片开启识图模式")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif content == "/end":
                self.env_detection(e_context)
                # 从会话中获取缓存的图片
                img_cache = self.sessions[sessionid].get_cache()
                base64Array = img_cache["base64Array"]
                prompt = img_cache["prompt"]
                length = len(base64Array)
                if length==0:
                    reply = Reply(ReplyType.TEXT, "缓存中无可混合的图片，请重新发送混图指令开启混图模式")
                elif length > 2:
                    reply = Reply(ReplyType.TEXT, "请再发送一张图片方可完成混图")
                else:
                    logger.debug("[MJ] /end")
                    status, msg, id = self.mj.blend(img_cache["base64Array"], prompt)
                    if status:
                        self.sendMsg(channel, context, ReplyType.TEXT, msg)
                        status2, msgs, imageUrl = self.mj.get_f_img(id)
                        if status2:
                            if imageUrl:
                                self.sendMsg(channel, context, ReplyType.TEXT, msgs)
                                reply_type, image_path = webp_to_png(imageUrl)
                                reply = Reply(reply_type, image_path)
                            else:
                                reply = Reply(ReplyType.TEXT, msgs)
                        else:
                            reply = Reply(ReplyType.ERROR, msgs)
                    else:
                        reply = Reply(ReplyType.ERROR, msg)
                self.sessions[sessionid].reset()
                del self.sessions[sessionid]
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif content == "/queue":
                self.env_detection(e_context)
                status, msg = self.mj.task_queue()
                if status:
                    reply = Reply(ReplyType.TEXT, msg)
                else:
                    reply = Reply(ReplyType.ERROR, msg)
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

    def get_help_text(self, isadmin=False, isgroup=False, verbose=False,**kwargs):
        if kwargs.get("verbose") != True:
            return "这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。"
        else:
            return self.mj.help_text()
    
    def env_detection(self, e_context: EventContext):
        if not self.mj_url:
            reply = Reply(ReplyType.ERROR, "未设置[mj_url]，请前往环境变量进行配置或在该插件目录下的config.json进行配置。")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return
    
    def sendMsg(self, channel, context, types, msg):
        return channel._send_reply(context, channel._decorate_reply(context, Reply(types, msg)))