#!/bin/bash
# 快速开始脚本

echo "=== 批量提示词测试系统 ==="
echo ""

# 检查依赖
echo "1. 检查Python依赖..."
pip install pandas openpyxl pyyaml tqdm openai -q
echo "   依赖安装完成！"

echo ""
echo "2. 请编辑 config/api_config.yaml 配置你的API密钥"
echo "   例如: vi config/api_config.yaml"

echo ""
echo "3. 准备好数据后，运行以下命令之一："
echo ""
echo "   # 仅批量生成（提示词A）"
echo "   python main.py run --input ../outputs/会话处理结果.xlsx --column '提示词Ainput' --prompt-type prompt_a --output results/prompt_a_results.xlsx"
echo ""
echo "   # 仅批量生成（提示词B）"
echo "   python main.py run --input ../outputs/会话处理结果.xlsx --column '提示词Binput' --prompt-type prompt_b --output results/prompt_b_results.xlsx"
echo ""
echo "   # 完整流水线（生成 + 评估）"
echo "   python main.py pipeline --input ../outputs/会话处理结果.xlsx --column '提示词Ainput' --prompt-type prompt_a --output results/full_results.xlsx"
echo ""
echo "   # 仅评估已有结果"
echo "   python main.py evaluate --input results/prompt_a_results.xlsx --output results/evaluated.xlsx"
echo ""

mkdir -p results

echo "准备完成！"
