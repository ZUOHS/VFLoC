import json
import requests
import time
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# --- 配置 ---
load_dotenv()
GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")
repo_name = "florisboard"
INPUT_JSON_FILE = f'../issue_results/{repo_name}/intermediates/{repo_name}_completed_with_images.json'
OUTPUT_JSON_FILE = f'../issue_results/{repo_name}/intermediates/{repo_name}_issues_with_closing_commit.json'

# --- GitHub API 辅助函数 ---
def get_owner_repo_from_url(html_or_api_url):
    parsed_url = urlparse(html_or_api_url)
    path_parts = parsed_url.path.strip('/').split('/')
    if parsed_url.hostname == "api.github.com" and len(path_parts) >= 3 and path_parts[0] == 'repos':
        return path_parts[1], path_parts[2]
    elif parsed_url.hostname == "github.com" and len(path_parts) >= 2:
        return path_parts[0], path_parts[1]
    return None, None

def search_closing_commits_by_graphql(owner, repo, issue_number, token):
    """
    使用GitHub GraphQL API查找直接关闭issue的commit（而非通过PR）
    返回commit SHA列表
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    query = f"""
    query {{
      repository(owner: \"{owner}\", name: \"{repo}\") {{
        issue(number: {issue_number}) {{
          timelineItems(itemTypes: [CLOSED_EVENT], first: 10) {{
            nodes {{
              ... on ClosedEvent {{
                closer {{
                  ... on Commit {{
                    oid
                    message
                    url
                    author {{
                      name
                      email
                      date
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    try:
        response = requests.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": query}
        )
        response.raise_for_status()
        data = response.json()
        nodes = (
            data.get('data', {})
            .get('repository', {})
            .get('issue', {})
            .get('timelineItems', {})
            .get('nodes', [])
        )
        commits = []
        for node in nodes:
            commit = node.get("closer")
            if commit and commit.get("oid"):
                commits.append({
                    'sha': commit.get("oid"),
                    'message': commit.get("message"),
                    'url': commit.get("url"),
                    'author': commit.get("author")
                })
        return commits
    except Exception as e:
        print(f"  GraphQL查找commit出错: {e}")
        return []

def search_closing_commits_by_search(owner, repo, issue_number_int, token):
    """
    使用GitHub Search API查找可能关闭此Issue的commit
    搜索commit消息中包含issue编号的commit
    """
    issue_number_str = str(issue_number_int)
    queries_to_try = [
        f"repo:{owner}/{repo} type:commit close {issue_number_str}",
        f"repo:{owner}/{repo} type:commit fix {issue_number_str}",
        f"repo:{owner}/{repo} type:commit resolve {issue_number_str}",
        f"repo:{owner}/{repo} type:commit #{issue_number_str}",
    ]

    all_commits = []

    for i, query in enumerate(queries_to_try):
        print(f"  搜索尝试 {i + 1}: {query}")
        url = f"https://api.github.com/search/commits?q={query}&sort=committer-date&order=desc"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.cloak-preview+json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            search_results = response.json()
            print(f"    找到 {search_results.get('total_count', 0)} 个commit")

            for item in search_results.get('items', []):
                commit_info = {
                    'sha': item.get('sha'),
                    'message': item.get('commit', {}).get('message'),
                    'url': item.get('html_url'),
                    'author': item.get('commit', {}).get('author'),
                    'committer': item.get('commit', {}).get('committer')
                }
                # 检查commit消息是否真的关闭了这个issue
                message = commit_info.get('message', '').lower()
                issue_ref = f"#{issue_number_str}"
                close_keywords = ['close', 'closes', 'closed', 'fix', 'fixes', 'fixed', 'resolve', 'resolves', 'resolved']

                if issue_ref in message.lower():
                    for keyword in close_keywords:
                        if keyword in message and issue_ref in message:
                            all_commits.append(commit_info)
                            break

            time.sleep(1)  # 避免API限制

        except requests.exceptions.HTTPError as e:
            print(f"  搜索commit时HTTP错误: {e}")
            if response is not None:
                print(f"  响应内容: {response.text}")
        except Exception as e:
            print(f"  搜索commit时出错: {e}")

    # 去重
    unique_commits = []
    seen_shas = set()
    for commit in all_commits:
        if commit['sha'] not in seen_shas:
            unique_commits.append(commit)
            seen_shas.add(commit['sha'])

    return unique_commits

def get_issue_timeline_commits(owner, repo, issue_number, token):
    """
    通过Issue Timeline API获取关闭该issue的commit信息
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/timeline"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.mockingbird-preview+json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        timeline_events = response.json()

        commits = []
        for event in timeline_events:
            if event.get('event') == 'closed' and event.get('commit_id'):
                # 获取commit详细信息
                commit_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{event['commit_id']}"
                commit_response = requests.get(commit_url, headers=headers)
                if commit_response.status_code == 200:
                    commit_data = commit_response.json()
                    commits.append({
                        'sha': commit_data.get('sha'),
                        'message': commit_data.get('commit', {}).get('message'),
                        'url': commit_data.get('html_url'),
                        'author': commit_data.get('commit', {}).get('author'),
                        'committer': commit_data.get('commit', {}).get('committer')
                    })
                time.sleep(0.5)  # 避免API限制

        return commits
    except Exception as e:
        print(f"  获取timeline commits出错: {e}")
        return []

# --- 主逻辑 ---
def main():
    if not GITHUB_TOKEN:
        print("错误：MY_GITHUB_TOKEN 环境变量未设置。请设置您的GitHub Personal Access Token。")
        return

    try:
        with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            issues_data_input = json.load(f)
    except FileNotFoundError:
        print(f"错误：输入文件 '{INPUT_JSON_FILE}' 未找到。")
        return
    except json.JSONDecodeError:
        print(f"错误：输入文件 '{INPUT_JSON_FILE}' 不是有效的JSON格式。")
        return

    if not isinstance(issues_data_input, list):
        if isinstance(issues_data_input, dict):
            issues_data_input = [issues_data_input]
        else:
            print(f"错误：输入文件 '{INPUT_JSON_FILE}' 的顶层结构应为JSON数组或单个JSON对象。")
            return

    issues_with_closing_commit_info = []
    total_issues_to_process = len(issues_data_input)
    print(f"开始处理 {total_issues_to_process} 个Issue...")

    for i, issue_item in enumerate(issues_data_input):
        if not isinstance(issue_item, dict):
            print(f"  警告: 第 {i+1} 个条目不是一个字典，已跳过。")
            continue

        issue_number = issue_item.get('number')
        repo_url_for_parsing = issue_item.get('repository_url') or issue_item.get('html_url')

        if not issue_number or not repo_url_for_parsing:
            print(f"  警告: Issue {issue_item.get('id', 'N/A')} 缺少 'number' 或 'repository_url'/'html_url' 字段，已跳过。")
            continue

        owner, repo = get_owner_repo_from_url(repo_url_for_parsing)
        if not owner or not repo:
            print(f"  警告: 无法从URL解析owner和repo: {repo_url_for_parsing}")
            continue

        print(f"\n处理Issue {i+1}/{total_issues_to_process}: #{issue_number}")

        # 方法1: 使用GraphQL查找关闭事件中的commit
        graphql_commits = search_closing_commits_by_graphql(owner, repo, issue_number, GITHUB_TOKEN)
        print(f"  GraphQL方法找到 {len(graphql_commits)} 个commit")

        all_commits = graphql_commits

        # 方法2: 使用Timeline API
        if len(graphql_commits) == 0:
            timeline_commits = get_issue_timeline_commits(owner, repo, issue_number, GITHUB_TOKEN)
            print(f"  Timeline方法找到 {len(timeline_commits)} 个commit")
            all_commits = graphql_commits + timeline_commits

        # # 方法3: 使用Search API
        if len(all_commits) == 0:
            search_commits = search_closing_commits_by_search(owner, repo, issue_number, GITHUB_TOKEN)
            print(f"  Search方法找到 {len(search_commits)} 个commit")
            all_commits = search_commits

        # 合并所有找到的commit，去重

        unique_commits = []
        seen_shas = set()
        for commit in all_commits:
            if commit['sha'] not in seen_shas:
                unique_commits.append(commit)
                seen_shas.add(commit['sha'])

        if unique_commits:
            print(f"    成功找到 {len(unique_commits)} 个关闭commit")
            issue_item_copy = issue_item.copy()
            issue_item_copy['pr_number'] = unique_commits[0]
            # issue_item_copy['commit_count'] = len(unique_commits)
            issue_item_copy['pr_source'] = 'commit'
            issues_with_closing_commit_info.append(issue_item_copy)
        else:
            print(f"    未找到关闭commit")


    if issues_with_closing_commit_info:
        try:
            with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(issues_with_closing_commit_info, f, indent=2, ensure_ascii=False)
            print(f"\n处理完成！{len(issues_with_closing_commit_info)} 个包含关闭commit信息的Issue已保存到 '{OUTPUT_JSON_FILE}'")
        except IOError:
            print(f"错误：无法写入输出文件 '{OUTPUT_JSON_FILE}'。")
    else:
        print("\n没有找到任何包含关闭commit信息的Issue。")

if __name__ == "__main__":
    main()
