#!/usr/bin/env python3
"""
批量提示词测试系统主程序
用法:
    python main.py run --input data/input.xlsx --prompt-type prompt_a --output results/output.xlsx
    python main.py evaluate --input results/output.xlsx --output results/evaluated.xlsx
"""
import os
import sys
import argparse
import pandas as pd

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.batch_runner import BatchRunner
from scripts.evaluator import ResultEvaluator


def run_batch(args):
    """执行批量生成"""
    print("=" * 60)
    print("开始批量执行...")
    print("=" * 60)
    
    runner = BatchRunner(config_path='config')
    
    # 检查是否有自定义提示词和温度
    custom_prompt = None
    if args.custom_prompt:
        if os.path.exists(args.custom_prompt):
            with open(args.custom_prompt, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()
            print(f"已加载自定义提示词文件: {args.custom_prompt}")
        else:
            custom_prompt = args.custom_prompt
    
    temperature = args.temperature if args.temperature else None
    if temperature:
        print(f"使用自定义温度: {temperature}")
    
    # 执行批量处理
    result_df = runner.process_from_excel(
        excel_path=args.input,
        input_column=args.column,
        prompt_type=args.prompt_type,
        output_path=args.output,
        temperature=temperature,
        delay=args.delay
    )
    
    print(f"\n批量执行完成！共处理 {len(result_df)} 条数据")
    return result_df


def run_evaluate(args):
    """执行批量评估"""
    print("=" * 60)
    print("开始批量评估...")
    print("=" * 60)
    
    evaluator = ResultEvaluator(config_path='config')
    
    result_df = evaluator.evaluate_from_excel(
        excel_path=args.input,
        input_column=args.input_column,
        output_column=args.output_column,
        prompt_type_column=args.prompt_column,
        result_output_path=args.output,
        delay=args.delay
    )
    
    print(f"\n评估完成！共评估 {len(result_df)} 条数据")
    return result_df


def run_pipeline(args):
    """执行完整流水线：生成 + 评估"""
    print("=" * 60)
    print("开始执行完整流水线（生成 + 评估）...")
    print("=" * 60)
    
    # 第一步：批量生成
    runner = BatchRunner(config_path='config')
    temp_output = args.output.replace('.xlsx', '_temp.xlsx') if args.output else None
    
    result_df = runner.process_from_excel(
        excel_path=args.input,
        input_column=args.column,
        prompt_type=args.prompt_type,
        output_path=temp_output,
        temperature=args.temperature,
        delay=args.delay
    )
    
    # 第二步：批量评估
    evaluator = ResultEvaluator(config_path='config')
    
    final_df = evaluator.evaluate_from_excel(
        excel_path=temp_output if temp_output else args.input,
        input_column='input',
        output_column='output',
        prompt_type_column='prompt_type',
        result_output_path=args.output,
        delay=args.eval_delay
    )
    
    # 删除临时文件
    if temp_output and os.path.exists(temp_output):
        os.remove(temp_output)
    
    print(f"\n流水线执行完成！")
    return final_df


def main():
    parser = argparse.ArgumentParser(description='批量提示词测试系统')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 批量运行命令
    run_parser = subparsers.add_parser('run', help='批量执行提示词生成')
    run_parser.add_argument('--input', required=True, help='输入Excel文件路径')
    run_parser.add_argument('--column', default='提示词Ainput', help='输入内容所在列名')
    run_parser.add_argument('--prompt-type', default='prompt_a', help='提示词类型 (prompt_a / prompt_b)')
    run_parser.add_argument('--custom-prompt', help='自定义提示词（文本或文件路径）')
    run_parser.add_argument('--temperature', type=float, help='温度参数')
    run_parser.add_argument('--delay', type=float, default=1.0, help='每次调用间隔(秒)')
    run_parser.add_argument('--output', required=True, help='输出Excel文件路径')
    
    # 评估命令
    eval_parser = subparsers.add_parser('evaluate', help='批量评估结果')
    eval_parser.add_argument('--input', required=True, help='输入Excel文件路径')
    eval_parser.add_argument('--input-column', default='input', help='输入内容列名')
    eval_parser.add_argument('--output-column', default='output', help='生成结果列名')
    eval_parser.add_argument('--prompt-column', default='prompt_type', help='提示词类型列名')
    eval_parser.add_argument('--delay', type=float, default=1.0, help='每次调用间隔(秒)')
    eval_parser.add_argument('--output', required=True, help='输出Excel文件路径')
    
    # 完整流水线命令
    pipeline_parser = subparsers.add_parser('pipeline', help='完整流水线（生成+评估）')
    pipeline_parser.add_argument('--input', required=True, help='输入Excel文件路径')
    pipeline_parser.add_argument('--column', default='提示词Ainput', help='输入内容所在列名')
    pipeline_parser.add_argument('--prompt-type', default='prompt_a', help='提示词类型')
    pipeline_parser.add_argument('--temperature', type=float, help='温度参数')
    pipeline_parser.add_argument('--delay', type=float, default=1.0, help='生成调用间隔(秒)')
    pipeline_parser.add_argument('--eval-delay', type=float, default=1.0, help='评估调用间隔(秒)')
    pipeline_parser.add_argument('--output', required=True, help='最终输出Excel文件路径')
    
    args = parser.parse_args()
    
    if args.command == 'run':
        run_batch(args)
    elif args.command == 'evaluate':
        run_evaluate(args)
    elif args.command == 'pipeline':
        run_pipeline(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
