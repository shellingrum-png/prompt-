#!/usr/bin/env python3
"""
演示脚本 - 展示系统如何工作（不实际调用API）
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("批量提示词测试系统 - 功能演示")
print("=" * 70)
print()

# 1. 展示配置
print("【1】配置文件示例")
print("-" * 40)
with open('config/api_config.yaml', 'r', encoding='utf-8') as f:
    print(f.read())
print()

print("提示词配置示例:")
with open('config/prompts_config.yaml', 'r', encoding='utf-8') as f:
    content = f.read()
    print(content[:500] + "...\n")

# 2. 展示输入数据
print("【2】输入数据示例")
print("-" * 40)
import pandas as pd
input_file = '../outputs/会话处理结果.xlsx'
if os.path.exists(input_file):
    df = pd.read_excel(input_file)
    print(f"输入文件: {input_file}")
    print(f"数据条数: {len(df)}")
    print(f"列名: {df.columns.tolist()}")
    print()
    print("第一条数据预览:")
    print(f"session_id: {df.iloc[0]['session_id']}")
    print(f"候选人姓名: {df.iloc[0]['候选人姓名']}")
    print(f"提示词Ainput (前300字):")
    print(str(df.iloc[0]['提示词Ainput'])[:300] + "...")
    print()

# 3. 展示使用方法
print("【3】使用方法")
print("-" * 40)
print("修改API配置后，运行以下命令：")
print()
print("1) 仅批量生成：")
print("   python main.py run --input ../outputs/会话处理结果.xlsx \\")
print("       --column '提示词Ainput' --prompt-type prompt_a \\")
print("       --output results/prompt_a_results.xlsx")
print()
print("2) 仅评估已有结果：")
print("   python main.py evaluate --input results/prompt_a_results.xlsx \\")
print("       --output results/evaluated.xlsx")
print()
print("3) 完整流水线（生成+评估）：")
print("   python main.py pipeline --input ../outputs/会话处理结果.xlsx \\")
print("       --column '提示词Ainput' --prompt-type prompt_a \\")
print("       --output results/full_results.xlsx")
print()

# 4. 展示预期输出
print("【4】输出示例")
print("-" * 40)
sample_output = {
    "accuracy_score": 9,
    "accuracy_reason": "输出格式完全符合XML要求，信息提取准确",
    "readability_score": 8,
    "readability_reason": "格式清晰，内容易读",
    "completeness_score": 9,
    "completeness_reason": "包含了所有必要字段",
    "overall_score": 8.67,
    "suggestions": "可以进一步优化对话格式的对齐"
}
print("评估输出JSON示例:")
print(json.dumps(sample_output, ensure_ascii=False, indent=2))
print()

print("=" * 70)
print("演示结束！请先配置API密钥，然后运行实际命令")
print("=" * 70)
