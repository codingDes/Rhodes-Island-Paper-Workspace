# 罗德岛工作终端

---

这是一个《明日方舟》风格交互界面的论文阅读与问答系统。（Web应用）
支持上传文档、RAG 检索问答、角色化聊天、公式渲染、理智系统与档案持久化。

---

## 项目亮点

- 多文档档案管理：上传、分类、筛选、关注（多选）
- 论文问答（RAG）：基于文档分块 + 向量检索后再生成回答
- 干员角色聊天：不同干员人设、语气、Lore 记忆注入
- 工具能力：内置 calculator 工具（表达式识别 + 安全计算）
- 前端增强：Markdown + LaTeX 公式渲染、上传/输入状态动画

---

## 技术栈

### 后端

- Python 3.10+
- FastAPI + Uvicorn
- Pydantic
- PyMuPDF（PDF 解析）
- FAISS（向量索引检索）
- OpenAI Compatible API（支持 DeepSeek/MiniMax 等）

### 前端

- 原生 HTML/CSS/JavaScript
- Marked（Markdown 渲染）
- KaTeX（LaTeX 公式渲染）

---

## 项目结构

```text
Final-HW-Agent/
├─ app/
│  ├─ api/                    # FastAPI 路由
│  ├─ models/                 # Pydantic Schema
│  ├─ services/               # 解析、RAG、聊天、Lore、工具、状态持久化
│  ├─ utils/
│  └─ main.py
├─ web/
│  ├─ index.html
│  ├─ css/style.css
│  ├─ js/{api.js,ui.js}
│  └─ img/
├─ data/
│  ├─ docs/                   # 上传后解析出的 txt 与原文件
│  ├─ index/                  # FAISS 索引与分块元数据
│  ├─ lore/                   # 全局与干员 Lore
│  └─ memory/                 # 档案状态等持久化数据
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

## 快速开始

### 1) 安装依赖

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) 配置环境变量

```bash
copy .env.example .env
```

常用配置（OpenAI 兼容）：

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIM`

示例（DeepSeek）：

- `OPENAI_BASE_URL=https://api.deepseek.com/v1`
- `OPENAI_MODEL=deepseek-chat`
- `EMBEDDING_MODEL=deepseek-embedding`

> 若嵌入接口不可用，系统会降级到本地哈希 embedding，以保证流程可运行。

> P.S. 为便于老师您一键使用，我项目的API KEY都留在里面了，您部署好之后可以直接游玩————当然，请您尽量不要挥霍我的KEY...我账户余额只有三块钱...

### 3) 启动服务

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

访问地址：

- Web：`http://127.0.0.1:8000/`
- Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/health`

---

## 核心接口

- `POST /api/upload`：上传并解析文档，自动构建索引
- `POST /api/chat`：问答（支持关注档案列表）
- `POST /api/summary/{doc_id}`：结构化总结
- `GET /api/operators`：干员列表
- `GET /api/lore/operators/{operator_id}` / `PUT ...`：干员 Lore 管理
- `GET /api/archive-state` / `PUT ...`：档案与分类状态持久化

---

## 常见问题

- 公式问答提示“缺失数学表达式”：
  - 通常是 PDF 原始可提取文本里公式缺失，或检索片段未命中理论部分
  - 建议重传论文触发新版解析，并优先提问含关键词（如 ATE、estimator、equation）

- 前端显示“读取/保存档案失败”：
  - 先确认后端服务是否运行在 `127.0.0.1:8000`
  - 再检查 `/api/archive-state` 是否可访问

---

## 许可证

深度学习理论与实践课程作业项目，默认仅用于学习与展示。
关于《明日方舟》的一切版权都归上海鹰角网络所有，本项目仅是一个二次同人创作、非商业盈利。
