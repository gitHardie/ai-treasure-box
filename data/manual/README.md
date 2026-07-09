# 手动添加工具

本目录用于存放手动添加的 AI 工具数据。每个工具对应一个 JSON 文件。

## 使用方法

1. 复制下方模板，创建新的 JSON 文件（如 `my_tool.json`）
2. 填写工具信息
3. 运行采集命令导入：
   ```bash
   python scripts/pipeline.py --source manual-tools
   ```

## JSON 格式规范

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 工具名称 |
| `url` | string | 工具官网地址 |
| `description` | string | 英文描述（一句话） |
| `category` | string | 一级分类（见分类列表） |
| `license_tier` | string | 许可等级 |

### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `description_zh` | string | 中文描述（不填则由 AI 翻译） |
| `subcategory` | string | 二级分类 |
| `is_china_tool` | bool | 是否国内工具，默认 `false` |
| `tags` | object | 标签（见下方标签体系） |

### 一级分类列表

`文本生成` / `图像创作` / `代码开发` / `数据分析` / `音视频` / `办公效率` / `学术研究` / `开发工具` / `设计创意` / `营销推广` / `教育培训` / `其他`

### 许可等级

`open-source` / `free` / `freemium` / `paid` / `source-available`

### 标签体系

标签分为 5 个维度，每个维度为一个字符串数组：

| 维度 | 键名 | 说明 | 示例 |
|------|------|------|------|
| 功能标签 | `function` | 核心功能描述 | `["对话", "文本生成", "翻译"]` |
| 场景标签 | `scenario` | 适用场景 | `["个人使用", "团队协作", "企业级"]` |
| 属性标签 | `attribute` | 工具特征 | `["免费", "中文支持", "离线可用"]` |
| 技术标签 | `tech` | 底层技术 | `["GPT-4", "Stable Diffusion", "RAG"]` |
| 质量标签 | `quality` | 推荐级别 | `["推荐", "热门", "新锐"]` |

## 示例模板

```json
{
  "name": "示例工具",
  "url": "https://example.com",
  "description": "一句话描述",
  "description_zh": "中文描述",
  "category": "文本生成",
  "subcategory": "聊天助手",
  "license_tier": "freemium",
  "is_china_tool": false,
  "tags": {
    "function": ["对话", "文本生成"],
    "scenario": ["个人使用"],
    "attribute": ["免费", "中文支持"],
    "tech": ["GPT-4"],
    "quality": ["推荐"]
  }
}
```

## 注意事项

- 文件名建议使用工具名的英文小写加连字符，如 `chat-gpt.json`
- 一个文件对应一个工具，不要在同一个文件中放多个工具
- `url` 字段用于去重，请确保填写工具的正式官网地址
- 手动添加工具的健康度默认为 `active`
