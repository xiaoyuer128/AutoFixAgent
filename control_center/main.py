import os
import sys
import json
import time
import requests
import threading
import asyncio
from datetime import datetime
from typing import List, Set, AsyncGenerator, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
import uvicorn

# 配置
APP_PORT = 8003
RED_AGENT_URL = "http://localhost:8002"  # 红队现在独立在8002端口
BLUE_AGENT_URL = "http://localhost:8001"
TARGET_APP_URL = "http://localhost:8000"
COT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "agent_thought.log")
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge_base.json")

# 初始化应用
app = FastAPI(title="红蓝对抗总指挥部", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://0.0.0.0:8001",
        "http://localhost:8003",
        "http://127.0.0.1:8003",
        "http://0.0.0.0:8003"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 读取前端模板
with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), "r", encoding="utf-8") as f:
    index_html = f.read()

# 全局状态
is_repairing = False
lock = threading.Lock()
active_connections: Set[WebSocket] = set()
last_log_position = 0
latest_diff = {"before": "", "after": "", "show": False}
message_queue = asyncio.Queue()

# 异步广播消息
async def broadcast_message(message: dict):
    for connection in list(active_connections):
        try:
            await connection.send_json(message)
        except Exception as e:
            pass

# 监控CoT日志变更，实时推送到前端
def monitor_cot_log():
    global last_log_position
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_broadcast(msg):
        await broadcast_message(msg)
    
    while True:
        try:
            if os.path.exists(COT_LOG_PATH):
                with open(COT_LOG_PATH, "r", encoding="utf-8") as f:
                    f.seek(last_log_position)
                    new_lines = f.readlines()
                    last_log_position = f.tell()
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            # 解析日志格式
                            if line.startswith("[") and "]" in line:
                                timestamp_part, rest = line.split("]", 1)
                                timestamp = timestamp_part[1:]
                                if "[" in rest and "]" in rest:
                                    step_part, content = rest.split("]", 1)
                                    step = step_part.strip()[1:]
                                    message = content.strip()
                                    log_data = {
                                        "type": "cot_log",
                                        "timestamp": timestamp,
                                        "step": step,
                                        "message": message
                                    }
                                    # 安全异步调用
                                    asyncio.run_coroutine_threadsafe(run_broadcast(log_data), loop)
        except Exception as e:
            print(f"日志监控错误: {e}")
        time.sleep(1)

# 启动日志监控线程
threading.Thread(target=monitor_cot_log, daemon=True).start()

# 服务健康检查
def check_service_health(url: str) -> bool:
    try:
        response = requests.get(f"{url}/docs", timeout=2)
        return response.status_code == 200
    except:
        return False

# WebSocket管理
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        # 发送初始状态
        await websocket.send_json({
            "type": "system_status",
            "is_repairing": is_repairing,
            "diff": latest_diff
        })
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# 前端页面
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(content=index_html)

# 获取系统状态
@app.get("/api/status")
async def get_system_status():
    return {
        "code": 200,
        "data": {
            "services": {
                "target": check_service_health(TARGET_APP_URL),
                "red": check_service_health(RED_AGENT_URL),
                "blue": check_service_health(BLUE_AGENT_URL),
                "dashboard": True
            },
            "is_repairing": is_repairing,
            "knowledge_count": len(json.load(open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8")))
        }
    }

# 红队注入Bug
@app.post("/api/red/inject/{level}")
async def red_inject(level: int, background_tasks: BackgroundTasks):
    global is_repairing
    with lock:
        if is_repairing:
            raise HTTPException(status_code=400, detail="修复进行中，禁止注入Bug")
    
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "main.py")
    print(f"[注入调试] 目标文件: {file_path}, 等级: {level}, 红队地址: {RED_AGENT_URL}")
    
    try:
        response = requests.post(
            f"{RED_AGENT_URL}/api/saboteur/inject",
            json={
                "file_path": file_path,
                "bug_level": level,
                "target_endpoint": f"{TARGET_APP_URL}/api/employees"
            },
            timeout=10
        )
        print(f"[注入调试] 红队返回状态码: {response.status_code}, 内容: {response.text}")
        if response.status_code == 200:
            return {"code": 200, "message": f"Level {level} Bug注入成功", "data": response.json()}
        raise HTTPException(status_code=response.status_code, detail=f"红队返回错误: {response.text}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=500, detail="连接红队服务失败，请确认红队服务(8002端口)已启动")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注入失败: {str(e)}")

# 红队恢复原始文件
@app.post("/api/red/restore")
async def red_restore():
    global is_repairing
    with lock:
        if is_repairing:
            raise HTTPException(status_code=400, detail="修复进行中，禁止操作")
    
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "main.py")
    
    try:
        response = requests.post(
            f"{RED_AGENT_URL}/api/saboteur/restore",
            json={
                "file_path": file_path
            },
            timeout=10
        )
        if response.status_code == 200:
            return {"code": 200, "message": "文件恢复成功", "data": response.json()}
        raise HTTPException(status_code=response.status_code, detail=f"红队返回错误: {response.text}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=500, detail="连接红队服务失败，请确认红队服务(8002端口)已启动")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")

# 蓝队修复
@app.post("/api/blue/repair")
async def blue_repair(background_tasks: BackgroundTasks):
    global is_repairing
    with lock:
        if is_repairing:
            raise HTTPException(status_code=400, detail="修复正在进行中")
        is_repairing = True
    
    # 广播修复开始状态
    asyncio.create_task(broadcast_message({
        "type": "system_status",
        "is_repairing": True
    }))
    
    def repair_task():
        global is_repairing, latest_diff
        try:
            # 调用蓝队修复接口
            response = requests.post(
                f"{BLUE_AGENT_URL}/api/repair/alarm",
                json={
                    "alarm_type": "SABOTEUR_ALARM",
                    "inject_info": {
                        "file_path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "main.py"),
                        "backup_path": os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "main.py.original"),
                        "bug_level": 1,
                        "inject_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "target_endpoint": f"{TARGET_APP_URL}/api/employees",
                        "status": "injected"
                    },
                    "probe_info": {
                        "success": False,
                        "status_code": 500,
                        "response_time": 0.5,
                        "error": "语法错误"
                    },
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                timeout=30
            )
            
            # 模拟diff数据
            original_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "main.py.original")
            current_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "main.py")
            if os.path.exists(original_file) and os.path.exists(current_file):
                with open(original_file, "r", encoding="utf-8") as f:
                    before = f.read()
                with open(current_file, "r", encoding="utf-8") as f:
                    after = f.read()
                latest_diff = {
                    "before": before,
                    "after": after,
                    "show": True
                }
                # 推送diff到前端
                asyncio.create_task(broadcast_message({
                    "type": "diff_update",
                    "diff": latest_diff
                }))
        except Exception as e:
            print(f"修复任务错误: {e}")
        finally:
            with lock:
                is_repairing = False
            # 广播修复结束状态
            asyncio.create_task(broadcast_message({
                "type": "system_status",
                "is_repairing": False
            }))
    
    background_tasks.add_task(repair_task)
    return {"code": 200, "message": "修复任务已启动"}

# 接收蓝队上报的思维步骤
@app.post("/api/report_step", summary="接收蓝队上报的思维步骤")
async def report_step(step: str, message: str, timestamp: Optional[str] = None):
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_data = {
        "type": "cot_log",
        "timestamp": timestamp,
        "step": step,
        "message": message
    }
    asyncio.create_task(broadcast_message(log_data))
    return {"code": 200, "message": "上报成功"}

# 合并修复代码
@app.post("/api/blue/merge")
async def merge_repair():
    global latest_diff
    # 模拟Git合并操作
    latest_diff["show"] = False
    # 广播diff关闭
    asyncio.create_task(broadcast_message({
        "type": "diff_update",
        "diff": latest_diff
    }))
    return {"code": 200, "message": "修复已合并到主分支"}

# 获取知识库详情
@app.get("/api/knowledge-base", summary="获取故障知识库详情")
async def get_knowledge_base():
    kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge_base.json")
    with open(kb_path, "r", encoding="utf-8") as f:
        knowledge_base = json.load(f)
    return {
        "code": 200,
        "message": "获取成功",
        "data": knowledge_base
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=APP_PORT, reload=True)
