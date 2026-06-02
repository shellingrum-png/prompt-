#!/usr/bin/env python3
"""
简单的Web管理界面
使用: python3 web_app.py
"""
import os
import sys
import json
import pandas as pd
from flask import Flask, render_template_string, request, jsonify, send_file
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# 简单的HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
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
        h1 { color: white; text-align: center; margin-bottom: 30px; font-size: 28px; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        h2 { color: #333; margin-bottom: 16px; font-size: 20px; border-bottom: 2px solid #667eea; 
             padding-bottom: 10px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; color: #555; }
        input[type="text"], input[type="number"], select, textarea {
            width: 100%; padding: 10px; border: 2px solid #e0e0e0; border-radius: 8px;
            font-size: 14px; transition: border-color 0.3s;
        }
        input:focus, select:focus, textarea:focus { border-color: #667eea; outline: none; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                 color: white; border: none; padding: 12px 24px; border-radius: 8px;
                 font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.2s; }
        button:hover { transform: translateY(-2px); }
        button:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .status { margin-top: 16px; padding: 12px; border-radius: 8px; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.info { background: #d1ecf1; color: #0c5460; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .log-area { background: #1e1e1e; color: #00ff00; padding: 16px; border-radius: 8px;
                    font-family: monospace; font-size: 12px; max-height: 300px; overflow-y: auto; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
        .stat-item { text-align: center; padding: 16px; background: #f8f9fa; border-radius: 8px; }
        .stat-number { font-size: 32px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 批量提示词测试系统</h1>
        
        <div class="grid">
            <!-- 配置区域 -->
            <div class="card">
                <h2>⚙️ API配置</h2>
                <div class="form-group">
                    <label>API Key</label>
                    <input type="text" id="apiKey" placeholder="sk-..." value="">
                </div>
                <div class="form-group">
                    <label>Base URL</label>
                    <input type="text" id="baseUrl" placeholder="https://api.openai.com/v1" value="https://api.openai.com/v1">
                </div>
                <div class="form-group">
                    <label>模型</label>
                    <select id="model">
                        <option value="gpt-4o">gpt-4o</option>
                        <option value="gpt-4">gpt-4</option>
                        <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>温度 (0-2)</label>
                    <input type="number" id="temperature" step="0.1" min="0" max="2" value="0.7">
                </div>
                <button onclick="saveConfig()">保存配置</button>
                <div id="configStatus" class="status" style="display:none;"></div>
            </div>
            
            <!-- 提示词配置 -->
            <div class="card">
                <h2>📝 提示词配置</h2>
                <div class="form-group">
                    <label>选择提示词类型</label>
                    <select id="promptType" onchange="loadPrompt()">
                        <option value="prompt_a">提示词A - 数据格式化引擎</option>
                        <option value="prompt_b">提示词B - 招聘数据模拟</option>
                        <option value="custom">自定义提示词</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>系统提示词</label>
                    <textarea id="systemPrompt" rows="8" placeholder="输入系统提示词..."></textarea>
                </div>
                <button onclick="savePrompt()">保存提示词</button>
            </div>
        </div>
        
        <!-- 任务执行区域 -->
        <div class="card">
            <h2>🎯 执行批量任务</h2>
            <div class="grid">
                <div class="form-group">
                    <label>上传Excel文件</label>
                    <input type="file" id="fileInput" accept=".xlsx,.xls" onchange="previewFile()">
                </div>
                <div class="form-group">
                    <label>输入列名</label>
                    <select id="inputColumn">
                        <option value="">请先上传文件</option>
                    </select>
                </div>
            </div>
            
            <div class="grid">
                <div class="form-group">
                    <label>任务类型</label>
                    <select id="taskType">
                        <option value="run">仅批量生成</option>
                        <option value="evaluate">仅评估结果</option>
                        <option value="pipeline">完整流水线（生成+评估）</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>调用间隔(秒)</label>
                    <input type="number" id="delay" step="0.5" value="1.0">
                </div>
            </div>
            
            <button id="runBtn" onclick="startTask()" disabled>开始执行</button>
            
            <div id="logArea" class="log-area" style="margin-top: 20px; display: none;">
                <div id="logs"></div>
            </div>
            
            <div id="resultArea" style="display: none; margin-top: 20px;">
                <h3>📊 执行结果</h3>
                <div class="stats" id="statsArea"></div>
                <button onclick="downloadResult()" style="margin-top: 16px;">下载结果Excel</button>
            </div>
        </div>
    </div>
    
    <script>
        let currentFile = null;
        let currentData = null;
        let resultData = null;
        
        function addLog(text, type = 'info') {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            logs.innerHTML += `[${time}] ${text}\\n`;
            logs.scrollTop = logs.scrollHeight;
        }
        
        async function saveConfig() {
            const status = document.getElementById('configStatus');
            status.style.display = 'block';
            status.className = 'status info';
            status.textContent = '配置已保存！';
            setTimeout(() => status.style.display = 'none', 3000);
        }
        
        function loadPrompt() {
            const type = document.getElementById('promptType').value;
            const prompts = {
                prompt_a: `你是一个数据格式化引擎。请严格执行以下逻辑步骤...`,
                prompt_b: `# Role\\n你是一个资深招聘数据模拟专家...`
            };
            if (prompts[type]) {
                document.getElementById('systemPrompt').value = 
                    type === 'prompt_a' ? document.getElementById('systemPrompt').placeholder : 
                    '招聘数据模拟专家提示词（已预设）';
            } else {
                document.getElementById('systemPrompt').value = '';
            }
        }
        
        function savePrompt() {
            alert('提示词已保存！');
        }
        
        async function previewFile() {
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;
            
            currentFile = file;
            addLog(`已选择文件: ${file.name}`);
            
            // 模拟读取列名
            document.getElementById('inputColumn').innerHTML = `
                <option value="提示词Ainput">提示词Ainput</option>
                <option value="提示词Binput">提示词Binput</option>
                <option value="input">input</option>
            `;
            document.getElementById('runBtn').disabled = false;
        }
        
        async function startTask() {
            const btn = document.getElementById('runBtn');
            btn.disabled = true;
            btn.textContent = '执行中...';
            document.getElementById('logArea').style.display = 'block';
            document.getElementById('logs').innerHTML = '';
            
            addLog('开始执行批量任务...');
            addLog(`输入列: ${document.getElementById('inputColumn').value}`);
            addLog(`提示词类型: ${document.getElementById('promptType').value}`);
            addLog(`调用间隔: ${document.getElementById('delay').value}秒`);
            
            // 模拟执行
            for (let i = 1; i <= 10; i++) {
                await new Promise(r => setTimeout(r, 500));
                addLog(`处理第 ${i}/10 条数据...`);
            }
            
            addLog('执行完成！');
            addLog('开始评估结果...');
            
            await new Promise(r => setTimeout(r, 1000));
            
            addLog('评估完成！');
            addLog('生成统计报告...');
            
            // 显示结果
            document.getElementById('resultArea').style.display = 'block';
            document.getElementById('statsArea').innerHTML = `
                <div class="stat-item">
                    <div class="stat-number">10</div>
                    <div class="stat-label">总条数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">8.5</div>
                    <div class="stat-label">平均分</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">8</div>
                    <div class="stat-label">≥7分</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">2</div>
                    <div class="stat-label"><7分</div>
                </div>
            `;
            
            btn.disabled = false;
            btn.textContent = '开始执行';
            resultData = new Blob(['模拟数据'], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
        }
        
        function downloadResult() {
            alert('这是Web演示版本，实际使用请运行命令行版本！\\n\\n命令示例:\\npython3 main.py pipeline --input ../outputs/会话处理结果.xlsx');
        }
        
        // 初始化
        loadPrompt();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def main():
    print("=" * 60)
    print("批量提示词测试系统 - Web界面")
    print("=" * 60)
    print("\nWeb演示模式启动中...")
    print("注意：这是一个简化的演示界面")
    print("实际批量处理请使用命令行：python3 main.py")
    print("\n访问 http://localhost:5000 查看Web界面")
    print("按 Ctrl+C 停止服务器\n")
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()
