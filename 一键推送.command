#!/bin/bash
cd "$(dirname "$0")"

echo "========================================="
echo "🚀 批量提示词测试系统 - 一键推送到GitHub"
echo "========================================="
echo ""

# 检查是否已经有remote了
if ! git remote | grep -q origin; then
    echo "🔗 添加远程仓库..."
    git remote add origin https://github.com/shellingrum-png/prompt-.git
fi

echo ""
echo "📤 推送到GitHub..."
git push -u origin main

echo ""
echo "========================================="
echo "✅ 推送完成！请刷新GitHub页面查看"
echo "========================================="
echo ""
read -p "按回车键退出..."
