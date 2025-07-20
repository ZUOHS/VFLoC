import json
import os
import re
from typing import List, Dict, Tuple
import requests
import time
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

folder = "thunderbird"  # 示例仓库

folder_to_name = {
    'All-Hands-AI': 'All-Hands-AI',
    'ant-design': 'ant-design',
    'AntennaPod': 'AntennaPod',
    'AppFlowy': 'AppFlowy',
    'bruno': 'bruno',
    'cgeo': 'cgeo',
    'ComfyUI': 'ComfyUI',
    'files': 'files',
    'florisboard': 'florisboard',
    'notepad': 'notepad-plus-plus',
    'TeamNewPipe_NewPipe': 'TeamNewPipe_NewPipe',
    'thunderbird': 'thunderbird',
    'uno': 'uno'
}

folder_to_extension_list = {
    'All-Hands-AI': ['.py', '.ts', '.tsx', '.jinja', '.jinja2', '.j2', '.css', '.less', '.scss', '.sass', '.js', '.jsx'],
    'ant-design': ['.ts', '.tsx', '.css', '.less', '.scss', '.sass'],
    'AntennaPod': ['.java', '.xml'],
    'AppFlowy': ['.dart', '.rs', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx', '.htm', '.html'],
    'bruno': ['.js', '.jsx', '.ts', '.tsx', '.htm', '.html', '.css', '.less', '.scss', '.sass'],
    'cgeo': ['.java', '.xml', '.htm', '.html'],
    'ComfyUI': ['.ts', '.tsx', '.vue', '.css', '.less', '.scss', '.sass'],
    'files': ['.cs', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx'],
    'florisboard': ['.kt', '.kts', '.xml', '.py', '.rs'],
    'notepad': ['.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx', '.htm', '.html', '.c', '.mm', '.py'],
    'TeamNewPipe_NewPipe': ['.java', '.kt', '.kts', '.xml', '.htm', '.html'],
    'thunderbird': ['.kt', '.kts', '.xml', '.java'],
    'uno': ['.cs', '.ts', '.tsx', '.m', '.h', '.java', '.js', '.jsx', '.css', '.less', '.scss', '.sass']
}



def extract_repo_info(html_url: str) -> tuple:
    """从GitHub URL提取仓库信息"""
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)', html_url)
    if match:
        owner, repo, issue_number = match.groups()
        return owner, repo, issue_number
    return None, None, None


def is_valid_file(filepath: str) -> bool:
    """判断文件是否为有效的源代码文件（排除测试文件）"""
    _, ext = os.path.splitext(filepath)
    if ext.lower() not in folder_to_extension_list[folder]:
        return False

    path_parts = filepath.replace('\\', '/').split('/')
    test_keywords = ['test', 'tests', 'spec', 'specs', '__test__', '__tests__']
    test_keywords_strict = ['__test__', '__tests__']

    for part in path_parts:
        part_lower = part.lower()
        if any(
                part_lower.startswith(k + '.') or
                part_lower.endswith('_' + k) or
                part_lower.startswith(k + '_') or
                part_lower.endswith(k)
                for k in test_keywords
        ):
            return False

        if any(
                k in part_lower
                for k in test_keywords_strict
        ):
            return False

    return True


def make_api_request_with_retry(url: str, max_retries: int = 3):
    """使用重试机制发送API请求"""
    for attempt in range(max_retries):
        try:
            print(f"尝试第 {attempt + 1} 次请求: {url}")
            response = requests.get(url, headers=HEADERS, timeout=30)
            return response

        except Exception as e:
            print(f"请求错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("重试次数已达上限")
                return None

    return None


def get_commit_files(owner: str, repo: str, commit_hash: str) -> Dict[str, List[str]]:
    """获取指定commit修改的文件列表，按状态分类"""
    empty_result = {'modified': [], 'added': [], 'removed': [], 'added_paths': []}

    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}"
        print(f"正在获取commit {commit_hash[:7]} 的文件信息...")

        response = make_api_request_with_retry(api_url)
        if response is None:
            print(f"错误: 无法获取commit {commit_hash[:7]} 的信息，所有重试都失败")
            return empty_result

        if response.status_code == 200:
            commit_data = response.json()
            result = {
                'modified': [],
                'added': [],
                'removed': [],
                'added_paths': []
            }

            if 'files' in commit_data:
                for file_info in commit_data['files']:
                    filename = file_info['filename']
                    status = file_info['status']

                    # 只处理有效的源代码文件
                    if not is_valid_file(filename):
                        continue

                    if status == 'modified':
                        result['modified'].append(filename)
                    elif status == 'added':
                        result['added'].append(filename)
                        # 提取新增文件的路径（目录部分）
                        file_path = os.path.dirname(filename)
                        if file_path and file_path not in result['added_paths']:
                            result['added_paths'].append(file_path)
                    elif status == 'removed':
                        result['removed'].append(filename)

                return result
            else:
                print(f"警告: commit {commit_hash[:7]} 没有文件变更信息")
                return empty_result

        else:
            print(f"错误: 获取commit {commit_hash[:7]} 失败，HTTP状态码: {response.status_code}")
            return empty_result

    except Exception as e:
        print(f"错误: 获取commit {commit_hash[:7]} 文件列表时发生未知错误: {type(e).__name__}: {e}")
        return empty_result


def get_commit_time(commit_hash: str, owner: str, repo: str) -> int:
    """获取commit的时间戳"""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}"

        response = make_api_request_with_retry(api_url)
        if response is None:
            print(f"错误: 无法获取commit {commit_hash[:7]} 的时间，所有重试都失败")
            return 0

        if response.status_code == 200:
            commit_data = response.json()

            if 'commit' in commit_data and 'author' in commit_data['commit'] and 'date' in commit_data['commit']['author']:
                commit_time = commit_data['commit']['author']['date']
                from datetime import datetime
                dt = datetime.fromisoformat(commit_time.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
                return timestamp

        return 0

    except Exception as e:
        print(f"错误: 获取commit时间时发生未知错误 (commit: {commit_hash[:7]}): {type(e).__name__}: {e}")
        return 0


def process_and_update_json(input_file_path: str, output_file_path: str):
    """处理JSON文件，重新计算图片数量并添加modified_files和add_paths"""

    # 读取原始JSON文件
    with open(input_file_path, 'r', encoding='utf-8') as f:
        issues_data = json.load(f)

    print(f"开始处理 {len(issues_data)} 个issues...")

    updated_issues = []

    for idx, issue in enumerate(issues_data, 1):
        print(f"处理第 {idx} 个issue: {issue['title']} (ID: {issue.get('number', 'N/A')})")


        updated_issue = issue.copy()


        # 提取仓库信息
        owner, repo, issue_number = extract_repo_info(issue['html_url'])
        if not owner or not repo:
            print(f"无法解析仓库信息: {issue['html_url']}")
            updated_issues.append(updated_issue)
            continue

        # 计算modified_files和add_paths
        commits = issue.get('commits', [])
        if commits:
            print(f"处理 {len(commits)} 个commits...")

            all_modified_files = set()
            all_added_paths = set()
            added_files_tracker = set()

            # 按时间顺序处理commits
            sorted_commits = sorted(commits, key=lambda c: get_commit_time(c, owner, repo))

            for commit in sorted_commits:
                commit_files = get_commit_files(owner, repo, commit)

                # 处理新增文件
                for added_file in commit_files['added']:
                    added_files_tracker.add(added_file)
                    file_path = os.path.dirname(added_file)
                    if file_path:
                        all_added_paths.add(file_path)

                # 处理修改的文件 - 但排除之前新增过的文件
                for modified_file in commit_files['modified']:
                    if modified_file not in added_files_tracker:
                        all_modified_files.add(modified_file)

                # 处理删除的文件 - 但排除之前新增过的文件
                for removed_file in commit_files['removed']:
                    if removed_file not in added_files_tracker:
                        all_modified_files.add(removed_file)

                time.sleep(0.5)  # 避免API请求过快

            # 添加到issue数据中
            updated_issue['modified_files'] = sorted(list(all_modified_files))
            updated_issue['added_paths'] = sorted(list(all_added_paths))

            print(f"Modified files: {len(all_modified_files)}, Added paths: {len(all_added_paths)}")
        else:
            print("没有commits信息")
            updated_issue['modified_files'] = []
            updated_issue['added_paths'] = []

        updated_issues.append(updated_issue)
        print("-" * 50)

    # 保存更新后的数据
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(updated_issues, f, indent=2, ensure_ascii=False)

    print(f"处理完成！更新后的数据已保存到: {output_file_path}")

    # 输出统计信息
    print("\n统计信息:")
    total_modified_files = sum(len(issue.get('modified_files', [])) for issue in updated_issues)
    total_added_paths = sum(len(issue.get('added_paths', [])) for issue in updated_issues)
    total_images = sum(issue.get('body_image_count', 0) for issue in updated_issues)

    print(f"总issues数: {len(updated_issues)}")
    print(f"总图片数: {total_images}")
    print(f"总modified files数: {total_modified_files}")
    print(f"总added paths数: {total_added_paths}")


def main():
    # 配置路径
    input_file_path = f"../issue_results/{folder}/{folder_to_name[folder]}_issues_with_code_checked_again.json"
    output_file_path = f"../issue_results/{folder}/{folder_to_name[folder]}_issues_with_code_updated.json"

    if not os.path.exists(input_file_path):
        print(f"错误: 输入文件不存在 {input_file_path}")
        return

    print(f"输入文件: {input_file_path}")
    print(f"输出文件: {output_file_path}")
    print()

    # 处理并更新JSON文件
    process_and_update_json(input_file_path, output_file_path)


if __name__ == "__main__":
    main()
