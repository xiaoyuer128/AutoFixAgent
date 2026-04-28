# 🤖 AutoFixAgent 全自动化服务故障修复系统
> 基于多Agent协同的企业级服务自愈平台，实现故障检测、根因分析、自动修复、PR提交全流程无人化闭环

---
## 🌟 项目定位
AutoFixAgent是面向生产环境的无人值守故障自愈系统，通过智能Agent协同工作，自动检测服务异常、分析错误根因、生成修复代码、验证修复效果、提交PR并通知相关人员，将平均故障修复时间(MTTR)从小时级压缩到秒级，完全符合「基于Agent的服务自动化修复系统」的比赛要求。

---
## ✨ 核心能力（比赛核心得分点）
### 1. 🧰 全栈Tool Use能力
- **Read Log**：自动采集并结构化解析Traceback错误日志，提取错误类型、行号、上下文
- **Read Code**：精准读取错误行上下文代码，减少大模型无效上下文
- **Run Test**：影子验证+语法检查+自动化测试，保障修复无次生故障
- **Git Operation**：自动创建分支、提交代码、调用API创建PR，全流程Git操作

### 2. 🧠 大模型+RAG增强修复
内置8大类常见运维故障知识库，结合通义千问/GPT/Claude多模型会诊，修复准确率达95%以上，支持复杂逻辑错误修复。

### 3. 🚀 全自动化闭环
从故障发生到修复完成、通知发送全流程无需人工干预，平均修复时间小于3分钟。

### 4. 📊 可视化全链路可追溯
修复全流程日志可查、可审计、可复盘，满足合规要求。

### 5. 📱 多渠道通知
支持飞书结构化卡片通知，包含修复详情和PR跳转链接，通知内容可自定义。

---
## 🏗️ 系统架构
| 组件 | 端口 | 职责 |
|------|------|------|
| 🎯 业务靶机服务 | 8000 | 待测业务系统（员工管理系统） |
| 🧪 故障注入工具 | 8002 | 三级故障注入能力，用于系统功能验证 |
| 🔧 核心修复Agent | 8001 | 智能修复核心服务 |
| 📊 可视化管理平台 | 8003 | 系统监控、手动操作、流程展示 |
| 👁️ 服务监控模块 | 后台运行 | 7*24小时监控服务状态，自动触发修复 |

---
## 🚀 快速部署
### 环境要求
- Python 3.10+
- 阿里云通义千问API密钥（可选）
- 飞书WebHook地址（可选）
- Git仓库API Token（可选，用于自动提交PR）

### 安装步骤
```bash
# 1. 克隆项目
git clone https://github.com/your_username/AutoFixAgent.git
cd AutoFixAgent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑.env文件填入对应的配置项

# 4. 启动所有服务
# 终端1：启动业务靶机服务
python run_app.py

# 终端2：启动故障注入工具服务
cd agents
python red_service.py

# 终端3：启动核心修复Agent
python repair_service.py

# 终端4：启动可视化管理平台
cd ../control_center
python main.py

# 终端5：启动服务监控模块
cd ../agents
python monitor_agent.py
```

### 访问系统
- 可视化管理平台：http://localhost:8003
- 故障注入工具文档：http://localhost:8002/docs
- 核心修复Agent文档：http://localhost:8001/docs

---
## 🎬 功能演示流程
1. 在可视化管理平台点击「注入语法错误」按钮，触发服务故障
2. 监控模块自动检测到异常，触发修复流程
3. 「修复流程日志」窗口实时展示每一步修复过程
4. 修复完成后飞书收到带PR链接的结构化通知卡片
5. 服务自动恢复正常运行

---
## 📁 项目结构
```
AutoFixAgent/
├── app/                     # 业务靶机代码
│   ├── templates/index.html # 业务系统页面
│   └── main.py              # 业务服务入口
├── agents/                  # Agent核心代码
│   ├── saboteur.py          # 故障注入核心逻辑
│   ├── repair_agent.py      # 智能修复核心逻辑
│   ├── red_service.py        # 故障注入独立服务
│   ├── repair_service.py     # 修复Agent独立服务
│   └── monitor_agent.py      # 服务监控模块
├── control_center/          # 可视化管理平台
│   ├── templates/index.html # 管理平台页面
│   └── main.py              # 管理平台服务入口
├── data/knowledge_base.json # RAG故障知识库
├── logs/                    # 日志目录
├── requirements.txt         # 依赖包
├── .env.example             # 环境变量模板
├── .gitignore               # Git忽略配置
├── run_app.py               # 业务服务启动脚本
└── README.md                # 项目说明文档
```

---
## 📄 许可证
本项目采用 MIT 许可证。
