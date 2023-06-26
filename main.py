# encoding:utf-8
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
from .api import mj

@plugins.register(
    name="midjourney",
    desc="一款AI绘画工具",
    version="0.1",
    author="mouxan"
)
class MidJourney(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info("[MJ] inited")

    def on_handle_context(self, e_context: EventContext):
        if e_context["context"].type not in [
            ContextType.TEXT,
        ]:
            return
        
        channel = e_context['channel']
        context = e_context['context']
        content = context.content

        if content.startswith("/mjhp") or content.startswith("/mjhelp") or content.startswith("/mj-help") or content.startswith("/mj_help") or content.startswith("/midjourneyhelp") or content.startswith("/midjourney-help") or content.startswith("/midjourney_help"):
            reply = Reply(ReplyType.TEXT, mj.help_text())
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
        
        if content.startswith("/mj") or content.startswith("/imagine") or content.startswith("/up"):
            query = content[3:].strip()
            logger.info("[MJ] query={}".format(query))
            reply = None
            if content.startswith("/mj") or content.startswith("/imagine"):
                status, msg, id = mj.imagine(query)
            else:
                status, msg, id = mj.simpleChange(query)
            if status:
                channel._send(Reply(ReplyType.INFO, msg), context)
                status2, msgs, imageUrl = mj.get_f_img(id)
                if status2:
                    channel._send(Reply(ReplyType.TEXT, msgs), context)
                    reply = Reply(ReplyType.IMAGE_URL, imageUrl)
                else:
                    reply = Reply(ReplyType.ERROR, msgs)
            else:
                reply = Reply(ReplyType.ERROR, msg)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑

        if content.startswith("/fetch"):
            query = content[6:].strip()
            logger.info("[MJ] query={}".format(query))
            status, msg = mj.fetch(query)
            if status:
                reply = Reply(ReplyType.TEXT, msg)
            else:
                reply = Reply(ReplyType.ERROR, msg)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK  # 事件结束，进入默认处理逻辑，一般会覆写reply


    def get_help_text(self, **kwargs):
        return mj.help_text()