import json
import requests
import time
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# --- 配置 ---
load_dotenv()
GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")
repo_name = "ant-design"
INPUT_JSON_FILE = f'../issue_results/{repo_name}/{repo_name}_issues_with_closing_pr_checked.json'
OUTPUT_JSON_FILE = f'../issue_results/{repo_name}/intermediates/{repo_name}_issues_with_code.json'
MAX_RETRIES = 5  # 最大重试次数


# --- GitHub API 辅助函数 ---
def handle_rate_limit(response):
    """
    处理API速率限制，等待限制重置后返回
    """
    # 处理多种可能的速率限制状态码: 429(标准限流), 403(可能的认证和限流混合), 443(SSL相关或自定义限流)
    if response.status_code in [429, 403, 443]:
        # 尝试从响应头获取限制重置时间
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))

        # 检查响应内容是否提到rate limit
        is_rate_limit = False
        try:
            response_json = response.json()
            message = response_json.get('message', '').lower()
            if 'rate limit' in message or 'api rate limit' in message:
                is_rate_limit = True
        except:
            # 无法解析JSON，检查响应文本
            try:
                response_text = response.text.lower()
                if 'rate limit' in response_text or 'api rate limit' in response_text:
                    is_rate_limit = True
            except:
                pass

        # 确认是速率限制错误或直接处理这三种状态码
        if is_rate_limit or response.status_code in [429, 443]:
            if reset_time > 0:
                current_time = int(time.time())
                sleep_time = reset_time - current_time + 5  # 额外等待5秒以确保重置完成
                if sleep_time > 0:
                    print(f"遇到API速率限制 (状态码: {response.status_code})，等待 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                    return True
            else:  # 如果无法获取重置时间，默认等待一定时间
                if response.status_code == 429:
                    wait_time = 60  # 标准限流, 等待60秒
                elif response.status_code == 443:
                    wait_time = 90  # SSL相关或自定义限流, 等待90秒
                else:  # 403
                    wait_time = 120  # 可能是长时间限流, 等待更长时间

                print(f"遇到API速率限制 (状态码: {response.status_code})，无法获取重置时间，等待{wait_time}秒后重试...")
                time.sleep(wait_time)
                return True
    return False

def get_commit_files(owner, repo, commit_sha, token):
    """
    获取指定Commit更改的文件列表。
    支持自动处理API速率限制。
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, headers=headers)

            if handle_rate_limit(response):
                # 遇到速率限制并处理后重试
                continue

            response.raise_for_status()  # 如果请求失败则抛出HTTPError
            commit_data = response.json()

            # 从commit响应中提取文件信息
            if 'files' in commit_data:
                return commit_data['files']
            return []

        except requests.exceptions.RequestException as e:
            print(f"Error fetching files for commit {owner}/{repo}@{commit_sha}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text}")

                # 对于其他可恢复的错误，也进行重试
                if e.response.status_code in [500, 502, 503, 504]:
                    retries += 1
                    wait_time = 2 ** retries  # 指数退避策略
                    print(f"服务器错误，{wait_time}秒后重试 (尝试 {retries}/{MAX_RETRIES})...")
                    time.sleep(wait_time)
                    continue
            else:
                print("网络连接问题")

            # 不可恢复的错误或超过重试次数
            if retries < MAX_RETRIES - 1:
                retries += 1
                wait_time = 2 ** retries
                print(f"将在{wait_time}秒后重试 (尝试 {retries}/{MAX_RETRIES})...")
                time.sleep(wait_time)
            else:
                return None

    return None

def get_pr_files(owner, repo, pr_number, token):
    """
    获取指定Pull Request更改的文件列表。
    支持自动处理API速率限制。
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, headers=headers)

            if handle_rate_limit(response):
                # 遇到速率限制并处理后重试
                continue

            response.raise_for_status()  # 如果请求失败则抛出HTTPError
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching files for PR {owner}/{repo}#{pr_number}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text}")

                # 对于其他可恢复的错误，也进行重试
                if e.response.status_code in [500, 502, 503, 504]:
                    retries += 1
                    wait_time = 2 ** retries  # 指数退避策略
                    print(f"服务器错误，{wait_time}秒后重试 (尝试 {retries}/{MAX_RETRIES})...")
                    time.sleep(wait_time)
                    continue
            else:
                print("网络连接问题")

            # 不可恢复的错误或超过重试次数
            if retries < MAX_RETRIES - 1:
                retries += 1
                wait_time = 2 ** retries
                print(f"将在{wait_time}秒后重试 (尝试 {retries}/{MAX_RETRIES})...")
                time.sleep(wait_time)
            else:
                return None

    return None

def get_pr_commits_info(owner, repo, pr_number, token):
    """
    获取指定Pull Request的commits列表 (SHA)。
    支持自动处理API速率限制。
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            response = requests.get(url, headers=headers)

            if handle_rate_limit(response):
                # 遇到速率限制并处理后重试
                continue

            response.raise_for_status()
            commits_data = response.json()
            return [commit['sha'] for commit in commits_data]

        except requests.exceptions.RequestException as e:
            print(f"Error fetching commits for PR {owner}/{repo}#{pr_number}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.text}")

                # 对于其他可恢复的错误，也进行重试
                if e.response.status_code in [500, 502, 503, 504]:
                    retries += 1
                    wait_time = 2 ** retries  # 指数退避策略
                    print(f"服务器错误，{wait_time}秒后重试 (尝试 {retries}/{MAX_RETRIES})...")
                    time.sleep(wait_time)
                    continue

            # 不可恢复的错误或超过重试次数
            if retries < MAX_RETRIES - 1:
                retries += 1
                wait_time = 2 ** retries
                print(f"将在{wait_time}秒后重试 (尝试 {retries}/{MAX_RETRIES})...")
                time.sleep(wait_time)
            else:
                return []

    return []

def parse_repo_url(repo_api_url):
    """
    从 'https://api.github.com/repos/owner/repo' 解析 owner 和 repo 名称。
    """
    path_parts = urlparse(repo_api_url).path.split('/')
    if len(path_parts) >= 4 and path_parts[1] == 'repos':
        return path_parts[2], path_parts[3]
    return None, None

# --- 主逻辑 ---
def main():
    if not GITHUB_TOKEN:
        print("错误：GITHUB_PAT 环境变量未设置。请设置您的GitHub Personal Access Token。")
        return

    try:
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            issues_data = json.load(f)
    except FileNotFoundError:
        print(f"错误：输入文件 '{INPUT_JSON_FILE}' 未找到。")
        return
    except json.JSONDecodeError:
        print(f"错误：输入文件 '{INPUT_JSON_FILE}' 不是有效的JSON格式。")
        return

    processed_issues = []
    total_issues = len(issues_data)
    print(f"开始处理 {total_issues} 个条目...")

    for i, issue in enumerate(issues_data):
        print(f"\n处理条目 {i+1}/{total_issues}: Issue Number {issue.get('number')}")

        # 先默认设为None
        pr_number_to_fetch = None
        commit_sha_to_fetch = None

        # 判断数据来源类型
        pr_source = issue.get('pr_source')

        if pr_source == 'commit' and 'pr_number' in issue and issue['pr_number'] is not None:
            # pr_source为commit，pr_number字段实际存储的是commit的SHA
            commit_sha_to_fetch = issue['pr_number']
            print(f"  检测到PR来源为commit: {commit_sha_to_fetch}")
        elif issue.get('type') == 'pull_request': # 如果条目本身就是PR
            pr_number_to_fetch = issue.get('number')
        elif 'pr_number' in issue and issue['pr_number'] is not None: # 如果是issue且有关联的pr_number
            pr_number_to_fetch = issue['pr_number']

        # 处理需要获取PR信息的情况
        if pr_number_to_fetch is not None and 'repository_url' in issue:
            owner, repo = parse_repo_url(issue['repository_url'])
            if not owner or not repo:
                print(f"  无法从 repository_url '{issue['repository_url']}' 解析 owner/repo。跳过PR信息获取。")
                issue['changed_files'] = [] # 添加空列表以保持结构一致
                issue['commits'] = []
                processed_issues.append(issue)
                continue

            print(f"  尝试获取 PR #{pr_number_to_fetch} 的变更文件信息 (仓库: {owner}/{repo})...")
            files_changed = get_pr_files(owner, repo, pr_number_to_fetch, GITHUB_TOKEN)
            time.sleep(1) # 尊重API速率限制

            if files_changed:
                issue['changed_files'] = []
                for file_info in files_changed:
                    changed_file_data = {
                        "file_path": file_info.get('filename'),
                        "status": file_info.get('status'),
                        "additions": file_info.get('additions'),
                        "deletions": file_info.get('deletions'),
                        "changes": file_info.get('changes'),
                        "sha": file_info.get('sha'),
                        "patch": file_info.get('patch'), # patch会很大，按需添加
                        "changed_methods": [] # 重点：方法级别变更需要额外解析
                    }
                    # ------------------------------------------------------------------
                    # 此处是实现方法级别变更检测的关键点和难点
                    # ------------------------------------------------------------------
                    issue['changed_files'].append(changed_file_data)
                print(f"    成功获取 {len(files_changed)} 个变更文件。")

                # 获取PR的commits
                print(f"  尝试获取 PR #{pr_number_to_fetch} 的 commits...")
                commit_shas = get_pr_commits_info(owner, repo, pr_number_to_fetch, GITHUB_TOKEN)
                issue['commits'] = commit_shas
                if commit_shas:
                    print(f"    成功获取 {len(commit_shas)} 个 commits。")
                else:
                    print(f"    未能获取 PR #{pr_number_to_fetch} 的 commits。")
                time.sleep(1)

            else:
                print(f"    未能获取 PR #{pr_number_to_fetch} 的文件变更信息。")
                issue['changed_files'] = [] # 即使失败也添加空列表
                issue['commits'] = []

        # 处理需要获取commit信息的情况
        elif commit_sha_to_fetch is not None and 'repository_url' in issue:
            owner, repo = parse_repo_url(issue['repository_url'])
            if not owner or not repo:
                print(f"  无法从 repository_url '{issue['repository_url']}' 解析 owner/repo。跳过Commit信息获取。")
                issue['changed_files'] = [] # 添加空列表以保持结构一致
                issue['commits'] = [commit_sha_to_fetch]  # 记录当前commit SHA
                processed_issues.append(issue)
                continue

            print(f"  尝试获取 Commit {commit_sha_to_fetch} 的变更文件信息 (仓库: {owner}/{repo})...")
            files_changed = get_commit_files(owner, repo, commit_sha_to_fetch, GITHUB_TOKEN)
            time.sleep(1) # 尊重API速率限制

            if files_changed:
                issue['changed_files'] = []
                for file_info in files_changed:
                    changed_file_data = {
                        "file_path": file_info.get('filename'),
                        "status": file_info.get('status'),
                        "additions": file_info.get('additions'),
                        "deletions": file_info.get('deletions'),
                        "changes": file_info.get('changes'),
                        "sha": file_info.get('sha'),
                        "patch": file_info.get('patch'), # patch会很大，按需添加
                        "changed_methods": [] # 重点：方法级别变更需要额外解析
                    }
                    issue['changed_files'].append(changed_file_data)
                print(f"    成功获取 {len(files_changed)} 个变更文件。")
                # 记录单个commit
                issue['commits'] = [commit_sha_to_fetch]
            else:
                print(f"    未能获取 Commit {commit_sha_to_fetch} 的文件变更信息。")
                issue['changed_files'] = [] # 即使失败也添加空列表
                issue['commits'] = [] # 空列表保持一致性
        else:
            if pr_number_to_fetch is None and commit_sha_to_fetch is None:
                print(f"  条目没有有效的PR编号或Commit SHA。跳过信息获取。")
            elif 'repository_url' not in issue:
                print(f"  条目缺少 'repository_url'。跳过信息获取。")
            issue['changed_files'] = []
            issue['commits'] = []

        processed_issues.append(issue)

    try:
        with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed_issues, f, indent=2, ensure_ascii=False)
        print(f"\n处理完成！结果已保存到 '{OUTPUT_JSON_FILE}'")
    except IOError:
        print(f"错误：无法写入输出文件 '{OUTPUT_JSON_FILE}'。")

if __name__ == '__main__':
    main()

