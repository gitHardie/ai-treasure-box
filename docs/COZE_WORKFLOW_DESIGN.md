# Coze 工作流设计方案 - AI工具分析

本文档描述 AI百宝箱 项目中用于独立分析 AI 工具的 Coze 工作流设计方案。

## 1. 工作流概览

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  采集数据    │ ──→ │  输入JSON    │ ──→ │  Coze工作流   │ ──→ │  分析结果    │
│  (collector) │     │  构建Prompt  │     │  AI独立分析   │     │  JSON输出    │
└─────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
```

### 设计原则

- **不盲信源头描述**：AI 必须基于多信号（URL、Stars、许可证、关键词）独立判断
- **五维标签生成**：function / scenario / attribute / tech / quality
- **许可识别**：准确判断 open-source / freemium / free / paid / source-available
- **分类映射**：映射到一级 + 二级分类体系
- **置信度评估**：给出分析结果的置信度，低置信度结果需人工复核

## 2. 输入参数

工作流接收单个输入参数 `input`，为 JSON 字符串格式的待分析工具信息：

```json
{
  "input": "工具信息JSON字符串"
}
```

工具信息 JSON 结构：

```json
{
  "name": "工具名称",
  "source": "数据来源ID（如 github-trending, aishenqi）",
  "url": "工具官网或仓库URL",
  "description": "英文描述",
  "description_zh": "中文描述",
  "raw_data": {
    "stargazers_count": 12345,
    "license": "MIT",
    "pushed_at": "2025-01-15T10:30:00Z",
    "language": "Python",
    "topics": ["ai", "llm", "agent"],
    "has_license": true
  }
}
```

### 关键字段说明

| 字段 | 说明 | 分析用途 |
|------|------|----------|
| `name` | 工具名称 | 品牌识别、分类参考 |
| `source` | 数据来源 | 判断工具属性和许可倾向 |
| `url` | 官网/仓库URL | 判断是否为国内工具、域名特征 |
| `description` | 原始英文描述 | 功能理解（但不可直接照搬） |
| `raw_data.stargazers_count` | GitHub Stars | 质量和热度评估 |
| `raw_data.license` | 许可证 | 许可等级判定 |
| `raw_data.pushed_at` | 最后推送时间 | 健康度评估 |

## 3. 输出格式

工作流输出为 JSON 字符串，包含以下字段：

```json
{
  "category": "代码开发",
  "subcategory": "代码补全",
  "license_tier": "open-source",
  "license_type": "MIT",
  "tags": {
    "function": ["代码生成", "编程辅助"],
    "scenario": ["个人开发者", "企业团队"],
    "attribute": ["开源", "API服务", "中文支持"],
    "tech": ["GPT-4", "Transformer"],
    "quality": ["热门", "高活跃"]
  },
  "ai_analysis": "这是一个面向开发者的AI编程辅助工具，基于GPT-4提供代码补全和代码审查功能。适合个人开发者和企业团队使用，支持VS Code等主流IDE。",
  "ai_confidence": 0.85,
  "is_china_tool": false,
  "health_status": "active"
}
```

### 输出字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `category` | string | 一级分类，从预定义列表中选择 |
| `subcategory` | string | 二级分类，更精细的功能描述 |
| `license_tier` | string | 许可等级：`open-source` / `freemium` / `free` / `paid` / `source-available` / `unknown` |
| `license_type` | string | 具体许可证名称：MIT / Apache-2.0 / GPL-3.0 等 |
| `tags` | object | 五维标签对象 |
| `tags.function` | string[] | 功能标签：文本生成、图像生成、代码生成、对话、翻译、数据分析等 |
| `tags.scenario` | string[] | 场景标签：个人开发者、企业团队、内容创作、教育学习、学术研究等 |
| `tags.attribute` | string[] | 属性标签：免费、开源、API服务、浏览器插件、中文支持、本地部署等 |
| `tags.tech` | string[] | 技术标签：GPT-4、Claude、Stable Diffusion、RAG、Multi-modal等 |
| `tags.quality` | string[] | 质量标签：热门、口碑好、高活跃、成长中等 |
| `ai_analysis` | string | 2-3句独立分析摘要，说明工具真正做什么、适合谁 |
| `ai_confidence` | float | 置信度 0-1，低于0.5的结果建议人工复核 |
| `is_china_tool` | bool | 是否为国内工具 |
| `health_status` | string | 健康度：`active` / `moderate` / `dormant` / `archived` |

## 4. Prompt 模板

```
请分析以下AI工具，给出独立判断（不要照搬描述）：

工具名称: {name}
来源: {source}
URL: {url}
描述: {description}
中文描述: {description_zh}
Stars: {stargazers_count}
许可证: {license}
最后更新: {pushed_at}

请返回JSON格式：
{
  "category": "一级分类(文本生成/图像创作/代码开发/数据分析/音视频/办公效率/学术研究/开发工具/设计创意/营销推广/教育培训/其他)",
  "subcategory": "二级分类",
  "license_tier": "open-source/freemium/free/paid/source-available/unknown",
  "license_type": "具体许可证如MIT/Apache等",
  "tags": {
    "function": ["功能标签"],
    "scenario": ["场景标签"],
    "attribute": ["属性标签"],
    "tech": ["技术标签"],
    "quality": ["质量标签"]
  },
  "ai_analysis": "2-3句独立分析摘要，说明这个工具真正做什么、适合谁",
  "ai_confidence": 0.8,
  "is_china_tool": false,
  "health_status": "active/moderate/dormant/archived"
}
```

### Prompt 设计要点

1. **强调独立判断**：要求"不要照搬描述"，AI 必须基于多信号综合分析
2. **结构化输出**：严格 JSON 格式，便于程序解析
3. **预定义分类**：一级分类使用固定列表，保证分类一致性
4. **多维评估**：不仅评估功能，还评估许可、健康度、国内属性等
5. **置信度要求**：强制输出置信度，便于下游过滤低质量结果

## 5. 一级分类体系

| 一级分类 | 典型关键词 | 二级分类示例 |
|---------|-----------|-------------|
| 文本生成 | chat, gpt, writing, 翻译, 文案 | 聊天助手、文案写作、翻译、摘要提取、AI Agent |
| 图像创作 | image, draw, paint, midjourney | 图像生成、图像编辑、图像抠图、图像增强 |
| 代码开发 | code, developer, ide, api, sdk | 代码补全、代码审查、调试工具、开发辅助 |
| 数据分析 | data, analytics, visualization, 图表 | 数据可视化、数据采集、数据处理 |
| 音视频 | audio, video, music, speech, whisper | 语音识别、语音合成、视频生成 |
| 办公效率 | office, document, email, 笔记, 日程 | 邮件工具、笔记工具、日程管理、文档处理 |
| 学术研究 | research, 论文, paper, arxiv | 论文工具、数据资源、模型研究 |
| 开发工具 | deploy, docker, kubernetes, devops | 部署工具、监控运维、CI/CD |
| 设计创意 | design, ui, figma, creative | UI设计、Logo设计、品牌设计 |
| 营销推广 | marketing, seo, social, ads | SEO优化、社媒营销、内容营销 |
| 教育培训 | education, learn, 课程, tutor | 在线学习、智能辅导、考试测评 |
| 其他 | - | 未分类 |

## 6. 配置工作流 ID 到 GitHub Secret

### 步骤

1. **在 Coze 平台创建工作流**
   - 登录 [Coze](https://www.coze.cn) → 工作空间 → 工作流
   - 创建新工作流，添加「代码节点」或「大模型节点」
   - 输入参数设置为 `input`（string 类型）
   - 输出为分析结果 JSON 字符串
   - 发布工作流并记录 `workflow_id`

2. **配置 GitHub Secret**
   - 进入仓库 `Settings` → `Secrets and variables` → `Actions`
   - 添加以下 Secret：

   | Secret 名称 | 值 | 说明 |
   |-------------|-----|------|
   | `AI_BOX_COZE` | Coze API Key | Coze 平台的 API 密钥 |
   | `COZE_WORKFLOW_ID` | 工作流ID | AI分析工作流的 ID |

3. **在 CI/CD 中使用**

   ```yaml
   # .github/workflows/daily-pipeline.yml
   - name: Run AI Analysis
     env:
       AI_BOX_COZE: ${{ secrets.AI_BOX_COZE }}
       COZE_WORKFLOW_ID: ${{ secrets.COZE_WORKFLOW_ID }}
     run: |
       python scripts/main.py analyze
   ```

4. **本地开发使用**

   ```bash
   export AI_BOX_COZE="your_coze_api_key"
   export COZE_WORKFLOW_ID="your_workflow_id"
   python scripts/main.py analyze
   ```

## 7. 降级策略

当 Coze 工作流不可用时（API Key 未配置、网络超时、返回错误），系统自动降级到本地规则分析：

```
Coze API 调用 → 成功 → 返回AI分析结果 (confidence: 0.8+)
                ↓ 失败
本地规则分析 → 返回规则匹配结果 (confidence: 0.6)
```

本地分析特点：
- 基于关键词匹配和规则推断
- 不依赖外部 API，零成本
- 置信度固定为 0.6（低于 AI 分析）
- 适合大批量初步分类，后续可用 AI 分析覆盖

## 8. 分析结果合并

分析结果会写回到采集数据中，合并逻辑：

```python
# 原始工具数据
tool = {"name": "xxx", "description": "...", "raw_data": {...}}

# 分析结果
analysis = analyzer.analyze_tool(tool)

# 合并后的数据
tool["category"] = analysis["category"]
tool["subcategory"] = analysis["subcategory"]
tool["license_tier"] = analysis["license_tier"]
tool["license_type"] = analysis["license_type"]
tool["tags"] = analysis["tags"]
tool["ai_analysis"] = analysis["ai_analysis"]
tool["ai_confidence"] = analysis["ai_confidence"]
tool["is_china_tool"] = analysis["is_china_tool"]
tool["health_status"] = analysis["health_status"]
tool["analyzed_at"] = "2025-01-15T10:30:00Z"
```

## 9. 质量保障

### 置信度阈值

| 置信度范围 | 处理方式 |
|-----------|---------|
| >= 0.8 | 直接使用，高质量 |
| 0.6 - 0.8 | 使用但标记为"待验证" |
| < 0.6 | 人工复核后再使用 |

### 持续优化

- 定期对比 AI 分析结果与人工审核结果
- 根据反馈调整 Prompt 模板中的关键词权重
- 扩展二级分类体系，提升分类精度
- 积累标注数据，训练分类模型替代规则匹配
