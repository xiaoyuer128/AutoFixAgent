import os
import sys
# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agents.saboteur import router as saboteur_router

# 红队独立服务，运行在端口8002，与业务服务完全解耦
app = FastAPI(
    title="红队Agent独立服务",
    description="完全独立的Bug注入服务，不依赖业务服务，业务崩溃时依然可用",
    version="1.0.0"
)

# 跨域配置
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

# 挂载红队路由
app.include_router(saboteur_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("red_service:app", host="0.0.0.0", port=8002, reload=True)
