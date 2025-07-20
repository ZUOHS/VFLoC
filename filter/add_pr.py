import json
import requests
import time
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# --- 配置 ---
load_dotenv()
GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")
repo_name = "AntennaPod"
INPUT_JSON_FILE = f'../issue_results/{repo_name}_completed_with_images.json'
OUTPUT_JSON_FILE = f'../issue_results/{repo_name}_issues_with_closing_pr.json'

# --- GitHub API 辅助函数 ---
def get_owner_repo_from_url(html_or_api_url):
    parsed_url = urlparse(html_or_api_url)
    path_parts = parsed_url.path.strip('/').split('/')
    if parsed_url.hostname == "api.github.com" and len(path_parts) >= 3 and path_parts[0] == 'repos':
        return path_parts[1], path_parts[2]
    elif parsed_url.hostname == "github.com" and len(path_parts) >= 2:
        return path_parts[0], path_parts[1]
    return None, None

def search_linked_pr_by_graphql(owner, repo, issue_number, token):
    """
    使用GitHub GraphQL API查找与issue关联的PR（即界面close标签右侧显示的PR）。
    返回PR号列表（通常只有一个）。
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    query = f"""
    query {{
      repository(owner: \"{owner}\", name: \"{repo}\") {{
        issue(number: {issue_number}) {{
          timelineItems(itemTypes: [CONNECTED_EVENT], first: 10) {{
            nodes {{
              ... on ConnectedEvent {{
                subject {{
                  ... on PullRequest {{
                    number
                    title
                    url
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
        pr_numbers = []
        for node in nodes:
            pr = node.get("subject")
            if pr and pr.get("number"):
                pr_numbers.append(pr["number"])
        return pr_numbers
    except Exception as e:
        print(f"  GraphQL查找PR出错: {e}")
        return []

def search_closing_pr_debug(owner, repo, issue_number_int, token):
    """
    使用 GitHub Search API 查找可能关闭此 Issue 并且已合并的 PR。
    选择满足条件中编号最小的 PR（表示最早的）。
    """
    issue_number_str = str(issue_number_int)
    queries_to_try = [
        f"repo:{owner}/{repo} type:pr is:merged closes:{issue_number_str}",
        f"repo:{owner}/{repo} type:pr is:merged {issue_number_str} in:title,body",
    ]
    pr_number_found = None

    for i, query in enumerate(queries_to_try):
        print(f"  DEBUG: Search Attempt {i + 1} for Issue #{issue_number_str} with query: {query}")
        url = f"https://api.github.com/search/issues?q={query}&sort=updated&order=desc"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        try:
            response = requests.get(url, headers=headers)
            print(f"    DEBUG: API URL: {url}")
            print(f"    DEBUG: Response Status Code: {response.status_code}")
            response.raise_for_status()
            search_results = response.json()
            print(f"    DEBUG: Total results for query {i + 1}: {search_results.get('total_count')}")

            valid_prs = []
            for item_idx, item in enumerate(search_results.get('items', [])):
                pr_num = item.get('number')
                pr_html_url = item.get('html_url')
                item_title = item.get('title')
                item_state = item.get('state')
                print(f"      DEBUG: Found item {item_idx + 1}: PR #{pr_num}, Title: '{item_title}', State: {item_state}, URL: {pr_html_url}")
                try:
                    if int(pr_num) > int(issue_number_int):
                        valid_prs.append((int(pr_num), pr_html_url))
                except Exception:
                    continue

            if valid_prs:
                valid_prs.sort()  # 按 PR 编号升序排序，取最小值
                pr_number_found = valid_prs[0][0]
                print(f"  DEBUG: 最老的满足条件的PR: #{pr_number_found} (URL: {valid_prs[0][1]})")
                break

        except requests.exceptions.HTTPError as e:
            print(f"  错误: HTTPError during Search API for query '{query}': {e}")
            if response is not None:
                print(f"  Response content: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"  错误: RequestException during Search API for query '{query}': {e}")
        except Exception as e_general:
            print(f"  未预期的错误在 search_closing_pr_debug (query: '{query}'): {e_general}")

    if pr_number_found:
        return pr_number_found
    else:
        print(f"  DEBUG: Issue #{issue_number_str} no pr.")
        return None

# --- 主逻辑 ---
def main():
    if not GITHUB_TOKEN:
        print("错误：GITHUB_PAT 环境变量未设置。请设置您的GitHub Personal Access Token。")
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

    issues_with_closing_pr_info = []
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

        print(f"\n处理Issue {i+1}/{total_issues_to_process}: #{issue_number}")

        owner, repo = get_owner_repo_from_url(repo_url_for_parsing)

        if not owner or not repo:
            print(f"  无法从 URL '{repo_url_for_parsing}' 解析 owner/repo。跳过此Issue。")
            continue

        if issue_item.get('state') != 'closed':
            print(f"  Issue #{issue_number} 状态为 '{issue_item.get('state')}'，不是closed。跳过查找关闭PR。")
            continue

        print(f"  仓库: {owner}/{repo}. Issue #{issue_number} (State: {issue_item.get('state')}).")
        print(f"  尝试使用GraphQL查找关联此Issue的PR...")
        pr_numbers = search_linked_pr_by_graphql(owner, repo, issue_number, GITHUB_TOKEN)
        time.sleep(1)

        found = False
        if pr_numbers:
            pr_numbers_filtered = [int(pr) for pr in pr_numbers if int(pr) > int(issue_number)]
            if pr_numbers_filtered:
                pr_numbers_filtered.sort()
                chosen_pr = pr_numbers_filtered[0]
                print(f"    成功找到最老关联 PR: #{chosen_pr}")
                issue_item_copy = issue_item.copy()
                issue_item_copy['pr_number'] = chosen_pr
                issue_item_copy['pr_source'] = 'graphql'
                issues_with_closing_pr_info.append(issue_item_copy)
                found = True

        if not found:
            print(f"    GraphQL未找到，尝试使用Search API查找...")
            try:
                issue_number_int = int(issue_number)
            except Exception:
                issue_number_int = issue_number
            closing_pr_number = search_closing_pr_debug(owner, repo, issue_number_int, GITHUB_TOKEN)
            time.sleep(2)
            if closing_pr_number is not None:
                try:
                    if int(closing_pr_number) > int(issue_number):
                        print(f"    Search API找到关闭 Issue #{issue_number} 的PR: #{closing_pr_number}")
                        issue_item_copy = issue_item.copy()
                        issue_item_copy['pr_number'] = closing_pr_number
                        issue_item_copy['pr_source'] = 'search_api'
                        issues_with_closing_pr_info.append(issue_item_copy)
                    else:
                        print(f"    Search API找到PR #{closing_pr_number}，但其编号不大于Issue #{issue_number}，忽略。")
                except Exception:
                    print(f"    Search API找到PR，但编号比较失败，忽略。")
            else:
                print(f"    未能找到明确关闭 Issue #{issue_number} 的PR。")

    if issues_with_closing_pr_info:
        try:
            with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(issues_with_closing_pr_info, f, indent=2, ensure_ascii=False)
            print(f"\n处理完成！{len(issues_with_closing_pr_info)} 个包含关闭PR信息的Issue已保存到 '{OUTPUT_JSON_FILE}'")
        except IOError:
            print(f"错误：无法写入输出文件 '{OUTPUT_JSON_FILE}'。")
    else:
        print(f"\n处理完成！没有找到任何包含明确关闭PR信息的Issue。输出文件 '{OUTPUT_JSON_FILE}' 未创建或为空。")

if __name__ == '__main__':
    main()
