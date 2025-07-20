import json

REPO_CONFIGS = {
    'All-Hands-AI': {
        'full_name': 'All-Hands-AI/OpenHands',
        'file_path': '../issue_results/All-Hands-AI/All-Hands-AI_issues_with_code_checked.json'
    },
    'ant-design': {
        'full_name': 'ant-design/ant-design',
        'file_path': '../issue_results/ant-design/ant-design_issues_with_code_checked.json'
    },
    'AntennaPod': {
        'full_name': 'AntennaPod/AntennaPod',
        'file_path': '../issue_results/AntennaPod/AntennaPod_issues_with_code_checked.json'
    },
    'AppFlowy': {
        'full_name': 'AppFlowy-IO/AppFlowy',
        'file_path': '../issue_results/AppFlowy/AppFlowy_issues_with_code_checked.json'
    },
    'bruno': {
        'full_name': 'usebruno/bruno',
        'file_path': '../issue_results/bruno/bruno_issues_with_code_checked.json'
    },
    'cgeo': {
        'full_name': 'cgeo/cgeo',
        'file_path': '../issue_results/cgeo/cgeo_issues_with_code_checked.json'
    },
    'ComfyUI': {
        'full_name': 'comfyanonymous/ComfyUI',
        'file_path': '../issue_results/ComfyUI/ComfyUI_issues_with_code_checked.json'
    },
    'files': {
        'full_name': 'files-community/Files',
        'file_path': '../issue_results/files/files_issues_with_code_checked.json'
    },
    'florisboard': {
        'full_name': 'florisboard/florisboard',
        'file_path': '../issue_results/florishboard/florisboard_issues_with_code_checked.json'
    },
    'TeamNewPipe': {
        'full_name': 'TeamNewPipe/NewPipe',
        'file_path': '../issue_results/TeamNewPipe_NewPipe/TeamNewPipe_NewPipe_issues_with_code_checked.json'
    },
    'thunderbird': {
        'full_name': 'thunderbird/thunderbird-android',
        'file_path': '../issue_results/thunderbird/thunderbird_issues_with_code_checked.json'
    },
    'uno': {
        'full_name': 'unoplatform/uno',
        'file_path': '../issue_results/uno/uno_issues_with_code_checked.json'
    }
}


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_repo_data(repo_name, data, full_repo_name):
    print(f"\n检查仓库 {repo_name}:")
    print(f"文件有: {len(data)} 条")
    print("详细如下:")
    for item in data:
        pr_number = item.get('pr_number')
        pr_link = f"https://github.com/{full_repo_name}/pull/{pr_number}" \
            if item.get('pr_source') != 'commit' else \
            f"https://github.com/{full_repo_name}/commit/{pr_number}"
        print(f"issue link: {item.get('html_url')}, pr/commit link: {pr_link}")


def main():
    total_issues = 0
    print("开始检查所有仓库数据...")

    for repo_name, config in REPO_CONFIGS.items():
        try:
            data = load_json(config['file_path'])
            total_issues += len(data)
            check_repo_data(repo_name, data, config['full_name'])
        except FileNotFoundError:
            print(f"\n警告: 找不到仓库 {repo_name} 的数据文件: {config['file_path']}")
        except json.JSONDecodeError:
            print(f"\n错误: 仓库 {repo_name} 的数据文件格式不正确: {config['file_path']}")
        except Exception as e:
            print(f"\n错误: 处理仓库 {repo_name} 时发生未知错误: {str(e)}")

    print(f"\n总结:")
    print(f"共检查了 {len(REPO_CONFIGS)} 个仓库")
    print(f"总计发现 {total_issues} 条 issue 记录")


if __name__ == '__main__':
    main()