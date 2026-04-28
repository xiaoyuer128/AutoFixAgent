import os
import sys
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from starlette.responses import JSONResponse
from agents.saboteur import router as saboteur_router
from agents.repair_agent import router as repair_router

# 日志配置
log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "app_error.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据库配置
SQLALCHEMY_DATABASE_URL = "sqlite:///./employees.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 员工模型
class EmployeeDB(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True, nullable=False)
    department = Column(String(50), index=True, nullable=False)
    position = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    status = Column(Boolean, default=True)  # True: 在职 False: 离职
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

# Pydantic模型
class EmployeeBase(BaseModel):
    name: str
    department: str
    position: str
    email: str
    phone: Optional[str] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(EmployeeBase):
    status: Optional[bool] = None

class Employee(EmployeeBase):
    id: int
    status: bool
    created_at: datetime

    class Config:
        from_attributes = True

# FastAPI初始化
app = FastAPI(title="企业员工管理系统")

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

# 挂载红蓝队Agent路由
app.include_router(saboteur_router)
app.include_router(repair_router)

# 读取前端页面
with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), "r", encoding="utf-8") as f:
    index_html = f.read()

# 自定义异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"请求路径: {request.url.path}, 错误信息: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "data": None
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"请求路径: {request.url.path}, 状态码: {exc.status_code}, 错误信息: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 前端页面
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=index_html)

# 员工列表查询
@app.get("/api/employees", response_model=dict)
async def get_employees(
    keyword: Optional[str] = None,
    status: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(EmployeeDB)
    if keyword:
        query = query.filter(
            (EmployeeDB.name.contains(keyword)) |
            (EmployeeDB.department.contains(keyword)) |
            (EmployeeDB.position.contains(keyword)) |
            (EmployeeDB.email.contains(keyword))
        )
    if status is not None:
        query = query.filter(EmployeeDB.status == status)
    employees = query.order_by(EmployeeDB.created_at.desc()).all()
    result = []
    for emp in employees:
        result.append({
            "id": emp.id,
            "name": emp.name,
            "department": emp.department,
            "position": emp.position,
            "email": emp.email,
            "phone": emp.phone,
            "status": emp.status,
            "created_at": emp.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return {
        "code": 200,
        "message": "获取成功",
        "data": result
    }

def serialize_employee(emp):
    return {
        "id": emp.id,
        "name": emp.name,
        "department": emp.department,
        "position": emp.position,
        "email": emp.email,
        "phone": emp.phone,
        "status": emp.status,
        "created_at": emp.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

# 获取单个员工
@app.get("/api/employees/{employee_id}", response_model=dict)
async def get_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    return {
        "code": 200,
        "message": "获取成功",
        "data": serialize_employee(employee)
    }

# 创建员工
@app.post("/api/employees", response_model=dict)
async def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.query(EmployeeDB).filter(EmployeeDB.email == employee.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已存在")
    db_employee = EmployeeDB(**employee.dict())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return {
        "code": 200,
        "message": "创建成功",
        "data": serialize_employee(db_employee)
    }

# 更新员工
@app.put("/api/employees/{employee_id}", response_model=dict)
async def update_employee(employee_id: int, employee: EmployeeUpdate, db: Session = Depends(get_db)):
    db_employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    if employee.email != db_employee.email:
        existing = db.query(EmployeeDB).filter(EmployeeDB.email == employee.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已存在")
    for key, value in employee.dict(exclude_unset=True).items():
        setattr(db_employee, key, value)
    db.commit()
    db.refresh(db_employee)
    return {
        "code": 200,
        "message": "更新成功",
        "data": serialize_employee(db_employee)
    }

# 切换员工状态
@app.patch("/api/employees/{employee_id}/toggle-status", response_model=dict)
async def toggle_employee_status(employee_id: int, db: Session = Depends(get_db)):
    db_employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    db_employee.status = not db_employee.status
    db.commit()
    db.refresh(db_employee)
    {
        "code": 200,
        "message": "状态切换成功",
        "data": serialize_employee(db_employee)
    }

# 删除员工
@app.delete("/api/employees/{employee_id}", response_model=dict)
async def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    db_employee = db.query(EmployeeDB).filter(EmployeeDB.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    db.delete(db_employee)
    db.commit()
    return {
        "code": 200,
        "message": "删除成功",
        "data": None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
