import os
import sys
import time
import re
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading
from dotenv import load_dotenv

# 加载环境变量
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(project_root, ".env"))

# 配置
TARGET_APP_URL = os.getenv("TARGET_APP_URL", "http://localhost:8000")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # 健康检查间隔秒
LOG_CHECK_INTERVAL = int(os.getenv("LOG_CHECK_INTERVAL", "10"))  # 日志检查间隔秒
ERROR_COOLDOWN_MINUTES = int(os.getenv("ERROR_COOLDOWN_MINUTES", "5"))  # 同一错误冷却时间

# 全局状态
processed_errors = {}  # 存储已处理过的错误哈希和处理时间
is_repairing = False
lock = threading.Lock()

def parse_traceback(log_content: str) -> Optional[Dict[str, Any]]:
    """解析Traceback日志，提取结构化错误信息"""
    traceback_pattern = re.compile(
        r'Traceback \(most recent call last\):\n'
        r'(.*?)\n'
        r'([A-Z][a-zA-Z0-9]*Error:.*)',
        re.DOTALL
    )
    
    match = traceback_pattern.search(log_content)
    if not match:
        return None
    
    stack_trace = match.group(1).strip()
    error_msg = match.group(2).strip()
    
    # 提取错误类型
    error_type = error_msg.split(':', 1)[0].strip()
    
    # 提取错误行和文件
    file_pattern = re.compile(r'File "([^"]+)", line (\d+), in')
    file_matches = list(file_pattern.finditer(stack_trace))
    
    error_file = None
    error_line = None
    if file_matches:
        last_match = file_matches[-1]
        error_file = last_match.group(1)
        error_line = int(last_match.group(2))
    
    # 提取错误代码上下文
    code_context = ""
    if error_file and os.path.exists(error_file):
        try:
            with open(error_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                start = max(0, error_line - 10)
                end = min(len(lines), error_line + 10)
                for i in range(start, end):
                    line_num = i + 1
                    prefix = "→ " if line_num == error_line else "  "
                    code_context += f"{prefix}{line_num}: {lines[i]}"
        except Exception as e:
            print(f"读取代码上下文失败: {e}")
    
    return {
        "error_type": error_type,
        "error_msg": error_msg,
        "stack_trace": stack_trace,
        "error_file": error_file,
        "error_line": error_line,
        "code_context": code_context,
        "raw_log": log_content,
        "error_hash": hash(f"{error_file}:{error_line}:{error_type}")
    }

def check_service_health() -> bool:
    """检查目标服务健康状态"""
    try:
        response = requests.get(f"{TARGET_APP_URL}/api/employees", timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

def read_latest_errors() -> list:
    """读取最新的错误日志"""
    log_files = [
        os.path.join(project_root, "logs", "app_error.log"),
        os.path.join(project_root, "logs", "system_critical.log")
    ]
    
    errors = []
    for log_file in log_files:
        if not os.path.exists(log_file):
            continue
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # 只读取最近100行
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                content = "\n".join(recent_lines)
                
                # 查找所有Traceback
                error = parse_traceback(content)
                if error:
                    errors.append(error)
        except Exception as e:
            print(f"读取日志失败: {e}")
    
    return errors

def is_error_processed(error_hash: int) -> bool:
    """检查错误是否已经处理过，在冷却时间内的错误不重复处理"""
    with lock:
        if error_hash in processed_errors:
            process_time = processed_errors[error_hash]
            if datetime.now() - process_time < timedelta(minutes=ERROR_COOLDOWN_MINUTES):
                return True
            else:
                # 冷却时间已过，移除记录
                del processed_errors[error_hash]
    return False

def mark_error_processed(error_hash: int):
    """标记错误已处理"""
    with lock:
        processed_errors[error_hash] = datetime.now()

def trigger_repair(error_info: Dict[str, Any]) -> bool:
    """触发蓝队修复流程"""
    global is_repairing
    with lock:
        if is_repairing:
            return False
        is_repairing = True
    
    try:
        print(f"触发自动修复: {error_info['error_msg']}")
        # 调用蓝队修复接口
        repair_payload = {
            "alarm_type": "SABOTEUR_ALARM",
            "inject_info": {
                "file_path": error_info["error_file"],
                "backup_path": f"{error_info['error_file']}.original",
                "bug_level": 1,
                "inject_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "target_endpoint": f"{TARGET_APP_URL}/api/employees",
                "status": "injected"
            },
            "probe_info": {
                "success": False,
                "status_code": 500,
                "response_time": 0.5,
                "error": error_info["error_msg"]
            },
            "error_log": error_info["raw_log"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        response = requests.post(
            "http://localhost:8001/api/repair/alarm",
            json=repair_payload,
            timeout=60  # 修复可能耗时较长
        )
        
        return response.status_code == 200
    except Exception as e:
        print(f"触发修复失败: {e}")
        return False
    finally:
        with lock:
            is_repairing = False

def health_check_loop():
    """健康检查循环线程"""
    print("🚀 健康监控线程已启动")
    consecutive_failure_count = 0
    max_consecutive_failures = 3  # 连续3次检测失败触发兜底修复
    
    while True:
        try:
            service_healthy = check_service_health()
            if not service_healthy and not is_repairing:
                consecutive_failure_count += 1
                print(f"⚠️ 检测到服务异常，连续失败次数: {consecutive_failure_count}")
                
                # 先尝试读取错误日志
                errors = read_latest_errors()
                error_found = False
                for error in errors:
                    if not is_error_processed(error["error_hash"]):
                        print(f"发现新错误: {error['error_msg']}")
                        success = trigger_repair(error)
                        if success:
                            mark_error_processed(error["error_hash"])
                        error_found = True
                        break  # 一次只处理一个错误
                
                # 连续多次失败且无日志错误，自动触发蓝队智能修复
                if not error_found and consecutive_failure_count >= max_consecutive_failures:
                    print("🔧 无错误日志，自动触发蓝队智能修复")
                    try:
                        file_path = os.path.join(project_root, "app", "main.py")
                        # 构造修复请求，调用蓝队修复接口
                        repair_payload = {
                            "alarm_type": "SABOTEUR_ALARM",
                            "inject_info": {
                                "file_path": file_path,
                                "backup_path": f"{file_path}.original",
                                "bug_level": 1,
                                "inject_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "target_endpoint": f"{TARGET_APP_URL}/api/employees",
                                "status": "injected"
                            },
                            "probe_info": {
                                "success": False,
                                "status_code": 500,
                                "response_time": 0.5,
                                "error": "服务无法访问，疑似语法错误"
                            },
                            "error_log": "服务启动失败，无Traceback日志",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        response = requests.post(
                            "http://localhost:8001/api/repair/alarm",
                            json=repair_payload,
                            timeout=60
                        )
                        if response.status_code == 200:
                            print("✅ 蓝队自动修复触发成功")
                            consecutive_failure_count = 0
                            mark_error_processed(hash("auto_repair_trigger"))
                        else:
                            # 蓝队修复失败，降级为恢复原始文件
                            print(f"蓝队修复失败，降级为恢复原始文件，状态码: {response.status_code}")
                            restore_payload = {"file_path": file_path}
                            requests.post(
                                "http://localhost:8002/api/saboteur/restore",
                                json=restore_payload,
                                timeout=10
                            )
                    except Exception as e:
                        print(f"自动修复失败: {e}")
            else:
                consecutive_failure_count = 0
                
        except Exception as e:
            print(f"健康检查循环异常: {e}")
        time.sleep(HEALTH_CHECK_INTERVAL)

def log_monitor_loop():
    """日志监控循环线程"""
    print("🚀 日志监控线程已启动")
    while True:
        try:
            if not is_repairing:
                errors = read_latest_errors()
                for error in errors:
                    if not is_error_processed(error["error_hash"]):
                        print(f"发现新错误日志: {error['error_msg']}")
                        success = trigger_repair(error)
                        if success:
                            mark_error_processed(error["error_hash"])
                        break
        except Exception as e:
            print(f"日志监控循环异常: {e}")
        time.sleep(LOG_CHECK_INTERVAL)

def start_monitor():
    """启动监控Agent"""
    print("🤖 自动化监控修复Agent启动")
    print(f"📡 监控目标服务: {TARGET_APP_URL}")
    print(f"⏱️ 健康检查间隔: {HEALTH_CHECK_INTERVAL}秒")
    print(f"⏱️ 日志检查间隔: {LOG_CHECK_INTERVAL}秒")
    
    # 启动监控线程
    threading.Thread(target=health_check_loop, daemon=True).start()
    threading.Thread(target=log_monitor_loop, daemon=True).start()
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n👋 监控Agent已停止")

if __name__ == "__main__":
    start_monitor()
