import os
import json
import time
from dotenv import load_dotenv
from github import Github

# 加载.env文件中的环境变量
load_dotenv()
GITHUB_TOKEN = os.getenv("MY_GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("请在.env文件中设置GITHUB_TOKEN")

g = Github(GITHUB_TOKEN)

repo_name_to_repo_full_name_dict = {
    'files': 'files-community/Files',
    'ComfyUI': 'Comfy-Org/ComfyUI_frontend',
    'florisboard': 'florisboard/florisboard',
    'TeamNewPipe_NewPipe': 'TeamNewPipe/NewPipe',
    'ant-design': 'ant-design/ant-design',
    'uno': 'unoplatform/uno',
    'AppFlowy': 'AppFlowy-IO/AppFlowy',
}

project_name = 'TeamNewPipe_NewPipe'  # 设置要处理的项目名称


def get_commit_hashes_in_pr(pr_number):
    """
    输入PR号，返回该PR下所有commit的hash列表。
    """
    try:
        repo_full_name = repo_name_to_repo_full_name_dict[project_name]
        repo = g.get_repo(repo_full_name)
        pr = repo.get_pull(int(pr_number))
        return [commit.sha for commit in pr.get_commits()]
    except Exception as e:
        print(f"[Exception] 获取PR所有commit hash失败: PR#{pr_number} -> {e}")
        return []


def get_modified_files_in_pr(pr_number):
    """
    输入PR号，返回该PR下所有被修改的文件的详细信息列表。
    每个元素包含：file_path, status, additions, deletions, changes, sha, patch, changed_methods
    """
    try:
        repo_full_name = repo_name_to_repo_full_name_dict[project_name]
        repo = g.get_repo(repo_full_name)
        pr = repo.get_pull(int(pr_number))
        files = pr.get_files()
        result = []
        for f in files:
            result.append({
                "file_path": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "sha": getattr(f, 'sha', None),
                "patch": getattr(f, 'patch', None),
                "changed_methods": []  # 方法级diff可后续补充
            })
        return result
    except Exception as e:
        print(f"[Exception] 获取PR所有被修改文件失败: PR#{pr_number} -> {e}")
        return []


def get_modified_files_in_commit(commit_hash):
    """
    输入commit hash，返回该commit下所有被修改的文件的详细信息列表。
    每个元素包含：file_path, status, additions, deletions, changes, sha, patch, changed_methods
    """
    try:
        repo_full_name = repo_name_to_repo_full_name_dict[project_name]
        repo = g.get_repo(repo_full_name)
        commit = repo.get_commit(commit_hash)
        result = []
        for f in commit.files:
            result.append({
                "file_path": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "sha": getattr(f, 'sha', None),
                "patch": getattr(f, 'patch', None),
                "changed_methods": []  # 方法级diff可后续补充
            })
        return result
    except Exception as e:
        print(f"[Exception] 获取commit所有被修改文件失败: {commit_hash} -> {e}")
        return []


def process_item(item):
    checked_pr_or_commit, unchecked_modified_file_list, \
        unchecked_commit_list, checked_commit_list = None, [], [], []
    pr_number = item.get('pr_number')
    pr_link = f"https://github.com/{repo_name_to_repo_full_name_dict[project_name]}/pull/{pr_number}" \
        if item.get('pr_source') != 'commit' else \
        f"https://github.com/{repo_name_to_repo_full_name_dict[project_name]}/commit/{pr_number}"
    print(f"issue link: {item.get('html_url')}")
    print(f"pr/commit link: {pr_link}")
    print('check issue-pr/commit mapping. Type in the new pr_number/commit_hash. Type 0 to dump.')
    while not checked_pr_or_commit:
        checked_pr_or_commit = input('pr_number/commit_hash: ')
    if checked_pr_or_commit == '0':
        return None, None, None, None
    if not str(checked_pr_or_commit).isdigit() or len(str(checked_pr_or_commit)) > 6:
        unchecked_commit_list = []
        checked_commit_list = []
        unchecked_modified_file_list = get_modified_files_in_commit(checked_pr_or_commit)
    else:
        unchecked_commit_list = get_commit_hashes_in_pr(checked_pr_or_commit)
        unchecked_modified_file_list = get_modified_files_in_pr(checked_pr_or_commit)
        if len(unchecked_commit_list) > 1:
            print(f'check the following commit hashes ({len(unchecked_commit_list)} in total):')
            print('\n'.join(unchecked_commit_list))
            print('type in the FULL hashes that should be excluded. Type in Enter to finish.')
            excluding_hash_list = []
            while True:
                excluding_hash = input('excluding FULL hash: ')
                if not excluding_hash:
                    break
                excluding_hash_list.append(excluding_hash)
            checked_commit_list = [commit_hash for commit_hash in unchecked_commit_list if commit_hash not in excluding_hash_list]
        else:
            checked_commit_list = unchecked_commit_list

    print('-' * 10)
    print('double check your verification: ')
    print('pr_number/commit_hash:', checked_pr_or_commit)
    print(f'checked_commit_hash_list ({len(checked_commit_list)} in total):')
    print('\n'.join(checked_commit_list))
    is_A = input('Type in Enter to continue, type in A to recheck: ')
    if is_A == 'A':
        print('=' * 10, 'RESTART', '=' * 10)
        return process_item(item)
    else:
        return checked_pr_or_commit, unchecked_modified_file_list, \
            unchecked_commit_list, checked_commit_list


def load():
    """
    加载已有的结果文件，如果不存在则返回空列表。
    返回：with_closing_pr_checked_result_list, with_code_result_list, with_code_processed_result_list, with_code_checked_result_list
    """
    import os
    base_dir = f'../issue_results/{project_name}'

    def _load(path):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return []

    with_closing_pr_checked_result_list = _load(
        os.path.join(base_dir, f'{project_name}_issues_with_closing_pr_checked.json'))
    with_code_result_list = _load(os.path.join(base_dir, f'intermediates/{project_name}_issues_with_code.json'))
    with_code_processed_result_list = _load(os.path.join(base_dir, f'intermediates/{project_name}_issues_with_code_processed.json'))
    with_code_checked_result_list = _load(os.path.join(base_dir, f'{project_name}_issues_with_code_checked.json'))
    return (with_closing_pr_checked_result_list, with_code_result_list,
            with_code_processed_result_list, with_code_checked_result_list)


def save(with_closing_pr_checked_result_list, with_code_result_list, with_code_processed_result_list,
         with_code_checked_result_list):
    def _save(path, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=4)

    base_dir = f'../issue_results/{project_name}'
    os.makedirs(base_dir, exist_ok=True)
    _save(os.path.join(base_dir, f'{project_name}_issues_with_closing_pr_checked.json'),
          with_closing_pr_checked_result_list)
    _save(os.path.join(base_dir, f'intermediates/{project_name}_issues_with_code.json'), with_code_result_list)
    _save(os.path.join(base_dir, f'intermediates/{project_name}_issues_with_code_processed.json'), with_code_processed_result_list)
    _save(os.path.join(base_dir, f'{project_name}_issues_with_code_checked.json'), with_code_checked_result_list)


def process_file():
    input_path = f"../issue_results/{project_name}/intermediates/{project_name}_issues_with_closing_pr.json"
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    (with_closing_pr_checked_result_list, with_code_result_list,
     with_code_processed_result_list, with_code_checked_result_list) = load()
    ptr = -1
    if len(with_closing_pr_checked_result_list) != 0:
        for idx, item in enumerate(data):
            if item.get('number') == with_closing_pr_checked_result_list[-1].get('number'):
                ptr = idx
                break

    for idx, item in enumerate(data[ptr+1:]):
        print('='*10, f'{idx + 1}/{len(data) - ptr - 1}', '='*10)
        (checked_pr_or_commit, unchecked_modified_file_list,
         unchecked_commit_list, checked_commit_list) = process_item(item)
        if checked_pr_or_commit is None:
            if idx % 10 == 9:
                print(f"Processed {idx + 1} items. Temp saving...")
                save(
                    with_closing_pr_checked_result_list,
                    with_code_result_list,
                    with_code_processed_result_list,
                    with_code_checked_result_list
                )
            continue
        # saving closing_pr_checked.json results
        if not str(checked_pr_or_commit).isdigit() or len(str(checked_pr_or_commit)) > 6:
            new_pr_source = 'commit'
        elif int(checked_pr_or_commit) != item.get('pr_number'):
            new_pr_source = 'manual'
            checked_pr_or_commit = int(checked_pr_or_commit)
        else:
            new_pr_source = item.get('pr_source')
        item['pr_number'] = checked_pr_or_commit
        item['pr_source'] = new_pr_source
        with_closing_pr_checked_result_list.append(item.copy())

        # saving with_code_checked.json results
        item['commits'] = checked_commit_list
        with_code_checked_result_list.append(item.copy())

        # saving with_code_processed.json results
        item['commits'] = unchecked_commit_list
        with_code_processed_result_list.append(item.copy())

        # saving with_code.json results
        item['changed_files'] = unchecked_modified_file_list
        with_code_result_list.append(item.copy())

        if idx % 10 == 9:
            print(f"Processed {idx + 1} items. Temp saving...")
            save(
                with_closing_pr_checked_result_list,
                with_code_result_list,
                with_code_processed_result_list,
                with_code_checked_result_list
            )

    save(
        with_closing_pr_checked_result_list,
        with_code_result_list,
        with_code_processed_result_list,
        with_code_checked_result_list
    )


if __name__ == "__main__":
    process_file()
