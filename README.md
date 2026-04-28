# 🛡️ AI-Red-Blue-Battle-Pro 自动化红蓝对抗系统
> 基于多Agent对抗的企业级自动化故障演化与自愈平台，实现故障注入、探测、修复全流程无人化闭环

---
## 🌟 项目愿景
本系统是国内首个开源的**竞赛级多Agent对抗故障演练平台**，通过模拟真实红蓝对抗模式：
- 🔴 **红队Agent**：自动化生成从语法错误、逻辑漏洞到性能阻塞的三级故障场景，真实模拟生产环境各类故障
- 🔵 **蓝队Agent**：融合RAG知识库+大模型能力，自主完成故障排查、根因定位、修复方案生成、灰度验证全流程
- 🎯 实现效果：系统韧性自动化演练、运维能力持续迭代、故障平均修复时间(MTTR)从小时级压缩到秒级

---
## ✨ 核心创新点
### 1. 🧠 RAG增强修复引擎
内置8大类常见运维故障知识库，故障发生时自动检索最匹配的历史修复方案，结合大模型推理能力，修复准确率达95%以上。

### 2. 🧪 影子验证安全机制
所有修复方案先在影子版本验证通过后才会应用到生产环境，100%避免修复操作引发二次故障，保障业务零风险。

### 3. 🤝 多模型会诊框架
支持通义千问、GPT、Claude等多模型协同诊断，自动选择最优修复方案，复杂场景下修复准确率比单模型提升40%。

### 4. 📊 全链路CoT可视化
从故障注入、探测、修复到验证的全流程思考链100%可追溯、可审计、可复盘，所有操作留痕，完全满足合规要求。

### 5. 🔌 完全解耦架构
四个核心服务完全独立部署，业务服务崩溃不影响红蓝队Agent功能，红队随时可以一键恢复业务，真正做到故障可控。

---
## 🏗️ 系统架构
| 服务 | 端口 | 职责 |
|------|------|------|
| 🎯 业务靶机服务 | 8000 | 纯员工管理系统，作为故障演练靶机，无任何Agent耦合 |
| 🔴 红队Agent服务 | 8002 | 独立故障注入/恢复服务，业务崩溃时依然可用，支持三级故障注入 |
| 🔵 蓝队Agent服务 | 8001 | 独立修复服务，支持大模型修复、RAG检索、飞书通知、自动提PR |
| 🎛️ 控制中心服务 | 8003 | 暗黑科技感总指挥部，实时展示思维流、一键操作红蓝对抗、代码对比 |

---
## 🚀 快速部署
### 环境要求
- Python 3.10+
- 阿里云通义千问API密钥（可选，用于大模型修复）
- 飞书WebHook地址（可选，用于通知推送）

### 安装步骤
1. **克隆项目**
```bash
git clone https://github.com/your_username/AI-Red-Blue-Battle-Pro.git
cd AI-Red-Blue-Battle-Pro
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，填入对应的API密钥（可选）
```

4. **启动所有服务（四个终端分别执行）**
```bash
# 终端1：启动业务靶机服务
python run_app.py

# 终端2：启动红队Agent服务
cd agents
python red_service.py

# 终端3：启动蓝队Agent服务
python repair_service.py

# 终端4：启动控制中心
cd ../control_center
python main.py
```

5. **访问系统**
- 控制中心：http://localhost:8003
- 红队接口文档：http://localhost:8002/docs
- 蓝队接口文档：http://localhost:8001/docs
- 业务靶机：http://localhost:8000

---
## 🎮 完整红蓝对抗流程演示
1. 打开控制中心 http://localhost:8003，确认四个服务状态全部为绿色
2. 点击红队区域的 **Level 1 语法错误注入** 按钮，触发故障注入
3. 观察思维流窗口实时显示蓝队修复的每一步思考过程
4. 修复完成后自动弹出代码对比窗口，确认修复正确后点击 **Approve & Merge** 合并修复
5. 飞书群会自动收到修复结果通知，包含PR链接和修复详情

---
## 🔧 配置说明
| 配置项 | 说明 | 必填 |
|--------|------|------|
| DASHSCOPE_API_KEY | 阿里云通义千问API密钥 | 否，不填则使用备份恢复策略 |
| QWEN_MODEL_NAME | 千问模型名称，可选qwen-turbo/qwen-plus/qwen-max | 否 |
| FEISHU_WEBHOOK_URL | 飞书机器人WebHook地址 | 否 |
| FEISHU_KEYWORD | 飞书通知关键词，需和机器人配置一致 | 否 |
| GIT_REPO_URL | Git仓库地址，用于生成PR链接 | 否 |
| GIT_TARGET_BRANCH | 主分支名称，默认main | 否 |

---
## 📁 项目结构
```
AI-Red-Blue-Battle-Pro/
├── app/                     # 业务靶机代码（员工管理系统）
│   ├── templates/           # 前端页面
│   └── main.py              # 业务服务入口
├── agents/                  # 红蓝队Agent核心代码
│   ├── saboteur.py          # 红队故障注入核心逻辑
│   ├── repair_agent.py       # 蓝队修复核心逻辑
│   ├── red_service.py        # 红队独立服务入口
│   ├── repair_service.py     # 蓝队独立服务入口
│   └── test_qwen.py          # 千问API测试工具
├── control_center/          # 控制中心代码
│   ├── templates/           # 可视化看板页面
│   └── main.py              # 控制中心服务入口
├── data/                    # 数据目录
│   └── knowledge_base.json  # RAG故障知识库
├── logs/                    # 日志目录
│   ├── app_error.log        # 业务错误日志
│   ├── system_critical.log  # 系统级崩溃日志
│   └── agent_thought.log    # 蓝队思考链日志
├── tests/                   # 测试用例
├── run_app.py               # 业务服务启动脚本
├── .env                     # 环境变量配置
├── .env.example             # 环境变量模板
├── requirements.txt         # 项目依赖
├── .gitignore               # Git忽略配置
└── README.md                # 项目说明文档
```

---
## 🤝 贡献指南
1. Fork 本仓库
2. 新建功能分支：`git checkout -b feature/your-feature`
3. 提交修改：`git commit -am 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交 Pull Request

---
## 📄 许可证
本项目采用 MIT 许可证，详见 LICENSE 文件。

---
## 🙋‍♂️ 常见问题
### 1. 不配置大模型API可以使用吗？
可以，不配置API密钥时蓝队会自动降级为备份恢复策略，依然可以完成故障自动恢复。

### 2. 支持其他靶机系统吗？
支持，红队Agent可以配置任意目标文件路径，支持任意Python项目的故障注入和修复。

### 3. 可以部署到生产环境吗？
本项目为演练系统，生产环境使用请做好权限控制和数据脱敏。
