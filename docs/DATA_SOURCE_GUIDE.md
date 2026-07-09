# 数据源管理指南

> AI百宝箱采用配置化数据源架构，新增数据源无需修改核心代码。

## 目录

- [如何添加新数据源](#如何添加新数据源)
- [配置文件字段说明](#配置文件字段说明)
- [手动添加工具](#手动添加工具)
- [一级分类体系](#一级分类体系)
- [许可/定价维度](#许可定价维度)
- [健康度机制](#健康度机制)

---

## 如何添加新数据源

添加新数据源只需 **3 步**：

### 第 1 步：编写配置

在 `config/sources.yaml` 的 `sources` 列表中添加一个新的源块：

```yaml
- id: my-new-source          # 唯一标识（英文，不可重复）
  name: My New Source         # 显示名称
  type: web                   # api / rss / web / manual
  tier: 2                     # 优先级 1-3（1最高）
  url: "https://example.com"  # 数据源地址
  schedule: "0 3 * * *"       # cron 表达式
  enabled: true
  parser: my_parser.py        # 采集器文件名
  category: "其他"            # 映射到的一级分类
  is_china_source: false      # 是否国内数据源
  auto_detect_license: false  # 是否自动检测许可类型
  ai_analysis: true           # 是否需要AI深度分析
  description: "描述信息"
```

**提示**：直接复制已有的 source 块进行修改是最快的方式。

### 第 2 步：编写采集器

在 `scripts/parsers/` 目录下创建对应的 Python 采集器文件（如 `my_parser.py`）。

采集器需要实现以下接口：

```python
def parse(config: dict) -> list[dict]:
    """
    从数据源抓取并解析工具数据
    
    Args:
        config: 该源的配置信息（来自 sources.yaml）
    
    Returns:
        工具列表，每个工具为一个字典，包含：
        - name: 工具名称
        - url: 工具地址
        - description: 英文描述
        - description_zh: 中文描述（可选，AI会自动翻译）
        - category: 一级分类
        - subcategory: 二级分类（可选）
        - tags: 标签字典（可选）
    """
    ...
```

### 第 3 步：测试验证

```bash
# 测试单个数据源的采集
python scripts/pipeline.py --source my-new-source --dry-run

# 检查采集结果
cat data/raw/my-new-source_*.json
```

确认数据格式正确后，设置 `enabled: true` 即可正式启用。

---

## 配置文件字段说明

配置文件位于 `config/sources.yaml`，包含两部分：`sources`（数据源列表）和 `global`（全局配置）。

### 数据源字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 唯一标识，英文，不可重复 |
| `name` | string | ✅ | 显示名称 |
| `type` | string | ✅ | 数据源类型：`api` / `rss` / `web` / `manual` |
| `tier` | int | ✅ | 优先级 1-3（1 最高），0 用于手动添加 |
| `url` | string | 条件 | 数据源地址（`manual` 类型可省略） |
| `schedule` | string | ✅ | cron 表达式，`manual` 类型填 `"manual"` |
| `enabled` | bool | ✅ | 是否启用 |
| `parser` | string | ✅ | 采集器文件名 |
| `category` | string | ✅ | 映射到的一级分类（见下方分类体系） |
| `is_china_source` | bool | ✅ | 是否国内数据源 |
| `auto_detect_license` | bool | ✅ | 是否自动检测许可类型 |
| `ai_analysis` | bool | ✅ | 是否需要 AI 深度分析 |
| `description` | string | 推荐 | 数据源描述 |
| `params` | dict | 可选 | 传给采集器的额外参数 |
| `tags_source` | list | 可选 | 指定从哪些字段提取标签 |

### 全局配置字段

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `retry_times` | 请求失败重试次数 | 3 |
| `retry_delay` | 重试间隔（秒） | 30 |
| `request_timeout` | 请求超时（秒） | 30 |
| `user_agent` | HTTP User-Agent | AI-Treasure-Box/1.0 |
| `rate_limit.requests_per_minute` | 每分钟最大请求数 | 10 |
| `dedup.strategy` | 去重策略 | url+title |
| `dedup.similarity_threshold` | 相似度阈值 | 0.85 |
| `ai_analysis.enabled` | 是否启用 AI 分析 | true |
| `ai_analysis.batch_size` | AI 分析批次大小 | 20 |
| `ai_analysis.confidence_threshold` | 置信度阈值 | 0.7 |

---

## 手动添加工具

不需要写采集器，直接在 `data/manual/` 目录下放置 JSON 文件即可。

### 操作步骤

1. 在 `data/manual/` 下创建一个新的 JSON 文件（如 `my_tool.json`）
2. 按照规定的 JSON 格式填写工具信息
3. 运行 `python scripts/pipeline.py --source manual-tools` 导入

### JSON 格式

详见 [data/manual/README.md](../data/manual/README.md) 中的模板和规范说明。

---

## 一级分类体系

所有工具按以下 12 个一级分类组织：

| 分类 | 说明 | 典型工具 |
|------|------|----------|
| **文本生成** | 文本写作、聊天助手、翻译、摘要等 | ChatGPT、Claude、Notion AI |
| **图像创作** | 图片生成、编辑、风格迁移等 | Midjourney、DALL-E、Stable Diffusion |
| **代码开发** | 代码生成、补全、调试、Code Review | Copilot、Cursor、Codeium |
| **数据分析** | 数据处理、可视化、BI、表格分析 | Julius AI、Rows、Hex |
| **音视频** | 语音合成、视频生成、音乐创作、转写 | ElevenLabs、Runway、Suno |
| **办公效率** | 文档、PPT、邮件、日程、项目管理 | Gamma、Tome、Reclaim AI |
| **学术研究** | 论文辅助、文献管理、实验分析 | Elicit、Consensus、Scite |
| **开发工具** | API 平台、模型部署、向量数据库、MLOps | Replicate、Pinecone、Weights & Biases |
| **设计创意** | UI/UX 设计、Logo、品牌、原型 | Figma AI、Uizard、Framer |
| **营销推广** | 文案生成、SEO、社媒管理、广告投放 | Jasper、Surfer SEO、Copy.ai |
| **教育培训** | 在线学习、辅导、语言学习、考试 | Duolingo、Khanmigo、Quizlet |
| **其他** | 不属于以上分类的工具 | — |

### 分类映射规则

- 每个数据源通过 `category` 字段指定其采集工具的主分类
- 采集器内部可为每个工具单独指定更精确的 `category` 和 `subcategory`
- AI 分析阶段会根据工具描述自动校验和修正分类

---

## 许可/定价维度

工具按许可和定价分为 5 个等级：

| 等级 | 标识 | 含义 | 示例 |
|------|------|------|------|
| **开源** | `open-source` | 完全开源，可自由使用、修改和分发 | Stable Diffusion、LLaMA、Ollama |
| **免费** | `free` | 免费使用，但代码不公开 | ChatGPT（网页版）、Google Bard |
| **免费增值** | `freemium` | 基础功能免费，高级功能付费 | Midjourney、Notion AI、Jasper |
| **付费** | `paid` | 需要付费才能使用 | GPT-4 API、Claude Pro |
| **源代码可见** | `source-available` | 源代码可查看，但许可限制商用 | Cohere、部分 Meta 模型 |

### 自动检测机制

- 当数据源的 `auto_detect_license: true` 时，采集器会自动分析工具页面，识别许可类型
- 对于无法自动检测的源，可通过手动标注或 AI 分析确定许可等级
- 许可信息存储在工具数据的 `license_tier` 字段中

---

## 健康度机制

每个工具的健康度反映其维护状态和活跃度：

| 状态 | 标识 | 判断标准 | 处理策略 |
|------|------|----------|----------|
| **活跃** | `active` | 近 30 天有更新/发布 | 正常展示，优先推荐 |
| **一般** | `moderate` | 30-90 天无更新 | 正常展示，降低推荐权重 |
| **休眠** | `dormant` | 90-180 天无更新 | 标注提醒，大幅降低权重 |
| **归档** | `archived` | 180+ 天无更新或已关停 | 移至归档区，不参与推荐 |

### 健康度评估维度

1. **代码仓库活跃度**：最近 commit 时间、issue 响应速度
2. **产品更新频率**：官方更新日志、版本发布间隔
3. **社区讨论热度**：社交媒体提及量、论坛讨论数
4. **网站可访问性**：官网是否正常响应

### 自动降级机制

- 系统每次采集时会检查工具的健康指标
- 连续 2 次检测到无更新 → 自动降级一级（active → moderate）
- 网站连续 3 次不可访问 → 直接标记为 archived
- 手动添加工具的初始健康度为 `active`
