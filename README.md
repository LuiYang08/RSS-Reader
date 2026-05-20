# RSS-Reader
基于 Python + AI Agent 开发的轻量级 RSS 订阅聚合与网页展示工具，支持多源内容抓取、自动解析、去重、HTML 转义与定时更新。

## 项目介绍
本项目使用 Python 构建轻量 Web 服务，通过 RSS 协议自动抓取各类资讯源内容，提供干净的网页端聚合展示。
全程借助 AI Agent 辅助开发，实现脚本编写、接口调试、页面渲染与流程自动化，大幅提升开发与信息获取效率。

适合个人信息聚合、资讯订阅、内容自动化监控等日常使用场景。

## 核心功能
- 多 RSS 源批量订阅与内容抓取
- 文章标题、时间、链接、正文自动解析
- HTML 标签自动转义与文本清洗
- 网页端可视化展示（前端：HTML/CSS/JS）
- 文章去重、时间格式化、异常处理
- 轻量 Flask Web 服务，开箱即用

## 技术栈
- **后端**：Python 3、Flask、feedparser、requests
- **前端**：HTML + CSS + JavaScript（标准前端三件套）
- **工具库**：hashlib、json、re、datetime、urllib、HTMLParser
- **开发方式**：AI Agent 辅助开发 + 自动化脚本工作流

## 项目结构
```
RSS-Reader/
├── app.py              # Flask 主程序 + RSS 抓取逻辑
├── templates/
│   └── index.html      # 前端展示页面
├── README.md           # 项目说明
└── requirements.txt    # 依赖清单
```

## 快速运行
1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 启动服务
```bash
python app.py
```

3. 打开浏览器访问
```
http://127.0.0.1:5000
```

## 亮点说明
- 纯轻量架构，无 heavy 依赖，启动速度快
- 自动处理 HTML 转义、文本格式化、时间时区转换
- 基于哈希实现文章去重，避免重复展示
- 代码结构清晰，易于扩展更多 RSS 源
- AI 辅助开发，高效完成全流程工作流
