import pandas as pd
import json
import os

def filter_issues():
    # 文件路径
    excel_path = "../issue_results/All-Hands-AI_OpenHands_issues_with_analysis_2025-06-13_02-21-15.xlsx"
    output_path = r"D:\Code2025S\enhancement_vision\issue_results\All-Hands-AI_completed_with_images.json"

    # 读取Excel文件
    print(f"正在读取 {excel_path}...")
    try:
        df = pd.read_excel(excel_path)
        print(f"成功读取数据，共 {len(df)} 条记录")

        # 显示数据结构和列名
        print(f"数据列: {', '.join(df.columns)}")

        # 筛选条件: state_reason为completed且total_image_count不为0
        filtered_df = df[(df['state_reason'] == 'completed') & (df['body_image_count'] > 0)]

        print(f"筛选后数据: {len(filtered_df)} 条记录")

        # 将筛选后的数据转为字典列表
        result = filtered_df.to_dict(orient='records')

        # 保存为JSON文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"筛选完成! 结果已保存至: {output_path}")
        return True

    except Exception as e:
        print(f"处理失败: {e}")
        return False

if __name__ == "__main__":
    filter_issues()
