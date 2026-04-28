import os
import shutil
import random
import re
import time
import requests
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 请求数据模型
class BugInjectRequest(BaseModel):
    file_path: str
    bug_level: int  # 1/2/3 三个等级
    target_endpoint: Optional[str] = None  # 注入后要探测的接口地址

class FileRestoreRequest(BaseModel):
    file_path: str

# 红队破坏者核心类
class Saboteur:
    def __init__(self):
        self.injection_history = []
        self.backup_suffix = ".original"

    def backup_file(self, file_path: str) -> str:
        """修改前备份文件，只会备份一次"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"目标文件不存在: {file_path}")
        backup_path = f"{file_path}{self.backup_suffix}"
        if not os.path.exists(backup_path):
            shutil.copy2(file_path, backup_path)
        return backup_path

    def inject_level1_bug(self, content: str) -> str:
        """Level1: 语法级Bug，删减语法符号导致语法错误"""
        lines = content.split('\n')
        # 筛选有效代码行（非空非注释）
        valid_lines = [i for i, line in enumerate(lines) 
                      if line.strip() and not line.strip().startswith('#')]
        if not valid_lines:
            return content
        
        target_line_idx = random.choice(valid_lines)
        target_line = lines[target_line_idx]
        
        # 随机选择语法破坏方式
        bug_strategies = [
            # 删除括号
            lambda l: l.replace('(', '', 1) if '(' in l else l.replace(')', '', 1) if ')' in l else l,
            # 删除引号
            lambda l: l.replace('"', '', 1) if '"' in l else l.replace("'", '', 1) if "'" in l else l,
            # 删除冒号
            lambda l: l.replace(':', '', 1) if ':' in l else l,
            # 删除关键字
            lambda l: re.sub(r'\b(def|if|for|while|return|import)\b', '', l, count=1) 
            if re.search(r'\b(def|if|for|while|return|import)\b', l) else l,
            # 删除等号
            lambda l: l.replace('=', '', 1) if '=' in l else l
        ]
        
        applicable_strategies = [f for f in bug_strategies if f(target_line) != target_line]
        if applicable_strategies:
            lines[target_line_idx] = random.choice(applicable_strategies)(target_line)
        return '\n'.join(lines)

    def inject_level2_bug(self, content: str) -> str:
        """Level2: 逻辑级Bug，篡改判断逻辑但语法正常"""
        lines = content.split('\n')
        valid_lines = [i for i, line in enumerate(lines) 
                      if line.strip() and not line.strip().startswith('#')]
        if not valid_lines:
            return content
        
        target_line_idx = random.choice(valid_lines)
        target_line = lines[target_line_idx]
        
        # 逻辑篡改策略
        bug_strategies = [
            lambda l: l.replace('==', '!='),
            lambda l: l.replace('!=', '=='),
            lambda l: l.replace('>', '<'),
            lambda l: l.replace('<', '>'),
            lambda l: l.replace('>=', '<='),
            lambda l: l.replace('<=', '>='),
            lambda l: l.replace('and', 'or'),
            lambda l: l.replace('or', 'and'),
            lambda l: l.replace('if ', 'if not ') if 'if ' in l else l,
            lambda l: l.replace('+', '-') if '+' in l else l.replace('-', '+') if '-' in l else l
        ]
        
        applicable_strategies = [f for f in bug_strategies if f(target_line) != target_line]
        if applicable_strategies:
            lines[target_line_idx] = random.choice(applicable_strategies)(target_line)
        return '\n'.join(lines)

    def inject_level3_bug(self, content: str) -> str:
        """Level3: 性能/资源级Bug，阻塞运行或内存溢出"""
        lines = content.split('\n')
        # 寻找函数定义位置注入
        func_lines = [i for i, line in enumerate(lines) 
                     if line.strip().startswith('def ') and line.strip().endswith(':')]
        if not func_lines:
            return content
        
        target_func_idx = random.choice(func_lines)
        # 确定函数缩进
        indent = '    '
        next_line_idx = target_func_idx + 1
        while next_line_idx < len(lines) and lines[next_line_idx].strip() == '':
            next_line_idx += 1
        if next_line_idx < len(lines):
            indent = lines[next_line_idx][:len(lines[next_line_idx]) - len(lines[next_line_idx].lstrip())]
        
        # 性能破坏策略
        bug_strategies = [
            f"{indent}import time; time.sleep(3600)  # 模拟永久阻塞",
            f"{indent}while True: pass  # 模拟死循环",
            f"{indent}_ = [b'x' * 1024 * 1024 * 100 for _ in range(1000)]  # 模拟内存溢出"
        ]
        
        inject_code = random.choice(bug_strategies)
        lines.insert(target_func_idx + 1, inject_code)
        return '\n'.join(lines)

    def inject_bug(self, file_path: str, bug_level: int, target_endpoint: Optional[str] = None) -> Dict[str, Any]:
        """注入Bug主流程"""
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # 1. 备份原始文件
        backup_path = self.backup_file(file_path)
        
        # 2. 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 3. 注入对应等级Bug
        if bug_level == 1:
            modified_content = self.inject_level1_bug(original_content)
        elif bug_level == 2:
            modified_content = self.inject_level2_bug(original_content)
        elif bug_level == 3:
            modified_content = self.inject_level3_bug(original_content)
        else:
            raise ValueError("Bug等级只能是 1/2/3")
        
        # 4. 写入修改后的文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        # 5. 记录注入历史
        inject_record = {
            "file_path": file_path,
            "backup_path": backup_path,
            "bug_level": bug_level,
            "inject_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_endpoint": target_endpoint,
            "status": "injected"
        }
        self.injection_history.append(inject_record)
        
        # 6. 自动探测接口
        if target_endpoint:
            probe_result = self.probe_endpoint(target_endpoint)
            inject_record["probe_result"] = probe_result
            # 探测失败立即发送报警
            if not probe_result["success"]:
                self.send_saboteur_alarm(inject_record, probe_result)
        
        return inject_record

    def probe_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """主动探测接口是否正常"""
        try:
            start_time = time.time()
            response = requests.get(endpoint, timeout=10)
            response_time = time.time() - start_time
            # 判定标准：200状态码 + 响应时间<5秒
            success = response.status_code == 200 and response_time < 5
            return {
                "success": success,
                "status_code": response.status_code,
                "response_time": round(response_time, 3),
                "error": None if success else f"响应异常，耗时{response_time:.2f}秒"
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": None,
                "response_time": None,
                "error": str(e)
            }

    def send_saboteur_alarm(self, inject_record: Dict[str, Any], probe_result: Dict[str, Any]):
        """向修复Agent发送SABOTEUR_ALARM报警"""
        alarm_data = {
            "alarm_type": "SABOTEUR_ALARM",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "inject_info": inject_record,
            "probe_info": probe_result
        }
        # 此处可扩展为发送到消息队列、HTTP调用修复Agent接口等
        print(f"[ALARM] 红队注入故障探测失败: {alarm_data}")

    def restore_original_file(self, file_path: str) -> bool:
        """恢复原始文件"""
        backup_path = f"{file_path}{self.backup_suffix}"
        if not os.path.exists(backup_path):
            return False
        shutil.copy2(backup_path, file_path)
        os.remove(backup_path)
        # 更新历史记录
        for record in self.injection_history:
            if record["file_path"] == file_path and record["status"] == "injected":
                record["status"] = "restored"
        return True

# 初始化红队实例
saboteur_agent = Saboteur()

# 暴露API路由
router = APIRouter(prefix="/api/saboteur", tags=["红队破坏者Agent"])

@router.post("/inject", summary="注入Bug到目标文件")
async def inject_bug_api(request: BugInjectRequest):
    try:
        result = saboteur_agent.inject_bug(
            file_path=request.file_path,
            bug_level=request.bug_level,
            target_endpoint=request.target_endpoint
        )
        return {
            "code": 200,
            "message": f"Level {request.bug_level} Bug注入成功",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/restore", summary="恢复目标文件的原始版本")
async def restore_file_api(request: FileRestoreRequest):
    success = saboteur_agent.restore_original_file(request.file_path)
    if success:
        return {
            "code": 200,
            "message": "文件恢复成功",
            "data": None
        }
    raise HTTPException(status_code=404, detail="未找到该文件的备份记录")

@router.get("/history", summary="获取Bug注入历史记录")
async def get_injection_history_api():
    return {
        "code": 200,
        "message": "获取成功",
        "data": saboteur_agent.injection_history
    }
