#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本用于处理 issue_results 中的 *_issues_with_code.json 文件
- 移除 changed_files 字段
- 在 html_url 后面添加 pr_url 字段
- 在最后添加 commit_check 字段并留空
"""

import json
import os
import glob
from pathlib import Path

repo_name = "uno"
INPUT_JSON_FILE = f'../issue_results/{repo_name}/intermediates/{repo_name}_issues_with_code.json'
OUTPUT_JSON_FILE = f'../issue_results/{repo_name}/intermediates/{repo_name}_issues_with_code_processed.json'

def process_code_json_file(input_file_path, output_file_path):
    """
    处理单个 with_code.json 文件

    Args:
        input_file_path (str): 输入文件路径
        output_file_path (str): 输出文件路径
    """
    try:
        # 读取原始JSON文件
        with open(input_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 处理数据
        processed_data = []

        for item in data:
            # 创建新的字典，保持字段顺序
            new_item = {}

            # 复制所有字段，在适当位置插入新字段
            for key, value in item.items():
                new_item[key] = value

                # 在 html_url 后面添加 pr_url 字段
                if key == 'html_url':
                    # 根据 pr_number 构建 pr_url
                    if 'pr_number' in item and item['pr_number'] and str(item['pr_number']).lower() != 'nan':
                        # 从 html_url 提取仓库基础URL
                        html_url = item['html_url']
                        if '/issues/' in html_url:
                            repo_base_url = html_url.split('/issues/')[0]
                            pr_url = f"{repo_base_url}/pull/{item['pr_number']}"
                        else:
                            pr_url = ""
                    else:
                        pr_url = ""
                    new_item['pr_url'] = pr_url

                # 跳过 changed_files 字段
                if key == 'changed_files':
                    del new_item[key]

            # 在最后添加 commit_check 字段
            new_item['commit_check'] = ""

            processed_data.append(new_item)

        # 写入处理后的数据
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 处理完成: {input_file_path} -> {output_file_path}")
        print(f"   处理了 {len(processed_data)} 个issue")

    except Exception as e:
        print(f"❌ 处理文件时出错 {input_file_path}: {str(e)}")

def main():
    # """主函数"""
    # # 设置路径
    # current_dir = Path(__file__).parent
    # issue_results_dir = current_dir.parent / 'issue_results'
    #
    # # 查找所有 *_issues_with_code.json 文件
    # pattern = str(issue_results_dir / '*_issues_with_code.json')
    # code_files = glob.glob(pattern)
    #
    # if not code_files:
    #     print("❌ 未找到任何 *_issues_with_code.json 文件")
    #     return
    #
    # print(f"📁 找到 {len(code_files)} 个待处理文件:")
    # for file_path in code_files:
    #     print(f"   {os.path.basename(file_path)}")
    #
    # print("\n🔄 开始处理文件...")
    #
    # # 处理每个文件
    # for input_file in code_files:
    #     input_path = Path(input_file)
    #
    #     # 构建输出文件名：原文件名 + _processed
    #     name_parts = input_path.stem.split('_')
    #     if name_parts[-1] == 'code':
    #         name_parts[-1] = 'code_processed'
    #     else:
    #         name_parts.append('processed')
    #
    #     output_filename = '_'.join(name_parts) + '.json'
    #     output_path = input_path.parent / output_filename
    #
    #     # 处理文件
    #     process_code_json_file(str(input_path), str(output_path))
    process_code_json_file(INPUT_JSON_FILE, OUTPUT_JSON_FILE)
    print("\n✅ 所有文件处理完成!")


if __name__ == "__main__":
    main()
