from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import requests
import json
import threading
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="羽毛球场预约 API")
force_stop = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,
    allow_methods=["*"],       
    allow_headers=["*"],       
)

URL = 'https://ss.jlu.edu.cn/easyserpClient/place/freeBuyPlace'
BASE_HEADERS = {
    'Host': 'ss.jlu.edu.cn',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://ss.jlu.edu.cn',
    'Referer': 'https://ss.jlu.edu.cn/easyserp/index.html'
}

TIME_SLOTS = {
    "06:00-07:30": ("06:00", "07:30"),
    "07:30-10:00": ("07:30", "10:00"),
    "10:00-12:00": ("10:00", "12:00"),
    "12:00-13:00": ("12:00", "13:00"),
    "13:00-15:30": ("13:00", "15:30"),
    "15:30-17:30": ("15:30", "17:30"),
    "17:30-19:30": ("17:30", "19:30"),
    "19:30-21:30": ("19:30", "21:30"),
}
auth = 'ertyrKASazex+K8oEGRnptUXDNZW2tIbFzdssmZKcJPUzg27ccENIlAmbT57zusN/epigWD9kDJEkASDroZUCXh3xa8Q7xVBnmLPMTqbVKQ2u4w9/NS16KwTdYaciNZ6RWXx0BO72mtVPaMA0In87u33/0sRQ5gww26VJHSDUH0kK7Zs4EZMv+5NTc6iBhzAatI/K9tEk9Pj6gWiUibm+Tp4AS9YJ1ikO9OH0yGOdoC3kcvevd/je65jWYgxwHpud6q3bECGT3nqwYNPmJwXygn75bXliloq7h+pdEOtd2KovvIURxjV01aNCbPfhgKccsTI8a5vT9ulQwlqZb0FfA==:SWE9RC0ENX/2DjshLPr9OTC//Ozqf2JJu6t8fqBVvKtdq2lLt9kGDF3t+2EzVdueKtdr0C8kFqsDzJPYCLbsL4b82j+PC/QzkICIxxuldO2RzOnWijeZX8j52vWIzj2A2/jm3Rl3HYFHOu1UXAnQMzg61WsKU3vzlRfEcnv9H7WYv1RbAhcb2n8pU1qNUK1bv0VTHVcB+1xwiJKXdIgKRpaGIwUkeqZWEyVcoeKCP2bwfbdL16FA5/eK5dbYCzMSQS5Keg0hyn8XP2dJCrFO5i96+JrDWpkrUo8TCo4zx1/GVUiEelsLPomGrAuG6sRr'

USERS = {
    1: {"token": "9118E4599ECE7EC40E2DED3626458092", "auth": f"{auth}"},
    2: {"token": "AAA30A0D95155E2833019071DA7A6FF7", "auth": f"{auth}"},
    3: {"token": "BC40F59FC0DDD1FE2866B7B9572EC0AA", "auth": f"{auth}"},
    4: {"token": "86B7E78789CAA20D0D08757730C897F4", "auth": f"{auth}"},
    5: {"token": "44D12C8BE494804D7C3BAAA45ADBB2E5", "auth": f"{auth}"},
}

DEFAULT_TOKEN = ""
DEFAULT_AUTH = ""


class ReserveRequest(BaseModel):
    user_id: Optional[int] = None          
    token: Optional[str] = None              
    auth: Optional[str] = None               
    place: int                               
    time_range: Optional[str] = None         
    start_time: Optional[str] = None        
    end_time: Optional[str] = None          
    schedule_at_midnight: bool = False      
    shopNum: str = "0002"                   
    txUserIds: str = "[2622]"              



def get_credentials(req: ReserveRequest):
    token = req.token or (USERS.get(req.user_id) or {}).get("token") or DEFAULT_TOKEN
    auth = req.auth or (USERS.get(req.user_id) or {}).get("auth") or DEFAULT_AUTH
    return token, auth

def build_fieldinfo(place: int, start_time: str, end_time: str):
    tomorrow = datetime.now() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y-%m-%d")
    print(date_str)
    fieldinfo = [{
        "day": date_str,
        "startTime": start_time,
        "endTime": end_time,
        "placeShortName": f"ymq{place}",
        "name": f"羽毛球{place}"
    }]
    return json.dumps(fieldinfo, ensure_ascii=False)

def do_post_request(token: str, auth: str, fieldinfo_str: str, shopNum: str, oldTotal="0.00", premerother=""):
    headers = BASE_HEADERS.copy()
    if auth:
        headers['auth'] = auth

    body = {
        "fieldinfo": fieldinfo_str,
        "token": token,
        "shopNum": shopNum,
        "oldTotal": oldTotal,
        "premerother": premerother,
        "txUserIds": "[2622]"
    }
    with requests.Session() as s:
        resp = s.post(URL, headers=headers, data=body, timeout=10)
    return resp

def schedule_at_midnight(func, *args, **kwargs):
    global force_stop
    force_stop = True
    now = datetime.now()
    
    target = datetime(now.year, now.month, now.day, 23, 30, 0)
    if now >= target:
        target = target + timedelta(days=1)

    wait_seconds = (target - now).total_seconds() - 2
    wait_minutes = wait_seconds / 60

    print(f"距离本地 0 点还有 {wait_minutes:.2f} 分钟（约 {wait_seconds:.0f} 秒），将在 {target} 触发请求")

    def runner():
        time.sleep(wait_seconds)
        try:
            func(*args, **kwargs)
        except Exception as e:
            print("midnight job error:", e)

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return True


@app.post("/reserve")
def reserve(req: ReserveRequest, background_tasks: BackgroundTasks):
    if req.time_range:
        if req.time_range not in TIME_SLOTS:
            return {"success": False, "error": "未知的 time_range，必须在 TIME_SLOTS 中"}
        start_time, end_time = TIME_SLOTS[req.time_range]
    else:
        if not (req.start_time and req.end_time):
            return {"success": False, "error": "需要提供 time_range 或 start_time 与 end_time"}
        start_time, end_time = req.start_time, req.end_time

    token, auth = get_credentials(req)
    if not token or not auth:
        print("Warning: token or auth is empty; remote server may reject the request.")

    fieldinfo_str = build_fieldinfo(req.place, start_time, end_time)

    def execute_send(condition=True):
        try:
            resp = do_post_request(token=token, auth=auth, fieldinfo_str=fieldinfo_str, shopNum=req.shopNum)
            print('被预约时间: ' + fieldinfo_str)
            print("预约响应（执行时间 {}）: {}".format(datetime.now().isoformat(), resp.text))
            if condition:
                for i in range(160):  
                    if ('请勿重复操作' in resp.text or '时间内预约' in resp.text or '预约失败' in resp.text) and force_stop:
                        time.sleep(0.25)
                        resp = do_post_request(token=token, auth=auth, fieldinfo_str=fieldinfo_str, shopNum=req.shopNum)
                        print("预约响应（执行时间 {}）: {} : {}".format(datetime.now().isoformat(), resp.text, token))
                        continue
                    break
            else:
                 resp = do_post_request(token=token, auth=auth, fieldinfo_str=fieldinfo_str, shopNum=req.shopNum)
                 print("预约响应（执行时间 {}）: {} : {}".format(datetime.now().isoformat(), resp.text, token))
                
            
            return {"status_code": resp.status_code, "text": resp.text}
        except Exception as e:
            print("请求异常:", e)
            return {"error": str(e)}

    if req.schedule_at_midnight:
        schedule_at_midnight(execute_send)
        return {"success": True, "scheduled": True, "message": "已安排在午夜执行（0:00）"}
    else:
        result = execute_send(False)
        return {"success": True, "scheduled": False, "result": result}


@app.get("/time_slots")
def get_time_slots():
    return {"time_slots": list(TIME_SLOTS.keys())}

@app.get("/stop")
def force_stopp():
    global force_stop
    force_stop = False


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}
