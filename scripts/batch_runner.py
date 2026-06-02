"""
批量执行模块
负责批量调用API生成结果
"""
import os
import json
import time
import yaml
import pandas as pd
from openai import OpenAI
from typing import List, Dict, Any
from tqdm import tqdm


class BatchRunner:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.load_config()
        self.init_client()
        
    def load_config(self):
        """加载API配置"""
        with open(os.path.join(self.config_path, 'api_config.yaml'), 'r', encoding='utf-8') as f:
            self.api_config = yaml.safe_load(f)
        
        with open(os.path.join(self.config_path, 'prompts_config.yaml'), 'r', encoding='utf-8') as f:
            self.prompts_config = yaml.safe_load(f)
    
    def init_client(self):
        """初始化OpenAI客户端"""
        self.client = OpenAI(
            api_key=self.api_config['openai']['api_key'],
            base_url=self.api_config['openai']['base_url']
        )
    
    def call_api(self, system_prompt: str, user_input: str, 
                 temperature: float = None, max_tokens: int = None) -> str:
        """调用OpenAI API"""
        if temperature is None:
            temperature = self.api_config['openai']['temperature']
        if max_tokens is None:
            max_tokens = self.api_config['openai']['max_tokens']
        
        try:
            response = self.client.chat.completions.create(
                model=self.api_config['openai']['model'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API调用失败: {str(e)}")
            return f"ERROR: {str(e)}"
    
    def process_single(self, input_data: str, prompt_type: str, 
                      custom_prompt: str = None, temperature: float = None) -> Dict:
        """处理单条数据"""
        if prompt_type in self.prompts_config:
            system_prompt = self.prompts_config[prompt_type]['system_prompt']
        else:
            system_prompt = custom_prompt if custom_prompt else "你是一个有用的助手。"
        
        result = self.call_api(system_prompt, input_data, temperature)
        
        return {
            "input": input_data,
            "prompt_type": prompt_type,
            "system_prompt": system_prompt[:200] + "...",
            "temperature": temperature if temperature else self.api_config['openai']['temperature'],
            "output": result
        }
    
    def process_batch(self, input_list: List[str], prompt_type: str, 
                     custom_prompt: str = None, temperature: float = None,
                     delay: float = 1.0) -> List[Dict]:
        """批量处理数据"""
        results = []
        print(f"开始批量处理，共 {len(input_list)} 条数据...")
        
        for i, input_data in enumerate(tqdm(input_list)):
            result = self.process_single(input_data, prompt_type, custom_prompt, temperature)
            result['index'] = i
            results.append(result)
            time.sleep(delay)  # 避免限流
        
        return results
    
    def process_from_excel(self, excel_path: str, input_column: str, 
                          prompt_type: str, output_path: str = None,
                          temperature: float = None, delay: float = 1.0) -> pd.DataFrame:
        """从Excel文件读取数据并批量处理"""
        df = pd.read_excel(excel_path)
        input_list = df[input_column].dropna().tolist()
        
        print(f"从Excel读取到 {len(input_list)} 条有效数据")
        
        results = self.process_batch(input_list, prompt_type, temperature=temperature, delay=delay)
        
        # 转换为DataFrame
        result_df = pd.DataFrame(results)
        
        # 合并原始数据
        df['index'] = df.index
        result_df = result_df.merge(df, left_on='index', right_index=True, how='left', suffixes=('', '_original'))
        
        if output_path:
            result_df.to_excel(output_path, index=False)
            print(f"结果已保存到: {output_path}")
        
        return result_df


if __name__ == "__main__":
    # 测试代码
    runner = BatchRunner(config_path='../config')
    print("批量执行模块加载成功！")
