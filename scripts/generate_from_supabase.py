#!/usr/bin/env python3
"""
从 Supabase 拉取候选人数据，与本地 Excel 对话数据关联，
按 session_id 聚合（每个 session 只保留一条记录），
按照提示词模板格式生成 input 列。

模板格式：
# Inputs
- 候选人优势与特征标签：{candidate_tags}
- 目标岗位信息与核心要求：{target_job_info}
- 最近5轮聊天记录：{latest_dialogue}
*注：你需要从最新对话记录中，精准提炼出求职者目前最纠结、最顾虑的核心阻碍点。*

关联逻辑：Excel.session_id == Supabase.candidate_talent.external_userid

用法：
    export SUPABASE_URL="https://xxxx.supabase.co"
    export SUPABASE_KEY="your-service-role-key"
    python scripts/generate_from_supabase.py [--output results/output.xlsx]
"""
import os
import sys
import json
import random
import re
from pathlib import Path

import pandas as pd

try:
    from supabase import create_client, Client
except ImportError:
    print("请先安装：pip install supabase openpyxl pandas")
    sys.exit(1)

# ===== 路径配置 =====
BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = Path.home() / "Downloads/app/线上skill 框架对话数据-5.19.xlsx"
OUTPUT_DIR = BASE_DIR / "results"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ 请先设置环境变量：")
    print('  export SUPABASE_URL="https://xxxx.supabase.co"')
    print('  export SUPABASE_KEY="your-service-role-key"')
    sys.exit(1)

# 设置随机种子保证可复现
random.seed(42)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


INPUT_TEMPLATE = """# Inputs
- 候选人优势与特征标签：{candidate_tags}
- 目标岗位信息与核心要求：{target_job_info}
- 最近5轮聊天记录：{latest_dialogue}
*注：你需要从最新对话记录中，精准提炼出求职者目前最纠结、最顾虑的核心阻碍点。*"""


# ===== 模拟岗位数据池 =====
MOCK_JOBS = [
    {
        "title": "餐厅服务员",
        "salary": "5000-7000元/月",
        "location": "北京朝阳区",
        "requirements": "年龄18-35岁，有服务意识，能接受轮班",
        "benefits": "包吃住，月休4天，带薪年假",
        "match_level": "matched"
    },
    {
        "title": "普工/操作工",
        "salary": "6000-9000元/月",
        "location": "苏州工业园区",
        "requirements": "年龄18-45岁，能适应两班倒",
        "benefits": "提供住宿，有餐补，五险一金",
        "match_level": "matched"
    },
    {
        "title": "酒店客房保洁",
        "salary": "4000-6000元/月",
        "location": "上海浦东新区",
        "requirements": "年龄20-50岁，有责任心，能吃苦",
        "benefits": "长白班，月休4天，包吃住",
        "match_level": "matched"
    },
    {
        "title": "仓库管理员",
        "salary": "5500-7500元/月",
        "location": "广州白云区",
        "requirements": "年龄20-45岁，有仓管经验者优先",
        "benefits": "长白班，月休2天，餐补",
        "match_level": "partial_match"
    },
    {
        "title": "快递员",
        "salary": "7000-12000元/月",
        "location": "深圳南山区",
        "requirements": "年龄18-45岁，会骑电动车，有C1驾照优先",
        "benefits": "多劳多得，提供电动车，月休4天",
        "match_level": "partial_match"
    },
    {
        "title": "工厂质检员",
        "salary": "5000-8000元/月",
        "location": "东莞厚街镇",
        "requirements": "年龄18-40岁，视力好，能接受夜班",
        "benefits": "提供宿舍，有餐补，五险一金",
        "match_level": "not_matched"
    },
    {
        "title": "保安",
        "salary": "4500-6000元/月",
        "location": "杭州西湖区",
        "requirements": "年龄18-55岁，身高170cm以上",
        "benefits": "包吃住，月休4天，年底双薪",
        "match_level": "not_matched"
    },
    {
        "title": "餐饮后厨帮工",
        "salary": "4500-6500元/月",
        "location": "成都武侯区",
        "requirements": "年龄18-50岁，能吃苦耐劳",
        "benefits": "包吃住，月休3天",
        "match_level": "matched"
    },
    {
        "title": "电子厂普工",
        "salary": "5500-8500元/月",
        "location": "苏州昆山",
        "requirements": "年龄18-42岁，能接受加班",
        "benefits": "提供住宿，有厂车接送，五险一金",
        "match_level": "partial_match"
    },
    {
        "title": "超市理货员",
        "salary": "3500-5000元/月",
        "location": "南京鼓楼区",
        "requirements": "年龄18-50岁，有责任心",
        "benefits": "长白班，月休4天，有餐补",
        "match_level": "not_matched"
    },
    {
        "title": "美容师",
        "salary": "5000-8000元/月",
        "location": "重庆渝北区",
        "requirements": "年龄18-35岁，有美容经验者优先",
        "benefits": "包吃住，月休4天，有提成",
        "match_level": "partial_match"
    },
    {
        "title": "搬运工",
        "salary": "6000-9000元/月",
        "location": "武汉洪山区",
        "requirements": "年龄18-50岁，体力好，能吃苦",
        "benefits": "日结/月结，包吃住",
        "match_level": "matched"
    }
]


def fetch_supabase_data():
    """从 candidate_talent 拉取所有数据"""
    print("\n📥 正在从 Supabase 拉取 candidate_talent...")
    try:
        resp = supabase.table("candidate_talent").select("*").execute()
        if not resp.data:
            print("   ⚠️  表为空")
            return {}

        mapping = {}
        for row in resp.data:
            eid = row.get("external_userid", "")
            if eid:
                mapping[eid] = row

        print(f"   ✅ 拉取 {len(mapping)} 条记录")
        return mapping
    except Exception as e:
        print(f"   ❌ 查询失败：{e}")
        return {}


def extract_dialogue_info(group):
    """
    从对话中提取求职意向信息（城市、岗位类型等）
    """
    all_text = ""
    for _, row in group.iterrows():
        user_msg = str(row.get("user_message", ""))
        if user_msg and user_msg != "nan":
            all_text += user_msg + " "

    # 常见城市关键词
    cities = ["北京", "上海", "广州", "深圳", "苏州", "杭州", "成都", "重庆", "南京", "武汉",
              "东莞", "张家港", "昆山", "朝阳", "海淀", "浦东", "南山", "武侯", "白云"]

    # 常见岗位关键词
    jobs = {
        "服务员": ["服务员", "餐厅", "酒店服务"],
        "普工": ["普工", "操作工", "工厂", "电子厂"],
        "保洁": ["保洁", "客房"],
        "搬运工": ["搬运", "力工"],
        "保安": ["保安", "门卫"],
        "快递": ["快递", "配送"],
        "仓管": ["仓管", "仓库"],
        "后厨": ["后厨", "帮厨", "厨房"],
        "美容": ["美容", "美体"],
        "理货": ["理货", "超市"]
    }

    found_cities = []
    for city in cities:
        if city in all_text:
            found_cities.append(city)

    found_jobs = []
    for job_name, keywords in jobs.items():
        for kw in keywords:
            if kw in all_text:
                found_jobs.append(job_name)
                break

    return {
        "cities": found_cities[:2] if found_cities else [],
        "jobs": found_jobs[:2] if found_jobs else [],
        "raw_text": all_text[:200]
    }


def generate_mock_target_job_info(dialogue_info, session_index):
    """
    根据对话内容和随机策略生成模拟岗位信息。
    策略：
    - 如果对话提到了具体岗位和城市，生成匹配的岗位
    - 如果只提到了城市，随机生成一个该城市的岗位
    - 如果都没提到，随机生成
    - 引入不匹配、部分匹配的场景
    """
    cities = dialogue_info.get("cities", [])
    jobs = dialogue_info.get("jobs", [])

    # 随机选择匹配等级
    match_type = random.choice(["matched", "matched", "partial_match", "not_matched"])

    # 筛选合适匹配度的岗位
    candidates = [j for j in MOCK_JOBS if j["match_level"] == match_type]
    if not candidates:
        candidates = MOCK_JOBS

    # 优先选择与对话相关的岗位
    if jobs and match_type in ["matched", "partial_match"]:
        related = [j for j in candidates if any(job in j["title"] for job in jobs)]
        if related:
            candidates = related

    # 优先选择与对话相关的城市
    if cities and match_type == "matched":
        city_related = [j for j in candidates if any(city in j["location"] for city in cities)]
        if city_related:
            candidates = city_related

    # 随机选一个
    job = random.choice(candidates)

    # 如果对话有城市信息，尽量用对话中的城市
    if cities and match_type == "matched":
        job = job.copy()
        job["location"] = random.choice(cities) + random.choice(["区", "市", ""])

    # 生成格式化的岗位信息
    parts = []
    parts.append(f"岗位名称: {job['title']}")
    parts.append(f"工作地点: {job['location']}")
    parts.append(f"薪资范围: {job['salary']}")
    parts.append(f"岗位要求: {job['requirements']}")
    parts.append(f"福利待遇: {job['benefits']}")

    # 添加匹配度标签（用于调试）
    match_labels = {
        "matched": "✅ 匹配",
        "partial_match": "⚠️ 部分匹配",
        "not_matched": "❌ 不匹配"
    }
    parts.append(f"匹配状态: {match_labels[job['match_level']]}")

    return "\n".join(parts)


def format_candidate_tags(db_row):
    """格式化候选人标签"""
    tags = db_row.get("candidate_tags", {}) if db_row else {}
    if not tags or tags == {}:
        return "待分析"

    parts = []
    if isinstance(tags, dict):
        for key, value in tags.items():
            if isinstance(value, dict):
                display = value.get("raw_value", value.get("value", ""))
            else:
                display = str(value)
            if display:
                parts.append(f"{key}: {display}")

    return "\n".join(parts) if parts else "待分析"


def format_target_job_info_from_db(db_row):
    """从数据库 ext_fields 提取岗位信息（备用）"""
    ext = db_row.get("ext_fields", {}) if db_row else {}
    if not ext:
        return None

    # 只有当有明确的岗位意向时才返回
    if not (ext.get("job_preference") or ext.get("looking_for")):
        return None

    parts = []
    if ext.get("job_preference"):
        parts.append(f"求职意向: {ext['job_preference']}")
    if ext.get("looking_for"):
        parts.append(f"正在寻找: {ext['looking_for']}")
    if ext.get("age"):
        parts.append(f"年龄: {ext['age']}")
    if ext.get("gender"):
        parts.append(f"性别: {ext['gender']}")
    if ext.get("work_experience_years"):
        parts.append(f"工作经验: {ext['work_experience_years']}年")
    if ext.get("education_level"):
        parts.append(f"学历: {ext['education_level']}")

    return "\n".join(parts) if parts else None


def get_latest_dialogue(group, n=5):
    """
    从该 session 的所有对话中，取最近 n 轮。
    """
    group = group.sort_values("event_time")
    messages = []
    for _, row in group.iterrows():
        user_msg = str(row.get("user_message", ""))
        ai_msg = str(row.get("assistant_message", ""))
        if user_msg and user_msg != "nan":
            messages.append(f"求职者: {user_msg}")
        if ai_msg and ai_msg != "nan":
            messages.append(f"AI: {ai_msg}")

    max_messages = n * 2
    latest = messages[-max_messages:] if len(messages) > max_messages else messages
    return "\n".join(latest) if latest else "无对话记录"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="从 Supabase 关联数据生成 input（按 session 聚合）")
    parser.add_argument("--output", default=None, help="输出文件路径")
    parser.add_argument("--show-sample", action="store_true", help="打印前3条完整样例")
    parser.add_argument("--use-mock-jobs", action="store_true", default=True,
                        help="使用模拟岗位数据补充缺失的目标岗位信息")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = Path(args.output) if args.output else OUTPUT_DIR / f"generated_input_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx"

    # 1. 读取本地 Excel
    print(f"📂 读取本地 Excel：{EXCEL_PATH}")
    if not EXCEL_PATH.exists():
        print(f"   ❌ 文件不存在：{EXCEL_PATH}")
        sys.exit(1)

    df = pd.read_excel(EXCEL_PATH)
    print(f"   原始: {len(df)} 条记录")

    # 2. 按 session_id 聚合
    print("\n🔄 正在按 session_id 聚合...")
    grouped = df.groupby("session_id")
    print(f"   聚合后: {grouped.ngroups} 个 session")

    # 3. 从 Supabase 拉取数据
    db_map = fetch_supabase_data()

    # 4. 按模板生成 input
    print(f"\n🔄 正在按模板生成 input 列...")

    records = []
    empty_tags_count = 0
    mock_job_count = 0

    for idx, (session_id, group) in enumerate(grouped):
        group = group.sort_values("event_time")
        first_row = group.iloc[0]
        db_row = db_map.get(session_id)

        # 候选人标签
        candidate_tags = format_candidate_tags(db_row)
        if candidate_tags == "待分析":
            empty_tags_count += 1

        # 目标岗位信息
        if args.use_mock_jobs:
            # 使用模拟岗位数据（覆盖数据库信息）
            dialogue_info = extract_dialogue_info(group)
            target_job_info = generate_mock_target_job_info(dialogue_info, idx)
            mock_job_count += 1
        else:
            # 优先使用数据库信息
            db_job_info = format_target_job_info_from_db(db_row)
            if db_job_info:
                target_job_info = db_job_info
            else:
                # 数据库没有岗位信息时，使用模拟数据
                dialogue_info = extract_dialogue_info(group)
                target_job_info = generate_mock_target_job_info(dialogue_info, idx)
                mock_job_count += 1

        # 最近5轮对话
        latest_dialogue = get_latest_dialogue(group)

        # 按模板组装
        input_text = INPUT_TEMPLATE.format(
            candidate_tags=candidate_tags,
            target_job_info=target_job_info,
            latest_dialogue=latest_dialogue
        )

        # 构造记录
        record = {
            "session_id": session_id,
            "dt": first_row.get("dt"),
            "source": first_row.get("source"),
            "identity_key": first_row.get("identity_key"),
            "user_id": first_row.get("user_id"),
            "dialogue_count": len(group),
            "external_userid": db_row.get("external_userid", "") if db_row else "",
            "candidate_name": db_row.get("name", "") if db_row else "",
            "input": input_text,
        }
        records.append(record)

    result_df = pd.DataFrame(records)
    print(f"   ✅ 已生成 {len(result_df)} 条记录（每个 session 一条）")
    print(f"   统计:")
    print(f"     - candidate_tags 为空: {empty_tags_count}/{len(result_df)}")
    print(f"     - 使用模拟岗位数据: {mock_job_count}/{len(result_df)}")

    # 5. 保存
    print(f"\n💾 保存结果到：{output_path}")
    result_df.to_excel(output_path, index=False)
    print(f"   ✅ 完成！共 {len(result_df)} 条记录")

    # 打印样例
    n = 3 if args.show_sample else 3
    print(f"\n 前 {n} 条样例：")
    for i in range(min(n, len(result_df))):
        print(f"\n{'='*60}")
        sid = result_df.iloc[i]["session_id"]
        dcount = result_df.iloc[i]["dialogue_count"]
        print(f"Session: {sid[:50]} ({dcount}轮对话)")
        print(f"候选人: {result_df.iloc[i]['candidate_name']}")
        print(f"{'='*60}")
        print(result_df.iloc[i]["input"])


if __name__ == "__main__":
    main()
