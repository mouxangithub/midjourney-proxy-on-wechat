# encoding:utf-8

import io
import json
import os

import webuiapi
import langid
from bridge.bridge import Bridge
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf
from plugins import *


@plugins.register(name="midjourney", desire_priority=-1, desc="A simple plugin to summary messages", version="0.3", author="mouxan")
class midjourney(Plugin):
    def __init__(self):
        super().__init__()
        curdir = os.path.dirname(__file__)
        config_path = os.path.join(curdir, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.rules = config["rules"]
                defaults = config["defaults"]
                self.default_params = defaults["params"]
                self.default_options = defaults["options"]
                self.start_args = config["start"]
                self.api = webuiapi.WebUIApi(**self.start_args)
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            logger.info("[SD] inited")
        except Exception as e:
            if isinstance(e, FileNotFoundError):
                logger.warn(f"[SD] init failed, {config_path} not found, ignore or see https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins/sdwebui .")
            else:
                logger.warn("[SD] init failed, ignore or see https://github.com/zhayujie/chatgpt-on-wechat/tree/master/plugins/sdwebui .")
            raise e
    
    def on_handle_context(self, e_context: EventContext):

        if e_context['context'].type != ContextType.IMAGE_CREATE:
            return
        channel = e_context['channel']
        if ReplyType.IMAGE in channel.NOT_SUPPORT_REPLYTYPE:
            return

        logger.debug("[SD] on_handle_context. content: %s" %e_context['context'].content)

        logger.info("[SD] image_query={}".format(e_context['context'].content))
        reply = Reply()
        try:
            content = e_context['context'].content[:]
            # 解析用户输入 如"横版 高清 二次元:cat"
            if ":" in content:
                keywords, prompt = content.split(":", 1)
            else:
                keywords = content
                prompt = ""

            keywords = keywords.split()
            unused_keywords = []
            if "help" in keywords or "帮助" in keywords:
                reply.type = ReplyType.INFO
                reply.content = self.get_help_text(verbose = True)
            else:
                rule_params = {}
                rule_options = {}
                for keyword in keywords:
                    matched = False
                    for rule in self.rules:
                        if keyword in rule["keywords"]:
                            for key in rule["params"]:
                                rule_params[key] = rule["params"][key]
                            if "options" in rule:
                                for key in rule["options"]:
                                    rule_options[key] = rule["options"][key]
                            matched = True
                            break  # 一个关键词只匹配一个规则
                    if not matched:
                        unused_keywords.append(keyword)
                        logger.info("[SD] keyword not matched: %s" % keyword)
                
                params = {**self.default_params, **rule_params}
                options = {**self.default_options, **rule_options}
                params["prompt"] = params.get("prompt", "")
                if unused_keywords:
                    if prompt:
                        prompt += f", {', '.join(unused_keywords)}"
                    else:
                        prompt = ', '.join(unused_keywords)
                if prompt:
                    lang = langid.classify(prompt)[0]
                    if lang != "en":
                        logger.info("[SD] translate prompt from {} to en".format(lang))
                        try:
                            prompt = Bridge().fetch_translate(prompt, to_lang= "en")
                        except Exception as e:
                            logger.info("[SD] translate failed: {}".format(e))
                        logger.info("[SD] translated prompt={}".format(prompt))
                    params["prompt"] += f", {prompt}"
                if len(options) > 0:
                    logger.info("[SD] cover options={}".format(options))
                    self.api.set_options(options)
                logger.info("[SD] params={}".format(params))
                result = self.api.txt2img(
                    **params
                )
                reply.type = ReplyType.IMAGE
                b_img = io.BytesIO()
                result.image.save(b_img, format="PNG")
                reply.content = b_img
            e_context.action = EventAction.BREAK_PASS  # 事件结束后，跳过处理context的默认逻辑
        except Exception as e:
            reply.type = ReplyType.ERROR
            reply.content = "[SD] "+str(e)
            logger.error("[SD] exception: %s" % e)
            e_context.action = EventAction.CONTINUE  # 事件继续，交付给下个插件或默认逻辑
        finally:
            e_context['reply'] = reply

    def get_help_text(self, **kwargs):
        help_text = "欢迎使用MJ机器人\n"
        help_text += f"这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。\n"
        help_text += f"------------------------------\n"
        help_text += f"🎨 AI绘图-使用说明：\n"
        help_text += f"输入: /imagine prompt\n"
        help_text += f"prompt 即你提的绘画需求\n"
        help_text += f"------------------------------\n"
        help_text += f"📕 prompt附加参数 \n"
        help_text += f"1.解释: 在prompt后携带的参数, 可以使你的绘画更别具一格\n"
        help_text += f"2.示例: /imagine prompt --ar 16:9\n"
        help_text += f"3.使用: 需要使用--key value, key和value空格隔开, 多个附加参数空格隔开\n"
        help_text += f"------------------------------\n"
        help_text += f"📗 附加参数列表\n"
        help_text += f"1. --v 版本 1,2,3,4,5 默认5, 不可与niji同用\n"
        help_text += f"2. --niji 卡通版本 空或5 默认空, 不可与v同用\n"
        help_text += f"3. --ar 横纵比 n:n 默认1:1\n"
        help_text += f"4. --q 清晰度 .25 .5 1 2 分别代表: 一般,清晰,高清,超高清,默认1\n"
        help_text += f"5. --style 风格 (4a,4b,4c)v4可用 (expressive,cute)niji5可用\n"
        help_text += f"6. --s 风格化 1-1000 (625-60000)v3"
        return help_text
