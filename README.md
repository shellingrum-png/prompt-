# 🚀 批量提示词测试系统

> 注意：以下所有命令默认在**项目根目录**下执行

一个功能完整的批量提示词测试工具，支持文件上传、在线配置、批量API调用、结果自动下载。

## ✨ 功能特性

- 📤 **文件上传**：支持 Excel (.xlsx, .xls) 和 CSV 格式
- ⚙️ **在线配置**：可视化配置 API Key、BaseURL、模型参数
- 📝 **提示词管理**：在线编辑和保存 System Prompt
- 🎯 **批量执行**：自动批量调用大模型API，支持限流间隔
- 📊 **实时进度**：实时显示任务进度和执行日志
- 💾 **结果下载**：自动生成带处理结果的Excel文件

---

## 📋 目录结构

```
batch_test_system/
├── server_simple.py          # Web服务主程序（推荐使用）
├── README.md                 # 本说明文档
├── config/                   # 配置文件目录（自动生成）
│   ├── api_config.json       # API配置
│   └── prompts_config.json   # 提示词配置
├── data/
│   └── uploads/              # 上传的文件存放目录
└── results/                  # 处理结果输出目录
```

---

## 🚀 快速开始

### 1. 启动服务

如果你是刚从GitHub克隆下来：
```bash
# 先进入项目目录
cd prompt-
python3 server_simple.py
```

如果你已经在项目目录里，直接运行：
```bash
python3 server_simple.py
```

### 2. 打开浏览器

访问：`http://localhost:18080`

---

## 📖 使用流程

### 第一步：配置模型

1. 点击「⚙️ 模型配置」标签页
2. 填写以下信息：
   - **API Key**：你的API密钥
   - **Base URL**：API接口地址（必须以 `/v3` 结尾）
   - **模型名称**：模型ID或接入点ID
   - **温度**：0-2之间的数值（越小越准确，越大越有创造力）
3. 点击「💾 保存配置」

### 第二步：配置提示词

1. 点击「📝 提示词配置」标签页
2. 在「提示词A」或「提示词B」中填写你的 System Prompt
3. 点击「💾 保存提示词」

### 第三步：上传数据

1. 点击「📤 上传数据」标签页
2. 点击或拖拽上传你的Excel文件
3. 确认上传成功（显示行数和列名）

### 第四步：执行任务

1. 点击「🎯 执行任务」标签页
2. 选择以下参数：
   - **数据文件**：选择你上传的Excel文件
   - **输入列名**：选择要批量处理的文本列
   - **提示词类型**：选择使用提示词A还是B
   - **测试数量**：处理前N条（0=全部处理）
3. 点击「🚀 开始执行」
4. 查看实时进度和日志

### 第五步：下载结果

任务完成后，点击「下载结果」链接，获取包含模型输出的Excel文件。

---

## 🔧 配置说明

### 兼容的API平台

本系统兼容 OpenAI 格式的API接口，支持以下平台：

| 平台 | Base URL 示例 | 模型名称格式 |
|------|-------------|------------|
| **火山引擎 Ark** | `https://ark.cn-beijing.volces.com/api/v3` | `ep-2025xxxxxx` |
| **豆包 Coding Plan** | `https://ark.cn-beijing.volces.com/api/coding/v3` | `Doubao-Seed-2.0-pro` |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-3.5-turbo` |
| **通义千问** | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` |
| **智谱AI** | `https://open.bigmodel.cn/api/paas/v4` | `glm-4` |

### 配置文件说明

配置会自动保存到 `config/` 目录下：

#### `api_config.json`
```json
{
  "openai": {
    "api_key": "你的API Key",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "ep-20250602xxxxxx",
    "temperature": 0.7
  }
}
```

#### `prompts_config.json`
```json
{
  "prompt_a": {
    "name": "提示词A",
    "system_prompt": "你的System Prompt内容"
  },
  "prompt_b": {
    "name": "提示词B",
    "system_prompt": "你的System Prompt内容"
  }
}
```

---

## 📊 Excel数据格式要求

| 要求 | 说明 |
|------|------|
| **必须有一列文本** | 这一列的内容会作为 User Input 发给模型 |
| **其他列原样保留** | 处理结果会新增列追加，原数据不会丢失 |

### 示例：

| session_id | 姓名 | 待处理文本（任意列名） | 其他字段 |
|-----------|------|---------------------|---------|
| 001 | 张三 | 这是第一条要处理的内容... | 其他数据 |
| 002 | 李四 | 这是第二条要处理的内容... | 其他数据 |

### 输出结果：

| session_id | 姓名 | 待处理文本 | 其他字段 | index | input | output | system_prompt | success |
|-----------|------|----------|---------|-------|-------|--------|--------------|---------|
| （原数据） | （原数据） | （原数据） | （原数据） | 0 | 输入内容 | 模型输出... | 提示词... | True |

---

## 🛠️ 代码说明

### 核心架构

```
server_simple.py
├── WebHandler 类                  # HTTP请求处理器
│   ├── do_GET()                   # 处理GET请求
│   ├── do_POST()                  # 处理POST请求
│   ├── handle_get_config()        # 读取配置
│   ├── handle_save_config()       # 保存配置
│   ├── handle_upload()            # 处理文件上传
│   ├── handle_run_task()          # 启动任务
│   ├── run_task_bg()              # 后台执行任务（核心）
│   ├── handle_list_tasks()        # 任务列表
│   ├── handle_get_task()          # 任务详情
│   └── handle_download()          # 下载结果
└── main()                         # 启动服务
```

### 核心执行流程

```
用户点击开始执行
    ↓
创建任务ID，状态设为 running
    ↓
启动后台线程 run_task_bg()
    ↓
读取API配置和提示词配置
    ↓
读取Excel文件，根据limit截取
    ↓
循环每一行：
    ├─ 提取输入列内容
    ├─ 调用API：System Prompt + User Input
    ├─ 保存返回结果
    └─ 更新任务进度
    ↓
所有行处理完成，生成结果Excel
    ↓
任务状态设为 completed，提供下载链接
```

### API调用逻辑

```python
# 构建请求
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

data = {
    'model': model,
    'messages': [
        {'role': 'system', 'content': system_prompt},  # 你配置的提示词
        {'role': 'user', 'content': input_text}         # Excel里的内容
    ],
    'temperature': temperature
}

# 发送请求
response = requests.post(f'{base_url}/chat/completions', 
                         headers=headers, json=data)
```

---

## 🔍 常见问题

### Q: 为什么输出还是模拟数据？
A: 请确保：
1. 重启了服务（按Ctrl+C后重新运行）
2. 在页面保存了提示词配置
3. API Key和BaseURL配置正确

### Q: API调用失败怎么办？
A: 检查：
1. API Key是否正确
2. BaseURL是否以 `/v3` 结尾
3. 模型名称是否正确（注意平台差异）
4. 网络是否能访问该API

### Q: 如何调整调用速度？
A: 在启动任务时，修改 `delay` 参数（秒），默认0.5秒，可设置更大值避免限流。

### Q: 处理大文件会崩溃吗？
A: 建议先用小批量测试（测试数量设为3-5条），确认配置正确后再全量处理。

---

## 📝 更新日志

### v1.0.0
- ✅ 完整的Web界面，支持5个功能标签页
- ✅ 在线配置API参数和提示词
- ✅ Excel/CSV文件上传
- ✅ 批量API调用，实时进度显示
- ✅ 结果Excel下载
- ✅ 兼容所有OpenAI格式的API

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 PR！
