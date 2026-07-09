#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器上传界面 - 使用Python内置http.server
无需安装额外依赖，直接通过浏览器上传视频到社媒平台
"""
import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(__file__))

from uploader import BufferUploader
from config import Config

UPLOAD_DIR = Config.OUTPUT_DIR
PORT = 8080

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频上传管理 - 社媒分发</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 {
            color: #fff;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
            font-weight: 600;
        }
        .card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .card h2 {
            color: #fff;
            font-size: 18px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card h2::before {
            content: '';
            width: 4px;
            height: 20px;
            background: #0ea5e9;
            border-radius: 2px;
        }
        .upload-area {
            border: 2px dashed rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: rgba(255, 255, 255, 0.03);
        }
        .upload-area:hover {
            border-color: #0ea5e9;
            background: rgba(14, 165, 233, 0.1);
        }
        .upload-area.dragover {
            border-color: #0ea5e9;
            background: rgba(14, 165, 233, 0.15);
            transform: scale(1.02);
        }
        .upload-area svg {
            width: 64px;
            height: 64px;
            margin-bottom: 16px;
            fill: rgba(255, 255, 255, 0.5);
        }
        .upload-area:hover svg {
            fill: #0ea5e9;
        }
        .upload-area p {
            color: rgba(255, 255, 255, 0.7);
            font-size: 16px;
        }
        .upload-area small {
            display: block;
            margin-top: 8px;
            color: rgba(255, 255, 255, 0.5);
            font-size: 13px;
        }
        #fileInput {
            display: none;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: rgba(255, 255, 255, 0.8);
            font-size: 14px;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: #fff;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        .form-group input:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #0ea5e9;
        }
        .form-group textarea {
            resize: vertical;
            min-height: 80px;
        }
        .channel-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
        }
        .channel-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .channel-item:hover {
            border-color: #0ea5e9;
            background: rgba(14, 165, 233, 0.1);
        }
        .channel-item.selected {
            border-color: #0ea5e9;
            background: rgba(14, 165, 233, 0.2);
        }
        .channel-item input[type="radio"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .channel-item .channel-info {
            flex: 1;
        }
        .channel-item .channel-name {
            color: #fff;
            font-size: 14px;
            font-weight: 500;
        }
        .channel-item .channel-service {
            color: rgba(255, 255, 255, 0.5);
            font-size: 12px;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 14px 32px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .btn-primary {
            background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
            color: #fff;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(14, 165, 233, 0.4);
        }
        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        .btn-group {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        .status {
            padding: 12px 16px;
            border-radius: 8px;
            margin-top: 16px;
            font-size: 14px;
        }
        .status.success {
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .status.error {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .status.info {
            background: rgba(14, 165, 233, 0.15);
            color: #0ea5e9;
            border: 1px solid rgba(14, 165, 233, 0.3);
        }
        .file-info {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 8px;
            margin-top: 12px;
        }
        .file-info svg {
            width: 32px;
            height: 32px;
            fill: #22c55e;
        }
        .file-info .file-details {
            flex: 1;
        }
        .file-info .file-name {
            color: #fff;
            font-size: 14px;
            font-weight: 500;
        }
        .file-info .file-size {
            color: rgba(255, 255, 255, 0.5);
            font-size: 12px;
        }
        .file-info button {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #ef4444;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
        }
        .file-info button:hover {
            background: rgba(239, 68, 68, 0.3);
        }
        .video-preview {
            margin-top: 16px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .video-preview video {
            width: 100%;
            display: block;
        }
        .platform-links {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 16px;
        }
        .platform-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: #fff;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        .platform-link:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: #0ea5e9;
        }
        .platform-link svg {
            width: 20px;
            height: 20px;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .result-section {
            display: none;
        }
        .result-section.active {
            display: block;
        }
        .api-limit-box {
            background: linear-gradient(135deg, rgba(249, 115, 22, 0.1) 0%, rgba(234, 88, 12, 0.1) 100%);
            border: 1px solid rgba(249, 115, 22, 0.3);
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }
        .api-limit-box h3 {
            color: #f97316;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .api-limit-box p {
            color: rgba(255, 255, 255, 0.7);
            font-size: 13px;
            line-height: 1.6;
        }
        .api-limit-box ul {
            margin-top: 8px;
            padding-left: 20px;
        }
        .api-limit-box li {
            color: rgba(255, 255, 255, 0.6);
            font-size: 12px;
            margin-bottom: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📹 视频上传管理 - 社媒分发</h1>
        
        <div class="card">
            <h2>步骤1：上传视频文件</h2>
            <div class="upload-area" id="uploadArea">
                <svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/></svg>
                <p>点击或拖拽视频文件到此处</p>
                <small>支持 MP4 格式，最大 50MB</small>
            </div>
            <input type="file" id="fileInput" accept="video/mp4">
            
            <div id="fileInfo" style="display: none;"></div>
            <div id="videoPreview" class="video-preview" style="display: none;"></div>
        </div>
        
        <div class="card">
            <h2>步骤2：填写视频信息</h2>
            <div class="form-group">
                <label for="title">标题</label>
                <input type="text" id="title" placeholder="输入视频标题...">
            </div>
            <div class="form-group">
                <label for="description">描述</label>
                <textarea id="description" placeholder="输入视频描述..."></textarea>
            </div>
            <div class="form-group">
                <label for="tags">标签（用空格或逗号分隔）</label>
                <input type="text" id="tags" placeholder="例如: #Yunnan #Travel #China">
            </div>
        </div>
        
        <div class="card">
            <h2>步骤3：选择目标频道</h2>
            <div id="channelList" class="channel-grid">
                <div style="color: rgba(255,255,255,0.5); padding: 20px; text-align: center;">正在加载频道列表...</div>
            </div>
        </div>
        
        <div class="card">
            <div class="btn-group">
                <button class="btn btn-primary" id="uploadBtn" disabled>
                    <span>🚀 上传到社媒</span>
                </button>
                <button class="btn btn-secondary" id="resetBtn">
                    <span>🔄 重置</span>
                </button>
            </div>
            <div id="status"></div>
        </div>
        
        <div class="card result-section" id="resultSection">
            <h2>上传结果</h2>
            <div id="resultContent"></div>
            <div class="api-limit-box">
                <h3>⚠️ API权限说明</h3>
                <p>当前使用的是Buffer免费计划的Public API Token，不支持REST API文件上传。</p>
                <ul>
                    <li>方案1：升级Buffer付费计划，创建OAuth应用获取Access Token</li>
                    <li>方案2：手动登录以下链接上传视频</li>
                </ul>
            </div>
            <div class="platform-links">
                <a href="https://publish.buffer.com" target="_blank" class="platform-link">
                    <svg viewBox="0 0 24 24"><path fill="#fff" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
                    Buffer 管理平台
                </a>
                <a href="https://www.tiktok.com/upload" target="_blank" class="platform-link">
                    <svg viewBox="0 0 24 24"><path fill="#fff" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 2.95-1.9 3.9-1.1.95-2.5 1.5-4.74 1.5-.48 0-.94-.05-1.38-.15-.44-.1-.66-.58-.56-1.02.1-.44.58-.66 1.02-.56.38.08.79.12 1.2.12 1.67 0 3.14-.57 4.22-1.75.9-1.01 1.49-2.48 1.39-4.18-.1-1.62-.77-3.04-1.87-4.04-.98-.9-2.29-1.44-3.68-1.44-.49 0-.97.05-1.43.16-.46.11-.68.59-.57 1.05.11.46.59.68 1.05.57.36-.09.77-.15 1.19-.15 1.94 0 3.58.76 4.89 2.07 1.12 1.12 1.79 2.71 1.69 4.36z"/></svg>
                    TikTok 上传
                </a>
                <a href="https://studio.youtube.com" target="_blank" class="platform-link">
                    <svg viewBox="0 0 24 24"><path fill="#fff" d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                    YouTube Studio
                </a>
            </div>
        </div>
    </div>
    
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const videoPreview = document.getElementById('videoPreview');
        const uploadBtn = document.getElementById('uploadBtn');
        const resetBtn = document.getElementById('resetBtn');
        const statusDiv = document.getElementById('status');
        const resultSection = document.getElementById('resultSection');
        const resultContent = document.getElementById('resultContent');
        const channelList = document.getElementById('channelList');
        
        let selectedFile = null;
        
        function showStatus(message, type = 'info') {
            statusDiv.innerHTML = `<div class="status ${type}">${message}</div>`;
        }
        
        function showFileInfo(file) {
            const size = (file.size / (1024 * 1024)).toFixed(2);
            fileInfo.innerHTML = `
                <div class="file-info">
                    <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                    <div class="file-details">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${size} MB</div>
                    </div>
                    <button onclick="clearFile()">移除</button>
                </div>
            `;
            fileInfo.style.display = 'block';
            
            videoPreview.innerHTML = `<video src="${URL.createObjectURL(file)}" controls></video>`;
            videoPreview.style.display = 'block';
            
            uploadBtn.disabled = false;
        }
        
        function clearFile() {
            selectedFile = null;
            fileInput.value = '';
            fileInfo.style.display = 'none';
            videoPreview.style.display = 'none';
            uploadBtn.disabled = true;
        }
        
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === 'video/mp4') {
                selectedFile = files[0];
                showFileInfo(selectedFile);
            } else {
                showStatus('请上传 MP4 格式的视频文件', 'error');
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                if (selectedFile.type === 'video/mp4') {
                    showFileInfo(selectedFile);
                } else {
                    showStatus('请上传 MP4 格式的视频文件', 'error');
                    clearFile();
                }
            }
        });
        
        resetBtn.addEventListener('click', () => {
            clearFile();
            document.getElementById('title').value = '';
            document.getElementById('description').value = '';
            document.getElementById('tags').value = '';
            statusDiv.innerHTML = '';
            resultSection.classList.remove('active');
        });
        
        async function loadChannels() {
            try {
                const response = await fetch('/api/channels');
                const data = await response.json();
                
                if (data.error) {
                    channelList.innerHTML = `<div style="color: rgba(239,68,68,0.8); padding: 20px;">${data.error}</div>`;
                    return;
                }
                
                if (data.channels.length === 0) {
                    channelList.innerHTML = `<div style="color: rgba(255,255,255,0.5); padding: 20px;">未找到任何频道</div>`;
                    return;
                }
                
                channelList.innerHTML = data.channels.map((ch, index) => `
                    <div class="channel-item ${index === 0 ? 'selected' : ''}" onclick="selectChannel(this, '${ch.id}')">
                        <input type="radio" name="channel" value="${ch.id}" ${index === 0 ? 'checked' : ''}>
                        <div class="channel-info">
                            <div class="channel-name">${ch.name}</div>
                            <div class="channel-service">${ch.service}</div>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                channelList.innerHTML = `<div style="color: rgba(239,68,68,0.8); padding: 20px;">加载频道失败: ${error.message}</div>`;
            }
        }
        
        window.selectChannel = function(el, channelId) {
            document.querySelectorAll('.channel-item').forEach(item => item.classList.remove('selected'));
            el.classList.add('selected');
        };
        
        uploadBtn.addEventListener('click', async () => {
            if (!selectedFile) {
                showStatus('请先选择视频文件', 'error');
                return;
            }
            
            const title = document.getElementById('title').value.trim();
            const description = document.getElementById('description').value.trim();
            const tags = document.getElementById('tags').value.trim();
            const channelId = document.querySelector('input[name="channel"]:checked')?.value;
            
            if (!title) {
                showStatus('请输入视频标题', 'error');
                return;
            }
            
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<span class="loading"></span> 上传中...';
            showStatus('正在上传视频，请稍候...', 'info');
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('title', title);
            formData.append('description', description);
            formData.append('tags', tags);
            formData.append('channel_id', channelId || '');
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('上传完成！', 'success');
                    resultContent.innerHTML = `
                        <div class="status success">
                            <strong>✅ 视频上传成功！</strong><br>
                            <br>
                            <strong>视频文件:</strong> ${data.video_path}<br>
                            <strong>标题:</strong> ${data.title}<br>
                            <strong>描述:</strong> ${data.description}<br>
                            <strong>标签:</strong> ${data.tags.join(', ')}<br>
                            <br>
                            <strong>上传状态:</strong><br>
                            ${data.upload_result}
                        </div>
                    `;
                    resultSection.classList.add('active');
                } else {
                    showStatus(data.error || '上传失败', 'error');
                    resultContent.innerHTML = `
                        <div class="status error">
                            <strong>❌ 上传失败</strong><br>
                            ${data.error || '未知错误'}
                        </div>
                    `;
                    resultSection.classList.add('active');
                }
            } catch (error) {
                showStatus('上传失败: ' + error.message, 'error');
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = '<span>🚀 上传到社媒</span>';
            }
        });
        
        loadChannels();
    </script>
</body>
</html>
"""


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
        
        elif parsed.path == '/api/channels':
            try:
                uploader = BufferUploader()
                channels = uploader.get_account_channels()
                
                if channels:
                    response = {"success": True, "channels": channels}
                else:
                    response = {"success": True, "channels": [], "message": "未找到频道"}
            except Exception as e:
                response = {"success": False, "error": str(e)}
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/upload':
            content_type = self.headers.get('Content-Type', '')
            
            if 'multipart/form-data' not in content_type:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "需要 multipart/form-data"}).encode('utf-8'))
                return
            
            boundary = content_type.split('boundary=')[1].encode('utf-8')
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            parts = body.split(b'--' + boundary)
            file_data = None
            file_name = None
            form_data = {}
            
            for part in parts:
                if not part.strip():
                    continue
                
                lines = part.split(b'\r\n')
                header_lines = []
                data_start = 0
                
                for i, line in enumerate(lines):
                    if line == b'':
                        data_start = i + 1
                        break
                    header_lines.append(line)
                
                headers = {}
                for h in header_lines:
                    if b':' in h:
                        key, value = h.split(b':', 1)
                        headers[key.strip()] = value.strip()
                
                content_disposition = headers.get(b'Content-Disposition', b'')
                name_match = content_disposition.decode('utf-8').split('name="')[1].split('"')[0]
                
                if b'filename=' in content_disposition:
                    file_name = content_disposition.decode('utf-8').split('filename="')[1].split('"')[0]
                    file_data = b'\r\n'.join(lines[data_start:-1])
                else:
                    if data_start < len(lines):
                        form_data[name_match] = b'\r\n'.join(lines[data_start:-1]).decode('utf-8')
            
            if not file_data or not file_name:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "未找到文件"}).encode('utf-8'))
                return
            
            try:
                if not os.path.exists(UPLOAD_DIR):
                    os.makedirs(UPLOAD_DIR)
                
                video_path = os.path.join(UPLOAD_DIR, file_name)
                with open(video_path, 'wb') as f:
                    f.write(file_data)
                
                title = form_data.get('title', '')
                description = form_data.get('description', '')
                tags_str = form_data.get('tags', '')
                channel_id = form_data.get('channel_id', '')
                
                tags = [t.strip() for t in tags_str.replace(',', ' ').split() if t.strip()]
                
                uploader = BufferUploader()
                upload_result = uploader.upload(video_path, title, description, tags, channel_id)
                
                response = {
                    "success": True,
                    "video_path": video_path,
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "upload_result": upload_result
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass


def main():
    print(f"{'='*60}")
    print(f"  视频上传管理界面")
    print(f"{'='*60}")
    print(f"")
    print(f"  服务器启动中...")
    print(f"  访问地址: http://localhost:{PORT}")
    print(f"")
    print(f"  按 Ctrl+C 停止服务器")
    print(f"{'='*60}")
    print(f"")
    
    server = HTTPServer(('0.0.0.0', PORT), RequestHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{'='*60}")
        print(f"  服务器已停止")
        print(f"{'='*60}")
        server.server_close()


if __name__ == '__main__':
    main()