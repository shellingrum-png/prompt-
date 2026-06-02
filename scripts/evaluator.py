"""
结果评估打分模块
负责对批量生成的结果进行质量评估
"""
import os
import json
import time
import yaml
import pandas as pd
from openai import OpenAI
from typing import List, Dict, Any
from tqdm import tqdm


class ResultEvaluator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.load_config()
        self.init_client()
        
    def load_config(self):
        """加载配置"""
        with open(os.path.join(self.config_path, 'api_config.yaml'), 'r', encoding='utf-8') as f:
            self.api_config = yaml.safe_load(f)
        
        with open(os.path.join(self.config_path, 'prompts_config.yaml'), 'r', encoding='utf-8') as f:
            self.prompts_config = yaml.safe_load(f)
    
    def init_client(self):
        """初始化OpenAI客户端"""
        self.eval_client = OpenAI(
            api_key=self.api_config['evaluation']['api_key'],
            base_url=self.api_config['evaluation']['base_url']
        )
    
    def evaluate_single(self, input_data: str, output_data: str, 
                       prompt_type: str = None) -> Dict:
        """评估单条结果"""
        system_prompt = self.prompts_config['evaluation_prompt']['system_prompt']
        
        user_content = f"""
        【输入数据】：
        {input_data}
        
        【生成结果】：
        {output_data}
        
        【提示词类型】：{prompt_type if prompt_type else '通用'}
        
        请对上述生成结果进行评估打分。
        """
        
        try:
            response = self.eval_client.chat.completions.create(
                model=self.api_config['evaluation']['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=self.api_config['evaluation']['temperature'],
                response_format={"type": "json_object"}
            )
            
            eval_result = json.loads(response.choices[0].message.content)
            return eval_result
        except Exception as e:
            print(f"评估失败: {str(e)}")
            return {
                "accuracy_score": 0,
                "accuracy_reason": f"评估失败: {str(e)}",
                "readability_score": 0,
                "readability_reason": f"评估失败: {str(e)}",
                "completeness_score": 0,
                "completeness_reason": f"评估失败: {str(e)}",
                "overall_score": 0,
                "suggestions": "评估过程出错"
            }
    
    def evaluate_batch(self, results_list: List[Dict], 
                      delay: float = 1.0) -> List[Dict]:
        """批量评估结果"""
        evaluated_results = []
        print(f"开始批量评估，共 {len(results_list)} 条结果...")
        
        for i, item in enumerate(tqdm(results_list)):
            input_data = item.get('input', '')
            output_data = item.get('output', '')
            prompt_type = item.get('prompt_type', '')
            
            eval_result = self.evaluate_single(input_data, output_data, prompt_type)
            
            # 合并结果
            merged = {**item, **{f"eval_{k}": v for k, v in eval_result.items()}}
            evaluated_results.append(merged)
            
            time.sleep(delay)
        
        return evaluated_results
    
    def evaluate_from_excel(self, excel_path: str, 
                           input_column: str = 'input',
                           output_column: str = 'output',
                           prompt_type_column: str = None,
                           result_output_path: str = None,
                           delay: float = 1.0) -> pd.DataFrame:
        """从Excel文件读取结果并批量评估"""
        df = pd.read_excel(excel_path)
        print(f"从Excel读取到 {len(df)} 条数据")
        
        # 准备数据
        results_list = []
        for idx, row in df.iterrows():
            results_list.append({
                'index': idx,
                'input': str(row[input_column]) if pd.notna(row[input_column]) else '',
                'output': str(row[output_column]) if pd.notna(row[output_column]) else '',
                'prompt_type': str(row[prompt_type_column]) if prompt_type_column and pd.notna(row.get(prompt_type_column)) else ''
            })
        
        # 批量评估
        evaluated_results = self.evaluate_batch(results_list, delay)
        
        # 转换为DataFrame
        eval_df = pd.DataFrame(evaluated_results)
        
        # 合并原始数据
        df['index'] = df.index
        final_df = eval_df.merge(df, left_on='index', right_index=True, how='left', suffixes=('', '_original'))
        
        if result_output_path:
            final_df.to_excel(result_output_path, index=False)
            print(f"评估结果已保存到: {result_output_path}")
            
            # 生成统计报告
            self.generate_statistics(final_df, result_output_path.replace('.xlsx', '_statistics.txt'))
        
        return final_df
    
    def generate_statistics(self, df: pd.DataFrame, output_path: str):
        """生成统计报告"""
        stats = []
        stats.append("=" * 60)
        stats.append("批量评估统计报告")
        stats.append("=" * 60)
        stats.append(f"\n总样本数: {len(df)}")
        
        # 各维度平均分
        if 'eval_overall_score' in df.columns:
            stats.append(f"\n整体平均分: {df['eval_overall_score'].mean():.2f} / 10")
            stats.append(f"- 准确性平均分: {df['eval_accuracy_score'].mean():.2f} / 10")
            stats.append(f"- 可读性平均分: {df['eval_readability_score'].mean():.2f} / 10")
            stats.append(f"- 完整性平均分: {df['eval_completeness_score'].mean():.2f} / 10")
            
            # 分数分布
            stats.append(f"\n整体分数分布:")
            stats.append(f"- 9-10分: {len(df[df['eval_overall_score'] >= 9])} 条")
            stats.append(f"- 7-8分: {len(df[(df['eval_overall_score'] >= 7) & (df['eval_overall_score'] < 9)])} 条")
            stats.append(f"- 5-6分: {len(df[(df['eval_overall_score'] >= 5) & (df['eval_overall_score'] < 7)])} 条")
            stats.append(f"- 0-4分: {len(df[df['eval_overall_score'] < 5])} 条")
        
        # 低分案例
        low_score = df[df['eval_overall_score'] < 6]
        if len(low_score) > 0:
            stats.append(f"\n低分案例（<6分）: {len(low_score)} 条")
            for idx, row in low_score.head(5).iterrows():
                stats.append(f"\n--- 案例 {idx} ---")
                stats.append(f"分数: {row['eval_overall_score']:.2f}")
                stats.append(f"建议: {row['eval_suggestions'][:100]}...")
        
        stats_text = "\n".join(stats)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(stats_text)
        
        print(stats_text)
        print(f"\n统计报告已保存到: {output_path}")


if __name__ == "__main__":
    # 测试代码
    evaluator = ResultEvaluator(config_path='../config')
    print("评估模块加载成功！")
