# 🤖 AI Treasure Box (AI百宝箱)

> AI工具、项目、资讯的一站式聚合平台，用AI分析每个工具，用数据记录AI发展历史。

[![Daily Collect](https://github.com/gitHardie/ai-treasure-box/actions/workflows/daily-collect.yml/badge.svg)](https://github.com/gitHardie/ai-treasure-box/actions/workflows/daily-collect.yml)
[![License](https://img.shields.io/github/license/gitHardie/ai-treasure-box)](LICENSE)

## ✨ 特色

- **19+ 数据源**：自动采集 GitHub Trending、HuggingFace、AI导航站、排行榜等
- **AI 深度分析**：对每个工具自动生成五维标签（功能/场景/属性/技术/质量）
- **历史沉淀**：所有数据变化通过 Git 记录，形成完整的 AI 发展档案
- **趋势洞察**：基于历史数据发现规律，生成趋势报告
- **智能对话**：基于网站沉淀数据回答 AI 资源相关问题

## 🏗 架构

```
GitHub Actions (定时采集)
    ↓
Python Collectors (19+数据源)
    ↓
AI Analysis (Coze工作流 → 五维标签)
    ↓
Git Storage (JSON + 历史快照)
    ↓
GitHub Pages (静态网站展示)
    ↓
Coze Bot (智能对话)
```

## 📁 项目结构

```
ai-treasure-box/
├── config/
│   └── sources.yaml          # 数据源配置
├── scripts/
│   ├── collectors/           # 各数据源采集器
│   │   ├── base.py           # 采集器基类
│   │   ├── github_trending.py
│   │   ├── huggingface.py
│   │   └── hyperai.py
│   ├── pipeline/
│   │   ├── data_model.py     # 数据模型（五维标签）
│   │   └── analyzer.py       # AI分析管道
│   └── main.py               # 管线入口
├── data/
│   ├── tools/                # 采集的工具数据
│   ├── rankings/             # 排名数据
│   ├── news/                 # 新闻资讯
│   └── snapshots/            # 每日快照
├── site/                     # 前端网站
├── .github/workflows/        # GitHub Actions
└── requirements.txt
```

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行采集（所有源）
cd scripts && python main.py collect

# 运行采集（指定源）
cd scripts && python main.py collect --source github-trending

# 运行AI分析
cd scripts && python main.py analyze

# 生成每日快照
cd scripts && python main.py snapshot

# 完整流程
cd scripts && python main.py all
```

## 🏷 五维标签体系

每个 AI 工具都会被分析并打上五维标签：

| 维度 | 说明 | 示例 |
|------|------|------|
| 功能 | 工具能做什么 | 文本生成、图像编辑、代码辅助 |
| 场景 | 适合谁用 | 开发者、设计师、营销人员 |
| 属性 | 产品特征 | 免费、开源、API服务 |
| 技术 | 底层技术 | GPT-4、Diffusion、RAG |
| 质量 | 状态评估 | 热门、新星、口碑好 |

## 📊 数据源

| 层级 | 数据源 | 采集方式 | 频率 |
|------|--------|----------|------|
| Tier 1 | GitHub Trending | HTML解析 | 每6h |
| Tier 1 | HuggingFace Models | REST API | 每8h |
| Tier 1 | HuggingFace Spaces | REST API | 每8h |
| Tier 1 | ArXiv | Atom API | 每天 |
| Tier 1 | Hacker News | Algolia API | 每4h |
| Tier 2 | AI神器集 | HTML解析 | 每天 |
| Tier 2 | AI工具排行榜 | HTML解析 | 每天 |
| Tier 2 | HyperAI | RSS | 每6h |
| Tier 2 | AI-Bot.cn | HTML解析 | 每天 |
| Tier 3 | Reddit AI | JSON API | 每8h |

## 🌐 网站

访问 [afterai.tech](https://afterai.tech) 查看完整的 AI 工具目录和趋势分析。

## 📄 License

MIT
