# 防汛应急报告生成系统

## 项目简介

防汛应急报告生成系统是一个专门为防汛应急情况设计的信息整合与报告生成平台。该系统通过收集、处理和分析各种防汛相关数据，快速生成结构化的应急报告，为防汛决策提供及时、准确的信息支持。

系统采用前后端分离架构，前端使用React和TypeScript构建用户界面，后端使用Python和FastAPI提供API服务，并集成大型语言模型(LLM)用于智能报告生成。

## 系统架构

系统采用分层架构设计，主要分为四个层次：

1. **前端层 (Frontend)** - 提供用户界面和交互功能
2. **API层 (Backend API)** - 提供RESTful API接口
3. **服务层 (Service Layer)** - 实现核心业务逻辑
4. **数据层 (Data Layer)** - 负责数据存储和访问

详细架构请参考[总体架构文档](./总体架构.md)。

## 主要功能

- 知识库管理：上传、分类和管理防汛相关知识
- 报告生成：基于用户请求和知识库内容，智能生成防汛应急报告
- 报告查看：查看、下载和分享生成的报告
- 用户管理：用户注册、登录和权限控制
- 系统监控：监控系统运行状态和资源使用情况

## 安装说明

### 环境要求

- Python 3.9+
- Node.js 18+
- npm 8+

### 后端安装

1. 克隆代码库
```bash
git clone https://github.com/HHU3637kr/FloodReport.git
cd FloodReport
```

2. 创建并激活虚拟环境
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量
```bash
# 复制示例配置文件
cp .env.example .env
# 编辑.env文件，填入必要的配置信息
```

### 前端安装

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

## 使用方法

### 启动后端服务

```bash
# 在项目根目录下执行
python src/main.py
```

或使用FastAPI开发服务器：

```bash
uvicorn src.ui.run_api:app --reload
```

### 启动前端服务

```bash
cd frontend
npm run dev
```

### 访问系统

打开浏览器，访问: http://localhost:3000

## 系统工作流程

1. 用户通过前端界面登录系统并提交报告生成请求
2. API层接收请求，验证用户权限
3. 服务层从数据层检索相关信息，通过知识库管理和LLM服务生成报告内容
4. 生成的报告保存到数据层，并通过API返回给前端
5. 前端展示报告内容给用户

## 技术栈

- **前端**: React, TypeScript
- **后端**: Python, FastAPI
- **数据存储**: 文件系统, 向量数据库
- **机器学习**: 大型语言模型 (LLM)

## 贡献指南

欢迎贡献代码或提出建议，请提交Issue或Pull Request。

## 许可证

[MIT](LICENSE)
