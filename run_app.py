import os
import sys
import subprocess
import signal
import time
from datetime import datetime

process = None

def signal_handler(sig, frame):
    global process
    print("\n正在停止服务...")
    if process:
        process.terminate()
        process.wait()
    print("服务已停止")
    sys.exit(0)

def main():
    global process
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建日志目录
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "system_critical.log")
    
    # 启动命令
    cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "app"]
    
    print(f"启动服务: {' '.join(cmd)}")
    print(f"系统错误日志将写入: {log_path}")
    
    with open(log_path, "a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            cmd,
            cwd=os.path.dirname(__file__),
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="gbk",
            errors="ignore",
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时捕获stderr
        try:
            while True:
                stderr_line = process.stderr.readline()
                if stderr_line == '' and process.poll() is not None:
                    break
                if stderr_line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    log_entry = f"[{timestamp}] {stderr_line}"
                    print(log_entry, end='', file=sys.stderr)
                    log_file.write(log_entry)
                    log_file.flush()
        except Exception as e:
            print(f"错误: {e}")
            if process:
                process.terminate()
                process.wait()
    
    exit_code = process.returncode if process else 1
    print(f"服务退出，退出码: {exit_code}")
    return exit_code

if __name__ == "__main__":
    # 服务崩溃自动重启机制
    restart_count = 0
    max_restarts = 100  # 最大重启次数
    restart_delay = 2  # 重启间隔秒
    
    while restart_count < max_restarts:
        try:
            exit_code = main()
            if exit_code == 0:
                break  # 正常退出，不重启
            print(f"服务异常退出，退出码: {exit_code}，{restart_delay}秒后自动重启...")
            restart_count += 1
            time.sleep(restart_delay)
        except KeyboardInterrupt:
            print("\n手动停止服务")
            break
        except Exception as e:
            print(f"服务运行异常: {e}，{restart_delay}秒后自动重启...")
            restart_count += 1
            time.sleep(restart_delay)
    
    if restart_count >= max_restarts:
        print(f"超过最大重启次数{max_restarts}，停止重启")
        sys.exit(1)
