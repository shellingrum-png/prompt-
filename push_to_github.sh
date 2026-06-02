#!/bin/bash
echo "========================================="
echo "🚀 批量提示词测试系统 - GitHub推送脚本"
echo "========================================="
echo ""

# 进入脚本所在目录
cd "$(dirname "$0")"

# 检查是否已经是git仓库
if [ ! -d .git ]; then
    echo "📦 初始化Git仓库..."
    git init
else
    echo "✅ Git仓库已存在"
fi

echo ""
echo "📝 添加所有文件..."
git add .

echo ""
echo "📋 提交代码..."
git commit -m "feat: 批量提示词测试系统

功能特性：
- 完整Web界面，5个功能标签页
- 在线配置API参数（API Key、BaseURL、模型、温度）
- 在线编辑和保存System Prompt
- Excel/CSV文件上传
- 批量API调用，实时进度显示
- 处理结果自动下载
- 兼容所有OpenAI格式API接口"

echo ""
echo "🔗 关联远程仓库..."
git remote remove origin 2>/dev/null
git remote add origin https://github.com/shellingrum-png/prompt-.git

echo ""
echo "📤 推送到GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "========================================="
echo "✅ 推送完成！刷新GitHub页面查看"
echo "========================================="
