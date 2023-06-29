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
from plugins import *
from PIL import Image
from .mjapi import _mjApi
from channel.chat_message import ChatMessage

def check_prefix(content, prefix_list):
    if not prefix_list:
        return False, None
    for prefix in prefix_list:
        if content.startswith(prefix):
            return True, content.replace(prefix, "").strip()
    return False, None

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        return encoded_string.decode("utf-8")

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
    version="1.0.25",
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
        logger.info("[MJ] inited. mj_url={} mj_api_secret={} imagine_prefix={} fetch_prefix={}".format(self.mj_url, self.mj_api_secret, self.imagine_prefix, self.fetch_prefix))

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
            ContextType.IMAGE,
        ]:
            return

        channel = e_context['channel']
        context = e_context['context']
        cmsg = context["msg"]
        content = context.content

        # 图片非群聊
        if ContextType.IMAGE == context.type and not context["isgroup"]:
            self.env_detection(e_context)
            cmsg.prepare()
            logger.debug(f"[MJ] 收到图片消息，开始处理 {content} {os.path.exists(content)}")
            reply = None
            base64_string = image_to_base64(content)
            status, msg, imageUrl = self.mj.describe(base64_string)
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
                self.env_detection(e_context)
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