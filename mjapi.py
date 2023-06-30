import time
import requests
from common.log import logger

class _mjApi:
    def __init__(self, mj_url, mj_api_secret, imagine_prefix, fetch_prefix, up_prefix, pad_prefix, blend_prefix, describe_prefix):
        self.baseUrl = mj_url
        self.headers = {
            "Content-Type": "application/json",
        }
        if mj_api_secret:
            self.headers["mj-api-secret"] = mj_api_secret
        if imagine_prefix:
            self.imagine_prefix = imagine_prefix
        if fetch_prefix:
            self.fetch_prefix = fetch_prefix
        if up_prefix:
            self.up_prefix = up_prefix
        if pad_prefix:
            self.pad_prefix = pad_prefix
        if blend_prefix:
            self.blend_prefix = blend_prefix
        if describe_prefix:
            self.describe_prefix = describe_prefix
    
    # 图片想象接口
    def imagine(self, text):
        try:
            url = self.baseUrl + "/mj/submit/imagine"
            data = {"prompt": text}
            res = requests.post(url, json=data, headers=self.headers)
            rj = res.json()
            if not rj:
                return False, "MJ服务异常", None
            code = rj["code"]
            if code == 1:
                msg = "✅ 您的任务已提交\n"
                msg += f"🚀 正在快速处理中，请稍后\n"
                msg += f"📨 ID: {rj['result']}\n"
                msg += f"✏  使用[{self.fetch_prefix[0]} + 任务ID操作]\n"
                msg += f"{self.fetch_prefix[0]} {rj['result']}"
                return True, msg, rj["result"]
            else:
                return False, rj["failReason"], None
        except Exception as e:
            logger.exception(e)
            return False, "任务提交失败", None
    
    # 放大/变换图片接口
    def simpleChange(self, content):
        try:
            url = self.baseUrl + "/mj/submit/simple-change"
            data = {"content": content}
            res = requests.post(url, json=data, headers=self.headers)
            rj = res.json()
            if not rj:
                return False, "MJ服务异常", None
            code = rj["code"]
            if code == 1:
                msg = "✅ 您的任务已提交\n"
                msg += f"🚀 正在快速处理中，请稍后\n"
                msg += f"📨 ID: {rj['result']}\n"
                msg += f"✏  使用[{self.fetch_prefix[0]} + 任务ID操作]\n"
                msg += f"{self.fetch_prefix[0]} {rj['result']}"
                return True, msg, rj["result"]
            else:
                return False, f"任务提交失败：{rj['failReason']}", None
        except Exception as e:
            logger.exception(e)
            return False, "任务提交失败", None
    
    # 识图接口
    def describe(self, base64):
        try:
            url = self.baseUrl + "/mj/submit/describe"
            data = {"base64": base64}
            res = requests.post(url, json=data, headers=self.headers)
            rj = res.json()
            if not rj:
                return False, "MJ服务异常", None
            code = rj["code"]
            if code == 1:
                msg = "✅ 您的任务已提交\n"
                msg += f"🚀 正在快速处理中，请稍后\n"
                msg += f"📨 ID: {rj['result']}\n"
                msg += f"✏  使用[{self.fetch_prefix[0]} + 任务ID操作]\n"
                msg += f"{self.fetch_prefix[0]} {rj['result']}"
                return True, msg, rj["result"]
            else:
                return False, f"任务提交失败：{rj['failReason']}", None
        except Exception as e:
            logger.exception(e)
            return False, "任务提交失败", None
    
    # 查询提交的任务信息
    def fetch(self, id):
        try:
            url = self.baseUrl + f"/mj/task/{id}/fetch"
            res = requests.get(url, headers=self.headers)
            rj = res.json()
            if not rj:
                return False, "查询任务不存在", None
            status = rj['status']
            startTime = ""
            finishTime = ""
            if rj['startTime']:
                startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj['startTime']/1000))
            if rj['finishTime']:
                finishTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj['finishTime']/1000))
            msg = "✅ 查询成功\n"
            msg += f"ID: {rj['id']}\n"
            msg += f"进度：{rj['progress']}\n"
            msg += f"内容：{rj['prompt']}\n"
            msg += f"内容(英文)：{rj['promptEn']}\n"
            msg += f"状态：{self.status(status)}\n"
            if rj['failReason']:
                msg += f"失败原因：{rj['failReason']}\n"
            if startTime:
                msg += f"开始时间：{startTime}\n"
            if finishTime:
                msg += f"完成时间：{finishTime}\n"
            if rj['imageUrl']:
                msg += f"✨ 图片地址: {rj['imageUrl']}\n"
                return True, msg, rj['imageUrl']
            return True, msg, None
        except Exception as e:
            logger.exception(e)
            return False, "查询失败", None
    
    # 轮询获取任务结果
    def get_f_img(self, id):
        try:
            url = self.baseUrl + f"/mj/task/{id}/fetch"
            status = ""
            rj = ""
            logger.debug("开始轮询任务结果")
            while status != "SUCCESS" and status != "FAILURE":
                time.sleep(3)
                res = requests.get(url, headers=self.headers)
                rj = res.json()
                status = rj["status"]
            if not rj:
                return False, "任务提交异常", None
            logger.debug(f"结果: {rj}")
            if status == "SUCCESS":
                msg = ""
                startTime = ""
                finishTime = ""
                action = rj["action"]
                if res.json()['startTime']:
                    startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.json()['startTime']/1000))
                if res.json()['finishTime']:
                    finishTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(res.json()['finishTime']/1000))
                if action == "IMAGINE":
                    msg = f"🎨 绘图成功\n"
                    msg += f"📨 ID: {id}\n"
                    msg += f"✨ 内容: {rj['prompt']}\n"
                    msg += f"✨ 内容(英文): {rj['promptEn']}\n"
                    msg += f"🪄 放大 U1～U4，变换 V1～V4\n"
                    msg += f"✏ 使用[{self.up_prefix[0]} 任务ID 操作]\n"
                    msg += f"{self.up_prefix[0]} {id} U1"
                elif action == "UPSCALE":
                    msg = "🎨 放大成功\n"
                    msg += f"✨ {rj['description']}\n"
                elif action == "VARIATION":
                    msg = "🎨 变换成功\n"
                    msg += f"✨ {rj['description']}\n"
                elif action == "DESCRIBE":
                    msg = "🎨 转述成功\n"
                    msg += f"✨ 内容: {rj['prompt']}\n"
                    msg += f"✨ 内容(英文): {rj['promptEn']}\n"
                    msg += f"✨ 地址: {rj['imageUrl']}\n"
                if startTime:
                    msg += f"开始时间：{startTime}\n"
                if finishTime:
                    msg += f"完成时间：{finishTime}"
                if rj["imageUrl"]:
                    return True, msg, rj["imageUrl"]
                return True, msg, None
            elif status == "FAILURE":
                failReason = rj["failReason"]
                return False, f"请求失败：{failReason}", None
            else:
                return False, f"请求失败：服务异常", None
        except Exception as e:
            logger.exception(e)
            return False, "请求失败", None
    
    # 查询任务队列
    def task_queue(self):
        try:
            url = self.baseUrl + f"/mj/task/queue"
            res = requests.get(url, headers=self.headers)
            rj = res.json()
            msg = f"✅ 查询成功\n"
            if not rj:
                msg += "暂无执行中的任务"
                return True, msg
            for i in range(0, len(rj)):
                msg += f"------------------------------\n"
                msg += f"ID: {rj[i]['id']}\n"
                msg += f"进度：{rj[i]['progress']}\n"
                msg += f"内容：{rj[i]['prompt']}\n"
                msg += f"描述：{rj[i]['description']}\n"
                msg += f"状态：{self.status(rj[i]['status'])}\n"
                startTime = ""
                if rj[i]['startTime']:
                    startTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(rj[i]['startTime']/1000))
                if startTime:
                    msg += f"开始时间：{startTime}\n"
            msg += f"------------------------------\n"
            msg += f"共计：{len(rj)}个任务在执行"
            return True, msg
        except Exception as e:
            logger.exception(e)
            return False, "查询失败"
    
    def status(self, status):
        msg = ""
        if status == "SUCCESS":
            msg = "已成功"
        elif status == "FAILURE":
            msg = "失败"
        elif status == "SUBMITTED":
            msg = "已提交"
        elif status == "IN_PROGRESS":
            msg = "处理中"
        else:
            msg = "未知"
        return msg
    
    def help_text(self):
        help_text = "欢迎使用MJ机器人\n"
        help_text += f"这是一个AI绘画工具，只要输入想到的文字，通过人工智能产出相对应的图。\n"
        help_text += f"------------------------------\n"
        help_text += f"🎨 插件使用说明：\n"
        help_text += f"(1) imagine想象绘图：输入: {self.imagine_prefix[0]} prompt\n"
        help_text += f"(2) 图片变换：使用[{self.up_prefix[0]} + 任务ID操作]即可放大和变换imagine生成的图片\n"
        help_text += f"(3) describe识图：在私信窗口直接发送图片即可帮你识别解析prompt描述\n"
        help_text += f"(4) 任务查询：使用[{self.fetch_prefix[0]} + 任务ID操作]即可查询所提交的任务\n"
        help_text += f"(5) 任务队列：使用[/queue]即可查询正在执行中的任务队列\n"
        help_text += f"------------------------------\n"
        help_text += f"Tips: prompt 即你提的绘画描述\n"
        help_text += f"📕 prompt附加参数 \n"
        help_text += f"1.解释: 在prompt后携带的参数, 可以使你的绘画更别具一格\n"
        help_text += f"2.示例: /mj prompt --ar 16:9\n"
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