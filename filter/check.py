import json

repo_name = 'uno'
file = f'../issue_results/uno/{repo_name}_issues_with_code_checked.json'
repo_name_to_repo_full_name_dict = {
    'cgeo': 'cgeo/cgeo',
    'AntennaPod': 'AntennaPod/AntennaPod',
    'All-Hands-AI': 'All-Hands-AI/OpenHands',
    'bruno': 'usebruno/bruno',
    'thunderbird': 'thunderbird/thunderbird-android',
}
def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    data = load_json(file)

    print(f"文件有: {len(data)} 条")
    print("详细如下:")
    for item in data:
        pr_number = item.get('pr_number')
        pr_link = f"https://github.com/{repo_name_to_repo_full_name_dict[repo_name]}/pull/{pr_number}" \
            if item.get('pr_source') != 'commit' else \
            f"https://github.com/{repo_name_to_repo_full_name_dict[repo_name]}/commit/{pr_number}"
        print(f"issue link: {item.get('html_url')}, pr/commit link: {pr_link}")

if __name__ == '__main__':
    main()

