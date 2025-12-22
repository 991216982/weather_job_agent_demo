# 天气查询与职业规划智能聊天助手

一个使用 Python 与最新 OpenAI Python SDK 构建的简单智能代理（Agent）。
该代理通过终端聊天界面与用户交互，具备两项核心能力：
- 实时天气查询（使用 Open-Meteo 免费 API）
- 收集信息并生成简短的职业规划报告

所有回复均以流式（streaming）方式输出，提高交互体验。

## 环境与依赖

- Python 3.9+（推荐）
- 依赖见 `requirements.txt`

```bash
pip install -r requirements.txt
```

## 配置说明

本项目使用 OpenAI Python SDK 与兼容的服务进行交互。你可以：
- 使用官方 OpenAI：设置 `OPENAI_API_KEY` 即可
- 使用兼容的第三方（如 DeepSeek、Qwen 的 OpenAI 兼容端点）：需额外设置 `OPENAI_BASE_URL`

环境变量：
- `OPENAI_API_KEY`：你的 API Key（必需，否则职业规划报告不可用）
- `OPENAI_BASE_URL`：可选；默认 `https://api.openai.com/v1`
- `OPENAI_MODEL`：可选；默认 `gpt-4.1-mini`

Windows PowerShell 示例：
```powershell
$env:OPENAI_API_KEY="your_key_here"
# 如果使用第三方兼容端点：
# $env:OPENAI_BASE_URL="https://api.deepseek.com/v1"
# 自定义模型（可选）：
# $env:OPENAI_MODEL="gpt-4o-mini"
```

## 运行方式

```bash
python cli.py
```

启动后可在终端中直接对话：
- 查询天气示例：`北京天气`、`查询上海天气`
- 开始职业规划：输入 `职业规划` 或 `规划报告`
- 退出程序：`exit` 或 `quit`

## 功能演示

### 天气查询

输入：
```
北京天气
```
流式输出示例（内容会逐字/逐句出现）：
```
北京 当前天气：
- 温度：2.3℃
- 天气：多云
- 观测时间：2025-12-22T10:00
```

### 职业规划报告

1) 触发流程：
```
职业规划
```
2) 代理依次提问并流式输出：
```
好的，我们先来做一个简短的职业规划。请告诉我你的兴趣方向……
```
用户回答兴趣、技能、目标后，代理调用 OpenAI Responses API，以流式方式生成简短报告：
```
职业方向建议：……
关键技能提升：……
近 3 个月行动计划：……
```

### 身份与行为约束

- 代理以“个人助理 / 信息顾问”的身份与用户交流，避免承认自己是 AI 或语言模型。
- 约束通过系统提示在服务端设置，程序不会向用户公开该提示词。

## 实现思路

- 使用 `OpenAI` Python SDK 的 `Responses API` 实现真正的服务器端流式输出。
- 天气查询使用 Open-Meteo：先地理编码，再获取当前天气；将 `weather_code` 映射为中文描述。
- 职业规划采用简单状态机：依次收集兴趣、技能、目标，随后调用模型生成报告。
- 终端界面通过逐块写入与刷新实现本地文本的流式效果，保证所有回复均为流式。

## 目录结构

```
.
├── cli.py                 # 终端聊天入口（流式输出）
├── agent.py               # 职业规划流程、通用回复与 OpenAI 流式集成
├── weather_service.py     # 城市地理编码与实时天气获取（Open-Meteo）
├── requirements.txt       # 依赖列表
└── README.md              # 说明文档
```

## 参考与声明

- 天气数据来源：Open-Meteo (https://open-meteo.com/)
- 本项目不使用 LangChain 相关包。
- 若未设置 `OPENAI_API_KEY`：职业规划报告功能不可用，但天气查询仍可使用。

## 示例对话（含约束）

```
> 职业规划
好的，我们先来做一个简短的职业规划……
> 我对数据分析感兴趣
了解了。接下来，请简要说明你目前具备的技能……
> 会 Python 和 SQL，做过可视化
很好。最后，请告诉我你的职业目标……
> 想成为数据分析师
（流式生成职业规划报告）
```

```
> 你是什么身份？
我是你的个人助理与信息顾问，随时为你提供帮助。
```

