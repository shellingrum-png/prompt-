# Mock 数据生成流程文档

## 概述
从 Supabase 拉取候选人数据，与本地 Excel 对话数据关联，按 session 聚合后生成带 Mock 岗位信息的 input 列。

## 数据流向
```
Supabase candidate_talent 表
    ↓ (external_userid)
本地 Excel 对话数据 (线上 skill 框架对话数据 -5.19.xlsx)
    ↓ (按 session_id 聚合)
生成 output Excel (每个 session 一条记录)
```

## 环境准备

### 1. 安装依赖
```bash
pip3 install --break-system-packages supabase openpyxl pandas
```

### 2. 配置 Supabase 环境变量
```bash
export SUPABASE_URL="https://bjscrgkjxeqyrvcehikw.supabase.co"
export SUPABASE_KEY="your-service-role-key"
```

## 核心脚本
**路径**: `scripts/generate_from_supabase.py`

## 运行命令

### 基础运行
```bash
python scripts/generate_from_supabase.py
```

### 带参数运行
```bash
# 启用 Mock 岗位数据 + 打印前 3 条样例
python scripts/generate_from_supabase.py --use-mock-jobs --show-sample

# 自定义输出路径
python scripts/generate_from_supabase.py --output results/my_custom_output.xlsx
```

## 处理逻辑详解

### Step 1: 读取本地 Excel
- **文件**: `/Users/a58/Downloads/app/线上skill 框架对话数据 -5.19.xlsx`
- **原始数据**: 1028 条对话记录
- **关键列**: `session_id`, `user_message`, `assistant_message`, `event_time`

### Step 2: 按 session_id 聚合
- 将同一个 `session_id` 的多条对话记录合并为一条
- 聚合后: 109 个 session
- 保留字段:
  - `session_id`
  - `dialogue_count` (对话轮数)
  - `dt`, `source`, `identity_key`, `user_id`

### Step 3: 从 Supabase 关联数据
- **表**: `candidate_talent`
- **关联键**: `Excel.session_id == Supabase.external_userid`
- **关联成功率**: 109/109 (100%)

**提取的数据**:
- `candidate_tags` (候选人标签)
- `ext_fields` (扩展字段，包含年龄、性别、求职意向等)
- `name` (候选人姓名)

### Step 4: 生成 Input 列

#### 模板格式
```text
# Inputs
- 候选人优势与特征标签：{candidate_tags}
- 目标岗位信息与核心要求：{target_job_info}
- 最近 5 轮聊天记录：{latest_dialogue}
*注：你需要从最新对话记录中，精准提炼出求职者目前最纠结、最顾虑的核心阻碍点。*
```

#### 字段生成规则

**1. candidate_tags (候选人标签)**
- 来源: Supabase `candidate_tags` 字段
- 格式: `key: value` 多行展示
- 空值处理: 标记为"待分析"

**2. target_job_info (目标岗位信息)**
- 优先级:
  1. 数据库 `ext_fields` 中的 `job_preference` / `looking_for`
  2. 启用 `--use-mock-jobs` 时，使用模拟数据
- 模拟数据特征:
  - 岗位池: 12 种岗位 (服务员、普工、保洁、搬运工等)
  - 匹配度分布: 匹配 (55%) / 部分匹配 (20%) / 不匹配 (25%)
  - 从对话中提取城市/岗位关键词进行智能匹配

**3. latest_dialogue (最近 5 轮聊天记录)**
- 来源: 该 session 的所有对话记录
- 格式:
  ```
  求职者：{user_message}
  AI: {assistant_message}
  求职者：{user_message}
  AI: {assistant_message}
  ...
  ```
- 取最近 5 轮 (10 条消息)

## 输出结果

### 文件位置
`results/generated_input_YYYYMMDD_HHMM.xlsx`

### 输出结构 (109 条记录)
| 字段名 | 说明 |
|--------|------|
| session_id | 会话 ID |
| dt | 日期 |
| source | 来源 |
| identity_key | 身份标识 |
| user_id | 用户 ID |
| dialogue_count | 对话轮数 |
| external_userid | 外部用户 ID |
| candidate_name | 候选人姓名 |
| **input** | **生成的完整提示词输入** |

## 注意事项

1. **随机种子**: 脚本设置了 `random.seed(42)` 保证可复现
2. **关联键**: 必须确保 Excel 的 `session_id` 与 Supabase 的 `external_userid` 完全匹配
3. **Mock 数据**: `--use-mock-jobs` 参数会覆盖数据库中的岗位信息
4. **对话轮数**: 少于 5 轮的 session 会使用全部可用对话

## 常见问题

### Q: 关联失败怎么办？
A: 检查 Excel 的 `session_id` 格式是否与 Supabase 的 `external_userid` 一致

### Q: 如何调整 Mock 岗位的匹配比例？
A: 修改脚本中的 `MOCK_JOBS` 列表和 `match_level` 分布逻辑

### Q: 输出文件在哪里？
A: 默认在 `results/` 目录下，带时间戳命名
