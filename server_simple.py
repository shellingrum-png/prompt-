#!/usr/bin/env python3
"""
批量提示词测试系统 - Web服务
"""
import os
import json
import time
import uuid
import pandas as pd
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# 配置目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESULTS_DIR = os.path.join(BASE_DIR, 'results')
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

tasks = {}

DEFAULT_API_CONFIG = {
    'openai': {
        'api_key': '9f485a0c-c4ea-4590-9f07-6d6925e04620',
        'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
        'model': 'ep-20250619152516-v97g5',
        'temperature': 0.7
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
        'name': '通用处理',
        'system_prompt': '你是一个智能数据处理助手。请根据用户输入的内容，按照要求进行处理并输出结果。'
    },
    'prompt_b': {
        'name': '内容生成',
        'system_prompt': '你是一个专业的内容生成助手。请根据用户的需求，生成高质量的文本内容。'
    },
    'evaluation_prompt': {
        'name': '结果评估',
        'system_prompt': '你是一个专业的AI输出质量评估师。请对生成结果进行评估打分。'
    }
}

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
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
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        if path == '/' or path == '/index.html':
            self.send_html(self.get_page())
        elif path == '/api/config':
            self.handle_get_config()
        elif path == '/api/files':
            self.handle_list_files()
        elif path == '/api/tasks':
            self.handle_list_tasks()
        elif path.startswith('/api/tasks/'):
            self.handle_get_task(path.split('/')[-1])
        elif path == '/api/download':
            self.handle_download(parsed.query)
        else:
            self.send_json({'error': 'Not Found'}, 404)
    
    def do_POST(self):
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
    
    def handle_get_config(self):
        api_cfg = os.path.join(CONFIG_DIR, 'api_config.json')
        prompt_cfg = os.path.join(CONFIG_DIR, 'prompts_config.json')
        
        api_config = json.load(open(api_cfg)) if os.path.exists(api_cfg) else DEFAULT_API_CONFIG
        prompt_config = json.load(open(prompt_cfg)) if os.path.exists(prompt_cfg) else DEFAULT_PROMPT_CONFIG
        
        self.send_json({'api': api_config, 'prompts': prompt_config})
    
    def handle_save_config(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if 'api' in body:
            json.dump(body['api'], open(os.path.join(CONFIG_DIR, 'api_config.json'), 'w'), ensure_ascii=False, indent=2)
        if 'prompts' in body:
            json.dump(body['prompts'], open(os.path.join(CONFIG_DIR, 'prompts_config.json'), 'w'), ensure_ascii=False, indent=2)
        self.send_json({'success': True, 'message': '配置已保存'})
    
    def handle_list_files(self):
        files = []
        for f in os.listdir(UPLOADS_DIR):
            if f.endswith(('.xlsx', '.xls', '.csv')):
                stat = os.stat(os.path.join(UPLOADS_DIR, f))
                files.append({'name': f, 'size': stat.st_size, 'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')})
        
        preview = {}
        if files:
            try:
                fp = os.path.join(UPLOADS_DIR, files[0]['name'])
                df = pd.read_excel(fp) if files[0]['name'].endswith(('.xlsx', '.xls')) else pd.read_csv(fp)
                preview = {'filename': files[0]['name'], 'rows': len(df), 'columns': df.columns.tolist()}
            except: pass
        
        self.send_json({'files': files, 'preview': preview})
    
    def handle_upload(self):
        content_type = self.headers['Content-Type']
        length = int(self.headers['Content-Length'])
        body = self.rfile.read(length)
        
        boundary = content_type.split('boundary=')[1].encode()
        parts = body.split(b'--' + boundary)
        
        for part in parts:
            if b'filename=' in part:
                header_end = part.find(b'\r\n\r\n')
                if header_end > 0:
                    file_data = part[header_end+4:-2]
                    import re
                    fname_match = re.search(rb'filename="([^"]+)"', part)
                    if fname_match:
                        filename = os.path.basename(fname_match.group(1).decode())
                        filepath = os.path.join(UPLOADS_DIR, filename)
                        with open(filepath, 'wb') as f:
                            f.write(file_data)
                        
                        try:
                            df = pd.read_excel(filepath) if filename.endswith(('.xlsx', '.xls')) else pd.read_csv(filepath)
                            return self.send_json({'success': True, 'filename': filename, 'columns': df.columns.tolist(), 'rows': len(df)})
                        except:
                            return self.send_json({'success': True, 'filename': filename, 'columns': [], 'rows': 0})
        
        self.send_json({'error': '上传失败'}, 400)
    
    def handle_run_task(self):
        params = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        task_id = str(uuid.uuid4())[:8]
        
        tasks[task_id] = {
            'id': task_id, 'status': 'running', 'params': params,
            'progress': 0, 'total': 0, 'results': [],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'output_file': None
        }
        
        import threading
        threading.Thread(target=self.run_task_bg, args=(task_id, params), daemon=True).start()
        self.send_json({'task_id': task_id, 'status': 'running'})
    
    def run_task_bg(self, task_id, params):
        task = tasks[task_id]
        try:
            # 读取配置
            prompt_cfg_path = os.path.join(CONFIG_DIR, 'prompts_config.json')
            prompts = json.load(open(prompt_cfg_path)) if os.path.exists(prompt_cfg_path) else DEFAULT_PROMPT_CONFIG
            
            api_cfg_path = os.path.join(CONFIG_DIR, 'api_config.json')
            api_config = json.load(open(api_cfg_path)) if os.path.exists(api_cfg_path) else DEFAULT_API_CONFIG
            
            system_prompt = prompts.get(params['prompt_type'], {}).get('system_prompt', '')
            api_info = api_config.get('openai', {})
            base_url = api_info.get('base_url', '').rstrip('/')
            api_key = api_info.get('api_key', '')
            model = api_info.get('model', '')
            
            # 读取数据
            df = pd.read_excel(os.path.join(UPLOADS_DIR, params['filename']))
            limit = params.get('limit')
            if limit and limit > 0 and limit < len(df):
                df = df.head(limit)
            
            task['total'] = len(df)
            results = []
            
            import requests
            
            for idx, row in df.iterrows():
                input_text = str(row[params['column']]) if pd.notna(row[params['column']]) else ''
                
                try:
                    # ========== 步骤1：生成输出 ==========
                    headers = {
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    }
                    data = {
                        'model': model,
                        'messages': [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': input_text}
                        ],
                        'temperature': api_info.get('temperature', 0.7)
                    }
                    response = requests.post(f'{base_url}/chat/completions', 
                                             headers=headers, json=data, timeout=120)
                    if response.status_code == 200:
                        result_data = response.json()
                        output = result_data['choices'][0]['message']['content']
                    else:
                        output = f"API错误: {response.status_code} - {response.text}"
                except Exception as e:
                    output = f"调用失败: {str(e)}"
                
                # ========== 步骤2：自动打分（如果启用） ==========
                accuracy_score = ''
                accuracy_reason = ''
                readability_score = ''
                readability_reason = ''
                
                if params.get('enable_auto_score', True) and 'API错误' not in output and '调用失败' not in output:
                    try:
                        eval_api_key = api_config.get('evaluation', {}).get('api_key', '') or api_key
                        eval_base_url = api_config.get('evaluation', {}).get('base_url', '') or base_url
                        eval_model = api_config.get('evaluation', {}).get('model', '') or model
                        eval_temp = api_config.get('evaluation', {}).get('temperature', 0.3)
                        
                        if eval_api_key and eval_base_url and eval_model:
                            # 专业的打分提示词
                            score_prompt = '''你是一个专业的AI输出质量评估专家。请对以下生成的输出进行质量评估，从两个维度进行打分：

【评估维度】
1. 准确性（0-10分）：输出内容是否准确回答了输入的问题？信息是否正确、完整？是否符合提示词的要求？
2. 可读性（0-10分）：输出格式是否清晰？语言是否通顺、易读？结构是否合理？

【输入数据】
系统提示词（System Prompt）：
{system_prompt}

用户输入（User Input）：
{input_text}

生成输出（Model Output）：
{output}

【输出要求】
请严格按照以下JSON格式输出，不要包含任何其他内容：
{{
    "accuracy_score": 分数,
    "accuracy_reason": "准确性评分理由，简要说明",
    "readability_score": 分数,
    "readability_reason": "可读性评分理由，简要说明"
}}'''
                            
                            score_headers = {
                                'Authorization': f'Bearer {eval_api_key}',
                                'Content-Type': 'application/json'
                            }
                            score_data = {
                                'model': eval_model,
                                'messages': [
                                    {'role': 'system', 'content': score_prompt.format(
                                        system_prompt=system_prompt,
                                        input_text=input_text,
                                        output=output
                                    )}
                                ],
                                'temperature': eval_temp
                            }
                            score_response = requests.post(f'{eval_base_url}/chat/completions',
                                                           headers=score_headers, json=score_data, timeout=120)
                            
                            if score_response.status_code == 200:
                                score_result = score_response.json()
                                score_text = score_result['choices'][0]['message']['content']
                                
                                # 尝试解析JSON
                                import json as json_lib
                                try:
                                    # 提取JSON部分
                                    if '{' in score_text and '}' in score_text:
                                        json_start = score_text.index('{')
                                        json_end = score_text.rindex('}') + 1
                                        score_json = score_text[json_start:json_end]
                                        score_data = json_lib.loads(score_json)
                                        accuracy_score = score_data.get('accuracy_score', '')
                                        accuracy_reason = score_data.get('accuracy_reason', '')
                                        readability_score = score_data.get('readability_score', '')
                                        readability_reason = score_data.get('readability_reason', '')
                                except:
                                    # 解析失败，保留原始文本
                                    accuracy_reason = score_text[:200]
                            else:
                                accuracy_reason = f"打分API错误: {score_response.status_code}"
                    except Exception as e:
                        accuracy_reason = f"打分失败: {str(e)}"
                
                result = {
                    'index': idx, 
                    'input': input_text, 
                    'output': output, 
                    'system_prompt': system_prompt[:100] + '...' if len(system_prompt) > 100 else system_prompt,
                    'accuracy_score': accuracy_score,
                    'accuracy_reason': accuracy_reason,
                    'readability_score': readability_score,
                    'readability_reason': readability_reason,
                    'success': 'API错误' not in output and '调用失败' not in output
                }
                results.append(result)
                task['progress'] = idx + 1
                task['results'] = results[-5:]
                time.sleep(params.get('delay', 0.5))
            
            output_filename = f"result_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            result_df = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)
            result_df.to_excel(os.path.join(RESULTS_DIR, output_filename), index=False)
            
            task['output_file'] = output_filename
            task['status'] = 'completed'
        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)
    
    def handle_list_tasks(self):
        self.send_json({'tasks': sorted([{
            'id': tid, 'status': t['status'], 'progress': t['progress'],
            'total': t['total'], 'created_at': t['created_at'],
            'filename': t['params'].get('filename', '')
        } for tid, t in tasks.items()], key=lambda x: x['created_at'], reverse=True)})
    
    def handle_get_task(self, task_id):
        if task_id in tasks:
            self.send_json(tasks[task_id])
        else:
            self.send_json({'error': '任务不存在'}, 404)
    
    def handle_download(self, query):
        params = urllib.parse.parse_qs(query)
        filename = params.get('file', [None])[0]
        filepath = os.path.join(RESULTS_DIR, filename)
        if not filename or not os.path.exists(filepath):
            self.send_json({'error': '文件不存在'}, 404)
            return
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())
    
    def get_page(self):
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
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: white; text-align: center; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: rgba(255,255,255,0.9); text-align: center; margin-bottom: 30px; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h2 { color: #333; margin-bottom: 16px; font-size: 20px; border-bottom: 2px solid #667eea; 
             padding-bottom: 10px; display: flex; align-items: center; }
        h2 span { margin-right: 10px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; color: #555; }
        input, select, textarea {
            width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;
            font-size: 14px; font-family: inherit;
        }
        input:focus, select:focus, textarea:focus { border-color: #667eea; outline: none; }
        textarea { min-height: 120px; resize: vertical; line-height: 1.6; }
        .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               color: white; border: none; padding: 10px 20px; border-radius: 8px;
               font-size: 14px; font-weight: 600; cursor: pointer; margin-right: 8px; }
        .btn:hover { transform: translateY(-2px); transition: transform 0.2s; }
        .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .btn-success { background: #28a745; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .tabs { display: flex; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; flex-wrap: wrap; }
        .tab { padding: 12px 18px; cursor: pointer; border-bottom: 3px solid transparent;
               font-weight: 600; color: #666; font-size: 14px; transition: all 0.3s; }
        .tab.active { color: #667eea; border-bottom-color: #667eea; }
        .tab:hover { color: #667eea; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .status { margin-top: 16px; padding: 12px; border-radius: 8px; }
        .status.success { background: #d4edda; color: #155724; }
        .upload-area { border: 3px dashed #667eea; border-radius: 12px; padding: 40px;
                       text-align: center; cursor: pointer; transition: all 0.3s; }
        .upload-area:hover { background: #f8f9ff; }
        .file-item { padding: 12px; background: #f8f9fa; border-radius: 8px; margin-top: 12px; }
        .progress-bar { height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden;
                        margin-top: 16px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);
                         width: 0%; transition: width 0.3s; }
        .task-item { padding: 16px; background: #f8f9fa; border-radius: 8px; margin-bottom: 12px; }
        .task-status { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        .task-status.running { background: #d1ecf1; color: #0c5460; }
        .task-status.completed { background: #d4edda; color: #155724; }
        .logs { background: #1e1e1e; color: #00ff00; padding: 16px; border-radius: 8px;
                font-family: 'Monaco', 'Menlo', monospace; font-size: 12px; max-height: 200px;
                overflow-y: auto; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 批量提示词测试系统</h1>
        <p class="subtitle">文件上传 · 在线配置 · 批量执行 · 自动评估</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('upload')">📤 上传数据</div>
            <div class="tab" onclick="switchTab('config')">⚙️ 模型配置</div>
            <div class="tab" onclick="switchTab('prompts')">📝 提示词配置</div>
            <div class="tab" onclick="switchTab('run')">🎯 执行任务</div>
            <div class="tab" onclick="switchTab('tasks')">📋 任务列表</div>
        </div>

        <div id="tab-upload" class="tab-content active">
            <div class="card">
                <h2><span>📤</span>上传数据文件</h2>
                <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                    <div style="font-size: 48px; margin-bottom: 16px;">📁</div>
                    <h3 style="margin-bottom: 8px; color: #333;">点击或拖拽文件到这里</h3>
                    <p style="color: #666;">支持 Excel (.xlsx, .xls) 和 CSV 文件</p>
                </div>
                <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" style="display: none;" onchange="uploadFile(this.files)">
                <div id="uploadResult"></div>
            </div>
        </div>

        <div id="tab-config" class="tab-content">
            <div class="card">
                <h2><span>⚙️</span>模型配置</h2><div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin-bottom: 16px; border-radius: 4px;">
    <strong>🔒 安全提示：</strong>API密钥仅保存在你本地的 config/api_config.json 文件中，不会上传到任何服务器。
</div>
                <div class="grid">
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="text" id="apiKey" value="9f485a0c-c4ea-4590-9f07-6d6925e04620">
                    </div>
                    <div class="form-group">
                        <label>Base URL</label>
                        <input type="text" id="baseUrl" value="https://ark.cn-beijing.volces.com/api/v3">
                    </div>
                </div>
                <div class="grid">
                    <div class="form-group">
                        <label>模型名称</label>
                        <input type="text" id="model" value="ep-20250619152516-v97g5">
                    </div>
                    <div class="form-group">
                        <label>温度</label>
                        <input type="number" id="temperature" step="0.1" value="0.7">
                    </div>

                <div style="margin-top: 24px; padding-top: 24px; border-top: 2px solid #eee;">
                    <h3 style="color: #333; margin-bottom: 16px;">⚖️ 打分模型配置（自动评估使用）</h3>
                    <div class="grid">
                        <div class="form-group">
                            <label>打分模型 API Key（可与生成模型相同）</label>
                            <input type="text" id="evalApiKey" value="">
                        </div>
                        <div class="form-group">
                            <label>打分模型 Base URL</label>
                            <input type="text" id="evalBaseUrl" value="">
                        </div>
                    </div>
                    <div class="grid">
                        <div class="form-group">
                            <label>打分模型名称</label>
                            <input type="text" id="evalModel" value="">
                        </div>
                        <div class="form-group">
                            <label>打分模型温度</label>
                            <input type="number" id="evalTemperature" step="0.1" value="0.3">
                        </div>
                    </div>
                </div>
                
                <div class="form-group" style="margin-top: 16px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="enableAutoScore" checked style="width: auto; margin-right: 10px;">
                        ✅ 启用自动打分功能（生成输出后自动评估准确性和可读性）
                    </label>
                </div>
                </div>
                <button class="btn btn-success" onclick="saveConfig()">💾 保存配置</button>
                <span id="configStatus"></span>
            </div>
        </div>

        <div id="tab-prompts" class="tab-content">
            <div class="card">
                <h2><span>📝</span>提示词配置</h2>
                <div class="form-group">
                    <label>提示词A（System Prompt）</label>
                    <textarea id="promptA">你是一个智能数据处理助手。请根据用户输入的内容，按照要求进行处理并输出结果。</textarea>
                </div>
                <div class="form-group">
                    <label>提示词B（System Prompt）</label>
                    <textarea id="promptB">你是一个专业的内容生成助手。请根据用户的需求，生成高质量的文本内容。</textarea>
                </div>
                <button class="btn btn-success" onclick="savePrompts()">💾 保存提示词</button>
                <span id="promptStatus"></span>
            </div>
        </div>

        <div id="tab-run" class="tab-content">
            <div class="card">
                <h2><span>🎯</span>执行批量任务</h2>
                <div class="grid">
                    <div class="form-group">
                        <label>选择数据文件</label>
                        <select id="runFile"></select>
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
                        <label>测试数量（0=全部）</label>
                        <input type="number" id="testLimit" value="3">
                    </div>
                </div>
                <button id="runBtn" class="btn btn-success" onclick="startTask()">🚀 开始执行</button>
                <div id="runStatus"></div>
                
                <div id="taskProgress" style="display: none;">
                    <div class="progress-bar"><div id="progressFill" class="progress-fill"></div></div>
                    <div id="progressText" style="text-align: center; margin-top: 8px;"></div>
                    <div id="taskLogs" class="logs"></div>
                </div>
            </div>
        </div>

        <div id="tab-tasks" class="tab-content">
            <div class="card">
                <h2><span>📋</span>任务列表</h2>
                <div id="taskList"></div>
            </div>
        </div>
    </div>

    <script>
        let currentTaskId = null, taskInterval = null;
        
        window.onload = function() {
            loadConfig();
            loadFiles();
        };
        
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            document.querySelectorAll('.tabs:first-of-type .tab').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
            if (tabId === 'tasks') loadTasks();
        }
        
        async function loadConfig() {
            const res = await fetch('/api/config');
            const data = await res.json();
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
            if (data.api && data.api.evaluation) {
                document.getElementById('evalApiKey').value = data.api.evaluation.api_key || '';
                document.getElementById('evalBaseUrl').value = data.api.evaluation.base_url || '';
                document.getElementById('evalModel').value = data.api.evaluation.model || '';
                document.getElementById('evalTemperature').value = data.api.evaluation.temperature || 0.3;
            }
            if (data.prompts) {
                if (data.prompts.prompt_a) document.getElementById('promptA').value = data.prompts.prompt_a.system_prompt || '';
                if (data.prompts.prompt_b) document.getElementById('promptB').value = data.prompts.prompt_b.system_prompt || '';
            }
        }
        
        async function saveConfig() {
            const config = {api: {openai: {
                api_key: document.getElementById('apiKey').value,
                base_url: document.getElementById('baseUrl').value,
                model: document.getElementById('model').value,
                temperature: parseFloat(document.getElementById('temperature').value)
            }, evaluation: {
                api_key: document.getElementById('evalApiKey').value,
                base_url: document.getElementById('evalBaseUrl').value,
                model: document.getElementById('evalModel').value,
                temperature: parseFloat(document.getElementById('evalTemperature').value)
            }}};
            config.api.evaluation = config.api.openai;
            
            await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            document.getElementById('configStatus').textContent = '✅ 配置已保存';
            setTimeout(() => document.getElementById('configStatus').textContent = '', 3000);
        }
        
        async function savePrompts() {
            const res = await fetch('/api/config');
            const current = await res.json();
            const config = {
                api: current.api,
                prompts: {
                    prompt_a: {name: '提示词A', system_prompt: document.getElementById('promptA').value},
                    prompt_b: {name: '提示词B', system_prompt: document.getElementById('promptB').value},
                    evaluation_prompt: {name: '评估', system_prompt: '评估输出质量'}
                }
            };
            await fetch('/api/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            });
            document.getElementById('promptStatus').textContent = '✅ 提示词已保存';
            setTimeout(() => document.getElementById('promptStatus').textContent = '', 3000);
        }
        
        async function uploadFile(files) {
            if (!files.length) return;
            const formData = new FormData();
            formData.append('file', files[0]);
            
            const res = await fetch('/api/upload', {method: 'POST', body: formData});
            const result = await res.json();
            
            if (result.success) {
                document.getElementById('uploadResult').innerHTML = 
                    `<div class="status success">✅ 上传成功！共 ${result.rows} 行数据，列：${result.columns.join(', ')}</div>`;
                loadFiles();
            }
        }
        
        async function loadFiles() {
            const res = await fetch('/api/files');
            const data = await res.json();
            const fileSelect = document.getElementById('runFile');
            fileSelect.innerHTML = data.files.map(f => `<option value="${f.name}">${f.name}</option>`).join('');
            
            if (data.preview) {
                document.getElementById('runColumn').innerHTML = 
                    data.preview.columns.map(c => `<option value="${c}">${c}</option>`).join('');
            }
        }
        
        async function startTask() {
            const limit = parseInt(document.getElementById('testLimit').value);
            const params = {
                filename: document.getElementById('runFile').value,
                column: document.getElementById('runColumn').value,
                prompt_type: document.getElementById('runPrompt').value,
                mode: 'run',
                delay: 0.5,
                limit: limit > 0 ? limit : null,
                enable_auto_score: document.getElementById('enableAutoScore').checked
            };
            
            const res = await fetch('/api/run', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(params)
            });
            const result = await res.json();
            currentTaskId = result.task_id;
            
            document.getElementById('runBtn').disabled = true;
            document.getElementById('taskProgress').style.display = 'block';
            
            if (taskInterval) clearInterval(taskInterval);
            taskInterval = setInterval(refreshTask, 1000);
        }
        
        async function refreshTask() {
            const res = await fetch(`/api/tasks/${currentTaskId}`);
            const task = await res.json();
            
            const progress = task.total > 0 ? (task.progress / task.total * 100) : 0;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('progressText').textContent = `${task.progress} / ${task.total} (${progress.toFixed(1)}%)`;
            
            if (task.results && task.results.length > 0) {
                const last = task.results[task.results.length - 1];
                const logLine = `[${new Date().toLocaleTimeString()}] #${task.progress}: 输出${last.output.length}字符<br>`;
                document.getElementById('taskLogs').innerHTML = logLine + document.getElementById('taskLogs').innerHTML;
            }
            
            if (task.status === 'completed') {
                clearInterval(taskInterval);
                document.getElementById('runBtn').disabled = false;
                if (task.output_file) {
                    document.getElementById('runStatus').innerHTML =
                        `<div class="status success">✅ 完成！<a href="/api/download?file=${task.output_file}" style="margin-left:16px;color:#155724;font-weight:600;" download>下载结果</a></div>`;
                }
            } else if (task.status === 'failed') {
                clearInterval(taskInterval);
                document.getElementById('runBtn').disabled = false;
                document.getElementById('runStatus').innerHTML = `<div class="status" style="background:#f8d7da;color:#721c24;">❌ 失败：${task.error}</div>`;
            }
        }
        
        async function loadTasks() {
            const res = await fetch('/api/tasks');
            const data = await res.json();
            document.getElementById('taskList').innerHTML = data.tasks.length ? data.tasks.map(t => `
                <div class="task-item">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:600;">任务 ${t.id}</span>
                        <span class="task-status ${t.status}">${t.status === 'running' ? '运行中' : t.status === 'completed' ? '已完成' : '失败'}</span>
                    </div>
                    <div style="color:#666;font-size:14px;margin-top:8px;">进度: ${t.progress}/${t.total} · ${t.created_at}</div>
                </div>
            `).join('') : '<div style="text-align:center;color:#999;padding:40px;">暂无任务</div>';
        }
    </script>
</body>
</html>'''

def main():
    port = 18080
    print("=" * 60)
    print("批量提示词测试系统 - Web服务启动")
    print("=" * 60)
    print(f"\n🚀 服务已启动！请在浏览器中打开:")
    print(f"   http://localhost:{port}")
    print(f"\n💡 提示：先配置提示词并保存，再运行任务")
    print(f"\n按 Ctrl+C 停止服务\n")
    
    server = HTTPServer(('127.0.0.1', port), WebHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        server.shutdown()

if __name__ == "__main__":
    main()
