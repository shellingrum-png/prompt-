#!/usr/bin/env python3
"""
批量提示词测试系统 - Web后端服务
支持：文件上传、在线配置、在线执行、结果查看
"""
import os
import sys
import json
import time
import uuid
import pandas as pd
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import cgi
import io

# 配置目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')

# 确保目录存在
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# 全局任务状态
tasks = {}

# 默认配置
DEFAULT_API_CONFIG = {
    'openai': {
        'api_key': '9f485a0c-c4ea-4590-9f07-6d6925e04620',
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': 'ep-20250619152516-v97g5',
        'temperature': 0.7,
        'max_tokens': 2000
    },
    'evaluation': {
        'api_key': '9f485a0c-c4ea-4590-9f07-6d6925e04620',
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': 'ep-20250619152516-v97g5',
        'temperature': 0.3
    }
}

DEFAULT_PROMPT_CONFIG = {
    'prompt_a': {
        'name': '数据格式化引擎',
        'system_prompt': '''你是一个数据格式化引擎。请严格执行以下逻辑步骤，不要执行任何其他任务：
Step 1: 检查输入文本，提取 [候选人姓名]、[职位]、[当前系统状态]。
Step 2: 检查输入文本中的对话记录。
Step 3: 将提取的信息按以下模板输出，不允许添加任何其他字符：
<candidate_context>
候选人姓名: {姓名}
目标职位: {职位}
当前系统记录状态 (current_status): {状态}
</candidate_context>
<dialogue>
{对话内容}
</dialogue>
约束：
如果没有对话记录，则在 <dialogue> 下方强制输出：[无对话记录]。
严禁进行自我分析、结论总结或任何【思考】。
必须输出 <dialogue> 标签，即使内容为空。'''
    },
    'prompt_b': {
        'name': '招聘数据模拟专家',
        'system_prompt': '''# Role
你是一个资深招聘数据模拟专家，负责为招聘系统的模型测试构建高质量的输入案例。

# Task
根据我指定的行业，生成一组符合测试要求的输入数据，要求逻辑闭环。

# Output Format
请严格按照以下 JSON 格式输出，不要包含任何额外说明。'''
    },
    'evaluation_prompt': {
        'name': '结果质量评估',
        'system_prompt': '''你是一个专业的AI输出质量评估师。请对以下生成结果进行评估，从三个维度打分（每个维度0-10分）：

1. 准确性（Accuracy）：结果是否符合输入要求？信息是否准确无误？
2. 可读性（Readability）：结果格式是否清晰？语言是否通顺易读？
3. 完整性（Completeness）：是否包含了所有要求的内容？是否有遗漏？

请按以下JSON格式输出，不要包含任何额外内容：
{
  "accuracy_score": 分数,
  "accuracy_reason": "准确性评分理由",
  "readability_score": 分数,
  "readability_reason": "可读性评分理由",
  "completeness_score": 分数,
  "completeness_reason": "完整性评分理由",
  "overall_score": 总分(平均分),
  "suggestions": "改进建议"
}'''
    }
}

# 简单的API调用函数
def call_api(system_prompt, user_content, api_config):
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {api_config["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': api_config['model'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_content}
            ],
            'temperature': api_config.get('temperature', 0.7),
            'max_tokens': api_config.get('max_tokens', 2000)
        }
        
        response = requests.post(
            f'{api_config["base_url"].rstrip("/")}/chat/completions',
            headers=headers,
            json=data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return f"ERROR: API返回 {response.status_code} - {response.text}"
    except ImportError:
        return f"模拟结果 (未安装requests库) - 输入长度: {len(user_content)}"
    except Exception as e:
        return f"ERROR: {str(e)}"

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 禁用默认日志
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_html(self, html, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def do_GET(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            
            if path == '/' or path == '/index.html':
                self.send_html(self.get_index_page())
            elif path == '/api/config':
                self.handle_get_config()
            elif path == '/api/files':
                self.handle_list_files()
            elif path == '/api/tasks':
                self.handle_list_tasks()
            elif path.startswith('/api/tasks/'):
                task_id = path.split('/')[-1]
                self.handle_get_task(task_id)
            elif path == '/api/download':
                self.handle_download(parsed.query)
            else:
                self.send_json({'error': 'Not Found'}, 404)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def do_POST(self):
        try:
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            
            if path == '/api/config':
                self.handle_save_config()
            elif path == '/api/upload':
                self.handle_upload()
            elif path == '/api/run':
                self.handle_run_task()
            else:
                self.send_json({'error': 'Not Found'}, 404)
        except Exception as e:
            self.send_json({'error': str(e)}, 500)
    
    def handle_get_config(self):
        """获取配置"""
        api_config_path = os.path.join(CONFIG_DIR, 'api_config.json')
        prompt_config_path = os.path.join(CONFIG_DIR, 'prompts_config.json')
        
        if os.path.exists(api_config_path):
            with open(api_config_path, 'r', encoding='utf-8') as f:
                api_config = json.load(f)
        else:
            api_config = DEFAULT_API_CONFIG
        
        if os.path.exists(prompt_config_path):
            with open(prompt_config_path, 'r', encoding='utf-8') as f:
                prompt_config = json.load(f)
        else:
            prompt_config = DEFAULT_PROMPT_CONFIG
        
        self.send_json({'api': api_config, 'prompts': prompt_config})
    
    def handle_save_config(self):
        """保存配置"""
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        config_data = json.loads(body)
        
        if 'api' in config_data:
            api_config_path = os.path.join(CONFIG_DIR, 'api_config.json')
            with open(api_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data['api'], f, ensure_ascii=False, indent=2)
        
        if 'prompts' in config_data:
            prompt_config_path = os.path.join(CONFIG_DIR, 'prompts_config.json')
            with open(prompt_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data['prompts'], f, ensure_ascii=False, indent=2)
        
        self.send_json({'success': True, 'message': '配置已保存'})
    
    def handle_list_files(self):
        """列出已上传的文件"""
        files = []
        for f in os.listdir(UPLOADS_DIR):
            if f.endswith(('.xlsx', '.xls', '.csv')):
                filepath = os.path.join(UPLOADS_DIR, f)
                stat = os.stat(filepath)
                files.append({
                    'name': f,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        preview = {}
        if files:
            try:
                first_file = os.path.join(UPLOADS_DIR, files[0]['name'])
                df = pd.read_excel(first_file) if files[0]['name'].endswith(('.xlsx', '.xls')) else pd.read_csv(first_file)
                preview = {
                    'filename': files[0]['name'],
                    'rows': len(df),
                    'columns': df.columns.tolist()
                }
            except:
                pass
        
        self.send_json({'files': files, 'preview': preview})
    
    def handle_upload(self):
        """上传文件"""
        content_type = self.headers['Content-Type']
        if 'multipart/form-data' not in content_type:
            self.send_json({'error': '需要multipart/form-data格式'}, 400)
            return
        
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
        )
        
        if 'file' not in form:
            self.send_json({'error': '没有文件'}, 400)
            return
        
        file_item = form['file']
        if not file_item.filename:
            self.send_json({'error': '没有选择文件'}, 400)
            return
        
        filename = os.path.basename(file_item.filename)
        filepath = os.path.join(UPLOADS_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(file_item.file.read())
        
        try:
            df = pd.read_excel(filepath) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(filepath)
            columns = df.columns.tolist()
            rows = len(df)
        except:
            columns = []
            rows = 0
        
        self.send_json({
            'success': True,
            'filename': filename,
            'columns': columns,
            'rows': rows
        })
    
    def handle_run_task(self):
        """运行任务"""
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        params = json.loads(body)
        
        task_id = str(uuid.uuid4())[:8]
        task = {
            'id': task_id,
            'status': 'running',
            'params': params,
            'progress': 0,
            'total': 0,
            'results': [],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'output_file': None
        }
        tasks[task_id] = task
        
        import threading
        thread = threading.Thread(target=self.run_background_task, args=(task_id, params))
        thread.daemon = True
        thread.start()
        
        self.send_json({'task_id': task_id, 'status': 'running'})
    
    def run_background_task(self, task_id, params):
        """后台执行任务"""
        task = tasks[task_id]
        
        try:
            api_config_path = os.path.join(CONFIG_DIR, 'api_config.json')
            prompt_config_path = os.path.join(CONFIG_DIR, 'prompts_config.json')
            
            with open(api_config_path, 'r', encoding='utf-8') as f:
                api_config = json.load(f)
            
            with open(prompt_config_path, 'r', encoding='utf-8') as f:
                prompt_config = json.load(f)
            
            input_file = os.path.join(UPLOADS_DIR, params['filename'])
            df = pd.read_excel(input_file) if params['filename'].endswith(('.xlsx', '.xls')) else pd.read_csv(input_file)
            
            input_column = params['column']
            prompt_type = params['prompt_type']
            run_mode = params['mode']
            limit = params.get('limit')
            
            if limit and limit < len(df):
                df = df.head(limit)
            
            system_prompt = prompt_config[prompt_type]['system_prompt']
            
            task['total'] = len(df)
            results = []
            
            for idx, row in df.iterrows():
                if task['status'] == 'stopped':
                    break
                
                input_text = str(row[input_column]) if pd.notna(row[input_column]) else ''
                
                output = call_api(system_prompt, input_text, api_config['openai'])
                
                result = {
                    'index': idx,
                    'input': input_text,
                    'output': output,
                    'success': not output.startswith('ERROR:')
                }
                
                if run_mode == 'pipeline' and result['success']:
                    eval_prompt = prompt_config['evaluation_prompt']['system_prompt']
                    eval_input = f"输入：{input_text}\n\n输出：{output}"
                    eval_output = call_api(eval_prompt, eval_input, api_config['evaluation'])
                    
                    try:
                        eval_result = json.loads(eval_output)
                        result.update({f'eval_{k}': v for k, v in eval_result.items()})
                    except:
                        result['eval_raw'] = eval_output
                
                results.append(result)
                task['progress'] = idx + 1
                task['results'] = results[-5:]
                
                time.sleep(params.get('delay', 1.0))
            
            output_filename = f"result_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            output_path = os.path.join(RESULTS_DIR, output_filename)
            
            result_df = pd.DataFrame(results)
            result_df = pd.concat([df.reset_index(drop=True), result_df], axis=1)
            result_df.to_excel(output_path, index=False)
            
            task['output_file'] = output_filename
            task['status'] = 'completed'
            
        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)
    
    def handle_list_tasks(self):
        """列出所有任务"""
        task_list = []
        for tid, task in tasks.items():
            task_list.append({
                'id': tid,
                'status': task['status'],
                'progress': task['progress'],
                'total': task['total'],
                'created_at': task['created_at'],
                'filename': task['params'].get('filename', '')
            })
        self.send_json({'tasks': sorted(task_list, key=lambda x: x['created_at'], reverse=True)})
    
    def handle_get_task(self, task_id):
        """获取任务详情"""
        if task_id in tasks:
            self.send_json(tasks[task_id])
        else:
            self.send_json({'error': '任务不存在'}, 404)
    
    def handle_download(self, query):
        """下载结果文件"""
        params = urllib.parse.parse_qs(query)
        filename = params.get('file', [None])[0]
        
        if not filename:
            self.send_json({'error': '缺少文件名'}, 400)
            return
        
        filepath = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(filepath):
            self.send_json({'error': '文件不存在'}, 404)
            return
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())
    
    def get_index_page(self):
        """返回主页面HTML"""
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>批量提示词测试系统</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: white; text-align: center; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: rgba(255,255,255,0.9); text-align: center; margin-bottom: 30px; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h2 { color: #333; margin-bottom: 16px; font-size: 20px; border-bottom: 2px solid #667eea; 
             padding-bottom: 10px; display: flex; align-items: center; }
        h2 span { margin-right: 10px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; color: #555; }
        input[type="text"], input[type="number"], select, textarea {
            width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;
            font-size: 14px; transition: border-color 0.3s; font-family: inherit;
        }
        input:focus, select:focus, textarea:focus { border-color: #667eea; outline: none; }
        textarea { resize: vertical; min-height: 100px; line-height: 1.6; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               color: white; border: none; padding: 10px 20px; border-radius: 8px;
               font-size: 14px; font-weight: 600; cursor: pointer; transition: transform 0.2s;
               margin-right: 8px; margin-bottom: 8px; }
        .btn:hover { transform: translateY(-2px); }
        .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .btn-secondary { background: #6c757d; }
        .btn-success { background: #28a745; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .tabs { display: flex; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab { padding: 12px 18px; cursor: pointer; border-bottom: 3px solid transparent;
               font-weight: 600; color: #666; transition: all 0.3s; font-size: 14px; }
        .tab.active { color: #667eea; border-bottom-color: #667eea; }
        .tab:hover { color: #667eea; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .status { margin-top: 16px; padding: 12px; border-radius: 8px; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.info { background: #d1ecf1; color: #0c5460; }
        .upload-area { border: 3px dashed #667eea; border-radius: 12px; padding: 40px;
                       text-align: center; cursor: pointer; transition: all 0.3s; }
        .upload-area:hover { background: #f8f9ff; }
        .upload-area.dragover { background: #eef2ff; border-color: #764ba2; }
        .file-item { display: flex; justify-content: space-between; align-items: center;
                     padding: 12px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; }
        .file-info { display: flex; align-items: center; }
        .file-icon { font-size: 24px; margin-right: 12px; }
        .progress-bar { height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden;
                        margin-top: 16px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);
                         width: 0%; transition: width 0.3s; }
        .task-item { padding: 16px; background: #f8f9fa; border-radius: 8px; margin-bottom: 12px; }
        .task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .task-status { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .task-status.running { background: #d1ecf1; color: #0c5460; }
        .task-status.completed { background: #d4edda; color: #155724; }
        .task-status.failed { background: #f8d7da; color: #721c24; }
        .logs { background: #1e1e1e; color: #00ff00; padding: 16px; border-radius: 8px;
                font-family: 'Monaco', 'Menlo', monospace; font-size: 12px; max-height: 200px;
                overflow-y: auto; margin-top: 16px; }
        .badge { display: inline-block; padding: 2px 8px; background: #667eea; color: white;
                 border-radius: 10px; font-size: 11px; font-weight: 600; margin-left: 8px; }
        .file-list { margin-top: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 批量提示词测试系统</h1>
        <p class="subtitle">文件上传 · 在线配置 · 批量执行 · 自动评估</p>

        <div class="tabs">
            <div class="tab active" onclick="switchMainTab('upload')">📤 上传数据</div>
            <div class="tab" onclick="switchMainTab('config')">⚙️ 模型配置</div>
            <div class="tab" onclick="switchMainTab('prompts')">📝 提示词配置</div>
            <div class="tab" onclick="switchMainTab('run')">🎯 执行任务</div>
            <div class="tab" onclick="switchMainTab('tasks')">📋 任务列表</div>
        </div>

        <!-- 上传数据 -->
        <div id="tab-upload" class="tab-content active">
            <div class="card">
                <h2><span>📤</span>上传数据文件</h2>
                <div id="uploadArea" class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <div style="font-size: 48px; margin-bottom: 16px;">📁</div>
                    <h3 style="margin-bottom: 8px; color: #333;">点击或拖拽文件到这里</h3>
                    <p style="color: #666;">支持 Excel (.xlsx, .xls) 和 CSV 文件</p>
                </div>
                <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" style="display: none;" onchange="handleFileUpload(this.files)">
                
                <div id="fileList" class="file-list"></div>
                <div id="uploadStatus" class="status info" style="display: none;"></div>
            </div>
        </div>

        <!-- 模型配置 -->
        <div id="tab-config" class="tab-content">
            <div class="card">
                <h2><span>⚙️</span>模型配置</h2>
                
                <div class="tabs">
                    <div class="tab active" onclick="switchSubTab('gen-config')">生成模型</div>
                    <div class="tab" onclick="switchSubTab('eval-config')">评估模型</div>
                </div>
                
                <div id="sub-gen-config" class="tab-content active">
                    <div class="grid">
                        <div class="form-group">
                            <label>API Key</label>
                            <input type="text" id="apiKey" placeholder="sk-...">
                        </div>
                        <div class="form-group">
                            <label>Base URL</label>
                            <input type="text" id="baseUrl" placeholder="https://...">
                        </div>
                    </div>
                    <div class="grid">
                        <div class="form-group">
                            <label>模型名称</label>
                            <input type="text" id="model" placeholder="ep-xxx">
                        </div>
                        <div class="form-group">
                            <label>温度 (0-2)</label>
                            <input type="number" id="temperature" step="0.1" min="0" max="2" value="0.7">
                        </div>
                    </div>
                </div>
                
                <div id="sub-eval-config" class="tab-content">
                    <div class="grid">
                        <div class="form-group">
                            <label>评估模型 API Key</label>
                            <input type="text" id="evalApiKey" placeholder="sk-...">
                        </div>
                        <div class="form-group">
                            <label>评估模型 Base URL</label>
                            <input type="text" id="evalBaseUrl" placeholder="https://...">
                        </div>
                    </div>
                    <div class="grid">
                        <div class="form-group">
                            <label>评估模型名称</label>
                            <input type="text" id="evalModel" placeholder="ep-xxx">
                        </div>
                        <div class="form-group">
                            <label>评估温度</label>
                            <input type="number" id="evalTemperature" step="0.1" min="0" max="2" value="0.3">
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 16px;">
                    <button class="btn btn-success" onclick="saveConfig()">💾 保存配置</button>
                    <span id="configStatus"></span>
                </div>
            </div>
        </div>

        <!-- 提示词配置 -->
        <div id="tab-prompts" class="tab-content">
            <div class="card">
                <h2><span>📝</span>提示词配置</h2>
                
                <div class="tabs">
                    <div class="tab active" onclick="switchPromptTab('prompt-a')">提示词A</div>
                    <div class="tab" onclick="switchPromptTab('prompt-b')">提示词B</div>
                    <div class="tab" onclick="switchPromptTab('prompt-eval')">评估提示词</div>
                </div>
                
                <div id="sub-prompt-a" class="tab-content active">
                    <div class="form-group">
                        <label>提示词A - 系统提示词</label>
                        <textarea id="promptA"></textarea>
                    </div>
                </div>
                
                <div id="sub-prompt-b" class="tab-content">
                    <div class="form-group">
                        <label>提示词B - 系统提示词</label>
                        <textarea id="promptB"></textarea>
                    </div>
                </div>
                
                <div id="sub-prompt-eval" class="tab-content">
                    <div class="form-group">
                        <label>评估提示词</label>
                        <textarea id="promptEval"></textarea>
                    </div>
                </div>
                
                <button class="btn btn-success" onclick="savePrompts()">💾 保存提示词</button>
                <span id="promptStatus"></span>
            </div>
        </div>

        <!-- 执行任务 -->
        <div id="tab-run" class="tab-content">
            <div class="card">
                <h2><span>🎯</span>执行批量任务</h2>
                
                <div class="grid">
                    <div class="form-group">
                        <label>选择数据文件</label>
                        <select id="runFile" onchange="loadFileColumns()"></select>
                    </div>
                    <div class="form-group">
                        <label>输入列名</label>
                        <select id="runColumn"></select>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label>提示词类型</label>
                        <select id="runPrompt">
                            <option value="prompt_a">提示词A</option>
                            <option value="prompt_b">提示词B</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>运行模式</label>
                        <select id="runMode">
                            <option value="run">仅批量生成</option>
                            <option value="pipeline">完整流水线（生成 + 评估）</option>
                        </select>
                    </div>
                </div>
                
                <div class="grid">
                    <div class="form-group">
                        <label>调用间隔（秒）</label>
                        <input type="number" id="runDelay" step="0.5" value="0.5">
                    </div>
                    <div class="form-group">
                        <label>测试数量（0=全部）</label>
                        <input type="number" id="testLimit" value="10">
                    </div>
                </div>
                
                <button id="runBtn" class="btn btn-success" onclick="startTask()">🚀 开始执行</button>
                
                <div id="runStatus"></div>
            </div>
            
            <div id="currentTaskCard" class="card" style="display: none;">
                <h2><span>⏳</span>当前任务</h2>
                <div id="currentTaskInfo"></div>
                <div class="progress-bar">
                    <div id="progressFill" class="progress-fill"></div>
                </div>
                <div id="progressText" style="text-align: center; margin-top: 8px; color: #666;"></div>
                <div id="taskLogs" class="logs"></div>
            </div>
        </div>

        <!-- 任务列表 -->
        <div id="tab-tasks" class="tab-content">
            <div class="card">
                <h2><span>📋</span>任务列表</h2>
                <div id="taskList"></div>
            </div>
        </div>
    </div>

    <script>
        let currentConfig = {};
        let currentTaskId = null;
        let taskRefreshInterval = null;

        window.onload = function() {
            loadConfig();
            loadFiles();
            setupDragDrop();
        };

        function switchMainTab(tabId) {
            document.querySelectorAll('[id^="tab-"]').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            document.querySelectorAll('.tabs:first-of-type .tab').forEach((el, idx) => {
                if (idx < 5) el.classList.remove('active');
            });
            event.target.classList.add('active');
            
            if (tabId === 'tasks') loadTasks();
        }

        function switchSubTab(tabId) {
            document.querySelectorAll('[id^="sub-gen-"], [id^="sub-eval-"]').forEach(el => el.classList.remove('active'));
            document.getElementById('sub-' + tabId).classList.add('active');
        }

        function switchPromptTab(tabId) {
            document.querySelectorAll('[id^="sub-prompt-"]').forEach(el => el.classList.remove('active'));
            document.getElementById('sub-' + tabId).classList.add('active');
        }

        async function loadConfig() {
            const res = await fetch('/api/config');
            const data = await res.json();
            currentConfig = data;
            
            if (data.api && data.api.openai) {
                document.getElementById('apiKey').value = data.api.openai.api_key || '';
                document.getElementById('baseUrl').value = data.api.openai.base_url || '';
                document.getElementById('model').value = data.api.openai.model || '';
                document.getElementById('temperature').value = data.api.openai.temperature || 0.7;
            }
            
            if (data.api && data.api.evaluation) {
                document.getElementById('evalApiKey').value = data.api.evaluation.api_key || '';
                document.getElementById('evalBaseUrl').value = data.api.evaluation.base_url || '';
                document.getElementById('evalModel').value = data.api.evaluation.model || '';
                document.getElementById('evalTemperature').value = data.api.evaluation.temperature || 0.3;
            }
            
            if (data.prompts) {
                if (data.prompts.prompt_a) document.getElementById('promptA').value = data.prompts.prompt_a.system_prompt || '';
                if (data.prompts.prompt_b) document.getElementById('promptB').value = data.prompts.prompt_b.system_prompt || '';
                if (data.prompts.evaluation_prompt) document.getElementById('promptEval').value = data.prompts.evaluation_prompt.system_prompt || '';
            }
        }

        async function saveConfig() {
            const config = {
                api: {
                    openai: {
                        api_key: document.getElementById('apiKey').value,
                        base_url: document.getElementById('baseUrl').value,
                        model: document.getElementById('model').value,
                        temperature: parseFloat(document.getElementById('temperature').value),
                        max_tokens: 2000
                    },
                    evaluation: {
                        api_key: document.getElementById('evalApiKey').value,
                        base_url: document.getElementById('evalBaseUrl').value,
                        model: document.getElementById('evalModel').value,
                        temperature: parseFloat(document.getElementById('evalTemperature').value)
                    }
                },
                prompts: currentConfig.prompts
            };
            
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            
            const result = await res.json();
            document.getElementById('configStatus').textContent = '✅ ' + result.message;
            setTimeout(() => document.getElementById('configStatus').textContent = '', 3000);
            currentConfig = config;
        }

        async function savePrompts() {
            const config = {
                api: currentConfig.api,
                prompts: {
                    prompt_a: {
                        name: '提示词A',
                        system_prompt: document.getElementById('promptA').value
                    },
                    prompt_b: {
                        name: '提示词B',
                        system_prompt: document.getElementById('promptB').value
                    },
                    evaluation_prompt: {
                        name: '评估提示词',
                        system_prompt: document.getElementById('promptEval').value
                    }
                }
            };
            
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            
            const result = await res.json();
            document.getElementById('promptStatus').textContent = '✅ 提示词已保存！';
            setTimeout(() => document.getElementById('promptStatus').textContent = '', 3000);
            currentConfig = config;
        }

        function setupDragDrop() {
            const area = document.getElementById('uploadArea');
            
            area.addEventListener('dragover', (e) => {
                e.preventDefault();
                area.classList.add('dragover');
            });
            
            area.addEventListener('dragleave', () => {
                area.classList.remove('dragover');
            });
            
            area.addEventListener('drop', (e) => {
                e.preventDefault();
                area.classList.remove('dragover');
                handleFileUpload(e.dataTransfer.files);
            });
        }

        async function handleFileUpload(files) {
            if (!files.length) return;
            
            const file = files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            const status = document.getElementById('uploadStatus');
            status.style.display = 'block';
            status.className = 'status info';
            status.textContent = '正在上传...';
            
            try {
                const res = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await res.json();
                if (result.success) {
                    status.className = 'status success';
                    status.textContent = `✅ 上传成功！共 ${result.rows} 行数据，列：${result.columns.join(', ')}`;
                    loadFiles();
                } else {
                    status.className = 'status error';
                    status.textContent = '❌ 上传失败：' + result.error;
                }
            } catch (e) {
                status.className = 'status error';
                status.textContent = '❌ 上传失败：' + e.message;
            }
        }

        async function loadFiles() {
            const res = await fetch('/api/files');
            const data = await res.json();
            
            const listEl = document.getElementById('fileList');
            listEl.innerHTML = data.files.map(f => `
                <div class="file-item">
                    <div class="file-info">
                        <span class="file-icon">📄</span>
                        <div>
                            <div style="font-weight: 600;">${f.name}</div>
                            <div style="font-size: 12px; color: #666;">${f.modified}</div>
                        </div>
                    </div>
                </div>
            `).join('');
            
            const fileSelect = document.getElementById('runFile');
            fileSelect.innerHTML = data.files.map(f => `<option value="${f.name}">${f.name}</option>`).join('');
            
            if (data.preview) {
                const colSelect = document.getElementById('runColumn');
                colSelect.innerHTML = data.preview.columns.map(c => `<option value="${c}">${c}</option>`).join('');
            }
        }

        async function loadFileColumns() {
            const res = await fetch('/api/files');
            const data = await res.json();
            if (data.preview) {
                const colSelect = document.getElementById('runColumn');
                colSelect.innerHTML = data.preview.columns.map(c => `<option value="${c}">${c}</option>`).join('');
            }
        }

        async function startTask() {
            const limitVal = parseInt(document.getElementById('testLimit').value);
            const params = {
                filename: document.getElementById('runFile').value,
                column: document.getElementById('runColumn').value,
                prompt_type: document.getElementById('runPrompt').value,
                mode: document.getElementById('runMode').value,
                delay: parseFloat(document.getElementById('runDelay').value),
                limit: limitVal > 0 ? limitVal : null
            };
            
            const res = await fetch('/api/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(params)
            });
            
            const result = await res.json();
            currentTaskId = result.task_id;
            
            document.getElementById('currentTaskCard').style.display = 'block';
            document.getElementById('runBtn').disabled = true;
            
            if (taskRefreshInterval) clearInterval(taskRefreshInterval);
            taskRefreshInterval = setInterval(refreshCurrentTask, 1000);
        }

        async function refreshCurrentTask() {
            if (!currentTaskId) return;
            
            const res = await fetch(`/api/tasks/${currentTaskId}`);
            const task = await res.json();
            
            const progress = task.total > 0 ? (task.progress / task.total * 100) : 0;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `${task.progress} / ${task.total} (${progress.toFixed(1)}%)`;
            
            document.getElementById('currentTaskInfo').innerHTML = `
                <div class="task-header">
                    <span style="font-weight: 600;">任务 ID: ${task.id}</span>
                    <span class="task-status ${task.status}">${
                        task.status === 'running' ? '运行中' : 
                        task.status === 'completed' ? '已完成' : '失败'
                    }</span>
                </div>
            `;
            
            if (task.results && task.results.length > 0) {
                const last = task.results[task.results.length - 1];
                const logLine = `[${new Date().toLocaleTimeString()}] 处理第 ${task.progress} 条 | 输出: ${last.output.substring(0, 80)}...<br>`;
                document.getElementById('taskLogs').innerHTML = logLine + document.getElementById('taskLogs').innerHTML;
            }
            
            if (task.status === 'completed') {
                clearInterval(taskRefreshInterval);
                document.getElementById('runBtn').disabled = false;
                
                if (task.output_file) {
                    document.getElementById('runStatus').innerHTML = `
                        <div class="status success">
                            ✅ 任务完成！
                            <a href="/api/download?file=${task.output_file}" style="margin-left: 16px; color: #155724; font-weight: 600;">下载结果</a>
                        </div>
                    `;
                }
            } else if (task.status === 'failed') {
                clearInterval(taskRefreshInterval);
                document.getElementById('runBtn').disabled = false;
                document.getElementById('runStatus').innerHTML = `
                    <div class="status error">❌ 任务失败：${task.error}</div>
                `;
            }
        }

        async function loadTasks() {
            const res = await fetch('/api/tasks');
            const data = await res.json();
            
            const listEl = document.getElementById('taskList');
            listEl.innerHTML = data.tasks.length ? data.tasks.map(t => `
                <div class="task-item">
                    <div class="task-header">
                        <div>
                            <span style="font-weight: 600;">任务 ${t.id}</span>
                            <span class="badge">${t.filename}</span>
                        </div>
                        <span class="task-status ${t.status}">${
                            t.status === 'running' ? '运行中' : 
                            t.status === 'completed' ? '已完成' : '失败'
                        }</span>
                    </div>
                    <div style="color: #666; font-size: 14px;">
                        进度: ${t.progress} / ${t.total} · 创建时间: ${t.created_at}
                    </div>
                </div>
            `).join('') : '<div style="text-align: center; color: #999; padding: 40px;">暂无任务</div>';
        }
    </script>
</body>
</html>'''

def main():
    port = 8888
    print("=" * 60)
    print("批量提示词测试系统 - Web服务启动")
    print("=" * 60)
    print(f"\n🚀 服务已启动！请在浏览器中打开:")
    print(f"   http://localhost:{port}")
    print(f"\n📁 工作目录: {BASE_DIR}")
    print(f"\n按 Ctrl+C 停止服务\n")
    
    try:
        server = HTTPServer(('127.0.0.1', port), WebHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        server.shutdown()

if __name__ == "__main__":
    main()
