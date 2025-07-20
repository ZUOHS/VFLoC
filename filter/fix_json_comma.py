import json
import os

def fix_json_file(file_path):
    print(f"Processing {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        fixed_lines.append(lines[i])
        
        if '"commits": [' in line:
            commit_lines = []
            i += 1
            while i < len(lines) and ']' not in lines[i]:
                commit_line = lines[i].strip()
                if commit_line.startswith('"'):
                    commit_lines.append(commit_line)
                i += 1
            
            if commit_lines and commit_lines[-1].endswith(','):
                commit_lines[-1] = commit_lines[-1].rstrip(',')
            
            fixed_lines.extend('      ' + line for line in commit_lines)
            if i < len(lines):
                fixed_lines.append(lines[i])
        i += 1
    
    fixed_content = '\n'.join(fixed_lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"Fixed {file_path}")

def main():
    files_to_process = [
        '../issue_results/cgeo/cgeo_issues_with_code_checked.json',
        '../issue_results/uno/uno_issues_with_code_checked.json'
    ]
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            fix_json_file(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == '__main__':
    main() 