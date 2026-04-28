import os
import sys
# 把项目根目录加入Python路径，确保模块导入正常
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agents.repair_agent import router as repair_router

# 初始化独立修复服务
app = FastAPI(
    title="蓝队修复Agent独立服务",
    description="与业务服务完全解耦的独立修复服务，业务服务崩溃不影响修复能力",
    version="1.0.0"
)

# 跨域配置：允许Dashboard跨源请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8003",
        "http://127.0.0.1:8003",
        "http://0.0.0.0:8003"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载修复Agent路由
app.include_router(repair_router)

if __name__ == "__main__":
    import uvicorn
    # 修复服务使用独立端口8001，与主业务服务8000完全隔离
    uvicorn.run(
        "repair_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=[os.path.dirname(__file__)]
    )
