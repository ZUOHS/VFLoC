import json
import os
import re
import requests
import subprocess
from typing import List, Dict, Optional
import time
from dotenv import load_dotenv
import ssl
from urllib3.exceptions import SSLError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")  # 可放入 .env 文件或直接设置环境变量

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

folder = "florisboard"  # 示例仓库

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

folder_to_language = {
    'All-Hands-AI': 'Python, TypeScript, Jinja and JavaScript',
    'ant-design': 'TypeScript',
    'AntennaPod': 'Java',
    'AppFlowy': 'Dart, Rust, C++ and HTML',
    'bruno': 'JavaScript, TypeScript and HTML',
    'cgeo': 'Java and HTML',
    'ComfyUI': 'TypeScript and Vue',
    'files': 'C# and C++',
    'florisboard': 'Kotlin, Python and Rust',
    'notepad': 'C++, HTML, C, Objective-C++ and Python',
    'TeamNewPipe_NewPipe': 'Java, Kotlin and HTML',
    'thunderbird': 'Kotlin and Java',
    'uno': 'C#, TypeScript, Objective-C, Java and JavaScript'
}

folder_to_extension = {
    'All-Hands-AI': '.py, .ts, .tsx, .jinja, .jinja2, .j2, .css, .less, .scss, .sass, .js and .jsx',
    'ant-design': '.ts, .tsx, .css, .less, .scss and .sass',
    'AntennaPod': '.java and .xml',
    'AppFlowy': '.dart, .rs, .cpp, .cc, .cxx, .h, .hpp, .hh, .hxx, .htm and .html',
    'bruno': '.js, .jsx, .ts, .tsx, .htm, .html, .css, .less, .scss and .sass',
    'cgeo': '.java, .xml, .htm and .html',
    'ComfyUI': '.ts, .tsx, .vue, .css, .less, .scss and .sass',
    'files': '.cs, .cpp, .cc, .cxx, .h, .hpp, .hh and .hxx',
    'florisboard': '.kt, .kts, .xml, .py and .rs',
    'notepad': '.cpp, .cc, .cxx, .h, .hpp, .hh and .hxx, .htm, .html, .c, .mm and .py',
    'TeamNewPipe_NewPipe': '.java, .kt, .kts, .xml, .htm and .html',
    'thunderbird': '.kt, .kts, .xml and .java',
    'uno': '.cs, .ts, .tsx, .m, .h, .java, .js, .jsx, .css, .less, .scss and .sass'
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



# 配置重试策略
def create_session_with_retries():
    """创建带有重试机制的requests session"""
    session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=5,  # 总重试次数
        backoff_factor=2,  # 退避因子
        status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
        allowed_methods=["HEAD", "GET", "OPTIONS"]  # 允许重试的HTTP方法
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def make_api_request_with_retry(url: str, max_retries: int = 3) -> Optional[requests.Response]:
    """使用重试机制发送API请求，专门处理SSL错误"""
    for attempt in range(max_retries):
        try:
            print(f"尝试第 {attempt + 1} 次请求: {url}")
            response = SESSION.get(url, headers=HEADERS, timeout=30)
            return response

        except requests.exceptions.SSLError as e:
            print(f"SSL错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if "UNEXPECTED_EOF_WHILE_READING" in str(e) or "EOF occurred in violation of protocol" in str(e):
                print("检测到SSL协议违规错误，可能是网络不稳定或GitHub服务器问题")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1  # 指数退避
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("SSL错误重试次数已达上限")
                return None

        except requests.exceptions.ConnectionError as e:
            print(f"连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("连接错误重试次数已达上限")
                return None

        except requests.exceptions.Timeout as e:
            print(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("超时重试次数已达上限")
                return None

        except Exception as e:
            print(f"其他网络错误 (尝试 {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print("网络错误重试次数已达上限")
                return None

    return None

# 创建全局session
SESSION = create_session_with_retries()


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


def extract_repo_info(html_url: str) -> tuple:
    """从GitHub URL提取仓库信息"""
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)', html_url)
    if match:
        owner, repo, issue_number = match.groups()
        return owner, repo, issue_number
    return None, None, None

def extract_images_from_body(body: str) -> tuple:
    """从body中提取图片URL并替换为标签"""
    # HTML img标签格式
    img_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
    html_images = re.findall(img_pattern, body)

    # Markdown图片格式 ![alt text](url)
    markdown_img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    markdown_images = re.findall(markdown_img_pattern, body)

    # 合并所有图片URL
    all_images = html_images + [img[1] for img in markdown_images]

    processed_body = body

    # 替换HTML格式图片为标签
    for i, img_url in enumerate(html_images, 1):
        img_tag = f'<img[^>]*src="{re.escape(img_url)}"[^>]*>'
        processed_body = re.sub(img_tag, f'[IMAGE_{i}]', processed_body)

    # 替换Markdown格式图片为标签
    start_index = len(html_images) + 1
    for i, (alt_text, img_url) in enumerate(markdown_images, start_index):
        # 转义特殊字符用于正则表达式
        escaped_alt = re.escape(alt_text)
        escaped_url = re.escape(img_url)
        markdown_pattern = f'!\[{escaped_alt}\]\({escaped_url}\)'
        processed_body = re.sub(markdown_pattern, f'[IMAGE_{i}]', processed_body)

    return processed_body, all_images

def get_image_extension_from_content(content: bytes) -> str:
    """从图片内容的文件头检测图片格式"""
    if content.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    elif content.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
        return '.gif'
    elif content.startswith(b'RIFF') and b'WEBP' in content[:20]:
        return '.webp'
    elif content.startswith(b'BM'):
        return '.bmp'
    else:
        return '.jpg'  # 默认使用jpg

def get_image_extension_from_url_and_response(url: str, response: requests.Response) -> str:
    """从URL和HTTP响应中推断图片扩展名"""
    # 首先尝试从URL中提取扩展名（排除查询参数和token）
    from urllib.parse import urlparse, parse_qs
    parsed_url = urlparse(url)
    path = parsed_url.path

    # 检查路径是否有明确的图片扩展名
    common_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    for ext in common_extensions:
        if path.lower().endswith(ext):
            return ext

    # 如果URL没有扩展名，尝试从Content-Type获取
    content_type = response.headers.get('content-type', '').lower()
    if 'jpeg' in content_type or 'jpg' in content_type:
        return '.jpg'
    elif 'png' in content_type:
        return '.png'
    elif 'gif' in content_type:
        return '.gif'
    elif 'webp' in content_type:
        return '.webp'
    elif 'bmp' in content_type:
        return '.bmp'

    # 最后尝试从内容检测
    return get_image_extension_from_content(response.content)

def download_image(url: str, folder_path: str, img_idx: int) -> tuple[bool, str]:
    """下载图片到指定文件夹，返回是否成功和实际文件名"""
    try:
        # 为GitHub用户图片使用特殊的请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site'
        }

        # 如果是GitHub API token，则添加授权头
        if 'api.github.com' in url or 'github.com' in url:
            if GITHUB_TOKEN:
                headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'

        print(f"正在下载图片 {img_idx}: {url}")

        # 使用session进行请求，支持重试
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)

                # 检查响应状态
                if response.status_code == 200:
                    # 检查内容是否为图片
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                        print(f"警告: URL {url} 返回的内容类型不是图片: {content_type}")
                        if len(response.content) < 1024:  # 如果内容很小，可能是错误信息
                            print(f"响应内容: {response.text[:200]}")
                            continue

                    # 获取正确的文件扩展名
                    extension = get_image_extension_from_url_and_response(url, response)
                    filename = f"IMAGE_{img_idx}{extension}"
                    filepath = os.path.join(folder_path, filename)

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    print(f"成功下载图片: {filename} (大小: {len(response.content)} 字节)")
                    return True, filename

                elif response.status_code == 404:
                    print(f"图片不存在 (404): {url}")
                    break  # 不重试404错误
                elif response.status_code == 403:
                    print(f"访问被拒绝 (403): {url}")
                    break  # 不重试403错误
                elif response.status_code == 400:
                    print(f"请求错误 (400): {url}")
                    if attempt < max_retries - 1:
                        print(f"等待 {attempt + 1} 秒后重试...")
                        time.sleep(attempt + 1)
                        continue
                    else:
                        break
                else:
                    print(f"HTTP错误 {response.status_code}: {url}")
                    if attempt < max_retries - 1:
                        print(f"等待 {attempt + 1} 秒后重试...")
                        time.sleep(attempt + 1)
                        continue
                    else:
                        break

            except requests.exceptions.Timeout:
                print(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {url}")
                if attempt < max_retries - 1:
                    time.sleep(attempt + 1)
                    continue
                else:
                    break
            except requests.exceptions.ConnectionError as e:
                print(f"连接错误 (尝试 {attempt + 1}/{max_retries}): {url} - {e}")
                if attempt < max_retries - 1:
                    time.sleep(attempt + 1)
                    continue
                else:
                    break
            except Exception as e:
                print(f"未知错误 (尝试 {attempt + 1}/{max_retries}): {url} - {e}")
                if attempt < max_retries - 1:
                    time.sleep(attempt + 1)
                    continue
                else:
                    break

        # 如果所有重试都失败，创建一个占位符文件
        placeholder_filename = f"IMAGE_{img_idx}_FAILED.txt"
        placeholder_path = os.path.join(folder_path, placeholder_filename)
        with open(placeholder_path, 'w', encoding='utf-8') as f:
            f.write(f"图片下载失败\n原始URL: {url}\n错误: 无法下载图片")

        print(f"图片下载失败，已创建占位符文件: {placeholder_filename}")
        return False, placeholder_filename

    except Exception as e:
        print(f"下载图片时发生异常 {url}: {e}")
        # 创建错误占位符文件
        error_filename = f"IMAGE_{img_idx}_ERROR.txt"
        error_path = os.path.join(folder_path, error_filename)
        try:
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(f"图片下载异常\n原始URL: {url}\n错误: {str(e)}")
        except:
            pass
        return False, error_filename
def get_commit_files(owner: str, repo: str, commit_hash: str) -> Dict[str, List[str]]:
    """获取指定commit修改的文件列表，按状态分类"""
    empty_result = {'modified': [], 'added': [], 'removed': [], 'added_paths': []}

    try:
        # 使用GitHub API获取commit信息
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}"
        print(f"正在获取commit {commit_hash[:7]} 的文件信息...")

        response = make_api_request_with_retry(api_url)
        if response is None:
            print(f"错误: 无法获取commit {commit_hash[:7]} 的信息，所有重试都失败")
            return empty_result

        if response.status_code == 200:
            commit_data = response.json()
            result = {
                'modified': [],  # 修改的文件
                'added': [],     # 新增的文件
                'removed': [],   # 删除的文件
                'added_paths': []  # 新增文件的路径（用于路径统计）
            }

            if 'files' in commit_data:
                total_files = len(commit_data['files'])
                valid_files = 0

                for file_info in commit_data['files']:
                    filename = file_info['filename']
                    status = file_info['status']

                    # 只处理有效的源代码文件
                    if not is_valid_file(filename):
                        continue

                    valid_files += 1

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
                    # 忽略 'renamed' 状态的文件

                return result
            else:
                print(f"警告: commit {commit_hash[:7]} 没有文件变更信息")
                return empty_result

        elif response.status_code == 404:
            print(f"错误: commit {commit_hash[:7]} 不存在或仓库 {owner}/{repo} 不可访问")
            return empty_result
        elif response.status_code == 403:
            print(f"错误: GitHub API访问被限制，可能是token问题或请求过于频繁 (commit: {commit_hash[:7]})")
            return empty_result
        elif response.status_code == 422:
            print(f"错误: commit hash {commit_hash[:7]} 格式无效")
            return empty_result
        else:
            print(f"错误: 获取commit {commit_hash[:7]} 失败，HTTP状态码: {response.status_code}")
            print(f"响应内容: {response.text[:200]}...")
            return empty_result

    except json.JSONDecodeError as e:
        print(f"错误: 解码GitHub API响应JSON失败 (commit: {commit_hash[:7]}): {e}")
        return empty_result
    except Exception as e:
        print(f"错误: 获取commit {commit_hash[:7]} 文件列表时发生未知错误: {type(e).__name__}: {e}")
        return empty_result
def get_parent_commit(owner: str, repo: str, commit_hash: str) -> Optional[str]:
    """获取指定commit的父commit"""
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_hash}"
        print(f"正在获取commit {commit_hash[:7]} 的父commit...")

        response = make_api_request_with_retry(api_url)
        if response is None:
            print(f"错误: 无法获取commit {commit_hash[:7]} 的父commit，所有重试都失败")
            return None

        if response.status_code == 200:
            commit_data = response.json()
            if 'parents' in commit_data and len(commit_data['parents']) > 0:
                parent_sha = commit_data['parents'][0]['sha']

                return parent_sha
            else:
                print(f"警告: commit {commit_hash[:7]} 没有父commit（可能是初始commit）")
                return None
        elif response.status_code == 404:
            print(f"错误: commit {commit_hash[:7]} 不存在或仓库 {owner}/{repo} 不可访问")
            return None
        elif response.status_code == 403:
            print(f"错误: GitHub API访问被限制，无法获取父commit (commit: {commit_hash[:7]})")
            return None
        else:
            print(f"错误: 获取父commit失败，HTTP状态码: {response.status_code} (commit: {commit_hash[:7]})")
            return None

    except json.JSONDecodeError as e:
        print(f"错误: 解析父commit响应JSON失败 (commit: {commit_hash[:7]}): {e}")
        return None
    except Exception as e:
        print(f"错误: 获取父commit时发生未知错误 (commit: {commit_hash[:7]}): {type(e).__name__}: {e}")
        return None
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

            if 'commit' not in commit_data:
                print(f"错误: commit {commit_hash[:7]} 响应中缺少commit信息")
                return 0

            if 'committer' not in commit_data['commit']:
                print(f"错误: commit {commit_hash[:7]} 响应中缺少committer信息")
                return 0

            if 'date' not in commit_data['commit']['committer']:
                print(f"错误: commit {commit_hash[:7]} 响应中缺少date信息")
                return 0

            # 获取commit时间
            commit_time = commit_data['commit']['author']['date']
            # 转换为时间戳
            from datetime import datetime
            dt = datetime.fromisoformat(commit_time.replace('Z', '+00:00'))
            timestamp = int(dt.timestamp())

            return timestamp

        elif response.status_code == 404:
            print(f"错误: commit {commit_hash[:7]} 不存在或仓库 {owner}/{repo} 不可访问")
            return 0
        elif response.status_code == 403:
            print(f"错误: GitHub API访问被限制，无法获取commit时间 (commit: {commit_hash[:7]})")
            return 0
        elif response.status_code == 422:
            print(f"错误: commit hash {commit_hash[:7]} 格式无效")
            return 0
        else:
            print(f"错误: 获取commit时间失败，HTTP状态码: {response.status_code} (commit: {commit_hash[:7]})")
            print(f"响应内容: {response.text[:200]}...")
            return 0

    except ValueError as e:
        print(f"错误: 时间格式解析失败 (commit: {commit_hash[:7]}): {e}")
        return 0
    except json.JSONDecodeError as e:
        print(f"错误: 解析commit时间响应JSON失败 (commit: {commit_hash[:7]}): {e}")
        return 0
    except Exception as e:
        print(f"错误: 获取commit时间时发生未知错误 (commit: {commit_hash[:7]}): {type(e).__name__}: {e}")
        return 0

def find_oldest_commit(commits: List[str], owner: str, repo: str) -> str:
    """找到最老的commit"""
    if not commits:
        return None

    oldest_commit = commits[0]
    oldest_time = get_commit_time(commits[0], owner, repo)

    for commit in commits[1:]:
        commit_time = get_commit_time(commit, owner, repo)
        if commit_time < oldest_time:
            oldest_time = commit_time
            oldest_commit = commit
        time.sleep(0.5)  # 避免API请求过快

    return oldest_commit

def process_issue_data(json_file_path: str, operation_dir: str):
    """处理JSON文件中的issue数据"""

    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        issues_data = json.load(f)

    # 创建operation目录
    os.makedirs(operation_dir, exist_ok=True)

    for idx, issue in enumerate(issues_data, 1):
        print(f"处理第 {idx} 个issue: {issue['title']}")

        # 提取仓库信息
        owner, repo, issue_number = extract_repo_info(issue['html_url'])
        if not owner or not repo:
            print(f"无法解析仓库信息: {issue['html_url']}")
            continue

        # 创建文件夹 - 使用���目名+issue_id格式
        folder_name = f"{repo}_{issue_number}"
        folder_path = os.path.join(operation_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # 处理图片
        processed_body, image_urls = extract_images_from_body(issue['body'])

        # 下载图片
        for img_idx, img_url in enumerate(image_urls, 1):
            success, actual_filename = download_image(img_url, folder_path, img_idx)
            if success:
                print(f"图片 {img_idx} 下载成功: {actual_filename}")
            time.sleep(1)  # 避免请求过快

        # 创建git命令文件
        git_commands_file = os.path.join(folder_path, "git_commands.sh")

        # 找到最老的commit
        commits = issue.get('commits', [])
        if commits:
            oldest_commit = find_oldest_commit(commits, owner, repo)
            if oldest_commit:
                parent_commit = get_parent_commit(owner, repo, oldest_commit)

                if parent_commit:
                    git_commands = f"""#!/bin/bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
git checkout {parent_commit}
"""
                else:
                    git_commands = f"""#!/bin/bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
git checkout {oldest_commit}^
"""
            else:
                git_commands = f"""#!/bin/bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
"""
        else:
            git_commands = f"""#!/bin/bash
git clone https://github.com/{owner}/{repo}.git
cd {repo}
"""

        with open(git_commands_file, 'w', encoding='utf-8') as f:
            f.write(git_commands)

        # 创建prompt文件
        prompt_file = os.path.join(folder_path, "prompt.txt")
        prompt_content = f"""You are a software engineer working on this codebase.

The codebase has been cloned and checked out to a specific commit. You have access to the file structure and source code.

Only consider source code files written in {folder_to_language[folder]}, typically ending with {folder_to_extension[folder]}. In addition to traditional source code files, relevant templates, layout definitions, or stylesheets (e.g., XML, HTML, CSS) may be included if they are essential to the implementation of the feature. Exclude non-code artifacts such as documentation, test scripts, or configuration files.

Your goal is to determine which existing source code files are most likely to require modification or deletion, and which new files (if any) are likely to be added in which directory paths, in order to implement the following feature request.

Please follow these steps:
1. Understand the feature request by analyzing the summary and description.
2. Identify the likely modules or components involved based on the description.
3. Determine which existing source code files (not directories) are most relevant and would likely need to be modified or deleted.
4. Consider whether implementing this request would require adding new files. If so, identify only the **directory paths** where such new files would likely be placed.
5. Return the result as a structured JSON object.

Instructions:
- Only return a JSON object with two fields: "modified_files" and "added_paths".
- "modified_files" must be a list of file paths (e.g., "src/main/app.py") that currently exist and are likely to be modified or deleted.
- "added_paths" must be a list of directory paths (e.g., "src/features") where new files are likely to be created. If no new files are needed, this list can be empty.
- All file paths must exist in the current codebase.
- All added paths must be valid directories; do not return any file names in this list.
- Do not include any explanation or reasoning.
- You may assume full access to the codebase for inspection.
- Note: In some cases, only new files may need to be added (i.e., non-empty `added_paths` and empty `modified_files`), or only existing files may need to be modified or deleted (i.e., non-empty `modified_files` and empty `added_paths`). Please determine this based on the actual requirements.

Feature request:
Summary: {issue['title']}
Description: {processed_body}

Please think step-by-step, but return only the JSON object with the two fields.
"""

        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(prompt_content)

        # 收集ground truth - 分类统计文件变更
        all_modified_files = set()  # 修改和删除的文件
        all_added_paths = set()     # 新增文件��路径
        added_files_tracker = set()  # 跟踪所有新增过的文件

        # 按时间顺序处理commits（从最老到最新）
        sorted_commits = sorted(commits, key=lambda c: get_commit_time(c, owner, repo))

        for commit in sorted_commits:
            commit_files = get_commit_files(owner, repo, commit)

            # 处理新增文件
            for added_file in commit_files['added']:
                added_files_tracker.add(added_file)
                # 提取新增文件的路径
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

            time.sleep(1)  # 避免API请求过快

        # 创建ground truth文件
        ground_truth_file = os.path.join(folder_path, "ground_truth.json")
        ground_truth_data = {
            "issue_id": issue['id'],
            "issue_number": issue['number'],
            "repository": f"{owner}/{repo}",
            "commits": commits,
            "modified_files": sorted(list(all_modified_files)),  # 修改和删除的文件
            "added_paths": sorted(list(all_added_paths))         # 新增文件的路径
        }

        with open(ground_truth_file, 'w', encoding='utf-8') as f:
            json.dump(ground_truth_data, f, indent=2, ensure_ascii=False)

        print(f"完成处理文件夹 {folder_name}")
        time.sleep(2)  # 避免请求过快
        # 加上break用于简单测试
        # break

def main():
    # 配置路径
    json_file_path = (f"../issue_results/{folder}/{folder_to_name[folder]}_issues_with_code_filtered.json")
    operation_dir = f"../operation/{folder}"

    # 处理数据
    process_issue_data(json_file_path, operation_dir)
    print("所有数据处理完成!")

if __name__ == "__main__":
    main()
