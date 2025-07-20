# Codebook: 人工筛选GitHub Issues与PR关联数据集

## 1. 概述

本文档提供了对自动爬取的GitHub Issues进行人工筛选的指导规范，目的是构建一个高质量的enhancement相关数据集，用于研究软件增强请求中视觉信息的使用及其对开发过程的影响。

### 1.1 研究背景与目标

我们正在构建一个多模态enhancement代码定位的benchmark（基准测试集），该benchmark具有以下特点：

1. **多模态特性**：包含文本描述和视觉信息（图片、设计图、屏幕截图等）
2. **代码定位映射**：建立enhancement需求与实际代码变更之间的对应关系

该benchmark的主要目标是：

- 评估视觉信息在软件需求理解和代码实现中的作用
- 为自动化代码生成和代码定位技术提供训练和测试数据
- 分析开发者如何理解和转化包含视觉元素的enhancement请求
- 促进多模态软件工程工具的发展，提高软件开发效率

本文档使用的前置条件是，正在进行人工enhancement issues的收集，或者已经通过自动化手段初步收集、正在进行enhancement issues的筛选。通过**规范检查GitHub中包含图片的enhancement issues及其对应的PR提交**，我们可以构建一个高质量的数据集，用于分析视觉信息如何影响代码实现，以及如何更好地利用视觉信息辅助软件开发过程。

### 1.2 检查内容

具体地，本文档在人工筛选PR过程中，指导检查人员检查并增改下列信息（具体数据项格式请参考6节）：

- issue编号和URL
- 图片类型
- 关联的PR编号或commit hash
- 代码合并方式（PR或直接commit）

此外，本文档在人工筛选commit过程中，指导检查人员检查并增改下列信息：

- enhancement真实对应的commit列表。

## 2. 筛选流程

### 2.1 步骤一：寻找合适的目标仓库

一个合适的仓库能让数据收集事半功倍。推荐选择满足以下条件的GitHub仓库：

1.  **开源且活跃**：项目应为非fork的开源项目，有着明确的license，且近期有较为频繁的活动（如代码提交、Issue讨论）。最低要求为仓库至少有50个Issue。
2.  **以GUI为中心**：项目最好是包含图形用户界面（GUI）的应用程序（如桌面应用、移动App、Web应用），这类项目更容易出现包含视觉信息的Enhancement Report。
3.  **规范的Issue管理**：项目维护者对Issue进行有效管理，例如使用`enhancement`、`feature`、`feature request`等标签对功能请求进行标记。

**建议的仓库寻找方法**：
- 在GitHub上使用关键词搜索，如 "open source android app", "react desktop app" 等。
- 浏览GitHub Explore或Trending页面，发现热门的开源项目。
- 从一些知名的开源软件列表或社区中寻找，如 F-Droid (Android), Awesome-Selfhosted (Web) 等。

### 2.2 前置步骤

1. 使用`issue_AntennaPod.py`等脚本爬取原始issues数据，统计包含的图片信息（具体每个仓库使用的标签不同，可能是`enhancement`或`feature request`其他相关标签）
2. 使用`filter_completed_with_images.py`筛选出状态为completed且包含图片的issues
3. 使用`add_pr.py`识别与每个issue关联的PR或commit。由于是通过自动化脚本获取的PR信息，可能存在错误或遗漏，因此需要**人工验证**

### 2.3 人工筛选PR

1. 打开自动生成的JSON文件（如`AntennaPod_issues_with_closing_pr.json`），并创建结果JSON文件（如`AntennaPod_issues_with_closing_pr_checked.json`，用于保存筛选后issue）
2. 访问每个issue的`html_url`链接
3. 检查issue中的图片是否为enhancement相关，并检查是否应该将issue排除，具体标准请查看3.1节和3.2节
4. 确认关联的PR或commit是否实际实现了该enhancement，具体验证流程如下：
   - **步骤1**：首先查看issue页面右侧"Closed"字段旁边是否有"Development"字段自动关联的PR，点击进入该PR核对其内容与issue的关联性
   - **步骤2**：如果步骤1没有找到相关PR，查找issue页面下方是否有"completed in xxx"字样，点击链接核对该PR
   - **步骤3**：如果步骤1和2都没有结果，检查issue评论中是否有人提到该issue在某个PR中完成（通常出现在完成信息附近）
   - **步骤4**：如果以上方法都未找到相关PR，按照JSON数据中给出的`pr_number`检查对应PR是否解决了这个issue
   - **步骤5**：确认PR是否已被合并，以及是否真正实现了issue中描述的enhancement功能
5. 如果不符合要求，则检查下一个；如果符合要求且存在关联的PR/commit，则判断图片类型，分类为Mockup、UI Design、Screenshot、Flowchart、Reference、Interaction、Else中的一个或多个，使用逗号分隔（如`Mockup,UI Design`）填入`image_types`字段。具体分类含义请查看3.3节
6. 将添加了分类信息的issue复制粘贴到新文件，然后在新文件中修改`pr_source`，`pr_number`。更详细的说明请查看3.4节
   - 如果PR是本身已经正确标注，`pr_source`不修改，保持为"search_api"或"graphql"
   - 如果PR是标注错误，手动修改`pr_number`，设置`pr_source`为"manual"
   - 如果PR是通过commit实现的，填写commit hash到`pr_number`，设置`pr_source`为"commit"

### 2.4 人工筛选commit - 1st Round

1. 打开包含commit对应信息的JSON文件`issue_results/[PROJECT]_issues_with_code_processed.json`，并创建结果JSON文件`issue_results/[PROJECT]_issues_with_code_checked.json`，用于保存筛选后issue。
2. 使用`filter/check.py`打开`issue_results/[PROJECT]_issues_with_code.json`，浏览器打开issue link和对应的pr/commit link。
3. 如果是PR url，检查所有commit message，必要时检查conversartion页面，确定哪些commit真正和指定的enhancement相关。在`issue_results/[PROJECT]_issues_with_code_checked.json`中，对应的enhancement项，`commits`列表中，**删除不相关的commit hashes，以及所有merge commit hashes**（一般是所有commit中最后一条，被命名为"Merge branch xxx into xxx"）。
4. `commit_check`字段修改为`1`，表示该issue的commit已经被检查过。

### 2.5 人工筛选commit - 2nd Round

1. 打开包含commit对应信息的JSON文件`issue_results/[PROJECT]/[PROJECT]_issues_with_code_checked.json`，并创建结果JSON文件`issue_results/[PROJECT]_issues_with_code_checked_again.json`，用于保存筛选后issue。
2. 使用`filter/check.py`打开`issue_results/[PROJECT]_issues_with_code_checked.json`，浏览器打开issue link和对应的pr/commit link。
3. 只在满足以下三种条件的时候保留pr中的commit（单条commit充当pr的不动）：
   1. 整个pr只和单个issue相关的，整个pr保留；
   2. commit message里出现且只出现指定issue id的，该commit保留（即不涉及其他issue）；
   3. commit message显式地描述了指定issue的一个功能点，且该功能点不存在于pr提及的其他issue的，该commit保留（即明显包含于指定issue的实现）。只考虑issue原本内容，不考虑后续与原始预想的功能增强无关的讨论内容。


## 3. 人工筛选标准

### 3.1 必要条件（inclusion criteria）

每个被选入最终数据集的issue必须**同时**满足以下两个条件：

1. **包含enhancement相关的图片**
   - 图片必须明确展示某种功能增强、UI改进或新特性
   - 图片必须与issue描述的enhancement直接相关

2. **被成功接受且有对应PR或直接commit**
   - issue必须处于closed状态且关闭原因为completed
   - 必须有一个与该issue关联的PR或直接commit
   - PR必须被合并到主分支，或commit必须存在于项目历史中

### 3.2 排除标准（exclusion criteria）

排除以下情况的issues：

1. **图片不相关或非enhancement用途**
   - 仅用于展示错误/bug的截图
   - 装饰性图片或与enhancement无关的图表
   - 例如：个人头像或非功能性图片
   - 例如：需要针对特定的键盘按键做适配，上传了该类型键盘的照片， 但键盘照片与代码定位无关。
2. **PR/commit状态不符合要求**
   - PR未被合并或commit未被接受
   - PR与issue关联存疑（如PR编号小于issue编号）
   - PR/commit解决的是bug修复而非enhancement实现
   - PR仅在内容中引用了本项目issue编号，但实际为适配/升级其他项目（如依赖库、外部模块等），未真正实现本项目该issue（如PR描述为“适配vue v0.0.2关于其#1234 bug的修复”，但未实现本项目的#1234的enhancement）
3. **重复（Duplicate）issue**
   - 对于**已收集数据中包含**内容重复、被标记为duplicate或人工判断为重复的issue，只保留最早（第一个）相关的issue，其余全部删除

### 3.3 图片类型分类指南

enhancement相关图片通常属于以下几类：

1. **模拟设计（Mockup）** - 展示新功能的草图或模拟图
2. **当前功能截图（Screenshot）** - 展示现有功能的界面截图（非另外设备拍摄的图片）
2. **UI设计稿（UI Design）** - 完整的界面设计效果图
3. **功能流程图（Flowchart）** - 展示功能运作流程的图示
4. **参考设计（Reference）** - 引用自其他软件或本软件中其他模块的功能截图作为参考
5. **交互演示（Interaction）** - 通过多图展示功能交互流程
6. **其他（Else）** - 其他类型的图片，但需与enhancement相关

### 3.4 PR与commit的区别与处理

一些enhancement可能不是通过标准PR流程实现的，而是直接通过commit提交：

1. **PR实现方式（常见情况）**
   - 通过GitHub Pull Request功能提交代码
   - 经过代码审查后合并到主分支
   - 数据记录中`pr_source`为'graphql'或'search_api'或'manual'

2. **直接commit实现方式（特殊情况）**
   - 直接将代码提交到仓库，无需经过PR流程
   - 通常出现在较早期项目或由项目维护者直接提交的情况
   - 数据记录中`pr_source`应标记为`commit`
   - `pr_number`字段中应填写对应的commit hash

**重要提示**：当遇到直接通过commit实现的enhancement时，请确保在JSON数据中将`pr_source`标记为`commit`，并在`pr_number`字段中填入commit hash，以便系统正确处理相应的代码变更。

## 4. 边界情况处理指南

| 情况                                         | 处理方法                                                     |
| -------------------------------------------- | ------------------------------------------------------------ |
| 图片部分相关但不完全展示enhancement          | 仅当图片对理解enhancement需求本身有明确帮助时保留（即使图片对具体代码有直接指导价值，如键盘照片展示了需要支持的按键，但和编码没用任何关联） |
| 仅展示设备实物而无设计内容的图片             | 排除不具备实质性设计指导的图片，例如仅显示numpad arrow keys的键盘照片但未展示如何在软件中实现该功能的图片 |
| 多个PR关联到同一issue                        | 选择最先实现核心功能的PR                                     |
| PR部分实现了issue中的enhancement             | 如果主要功能已实现则保留                                     |
| 存在duplicate（重复）issue                   | 只保留第一个相关的issue，其余全部删除                        |
| PR仅引用本项目issue编号但为适配/升级其他项目 | 排除该PR与本issue的关联，不计入数据集                        |
| 通过直接commit实现而非PR                     | 标记`pr_source`为`commit`，`pr_number`填写commit ID          |

## 5. 质量控制

为确保筛选质量，实行以下策略：

1. **多人筛选验证** - 至少2名评估者独立筛选相同数据子集，计算一致性
2. **边界校准** - 评估者定期讨论边界案例，保持一致标准，对存在争议的数据项组织面对面会议，由该项参与标注人员讨论得到一致共识。
4. **记录决策理由** - 针对复杂或有争议的案例，记录接受/排除的详细理由

## 6. 数据记录格式

筛选结果在`xxx_issues_with_closing_pr_checked.json`文件中保存，记录格式如下：

```json
{
  "id": 3100196080,
  "number": 8784,
  "html_url": "https://github.com/All-Hands-AI/OpenHands/issues/8784",
  "type": "issue",
  "labels": "enhancement,openhands",
  "created_date": "2025-05-29 12:29:51",
  "updated_date": "2025-05-29 18:13:50",
  "resolved_date": "2025-05-29 18:13:50",
  "title": "Add images to docs page for OpenHands Cloud issue resolver",
  "body": "...", 
  "state": "closed",
  "comments": 2,
  "state_reason": "completed",
  "repository_url": "https://api.github.com/repos/All-Hands-AI/OpenHands",
  "labels_url": "https://api.github.com/repos/All-Hands-AI/OpenHands/issues/8784/labels{/name}",
  "comments_url": "https://api.github.com/repos/All-Hands-AI/OpenHands/issues/8784/comments",
  "events_url": "https://api.github.com/repos/All-Hands-AI/OpenHands/issues/8784/events",
  "user_login": "neubig",
  "user_url": "https://github.com/neubig",
  "assignees": "",
  "milestone_title": "",
  "milestone_description": "",
  "pull_request_url": "",
  "body_image_count": 2,
  "comment_image_count": 0,
  "total_image_count": 2,
  "pr_number": 8785,
  "pr_source": "search_api/graphql/manual/commit", 
   "image_types": [
    "Mockup",
    "UI Design",
    "Screenshot",
    "Flowchart",
    "Reference",
    "Interaction"
   ]
}
```

**重要字段说明**：
- `pr_number`: 关联的PR编号或commit ID
- `pr_source`: 指示PR关联来源
  - `search_api`或`graphql`: 通过API自动找到的关联
  - `manual`: 人工确认或修正的关联关系
  - `commit`: 直接通过commit（非PR）实现的功能，此时`pr_number`存储的是commit ID

## 7. 可靠性与效度保证（暂定）

在论文中报告以下指标以保证数据集的科学严谨性：

1. **评估者间一致性** - 计算Cohen's Kappa系数
2. **筛选覆盖率** - 记录筛选的issue总数与最终保留比例
3. **数据来源多样性** - 记录数据来源的项目数量及多样性
4. **时间分布** - 分析数据集中issue-PR/commit对的时间分布
