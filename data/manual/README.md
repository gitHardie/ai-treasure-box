# 手动添加工具

本目录用于存放手动添加的 AI 工具数据。每个工具对应一个 JSON 文件。

## 使用方法

### 方式一：对话式收录（推荐）
直接告诉 CTO："收录 xxx，地址是 xxx"，CTO 会自动生成 JSON 并提交。

### 方式二：手动创建
1. 复制下方模板，创建新的 JSON 文件（如 `my_tool.json`）
2. 填写工具信息
3. 提交到仓库，workflow 自动跑 pipeline

## 两种格式

### 极简格式（只需 name + url）
其余字段由 pipeline 自动补全（搜索增强 + LLM 分析）：

```json
{
  "name": "Page Agent",
  "url": "https://alibaba.github.io/page-agent/"
}
```

### 完整格式
适合你已经了解工具详细信息时：

```json
{
  "name": "Page Agent",
  "url": "https://alibaba.github.io/page-agent/",
  "description": "AI Agent in your webpage",
  "description_zh": "网页AI Agent，一行代码将网站变成AI原生应用",
  "category": "开发工具",
  "license_tier": "open-source",
  "is_china_tool": true,
  "tags": {
    "function": ["网页自动化", "AI Agent"],
    "attribute": ["开源", "纯前端"]
  }
}
```

## 字段说明

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `name` | 是 | string | 工具名称 |
| `url` | 是 | string | 工具官网地址 |
| `description` | 否 | string | 英文描述（不填由AI生成） |
| `description_zh` | 否 | string | 中文描述（不填由AI生成） |
| `category` | 否 | string | 分类（不填由AI判断） |
| `license_tier` | 否 | string | open-source/free/freemium/paid |
| `is_china_tool` | 否 | bool | 是否国内工具（不填自动检测） |
| `tags` | 否 | object | 标签（5维度） |

## 注意事项

- 文件名用英文小写加连字符，如 `page-agent.json`
- 一个文件对应一个工具
- `url` 用于去重，填正式官网地址
