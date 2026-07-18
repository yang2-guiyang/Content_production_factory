# SKILL 开发说明

> 本文档是 Skill 文件包的通用开发规范。面向 AI 和开发者，说明 Skill 项目的架构设计、编码风格、打包流程和文档编写标准。适用于任何新 Skill 的开发。

> **平台说明**：本文以 Windows 11 为基准平台编写（打包、测试、目录约定均基于此）。Linux/Mac 开发者需相应调整路径分隔符和打包命令。

> **打包阶段判断**：首次打包前，用户未明确要求时禁止生成 `.spec`、运行 PyInstaller、创建 exe 或发布压缩包。若工程中已经存在 `.spec`、已发布 exe 或明确的打包配置，说明项目已经进入打包维护阶段；此后每次修改或新增代码都必须自动重新打包并验证，不能继续沿用旧构建产物。

> **更新记录**（近 5 条）
> - 2026-07-19 v6：开发流程改为循环式状态判断；Step 1 独立用于最小验证，用户要求 CLI 封装时自动执行 2～7 的适用步骤；鉴权、main 和打包按项目现状判断；SOP 与首次打包必须由用户明确要求
> - 2026-07-18 v5：统一 CLI.md 编写规范；取消简写版 CLI.md，要求已创建的 CLI.md 按实际 `--help` 结果逐条完整展开用途、完整语法、参数表和示例；v5.1：删除 SKILL.md 正文中重复的“激活条件”，触发场景只写在 frontmatter 的 `description` 中；v5.2：细化九步开发流程，增加每步进入条件、执行范围、验证标准、交付物和强制停点；v5.3：打包改为用户明确要求后才执行的可选流程；v5.4：开发流程仅供 AI 判断当前阶段，禁止自动规划或连续执行全部步骤
> - 2026-06-24 v4：§三.1 新增 AI 引导规则（逐步执行，禁止跨步）；§四.1 目录结构图、说明、§八.5 发布清单统一 .env 位置到 scripts/（与 main.py、exe 同级）
> - 2026-06-24 v3：第二轮审计修复——§一 核心概念图重绘（四步自发现居中）；§8.5/§6.2/§四.1/§三.1 五处条件标注统一；§九.1 加自发现验证项；§一末尾加快速上手路径；v3.1 第三轮修复——§一言辞改为"套装（按需）"、§四.1 加最简模式适用说明、§七.12 依赖按类型区分、§六改题为"鉴权系统（按需）"并明确多账号管理体系定位
> - 2026-06-19 02:04:20：§十.10.2 模板和 §十.10.5 放宽 description 语言限制，中英文均可，新增中文示例
> - 2026-06-19 00:05:06：最初版本

---

## 一、Skill 是什么

一个 Skill 文件包是把一项 AI 能力封装成的“Python CLI + SKILL.md + 文档（按需）+ SOP 手册”套装。Python CLI 和 SKILL.md 是必有项，main 统一入口、exe、CLI.md、SOP 手册和发布压缩包均按需配置。首次生成 exe 必须由用户明确要求；项目进入打包阶段后，每次代码变化都要重建 exe。

四层文件的分工：

| 文件 | 层 | 解决什么问题 | 谁来写 |
|------|-----|-------------|--------|
| `scripts/commands/*_commands.py` | 执行层 | 单个能力的 Click 命令组，是 CLI 开发期的默认运行入口 | 开发者 |
| `scripts/main.py`（按需） | 集成层 | 项目已经开始统一入口封装时，注册全部命令组并提供四步自发现 | 开发者 |
| `scripts/xxx.exe`（按需） | 发布执行层 | 首次打包需用户明确要求；已有打包产物后随源码更新重建 | 开发者（Python → exe） |
| `SKILL.md` | 路由层 + 命令速查 | 用户说「帮我做 X」→ 匹配场景 → 对应命令。小项目直接嵌入命令表，大项目引用 CLI.md | 开发者（按模板写） |
| `CLI.md` | 参考层（按需） | 命令参数快照——四步流程的预计算结果。创建后必须逐条完整展开；小项目可并入 SKILL.md | 开发者（按 §十.1 判断） |
| `references/*.md` | 操作层 | 一个具体需求的完整操作步骤（SOP 手册） | 开发者 + 用户可扩展 |

> **命名约定**：文件组织遵循 skill-creator 标准——可执行代码放在 `scripts/` 下；首次打包由用户明确要求，已打包项目后续自动重建。CLI.md 和 SOP 手册统一放在 `references/` 目录下。

核心概念：

```
┌───────────────────────────────────────────────────┐
│                  Skill 文件包                       │
│                                                   │
│  ┌──────────┐                    ┌──────────────┐ │
│  │   法器    │ ← 四步自发现 ──→  │  SKILL.md   │ │
│  │  (exe)   │   list-groups     │  需求路由表   │ │
│  │ 实际干活  │   list-commands   │  什么场景用   │ │
│  │          │   --help          │  哪个命令     │ │
│  │          │   ← 自描述能力    │              │ │
│  └──────────┘                    └──────────────┘ │
│       │                               │           │
│       │           ┌────────────┐      │           │
│       └──────────→│  CLI.md    │←─────┘           │
│                   │ (按需快照)  │                  │
│                   │ 省--help   │                  │
│                   │ 往返成本    │                  │
│                   └────────────┘                  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │         📂 references/  参考文档文件夹         │  │
│  │                                             │  │
│  │  📄 提取图片中的文字.md    ← 一个需求=一个SOP │  │
│  │  📄 对比两张图片差异.md    ← 多命令组合步骤   │  │
│  │  📄 分析菜单翻译中文.md    ← 手把手操作指南   │  │
│  │  📄 视频转字幕文件.md                        │  │
│  │  ...                                        │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
└───────────────────────────────────────────────────┘
```

四层协同链路：

```
用户对 AI 说：「帮我做×××」

    ↓ AI 首次使用：四步自发现
exe list-groups → exe list-commands <组> → exe <组> <cmd> --help
    AI 自行掌握工具用法，无需等待人类编写文档

    ↓ SKILL.md 路由
匹配用户意图 → 找到对应的 SOP 手册或直接定位命令

    ↓ references/ 手册（按需）
按 SOP 步骤编排业务 → 确定要用哪个命令

    ↓ CLI.md / SKILL.md 命令章节（按需，省 --help 往返）
查命令格式 → 构造完整 CLI 命令

    ↓ exe 法器执行
用户复制命令回车 → 得到结果
```

> **快速上手**：新读者按此路径阅读——§一（了解模型）→ §四.4（掌握 Click 封装模式 + 四步自发现）→ §三.1（跟开发流程）→ 按需取模板（§四.2 main.py / §四.3 命令实现 / §十 文档模板）。15 分钟可掌握核心。

---

## 二、设计理念：为什么这样设计

Skill 脚手架的设计背后有五条核心取舍，每条都是对市面上常见做法的问题回应。

### 2.1 CLI 接口 vs 固化路径

大多数 AI 应用被做成网页或 App，用户只能按预设按钮操作。比如「数据转换」工具，你只能导入→转换→导出；如果要同时筛选并生成报表，没有这个按钮就做不了。

Skill 走相反的路——按照第一性原理，只封装和暴露最核心的 CLI 接口。一个命令只做一件事（如 filter 筛选数据），至于筛选之后是导出、汇总、还是分析，由用户自由组合。用户像搭乐高一样编排命令，AI 负责生成组合指令。

### 2.2 封装调用 vs 临时生成代码

大部分 Skill 是纯提示词包——AI 只能输出文字，无法执行实际操作。即使 AI 能当场生成 Python 代码，每次生成的代码不一样，缺乏文档化，质量不稳定，且每次都要在对话里解释需求、生成代码、调试修正，大量浪费 Token。

Skill 的做法：把经过验证的 Python 代码预先封装成固定的 CLI 命令。AI 不再临时生成代码，而是直接调用已封装好的命令——稳定、可复用、省 Token。这些命令有明确的文档（咒语表），AI 每次调用的是同一套逻辑。

更重要的是：**封装成 exe 后，AI 无法触及代码层**。纯脚本方案中，AI 可能尝试"优化"或"修复"代码，一不小心就把整个 Skill 改废。exe 是封闭的——AI 只能通过 CLI 命令调用它，永远改不到内部逻辑。Skill 的稳定性得到了硬保障。

对比 MCP 方案：Skill 用 Markdown 文档（SKILL.md + references/）编排业务逻辑，不需要 JSON Schema 定义工具，编写和维护成本大幅降低。

### 2.3 exe 封装 vs 环境依赖

纯代码方案（如开源 Python 项目）需要先装 Python、再 pip install 依赖，换台电脑就要重来。对非技术用户来说，环境配置这一步就劝退了。

Skill 把所有依赖和运行环境打包成单个 exe 文件。不需要安装 Python，不需要命令行基础——下载 exe 放到任意目录，AI 直接生成 CLI 命令，用户复制粘贴到终端就能执行。在任何 Windows 设备上都能直接用。

### 2.4 文档分层 vs 混杂配置

很多工具把"能干什么命令"和"什么场景用什么命令"混在一个配置里，改一个使用场景就要翻整个文件。

Skill 严格分层：
- **四步自发现**（`list-groups` / `list-commands` / `--help`）：AI 的运行时入口——拿到 exe 即可自行掌握全部命令。零维护，永远与代码同步
- **SKILL.md**：负责「用户说什么话时用哪个命令」——路由表 + 命令速查。小项目直接在此嵌入命令表，大项目引用 CLI.md
- **CLI.md**（按需）：命令参数快照——四步流程的预计算结果。创建后按固定格式逐条完整展开；小项目可并入 SKILL.md
- **references/*.md**（SOP 手册）：负责「某个具体需求怎么一步步做」——操作手册，用户可以自己增删

四层独立，互不干扰。核心原则：**Code is the source of truth — 四步自发现永远准确；文档是加速包，不是必需品。**

### 2.5 独立鉴权 vs 完全开源

传统 Skill 大多是开源脚本或纯提示词，代码完全暴露，无法控制分发、无法计费、无法保护核心逻辑。

Skill 的鉴权方案通过 `.env` 文件把三件事解耦：
- **代码闭源**：exe 封装后，核心逻辑不可见、不可改
- **用户自带 Key**：用户用自己的云服务 Key，按量付费给云平台
- **法器可计费**：未来可扩展为发放授权 Key、按调用次数计费、订阅制等

不需要自己搭建后端服务，不需要维护用户数据库，`.env` 一个文件就完成了鉴权闭环。这让 Skill 从"开源小工具"变成"可商业化的产品"。

---

## 三、开发工作流

### 3.1 新 Skill 开发流程

> **AI 引导规则**：以下 Step 是状态判断，不是必须从 1 走到 9 的线性流水线。测试新接口、功能或脚本时只执行 Step 1；用户明确要求“封装为 CLI”时，自动规划并执行 Step 2～7 中适用的步骤，不再逐步向用户索要确认。一个步骤包含多项实现时，仍必须逐项实现、立即验证，禁止全部写完后统一测试。

> **循环原则**：项目会长期在“Step 1 最小验证 → Step 2～7 CLI 更新循环 → 再回到 Step 1 验证下一个能力”之间反复。不得因为一个能力验证成功，就自动创建 CLI、main、SOP 或打包；也不得因为一个 CLI 完成，就假设全部功能开发结束。

```
用户要求测试新接口、功能或脚本
        │
        ▼
Step 1: 写最小可运行 Python 脚本并真实验证
        │
        └── 汇报结果后停止，不自动封装 CLI

用户明确要求把已验证能力封装为 CLI
        │
        ▼
Step 2: 创建或更新 Click 命令并立即实测
        │
        ▼
Step 3（条件）: 外部 API 且现有鉴权不足时创建或更新 .env 鉴权
        │
        ▼
Step 4（条件）: 已有 main.py 时注册新命令；没有 main.py 时跳过
        │
        ▼
检查是否已有打包文件或历史发布物
        ├── 有 → Step 5 重新打包 → Step 6 验证新构建
        └── 无 → 跳过 Step 5、Step 6，保持 CLI 开发期
        │
        ▼
Step 7: 创建或同步更新 SKILL.md、CLI.md 等相关命令文档
        │
        └── 完成本次 CLI 更新循环，等待下一个测试或封装需求

全部功能和 CLI 基本完成后
        ├── 用户明确要求 SOP → Step 8
        ├── 用户明确要求首次打包 → Step 5、Step 6
        └── 用户明确要求发布包 → Step 9
```

#### 3.1.1 触发与循环协议

AI 必须先识别用户当前表达的是哪一种意图，再决定执行范围：

| 用户意图 | 自动执行范围 | 执行后行为 |
|---|---|---|
| 测试新接口、新功能、新脚本 | 只执行 Step 1 | 汇报真实结果并停止，不规划 Step 2～9 |
| 将功能、脚本或接口封装为 CLI | 自动规划并执行 Step 2～7 中适用的步骤 | 完成代码、真实 CLI 测试、条件集成、条件重打包和文档同步 |
| 新增或修改已有 CLI | 重新执行 Step 2，并按现状检查 Step 3～7 | 已有 main、打包和文档必须同步更新 |
| 编写 SOP | 仅用户明确要求时执行 Step 8 | 默认不做，通常等待全部 CLI 和 main 基本完成 |
| 首次打包 | 仅用户明确要求时执行 Step 5、Step 6 | 工程从此进入打包维护阶段 |
| 更新已打包项目 | 修改代码后自动执行 Step 5、Step 6 | 新代码不得配旧 exe |
| 生成最终发布包 | 仅用户明确要求时执行 Step 9 | 输出发布文件清单和验证结果 |

CLI 更新循环固定按以下顺序处理，但条件步骤可根据工程现状自动跳过：

1. **Step 2 必做**：创建或修改 Click 命令，逐个命令真实运行。
2. **Step 3 条件执行**：需要新鉴权且现有鉴权不满足时执行；纯计算或已有鉴权可直接跳过并说明理由。
3. **Step 4 条件执行**：发现现有 `scripts/main.py` 时必须注册并验证新命令；没有 main 时不创建，继续保持独立命令模块。
4. **Step 5～6 按打包状态执行**：已有打包文件或发布物时必须重打包并验证；没有时默认跳过，首次打包必须有用户明确指示。
5. **Step 7 必做**：同步命令帮助、CLI.md、SKILL.md 和 README 中已经存在的相关内容；缺失文档按本 Step 规则创建。
6. **Git 提交**：整个 CLI 更新循环验证通过后，使用中文说明创建一次范围清晰的提交。
7. **结果汇报**：说明哪些条件步骤执行、哪些跳过及原因，然后停止，等待下一项能力测试或 CLI 需求。

以下行为一律禁止：

- 用户只要求测试时，在 Step 1 同时创建 Click 命令、`.env`、`main.py`、文档或打包文件
- 用户要求 CLI 封装时，只写 Click 命令却不检查鉴权、main、打包状态和相关文档
- 工程没有任何打包迹象且用户未明确要求首次打包时，生成 `.spec`、exe 或发布压缩包
- 工程已有打包文件或历史 exe 时，修改代码后跳过重打包
- 工程没有 `main.py` 且用户未要求统一入口时，擅自创建 main
- 未完成全部主要功能和 CLI，或用户未明确要求时，自动编写 SOP
- 把 Step 1、CLI 封装、main、SOP 和首次打包机械串成一次性线性任务
- 未运行真实命令就宣称验证通过
- 当前命令测试失败时继续本次循环的后续步骤
- 用户改变模型、接口或功能范围后继续沿用旧验证结果

如果用户中途改变模型、API、输入方式或功能范围，先回到 Step 1 只验证变化部分。只有用户明确要求把变化后的能力封装为 CLI 时，才进入一次新的 Step 2～7 更新循环。

#### 3.1.2 Step 1：写最小可运行 Python 脚本

**目标**：用最少代码证明核心 API 或核心计算能力真实可用。

**进入条件**：

- 用户明确要求测试一个新接口、新功能或新脚本
- 已确定模型、API、输入方式和预期输出
- 已取得真实测试所需的密钥、样本或测试数据

**只做以下工作**：

1. 创建一个最小 Python 脚本，不使用 Click、argparse 或复杂封装
2. 固定一组最小测试参数，直接调用核心 API 或核心函数
3. API 请求优先使用直白的 `requests.post(url, headers=headers, json=data)`
4. 按项目规范处理 UTF-8 stdout、超时和最基本的错误信息
5. 使用真实样本运行脚本，保存真实返回结构

**验证标准**：

- 脚本能从头到尾运行
- API 返回成功状态，或本地计算得到可核对的正确结果
- 能从真实响应中读取最终业务字段
- 中文输出无乱码
- 密钥未写入受 Git 管理的文件

**交付物**：

- 最小 Python 脚本
- 实际运行命令
- 真实响应的关键字段和示例值
- 需要保留脚本时创建中文 Git 提交；一次性验证脚本按用户约定清理后可以无提交

**禁止事项**：不得创建命令组、`.env` 读写模块、`main.py`、spec、SKILL.md、CLI.md 或 SOP。

**结束规则**：汇报真实验证结果后停止。不得自动规划、建议或执行 CLI 封装；只有用户随后明确要求“封装为 CLI”时，才启动 Step 2～7 更新循环。

#### 3.1.3 Step 2：拆分 Click 命令组

**目标**：把已验证的功能、脚本或接口转换为清晰、可发现的 CLI 接口。

**进入条件**：用户明确要求将某个功能、脚本或接口封装为 CLI。能力可以来自当前会话的 Step 1，也可以是工程中已经存在并验证过的脚本或功能。

**只做以下工作**：

1. 将最小脚本迁移到 `scripts/commands/<name>_commands.py`
2. 使用 `click.group()` 创建命令组
3. 按“一件事一个子命令”设计命令、必填参数和可选参数
4. 为每个参数补充中文 `metavar`、格式说明和示例值
5. 为命令 docstring 补充完整调用示例
6. 添加网络异常、接口错误、输入错误和 JSON 解析错误处理
7. 输出便于 AI 解析的 JSON

**验证标准**：

- 命令组 `--help` 正常
- 每个子命令 `--help` 能独立说明完整用法
- 必填参数缺失时返回非零退出码
- 错误输入不会输出 Python 堆栈
- 至少执行一次真实 CLI 命令，结果与 Step 1 一致

**交付物**：

- Click 命令模块
- 最终 CLI 命令格式
- `--help` 输出
- 正常路径和错误路径验证结果
- 本 Step 的改动纳入本次 CLI 更新循环统一提交

**禁止事项**：不得封装尚未真实验证的模型、API 或功能；不得在 CLI 命令尚未通过时继续条件集成和文档同步。

**循环衔接**：CLI 实测通过后，自动检查 Step 3～7 的适用条件，不需要再次向用户请求逐步确认。

#### 3.1.4 Step 3：实现 .env 鉴权

**目标**：让外部 API 密钥从 `scripts/.env` 安全读取和维护。

**进入条件**：Step 2 已通过，并且新 CLI 需要外部鉴权，而现有 `.env`、读取模块或密钥命令不存在或不能满足新需求。

**API 型 Skill 只做以下工作**：

1. 检查现有鉴权实现，优先复用已有 `.env`、读取模块和密钥命令
2. 不存在时创建 `scripts/.env`，写入当前 Skill 实际需要的键名
3. 将 `scripts/.env` 加入 `.gitignore`
4. 不存在时创建只读模块，按 UTF-8 逐行读取，使用 `split("=", 1)`
5. 不存在时创建独立写入命令模块，提供状态查询、写入和删除能力
6. 状态查询只显示是否配置，不回显密钥
7. 修改业务命令，使其只通过读取模块取得密钥
8. 同时验证源码模式；项目已进入打包阶段时再验证 PyInstaller 路径逻辑

**验证标准**：

- 移除系统环境变量后，业务命令仍能通过 `scripts/.env` 成功调用 API
- 密钥中包含 `=` 时不会被截断
- 写入和删除不会破坏其他配置项
- `.env` 不出现在 Git 暂存区或提交中
- 真实 API 调用成功

**交付物**：

- `scripts/.env`（不提交）
- 只读配置模块
- 独立密钥维护命令模块
- `.gitignore` 规则
- 真实鉴权验证结果
- 本 Step 的改动纳入本次 CLI 更新循环统一提交

**自动跳过规则**：纯计算型 CLI，或工程现有鉴权已经覆盖新命令时，自动跳过 Step 3，并在最终汇报中说明“无需新增鉴权”或“已复用现有鉴权”。

**循环衔接**：完成或跳过后自动检查 Step 4，不展示密钥内容。

#### 3.1.5 Step 4（条件）：更新 main.py

**目标**：在项目已经使用统一入口时，把新 CLI 注册到现有 main 并保持 AI 四步自发现完整。

**进入条件**：工程中已经存在 `scripts/main.py`，或用户明确要求开始建立统一入口。

**只做以下工作**：

1. 读取现有 `scripts/main.py`，保持当前注册和命名风格
2. 显式导入并注册本次新增或修改的命令组，不做动态发现
3. 更新 `list-groups` 和 `list-commands <group>` 的结构化自发现结果
4. 在第三方库导入前保持 stdout 使用 UTF-8
5. 保持源码入口格式为 `python scripts/main.py <组> <命令> [参数]`
6. 只有用户明确要求首次建立统一入口时才创建 `scripts/main.py`

**验证标准**：

- `python scripts/main.py --help` 正常
- `list-groups` 返回完整、有效的 JSON
- 每个命令组都能通过 `list-commands` 被发现
- 每个子命令的 `--help` 可访问
- 业务命令通过 `main.py` 真实运行成功
- 中文输出无乱码

**交付物**：

- `scripts/main.py`
- 四步自发现的实际输出
- 通过统一入口执行的真实结果
- 本 Step 的改动纳入本次 CLI 更新循环统一提交

**自动跳过规则**：工程中没有 `scripts/main.py` 且用户没有要求统一入口时，说明项目仍处于独立 CLI 开发期，自动跳过 Step 4；不得为了走流程而创建 main。

**循环衔接**：完成或跳过后检查工程是否已进入打包阶段，再决定 Step 5、Step 6 是否执行。

#### 3.1.6 Step 5（条件）：生成或更新 spec 并打包 exe

**目标**：将已验证的 Python CLI 打包为 Windows 可执行文件。

**进入条件**满足任一项即可：

- 工程中已经存在 `.spec`、历史 exe、`dist/` 发布物或明确的打包脚本，说明项目已进入打包维护阶段
- 用户明确要求首次打包，并且主要功能和 CLI 已基本完成

**只做以下工作**：

1. 优先读取并更新现有 spec；首次打包时才运行 `pyi-makespec` 生成 spec
2. 按项目命名规范修改 exe 名称
3. 检查并补充必要的 `hiddenimports`、数据文件和依赖
4. 运行 PyInstaller 生成 exe
5. 将 exe 放在 `dist/` 中验证，再按发布结构准备放入 `scripts/`

**验证标准**：

- PyInstaller 无构建错误
- exe 能显示 `--help`
- exe 的 `list-groups` 和 `list-commands` 返回正确 JSON
- exe 能读取同级 `.env`
- 至少执行一次真实业务命令
- 中文输出无乱码

**交付物**：

- 现有或临时生成的 `<name>.spec`（是否保留遵循项目现有规则）
- 最新的 `<name>.exe`
- 构建命令和构建结果
- exe 基础验证结果
- 本 Step 的改动纳入本次 CLI 更新循环统一提交

**自动执行规则**：项目已有打包迹象时，任何源码或依赖变化都必须自动重新执行本 Step。没有打包迹象且用户未明确要求首次打包时，自动跳过。

**禁止事项**：不得用旧 exe 代表新源码；本 Step 只验证当前开发环境中的 exe，不得把它描述为已通过干净环境验证。

**循环衔接**：本 Step 执行成功后必须自动进入 Step 6；跳过时直接进入 Step 7。

#### 3.1.7 Step 6（条件）：在干净环境验证 exe

**目标**：证明发布物在没有源码和 Python 依赖的环境结构中可以独立运行。

**进入条件**：本次 CLI 更新循环实际执行了 Step 5，并成功生成新的 exe。

**只做以下工作**：

1. 创建独立测试目录，不直接在源码目录中验证
2. 只复制 exe 和测试所需的 `.env`、输入样本
3. 不复制 Python 源码、虚拟环境或本机依赖目录
4. 依次验证 `--help`、四步自发现、配置读取、正常业务命令和错误路径
5. 验证完成后清理测试目录中的密钥副本

**验证标准**：

- 无需调用 `python` 即可运行
- 四步自发现结果与源码模式一致
- 正常命令返回正确结果
- 缺少参数、缺少密钥、文件不存在和网络错误均有友好提示
- 中文输出无乱码

**交付物**：

- 干净环境目录结构说明
- 实际执行命令和输出
- 正常路径与错误路径验证记录
- 本 Step 的验证记录纳入本次 CLI 更新循环统一提交

**禁止事项**：不得使用源码模式的成功结果代替 exe 验证。

**循环衔接**：验证通过后自动进入 Step 7。Step 5 未执行时不得单独执行本 Step。

#### 3.1.8 Step 7：创建或同步命令文档

**目标**：每次 CLI 变化后立即同步命令文档和意图路由，避免文档落后于源码。

**进入条件**：本次 Step 2 CLI 修改已经通过真实测试；条件执行的鉴权、main 和打包步骤也已完成或明确跳过。

**只做以下工作**：

1. `SKILL.md` 已存在时，更新 `description`、场景路由和命令速查
2. `SKILL.md` 不存在时，为第一个正式 CLI 创建最小合规文件；frontmatter 只保留 `name` 和 `description`
3. 所有触发场景只写入 `description`，正文不重复“激活条件”
4. 根据 §十.1 创建或更新 `references/CLI.md`
5. CLI.md 按真实 `--help` 逐条完整展开用途、语法、参数表和已验证示例
6. 同步 README 中已经存在的命令说明、目录结构或运行示例
7. 项目存在 main 或 exe 时，同时更新统一入口或 exe 的运行方式；不存在时只写独立源码命令
8. 运行 skill-creator 的 `quick_validate.py`；若原来没有根 `SKILL.md`，先按第 2 项创建，再执行校验

**验证标准**：

- frontmatter 格式和技能名称合法
- `description` 同时说明能力和触发场景
- 正文没有重复激活条件
- 文档中的命令、参数和默认值与真实 `--help` 一致
- 所有示例均已实际运行
- `quick_validate.py` 通过

**交付物**：

- `SKILL.md`
- 按需创建的 `references/CLI.md`
- 文档与 CLI 对照结果
- skill 校验结果
- 本次 CLI 更新循环的中文 Git 提交

**禁止事项**：不得根据源码印象或旧文档猜测参数，不得留下 TODO、待补充或省略号。

**结束规则**：完成文档对照、中文 Git 提交和结果汇报后，结束本次 CLI 更新循环。不得自动进入 Step 8、首次打包或发布；等待用户提出下一项测试、CLI 封装或明确的后期任务。

#### 3.1.9 Step 8：编写 SOP 手册

**目标**：用场景化操作文档覆盖用户最常见的完整任务。

**进入条件**：用户明确要求编写 SOP，并且主要功能、CLI 及通常情况下的 main 入口已经基本完成。

**只做以下工作**：

1. 从真实用户需求中选择 3～5 个最高频场景
2. 每个场景创建一份 `references/<动词+名词>.md`
3. 每份 SOP 写明需求、适用场景、前置条件、逐步命令、预期结果和已知限制
4. 每条命令必须给出源码运行方式；项目已按用户要求生成 exe 时，再同时给出 exe 运行方式
5. 使用相关 SOP 链接形成简单知识网络
6. 逐篇执行命令并核对预期输出

**验证标准**：

- 至少 3 份 SOP
- 每份 SOP 独立、自包含
- 命令可直接复制执行
- 预期结果来自真实运行
- 文件名、交叉链接和 SKILL.md 路由一致

**交付物**：

- 3～5 份 SOP 手册
- 每份 SOP 的实际验证记录
- 路由与 SOP 对照表
- 中文 Git 提交

**禁止事项**：不得一次写完全部 SOP 后统一测试；必须写一篇、验证一篇，再写下一篇。

**结束规则**：逐篇汇报验证结果后停止。SOP 默认不做，不得因为一次 CLI 更新自动进入本 Step。

#### 3.1.10 Step 9（可选）：打包发布

**目标**：生成不含源码和密钥的最终 Skill 发布包。

**进入条件**：主要功能、CLI 和所需 SOP 已完成，用户主动明确要求生成最终发布包。若工程尚未打包，先执行 Step 5、Step 6；若已打包，确认当前 exe 与最新源码一致。

**只做以下工作**：

1. 按发布清单收集 exe、SKILL.md、CLI.md（按需）、SOP 和必要 assets
2. 将 exe 放到发布包的 `scripts/` 下
3. 排除 `.env`、Python 源码、`runtime/`、`build/`、缓存和测试文件
4. 按 `skill-<名称>-v<版本>.zip` 命名压缩包
5. 解压到新目录，按发布结构执行最终冒烟验证
6. 运行 §九的完整质量检查清单

**验证标准**：

- 发布包结构完整
- 发布包不包含密钥、源码或临时文件
- 解压后 exe 可运行
- 四步自发现、业务命令和文档示例通过
- SKILL.md、CLI.md、SOP 与 exe 行为一致

**交付物**：

- 最终 zip 发布包
- 发布文件清单
- 解压验证记录
- 最终质量检查结果
- 中文 Git 提交

**强制停点**：向用户展示发布包路径、文件清单、验证结果和最终提交 ID，等待用户决定是否发布或推送远程仓库。

### 3.2 开发优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 最小 Python 验证 | 用户要求测试时，只证明接口、功能或脚本可运行 |
| P0 | CLI 更新循环 | 用户要求封装时，完成 Click 命令、真实 CLI 测试和相关文档同步 |
| P0（条件） | 鉴权与 main 集成 | 仅在新鉴权确有需要，或工程已有 main/用户明确要求入口时执行 |
| P0（条件） | 重打包与 exe 验证 | 已进入打包阶段的工程，每次代码变化后必须执行 |
| P1 | SKILL.md / CLI.md | 随每次 CLI 变化创建或同步意图路由、命令和示例 |
| P2（明确要求） | SOP 手册 | 主要功能和 CLI 完成后，用户明确要求才编写 |
| P2（明确要求） | 首次打包与发布 | 工程无打包迹象时，必须等待用户明确要求 |
| P3 | 排版 + 互链 | 统一格式，完善交叉引用 |

---

## 四、项目架构

### 4.1 目录结构

每一个 Skill 是一个独立的项目，目录结构如下：

```
📦 skill-<名称>/
├── <name>.spec（条件）         # 已进入打包阶段时才存在的 PyInstaller 配置
├── .gitignore                 # 忽略 build / dist / runtime / __pycache__
├── SKILL.md                   # 需求路由表（必需；frontmatter 定义触发条件，正文定义场景路由）
├── scripts/                   # 可执行代码（必需）
│   ├── .env（按需）            # 外部 API Key 配置，不计入 Git
│   ├── main.py（条件）         # 已有统一入口或用户明确要求时才创建和更新
│   ├── <name>.exe（条件）      # 项目进入打包阶段后生成和持续重建
│   ├── commands/               # 命令组实现（多命令组 Skill 需要。单文件 Skill 可省略，见 §四.4 最简模式）
│   │   ├── env_reader.py         # .env 读模块（给其他代码调用，需鉴权时）
│   │   ├── env_writer.py         # .env 写模块（CLI 维护命令，需鉴权时）
│   │   └── xxx_commands.py        # 各子命令的实现
│   └── api/                    # 外部 API 封装（按需存在）
│       └── xxx_api.py         # 对应外部 API 的 Python 封装
├── references/                # 参考文档（按需存在）
│   ├── CLI.md                  # CLI 命令参考（按需，详见 §十.1。小项目可省略，并入 SKILL.md）
│   ├── 需求A.md                # 场景化 SOP 手册（仅用户明确要求时创建）
│   ├── 需求B.md
│   └── 需求C.md
├── assets/                     # 静态资源（按需存在）
│   └── template.json           # 输出模板、图标、字体等
├── runtime/                    # 运行时工作区（.gitignore）
│   ├── inputs/                 # 输入文件暂存
│   ├── outputs/                # 输出文件
│   └── tmp/                    # 临时脚本和缓存
├── build/（条件）              # 打包时产生的 PyInstaller 临时文件（.gitignore）
└── dist/（条件）               # 项目现有打包流程使用时产生的输出目录
```

**说明：**
- 只有需要外部 API 鉴权时才创建 `.env`；创建后固定放在 `scripts/` 下，与可选的 `main.py`、exe 同级。用 `getattr(sys, "frozen", False)` 判断运行模式，两个阶段路径一致
- 可执行代码统一放在 `scripts/` 下，遵循 skill-creator 标准
- `commands/` 和 `api/` 之间没有相互依赖，`commands/` 中的 Click 命令调用 `api/` 的函数
- `.env` 的读写需拆为两个模块：**读模块**（供其他代码调用取值）和 **写模块**（Click CLI 命令，供用户维护），详见 §六
- 以上规则适用于多命令组 + 鉴权型 Skill。单文件 / 纯计算型 Skill 按 §四.4 最简模式适用
- 每个 Skill 项目独立，不与其它 Skill 共享代码
- `main.py`、spec、exe、`build/` 和 `dist/` 都不是首次 CLI 封装的默认产物，必须按 §三的入口状态和打包状态判断
- 项目进入打包阶段后，PyInstaller 将入口及依赖合并成一个 exe。发布包中 exe 放在 `scripts/` 下；源码 `scripts/` 中的 `.py` 文件不包含在发布包中
- CLI.md 和 SOP 手册统一放在 `references/` 下，遵循 skill-creator 标准
- `runtime/` 是运行时工作区，下设三个子目录：`inputs/`（输入文件暂存）、`outputs/`（处理结果）、`tmp/`（临时脚本和缓存）。**此目录由 AI 按需创建**——脚本需要读写文件时，先检查 `runtime/inputs/`、`runtime/outputs/`、`runtime/tmp/` 是否存在，不存在则自动创建。整个 `runtime/` 不计入版本控制

### 4.2 main.py — 条件启用的 CLI 统一入口

只有工程已经存在 `scripts/main.py`，或用户明确要求首次建立统一入口时，才应用本节。没有 `main.py` 时，保持单个脚本或独立 Click 命令组，不为满足目录模板而创建入口。

```python
import sys
import io
import json
import click

# 步骤1：解决 PyInstaller 打包后 GBK 编码问题。
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 步骤2：导入所有命令组。
from commands.xxx_commands import cli as xxx_cli

#---------------------------
# 函数说明：创建主命令组，注册所有子命令。
#---------------------------
@click.group()
def cli():
    """<Skill名称> — <一句话描述>。"""
    pass

# 步骤3：注册子命令组。
cli.add_command(xxx_cli, name="<子命令名>")

# ═══════════════════════════════════════════════════════
# 步骤4：注册 AI 自发现辅助命令（必须，每个 Skill 必备）
# ═══════════════════════════════════════════════════════

@cli.command(name="list-groups")
def list_groups():
    """列出所有已注册的命令组及其描述（JSON 格式，供 AI 解析）。"""
    groups = []
    for cmd_name, cmd_obj in cli.commands.items():
        if cmd_name in ("list-groups", "list-commands"):
            continue
        desc = (cmd_obj.help or "").strip().split("\n")[0]
        groups.append({"name": cmd_name, "description": desc})
    print(json.dumps(groups, ensure_ascii=False, indent=2))


@cli.command(name="list-commands")
@click.argument("group_name")
def list_commands(group_name):
    """列出指定命令组下的所有子命令（JSON 格式，供 AI 解析）。"""
    group = cli.commands.get(group_name)
    if group is None:
        print(json.dumps({"error": "命令组 '" + group_name + "' 不存在"}, ensure_ascii=False))
        return
    commands = []
    for cmd_name, cmd_obj in group.commands.items():
        desc = (cmd_obj.help or "").strip().split("\n")[0]
        commands.append({"name": cmd_name, "description": desc})
    print(json.dumps(commands, ensure_ascii=False, indent=2))


# 步骤5：程序入口。
if __name__ == "__main__":
    cli()
```

**关键规则：**
- 用 `click.group()` 创建命令组，用 `cli.add_command()` 注册子命令组
- 必须包含 UTF-8 stdout hack（前三行），解决 Windows GBK 编码问题
- **必须包含 `list-groups` 和 `list-commands` 两个辅助命令**（详见 §四.4）
- 不搞动态发现、不搞 `__init__.py`、不搞 `pkg_resources`
- `name` 参数用英文小写加连字符，如 `"image-understand"`

### 4.3 commands/xxx_commands.py — 命令实现

每个命令文件遵循以下结构：

```python
import json
import os
import sys

import click
import requests

# 步骤0：把 scripts/ 目录加入模块搜索路径。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commands.authorization_env import get_env_value


#---------------------------
# 函数说明：创建 click 命令组，统一管理所有子命令。
#---------------------------
@click.group()
def cli():
    """<命令组描述>"""
    pass


#---------------------------
# 函数说明：执行 xxx 子命令。
#---------------------------
@cli.command(name="<子命令名>")
@click.argument("<参数名>")
@click.option("--<选项名>", default="<默认值>", help="<说明>")
def xxx_command(参数名, 选项名):
    """<命令说明>"""
    # 步骤1：读取 API Key。
    api_key = get_env_value("<KEY名>")
    if api_key is None:
        click.echo("未配置 <KEY名>，请检查 .env 文件")
        return

    # 步骤2：准备接口地址。
    url = "https://api.example.com/endpoint"

    # 步骤3：准备请求头。
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
    }

    # 步骤4：准备请求体。
    data = {
        "param1": param1,
        "param2": param2,
    }

    # 步骤5：发送请求。
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.post(url, headers=headers, json=data, timeout=30)
    except requests.exceptions.Timeout:
        click.echo("请求超时，请检查网络后重试")
        return
    except requests.exceptions.ConnectionError:
        click.echo("网络连接失败，请检查网络设置")
        return
    except requests.exceptions.RequestException as error:
        click.echo("请求失败：" + str(error))
        return

    # 步骤6：检查响应状态。
    if response.status_code != 200:
        click.echo("接口返回错误，状态码：" + str(response.status_code))
        click.echo("响应内容：" + response.text[:500])
        return

    # 步骤7：输出结果。
    click.echo(json.dumps(response.json(), ensure_ascii=False))


if __name__ == "__main__":
    cli()
```

**关键规则：**
- 每个 `@cli.command()` 的函数内部按"步骤1、步骤2……"标注
- 输出用 `click.echo`，不用 `print`
- HTTP 请求统一用 `requests.Session()`，设置 `trust_env = False` 和 `timeout=30`
- HTTP 请求必须用 `try/except` 捕获超时、连接错误等异常，见 §七 7.13
- 返回 JSON 用 `json.dumps(..., ensure_ascii=False)` 输出，保证中文不转义

#### 纯计算型命令模板（无需鉴权、无网络请求）

当 Skill 只做本地计算（如量化指标、文件格式转换、数据处理）时，不需要 `authorization_env.py`、不需要 API Key、不需要 HTTP 请求。命令实现更简单：

```python
import os
import sys

import click

# 步骤0：把 scripts/ 目录加入模块搜索路径。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calc_module import compute_something    # 纯计算模块，零外部依赖


#---------------------------
# 函数说明：创建 click 命令组。
#---------------------------
@click.group()
def cli():
    """<命令组描述>"""
    pass


#---------------------------
# 函数说明：执行 xxx 子命令。
#---------------------------
@cli.command(name="<子命令名>")
@click.option("--data-file", required=True, help="输入数据文件路径")
@click.option("--out", default=None, help="输出 JSON 文件路径")
def xxx_command(data_file, out):
    """<命令说明>"""
    # 步骤1：校验输入文件。
    if not os.path.exists(data_file):
        click.echo("错误：文件不存在 — " + data_file)
        return

    # 步骤2：读取数据。
    import json
    data_file_handle = open(data_file, "r", encoding="utf-8")
    data = json.load(data_file_handle)
    data_file_handle.close()

    # 步骤3：计算。
    result = compute_something(data)

    # 步骤4：输出。
    output_json = json.dumps(result, ensure_ascii=False)
    if out:
        out_file = open(out, "w", encoding="utf-8")
        out_file.write(output_json)
        out_file.close()
        click.echo("结果已写入 " + out)
    else:
        click.echo(output_json)


if __name__ == "__main__":
    cli()
```

**关键规则（纯计算型）：**
- 不 import `requests`、不调 `authorization_env`
- 输入通过 `--data-file` 或标准输入读取，输出 JSON 到控制台或 `--out` 文件
- 纯计算逻辑放在独立模块（如 `calc_module.py`），命令文件只做 CLI 适配
- 错误处理同样用中文提示，禁止暴露 Python 堆栈

### 4.4 Click 命令组封装模式与 AI 四步自发现

#### 模式概述

将 Python 脚本封装为 Click 命令组，多个命令组注册到 `main.py` 作为统一入口。打包成 exe 后，AI 无需查阅任何外部文档，通过固定的四步流程即可自行发现并调用所有命令。

> **实例参考**：`scripts/akdoc.py` 是此模式的典型案例——从手工 `sys.argv` 解析迁移到 Click 后，删掉 ~90 行解析代码，换为 ~55 行装饰器，子命令逻辑零改动。`--help` 自动生成、参数类型自动校验、错误信息统一风格。

#### 与传统手工解析的对比

| 维度 | 手工 sys.argv | Click 封装 |
|------|-------------|-----------|
| 帮助信息 | 需手写 print 语句 | `--help` 自动生成（含子命令帮助） |
| 参数校验 | 手动 `if len <` 判断 | 声明式 `required` / `type` |
| 类型转换 | 手动 `int()` / `float()` | `type=int` 声明式，自动校验 |
| 错误提示 | 自行拼接字符串 | Click 统一风格，中文友好 |
| AI 发现能力 | 需人工编写 CLI.md | 内置四步自发现 + `--help` 链 |
| 打包准备 | 需额外适配 | 天然适合 PyInstaller 打包为 exe |
| 代码量 | ~90 行解析样板 | ~55 行装饰器 |

#### AI 四步自发现流程

AI 拿到 exe 后，无需查阅任何文档即可自行掌握全部命令。此流程是 Skill 设计的核心机制——让 AI 自己"学会"工具用法，而非依赖人类预写的文档。

```
Step 1: 查顶层有哪些命令组（能力模块）
        → exe list-groups
        → 返回 JSON：{"name": "data", "description": "数据处理命令组"}
        → 备选：exe --help（文本格式，人类友好）

Step 2: 查命令组下有哪些子命令及用途
        → exe list-commands data
        → 返回 JSON：[{"name": "filter", "description": "按条件筛选数据"}, ...]
        → 备选：exe data --help（文本格式）

Step 3: 查子命令的帮助文档——了解参数、使用方法、注意事项
        → exe data filter --help
        → Click 自动输出：必填参数列表、可选参数及默认值、命令说明
        → 重点关注：必填参数（不可为空）、默认值（可省略）

Step 4: 执行命令
        → 按 Step 3 获取的参数信息构造并执行命令
        → exe data filter --input source.dat --out result.json
```

**为什么需要 `list-groups` / `list-commands`（JSON 输出）？**

Click 的 `--help` 输出是面向人类的格式化文本，AI 解析文本的可靠性不如直接解析 JSON。`list-groups` 和 `list-commands` 提供结构化输出，确保 AI 能 100% 准确获取命令列表。`--help` 则作为人类阅读和 Step 3（参数级详情）的主要入口。

#### 必需的三条辅助命令

每个 Skill 的 `main.py` 必须注册以下命令：

| 命令 | 输出格式 | 对应 AI 步骤 | 说明 |
|------|---------|------------|------|
| `list-groups` | JSON | Step 1 | 列出所有已注册的命令组及其 docstring 首行 |
| `list-commands <group>` | JSON | Step 2 | 列出指定命令组下的所有子命令及 docstring 首行 |
| `<group> <cmd> --help` | 文本 | Step 3 | Click 原生，打印命令的完整帮助（参数+用法） |

**实现要点：**
- `list-groups` 须排除自身和 `list-commands`，避免无限嵌套
- `list-commands` 须处理不存在的命令组名，返回 `{"error": "..."} ` 而非崩溃
- 命令组 docstring 首行即为 `description` 字段——编写时须确保第一行说清用途
- 这两个命令的实现不依赖任何外部模块，纯 Click 内省（`cli.commands` 属性）

#### 命令组编写约定

每个 `commands/xxx_commands.py` 遵循以下结构，确保 docstring 被正确提取：

```python
import click

@click.group()
def cli():
    """数据处理命令组。"""   # ← 此行会被 list-groups 提取为 description
    pass

@cli.command(name="filter")
@click.option("--input", required=True, help="输入文件路径")
@click.option("--out", default=None, help="输出 JSON 文件路径")
def filter_command(input, out):
    """按条件筛选数据。"""   # ← 此行会被 list-commands 提取为 description
    ...
```

**关键规则：**
- 命令组的 docstring 首行 ≤ 40 字，说清模块能力范围
- 子命令的 docstring 首行 ≤ 30 字，说清命令做什么
- 子命令命名用英文小写加连字符，如 `data-filter`
- 命令组之间保持独立，互不依赖
- main.py 只做路由注册 + 两个辅助命令，不写任何业务逻辑

#### 最简 Skill：单文件，无 commands/ 目录

并非所有 Skill 都需要 `commands/` + `authorization_env.py` 的完整结构。当 Skill 只有 1-2 个命令组、无需鉴权时，可以用最简形态——单文件即 Skill：

```python
# scripts/my_skill.py — 最简 Skill 示例
import sys
import io
import click

if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


@click.group()
def cli():
    """<Skill名称> — <一句话描述>。"""
    pass


@cli.command(name="list-groups")
def list_groups():
    """列出所有已注册的命令组及其描述（JSON 格式，供 AI 解析）。"""
    import json
    groups = []
    for cmd_name, cmd_obj in cli.commands.items():
        if cmd_name in ("list-groups", "list-commands"):
            continue
        desc = (cmd_obj.help or "").strip().split("\n")[0]
        groups.append({"name": cmd_name, "description": desc})
    print(json.dumps(groups, ensure_ascii=False, indent=2))


@cli.command(name="list-commands")
@click.argument("group_name")
def list_commands(group_name):
    """列出指定命令组下的所有子命令（JSON 格式，供 AI 解析）。"""
    import json
    group = cli.commands.get(group_name)
    if group is None:
        print(json.dumps({"error": "命令组 '" + group_name + "' 不存在"}, ensure_ascii=False))
        return
    commands = []
    for cmd_name, cmd_obj in group.commands.items():
        desc = (cmd_obj.help or "").strip().split("\n")[0]
        commands.append({"name": cmd_name, "description": desc})
    print(json.dumps(commands, ensure_ascii=False, indent=2))


@cli.command()
@click.argument("name", default="世界")
def hello(name):
    """打招呼。"""
    print("你好，" + name + "！")


if __name__ == "__main__":
    cli()
```

**适用条件**：
- 子命令 ≤ 5 个，单一命令组
- 无外部 API 调用，不需鉴权
- 打包只需 `pyi-makespec scripts/my_skill.py`，main.py 和 commands/ 目录都不需要

> 此模式即 `akdoc.py` 的做法——单文件 Click CLI，内嵌 `list-groups` / `list-commands`。适用于工具型 Skill。

#### 与 CLI.md 的关系

| 项目规模 | CLI.md | 说明 |
|---------|:------:|------|
| 小项目（≤3 组、≤15 子命令） | **不需要** | 命令直接列在 SKILL.md「## 可用命令」章节，减少上下文加载 |
| 中型项目（4-10 组） | **完整** | 四步流程 + 通用语法 + 全部命令 + 参数表 + 示例 |
| 大型项目（>10 组或 >50 子命令） | **完整** | 在中型项目格式基础上增加目录，仍需逐条完整展开 |

CLI.md 本质是"四步流程的预计算快照"——AI 走一遍四步流程得到的结果，用文档固化下来。它的作用是省去 AI 多次往返，而非提供代码无法提供的信息。详见 §十.1。

---

## 五、CLI 接口设计

Skill 的本质是"一件事一个子命令"，用户说的需求能直接映射到一条命令。设计 CLI 接口时遵循以下原则。

### 5.1 子命令粒度

一个子命令完成一个独立任务，用户说完一句话就能对应到一条命令：

| 用户说法 | 对应命令 |
|----------|----------|
| 「看看这个文件里有什么」 | `<skill> inspect <路径>` |
| 「把结果导出为 JSON」 | `<skill> export --format json <路径>` |
| 「按条件筛选数据」 | `<skill> filter --key <字段> --value <值>` |

什么时候拆成独立子命令：
- 底层调用的是**不同的 API 或不同的模型**
- 输入源不同（本地文件 vs URL vs Base64）
- 输出格式不同（纯文本 vs 文件 vs 结构化数据）

什么时候用选项而不是子命令：
- 同一个操作的不同参数（如 `--key` 指定筛选字段）
- 影响输出格式的参数（如 `--out` 指定输出路径、`--json` 控制输出格式）
- 分页、过滤等通用控制参数

### 5.2 命令命名

- 子命令名用英文小写单词，如 `list`、`add`、`export`、`filter`
- exe 文件名用英文小写加下划线，如 `data_tool`、`config_cli`
- 避免缩写，一个单词能说清的别用两个

### 5.3 参数设计

- 必填参数用 `@click.argument("参数名")`
- 可选参数用 `@click.option("--选项名")`
- 文件路径参数统一叫 `<路径>` 或 `--image <路径>`
- URL 参数统一叫 `<URL>` 或 `--url "<URL>"`
- 输出路径统一叫 `--out <路径>`
- 提问文本统一叫 `--question "问题"`
- 参数说明用中文，写清楚格式要求和取值范围

### 5.4 --help 信息完整性规范（必须）

`--help` 是 AI 掌握命令用法的唯一入口。**每一条 Click 命令及其参数的 help 信息必须足够详细，使 AI 无需外部文档即可正确构造命令**。

**命令 docstring 要求：**

- 首行说清命令做什么，末尾**附带一个完整的调用示例**
- 格式：`"""<命令说明>（例: <完整示例命令>）"""`

**必填参数（`@click.argument`）要求：**

- 必须设置 `metavar="<中文名>"`，用中文描述参数含义
- docstring 中的示例必须展示该参数的用法

**必填选项（`@click.option`）要求：**

- 必须设置 `metavar="<中文名>"`，用中文描述参数含义
- `help` 必须包含三要素：① 格式说明 ② 示例值 ③ `[required]`（Click 自动标注）

**示例——合格的写法：**

```python
@cli.command("convert")
@click.argument("input_file", metavar="<输入文件>")
@click.option("--format", required=True, metavar="<格式>",
              help="输出格式（值: json / csv / xml），如 json")
@click.option("--out", required=True, metavar="<输出路径>",
              help="输出文件路径，如 ./result.json")
@click.option("--pretty", is_flag=True,
              help="是否格式化输出（有则启用，无则紧凑）")
def cmd_convert(input_file, format, out, pretty):
    """文件格式转换（例: convert data.csv --format json --out result.json --pretty）"""
```

**产生的 --help 输出：**

```
Usage: main.py convert [OPTIONS] <输入文件>

  文件格式转换（例: convert data.csv --format json --out result.json --pretty）

Options:
  --format <格式>    输出格式（值: json / csv / xml），如 json  [required]
  --out <输出路径>   输出文件路径，如 ./result.json              [required]
  --pretty          是否格式化输出（有则启用，无则紧凑）
  --help            Show this message and exit.
```

AI 凭此输出即可判断：`<输入文件>` 和 `--format`、`--out` 必填，`--format` 值限制为 json/csv/xml，`--pretty` 是可选开关。无需查 CLI.md。

**检查清单：**

- [ ] 每个 `@click.argument` 有 `metavar="<中文名>"`
- [ ] 每个 `@click.option` 有 `metavar="<中文名>"` + 含示例值的 `help`
- [ ] 命令 docstring 末尾有完整示例
- [ ] `--help` 输出中所有必填项都有 `[required]` 标记

---

## 六、鉴权系统（按需）

> **定位**：鉴权系统不是 Skill 的必选项。纯计算型 / 本地工具型 Skill 完全不需要。只有当 Skill 需要调用外部 API、连接外部服务时才启用。

### 6.1 .env 基本架构

.env 文件固定在 `scripts/` 下。围绕它需要建立**两个模块**，职责严格分离：

| 模块 | 位置 | 职责 | 调用方 |
|------|------|------|--------|
| **读模块** | `commands/` 或独立文件 | 只读 .env，返回数据给调用方。暴露一组取值函数，每个函数返回特定字段 | 其他脚本 / 命令（内部调用） |
| **写模块** | `commands/` + Click 命令 | 维护 .env 内容，提供 CLI 增删改查命令 | 用户（终端直接操作） |

**读模块**是被调用方——其他函数需要获取配置时，import 它、调用对应的取值函数即可。读模块不涉及 Click、不做任何写操作。

**写模块**是用户操作入口——通过 Click 注册为 CLI 子命令，提供 list / current / add / remove 等命令让用户在终端管理 .env 内容。

### 6.2 .env 内容：无固定格式

.env 的内部结构**没有统一规范**——每个 Skill 根据自己的业务决定存什么字段、用什么命名、是单账号还是多账号。例如：

- 简单 API Key 场景：`API_KEY=sk-xxx`，几行即可
- 多服务场景：`SERVICE_A_KEY=...` / `SERVICE_B_KEY=...`，按服务分行
- 多账号场景：用数字后缀区分，如 `LOGIN_1=...` / `LOGIN_2=...`

因此，**读模块和写模块的实现代码随 .env 格式变化，本节不提供通用模板**。开发时根据实际业务临时设计。

### 6.3 技术约束

无论 .env 内容如何定制，以下规则必须遵守：

- **路径**：用 `getattr(sys, "frozen", False)` 判断打包/源码，`.env` 始终与 `main.py`、exe 同在 `scripts/` 下
- **解析**：逐行手动解析，`split("=", 1)` 防 Value 含等号截断，不依赖 `python-dotenv`
- **编码**：读写统一用 `utf-8`
- **安全**：读模块对外只暴露值，不暴露 .env 文件路径；写模块的 list 命令只显示键名或摘要，不输出敏感值
- **即时写入**：写模块的增删改操作立即写回 .env 文件

---

## 七、编码规范

### 7.1 函数和类的注释头

每个函数和类前**必须**加分隔注释说明其功能：

```python
#---------------------------
# 函数功能说明
#---------------------------
def do_something():
    ...
```

### 7.2 最小可运行版本优先

- 编写脚本或示例代码时，优先追求最小可运行版本
- 不要主动做复杂封装、命令行参数解析、环境变量兼容或工具化设计，除非明确要求

### 7.3 功能正确优先

- 功能正确是底线，优先保证功能和性能

### 7.4 变量命名

- 用完整单词，见名知意
- 不用缩写、拼音、单字母（循环中的 `i` 除外）
- 示例：`image_file_path` 而不是 `img` 或 `fp`

### 7.5 简洁胜于机巧

- 功能和性能差不多时，用最直白、最朴素的写法
- 不追"高级""优雅"，追一眼就懂

### 7.6 易读性优先

- 复杂逻辑拆成多步
- 用中间变量表明步骤意图
- 一行只做一件事

### 7.7 为目标读者编写

- 时刻想着代码是写给基础较弱的同事看的
- 如果某个写法可能让他们困惑，就换一种更直白的方式

### 7.8 风格一致

- 与项目现有风格、架构、分层、命名方式保持统一

### 7.9 禁止的语法

以下语法**推荐避免使用**（优先用显式 for 循环），以保持代码风格一致、降低阅读门槛：

- 列表推导式：`[x for x in items]`
- 字典推导式：`{k: v for k, v in items}`
- 生成器表达式：`(x for x in items)`
- lambda 表达式：`lambda x: x + 1`

**推荐写法：**

```python
# 不推荐的写法
active_items = [item for item in items if item["status"] == "active"]

# 推荐的写法
active_items = []
for item in items:
    if item["status"] == "active":
        active_items.append(item)
```

> **说明**：推导式语法简洁但可读性不如显式循环。此规范在 AKShare-CLI 项目中严格执行；其他 Skill 项目可选择遵守。

### 7.10 步骤注释

- 函数内部按"步骤1、步骤2……"依次标注每一步做什么
- 用 `# 步骤N：xxx` 的格式
- 主流程也按步骤标注
- 让不熟悉代码的人只看注释就能串起整段逻辑

### 7.11 不常见特性的注释

- 用到不常见的语言特性或库用法时，注释里一句话说清它的作用

### 7.12 依赖原则

- 尽量使用 Python 标准库
- 核心依赖：`click`；HTTP API 型 Skill 加 `requests`
- 第三方 API SDK 按需添加
- 不引入 ORM、异步框架、Web 框架等重型依赖
- 每个 Skill 项目独立，不共享代码

### 7.13 错误处理

所有可能失败的操作必须有明确的错误提示，不能让用户看到 Python 堆栈。

**HTTP 请求错误处理**见 §四 4.3 命令模板中的 try/except 写法，核心要点：
- 分别捕获 `Timeout`、`ConnectionError`、`RequestException`
- 检查 `response.status_code != 200` 并输出响应前 500 字符
- 每种错误给出中文提示和可能的解决方向

**参数校验：**

```python
# 步骤1：校验必填参数。
if not image_path:
    click.echo("错误：<参数名> 不能为空")
    return

# 步骤2：校验文件是否存在。
if not os.path.exists(image_path):
    click.echo("错误：文件不存在 — " + image_path)
    return
```

**错误提示原则：**
- 说清楚什么出了错、可能的原因、用户可以怎么解决
- 错误信息用中文，不用英文
- 不要直接输出 Python 异常信息
- 不要在错误信息里暴露内部路径

---

## 八、打包发布

> **执行门槛**：本章只提供打包阶段的实现参考，不代表创建或更新 CLI 时默认执行。工程没有 `.spec`、历史 exe、打包脚本或其他打包迹象时，必须等待用户明确要求首次打包；工程已经进入打包维护阶段时，每次代码或依赖变化后必须重新打包并验证。首次打包通常应等待主要功能和 CLI 基本完成。

### 8.1 PyInstaller spec 模板

```python
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['scripts/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='<skill_name>',        # ← 改这里：exe 文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**关键配置：**
- `name='<skill_name>'`：输出的 exe 文件名，与 CLI.md 中的命令名一致
- `console=True`：启用控制台窗口，用户可在终端中看到命令输出（CLI 工具必须设为 True，否则无任何可见输出）
- `upx=True`：启用 UPX 压缩，减小 exe 体积
- **单文件模式**：EXE 直接包含 `a.binaries` 和 `a.datas`，不使用 COLLECT（不产生 `_internal/` 依赖目录），所有依赖封进单个 exe

### 8.2 打包命令

```bash
# 安装 PyInstaller
pip install pyinstaller

# 生成 spec 文件（首次，spec 不提交 Git）
pyi-makespec scripts/main.py

# 打包：单文件模式，exe 直接输出到 scripts/
pyinstaller --distpath scripts main.spec

# 打包完成后清理构建产物，保持项目干净
# Windows: rd /s /q build & rd /s /q dist & del main.spec
# Linux/Mac: rm -rf build dist main.spec
```

**打包流程说明：**
- `--distpath scripts`：exe 直接生成在 `scripts/` 下，与源码 `main.py` 同级
- 单文件模式（无 COLLECT）：所有依赖封进 exe，不产生 `_internal/` 目录
- 清理 `build/`（PyInstaller 临时文件）、`dist/`（默认输出目录，已通过 `--distpath` 重定向）、`main.spec`（构建配置，不提交 Git）
- 最终只保留 `scripts/<skill_name>.exe`

### 8.3 .gitignore

```
.env
__pycache__/
*.pyc
build/
dist/
*.spec
runtime/
```

### 8.4 版本号规范

采用语义化版本 `主版本.次版本.修订号`，如 `v1.2.3`：

| 版本位 | 变化条件 | 示例 |
|--------|---------|------|
| 主版本 | 新增子命令或破坏性变更（旧命令行为改变） | `v1.0.0` → `v2.0.0` |
| 次版本 | 新增可选参数、性能优化、SOP 手册新增 | `v1.0.0` → `v1.1.0` |
| 修订号 | Bug 修复、文档修正、错误提示优化 | `v1.0.0` → `v1.0.1` |

### 8.5 发布清单

每个 Skill 包发布时，确认以下文件齐全：

```
📦 skill-<名称>/
├── 📋 SKILL.md               ← 路由层：用户意图 → references/ 中的 SOP 手册
├── scripts/
│   ├── 🔑 .env               ← 鉴权文件：用户自建，填入自己的 API Key。与 exe 同级
│   └── 🏺 <skill_name>.exe    ← 法器（执行层）：暴露 CLI 命令，实际干活
├── 📂 references/            ← 参考层 + 操作层
│   ├── 📋 CLI.md              ← CLI 命令参考（按需，小项目可省略。详见 §十.1）
│   ├── 📄 需求A.md            ← SOP 手册（一个需求一个操作步骤）
│   └── ...
├── 📂 assets/                ← 静态资源（按需）
└── 📂 runtime/               ← 运行时工作区（AI 按需创建，不计入版本控制）
    ├── inputs/                ← 输入文件暂存
    ├── outputs/               ← 输出文件
    └── tmp/                   ← 临时脚本和缓存
```

发布包命名：`skill-<名称>-v<版本>.zip`。

**注意**：`.env` 由用户自建，不随发布包分发。`runtime/` 由 AI 在运行时按需创建——脚本或 AI 需要读写临时文件时，先检查对应子目录是否存在，不存在则 `mkdir -p` 创建后再使用。所有脚本、代码的临时文件、输入暂存、输出结果统一走 `runtime/` 下的对应子目录。

---

## 九、验证清单

### 9.1 质量检查清单

发布前逐项检查：

```
□ exe 能在干净的 Windows 设备上运行（无 Python 环境）
□ .env 读取正常（含打包后路径和源码路径）
□ 每个子命令都能通过 CLI 调用
□ 中文输出无乱码（GBK 编码已处理）
□ 命令文档齐全：CLI.md 或 SKILL.md 中的命令章节（按 §十.1 判断）
□ 四步自发现正常：list-groups / list-commands 输出 JSON 正确，--help 完整
□ SKILL.md 覆盖了常见的用户说法，含 name 和 description frontmatter
□ references/ 至少 3 个 SOP 手册
□ 所有命令示例可复制粘贴直接运行
□ 错误提示友好（API Key 未配、API 挂了、参数错误等）
□ .gitignore 正确（.env / build / dist / __pycache__ / runtime）
```

### 9.2 测试方法

**源码环境下测试：**

```bash
# 在 scripts/ 下创建 .env 并填入测试用 API Key

# 直接运行 Python 脚本测试每个子命令
python scripts/main.py <子命令> <参数>

# 测试错误场景：故意不配 Key，确认提示友好
python scripts/main.py key-get NONEXISTENT_KEY

# 测试文件不存在场景
python scripts/main.py filter --input not_exist.dat
```

**打包后测试（模拟发布包结构）：**

```bash
# 搭建与发布包一致的目录结构
mkdir test_env\scripts
copy dist\<skill_name>.exe test_env\scripts\
cd test_env

# 在 scripts/ 下创建 .env（与 main.py 同级）
echo SERVICE_X_API_KEY=sk-test > scripts/.env

# 运行 exe 测试每个子命令
scripts\<skill_name>.exe <子命令> <参数>

# 验证中文输出无乱码
scripts\<skill_name>.exe <子命令> --question "测试中文"
```

**测试检查点：**
- 正常输入 → 预期输出正确
- 缺少必填参数 → 报错但不崩溃
- API Key 未配置 → 提示"请检查 .env"
- API Key 错误 → 提示"接口返回错误"并显示状态码
- 网络不通 → 提示"网络连接失败"
- 文件不存在 → 提示"文件不存在"
- 打包后 exe 输出中文无乱码

---

## 十、文档编写标准

### 10.1 咒语表（CLI 命令参考）— 固定完整格式

**定位**：告诉 AI 和开发者「有哪些命令、完整语法是什么、每个参数怎么填」。文件名为 `CLI.md`，放在 `references/` 目录下。CLI.md 只写命令事实，不写场景选择逻辑。

**事实来源**：必须以当前可执行程序的真实输出为准。先实际运行 `list-groups`、`list-commands` 和每条命令的 `--help`，再整理文档。禁止根据源码印象、旧版本文档或猜测补全命令和参数。

#### 是否需要 CLI.md？

| 项目规模 | 做法 | 原因 |
|---------|------|------|
| **小项目**（≤3 个命令组，≤15 个子命令） | 可不写 CLI.md，将命令并入 SKILL.md 的「## 可用命令」章节 | 减少上下文加载量 |
| **中型项目**（4-10 个命令组） | 创建完整 CLI.md，逐条展开全部命令 | 避免 AI 反复查询参数 |
| **大型项目**（>10 个命令组或 >50 个子命令） | 创建完整 CLI.md，并在开头增加目录 | 便于快速定位命令组 |

> 一旦创建 CLI.md，就不允许只写命令骨架或省略参数表。所有命令都必须按下方固定格式逐条展开。

#### 文档结构

CLI.md 按以下顺序编写：

1. `# <工具名> CLI 命令清单`
2. 版本和生成依据：说明工具版本、实际执行的帮助命令、命令数和参数数；版本更新后以当前环境真实输出为准
3. `## AI 自发现流程（四步掌握全部命令）`
4. `## 通用语法`
5. 按业务能力划分的二级标题，如 `## 文件与文件夹`
6. 每条命令使用三级标题，如 `### create`

大型项目在版本说明后增加目录，目录按命令组或业务分类组织，不逐条罗列参数。

#### AI 自发现流程

```text
Step 1：运行 exe list-groups，获取全部命令组。
Step 2：运行 exe list-commands <group>，获取命令组内的全部子命令。
Step 3：运行 exe <group> <command> --help，获取完整语法、参数、默认值和可选值。
Step 4：根据帮助信息构造并实际执行命令，确认示例可运行。
```

#### 通用语法模板

```markdown
## 通用语法

| 写法 | 说明 | 示例 |
|---|---|---|
| `<exe> <group> <command> [options]` | 基本命令格式 | `<exe> data filter --input source.csv` |
| `<name>=<value>` | 有值参数；值含空格时加双引号 | `query="search term"` |
| `<flag>` | 无值布尔标志，写出即启用 | `verbose` |
| `--<option> <value>` | Click 风格选项 | `--format json` |
```

只保留当前工具真实支持的参数写法。工具不支持 `name=value` 或无值标志时，不要为了套模板而写入。

#### 单条命令固定模板

每条命令必须包含用途、完整语法、参数和示例四部分，命令之间用 `---` 分隔：

```markdown
### `filter`

**用途：** 按指定条件筛选数据。

**完整语法：**

\```powershell
<exe> data filter --input <path> [--format json|csv] [--out <path>]
\```

**参数：**

| 参数 | 说明 | 必填 | 默认值 / 可选值 |
|---|---|---|---|
| `--input <path>` | 输入文件路径 | 是 | — |
| `--format json\|csv` | 输出格式 | 否 | 默认：`json`<br>可选：`json`、`csv` |
| `--out <path>` | 输出文件路径 | 否 | 默认输出到控制台 |

**示例：**

\```powershell
<exe> data filter --input source.csv --format json --out result.json
\```

---
```

没有参数的命令写 `**参数：** 无。`，不得创建空参数表。一个命令至少提供一个已实际验证的最小示例。

#### 参数编写规则

- 参数名称和顺序必须与真实 `--help` 输出一致
- 必填参数写「是」，可选参数写「否」，不使用图标代替文字
- 没有默认值时写 `—`，不要写空单元格
- 同时存在默认值和可选值时，使用 `默认：...<br>可选：...` 分两行展示
- 多个可选值在完整语法中用 `|` 连接，在 Markdown 表格中转义为 `\|`
- 路径、文本、数字等占位值用尖括号表示，如 `<path>`、`<text>`、`<n>`
- 可选参数在完整语法中用方括号包裹；必填参数不加方括号
- 参数值含空格时，示例必须使用双引号
- 命令示例使用 `powershell` 代码块，并保证可直接复制执行

#### 校验要求

1. 实际运行工具的总帮助命令，记录全部命令和版本
2. 逐条运行命令帮助，核对用途、完整语法、参数、默认值和可选值
3. 逐条运行最小示例；涉及删除、覆盖、发布等副作用时，使用隔离测试数据
4. 统计 CLI.md 中的命令数和参数数，与真实帮助输出核对
5. 搜索 `TODO`、`待补充`、`...` 等占位内容，发布前必须清零

#### 小项目 SKILL.md 嵌入规则

小项目不创建 CLI.md 时，可在 SKILL.md 的「## 可用命令」中保留四步自发现流程、命令组一览和最常用命令。完整参数仍以实际 `--help` 输出为准。只要创建了 CLI.md，就必须使用本节的固定完整格式。

### 10.2 SKILL.md（需求路由表）

**定位**：告诉 AI「用户说这种话时，应该查找哪个 SOP 手册」。连接用户自然语言和 `references/` 中 SOP 手册的桥梁。放在项目根目录。

**模板：**

```markdown
---
name: <skill-name>
description: <一句话描述，含触发场景。中英文均可，根据目标 AI 平台选择。英文示例：When the user wants to query, filter, or transform structured data — including CSV files, JSON datasets, and database exports. Use for data cleaning, format conversion, and batch processing. 中文示例：当用户想查询、筛选或转换结构化数据时——包括 CSV 文件、JSON 数据集和数据库导出。用于数据清洗、格式转换和批量处理。>
---

# <Skill名称> Skill — 需求路由表

## 场景路由

### 路由 1：<场景名称>
**用户说法**：「<用户会怎么说 1>」「<用户会怎么说 2>」
**路由到**：`references/<SOP手册名>.md`
**选择命令**：`<命令>`
**决策逻辑**：<为什么选这个命令而不是别的>

### 路由 2：<场景名称>
**用户说法**：「<用户会怎么说 1>」「<用户会怎么说 2>」
**路由到**：`references/<SOP手册名>.md`
**选择命令**：`<命令>`
**决策逻辑**：<为什么选这个命令>

## 注意事项
- <使用注意 1>
- <使用注意 2>
```

**编写要点：**
- 触发条件只写在 frontmatter 的 `description` 中，正文不要再写“激活条件”“何时使用”或同义章节
- 每个路由对应一种用户意图，并通过"路由到"字段指向具体的 SOP 手册
- "用户说法"要写口语化、有代表性的句子，至少 2-3 句
- "决策逻辑"解决"为什么选 A 不选 B"——这是 AI 匹配的关键
- 路由之间不要重叠（同一句话不应命中两个路由）
- 注意事项写在最后
- 如果涉及多个 skill 协同，注明需要哪些其他 skill
- **小项目可省略 CLI.md**：在「注意事项」之前加入「## 可用命令」章节，嵌入命令速查表（模板见 §十.1「小项目 SKILL.md 嵌入写法」）

### 10.3 SOP 手册（场景化操作文档）

**定位**：一个 md 文件 = 一个具体需求。AI 读完就能手把手引导用户完成。放在 `references/` 目录下。

**模板：**

```markdown
# SOP：<需求名称>

## 需求
<一句话描述用户想要什么>

## 适用场景
- <场景 1>
- <场景 2>

## 前置条件
- <需要准备什么>
- 开发环境需 Python 3，生产环境用 `scripts/<skill_name>.exe` 免 Python 运行

## 操作步骤

### Step 1：<步骤名称>
<做什么>

    # 开发环境
    python scripts/main.py <子命令> <参数>

    # 生产环境
    scripts\<skill_name>.exe <子命令> <参数>

<预期输出描述>

### Step 2：<步骤名称>
<做什么>

    # 开发环境
    python scripts/main.py <子命令> <参数>

    # 生产环境
    scripts\<skill_name>.exe <子命令> <参数>

<预期输出描述>

## 预期结果
<最终得到什么>

## 已知限制
- <限制 1>
- <限制 2>

## 相关 SOP
- [[<另一个 SOP 名称>]] — <什么情况用它>
```

**编写要点：**
- 每个 SOP 独立、自包含——读一篇就能完成一个需求
- 步骤要具体到命令可以复制粘贴
- 预期输出要写清楚大致的返回内容
- 已知限制要提前说，减少用户困惑
- 相关 SOP 用 `[[文件名]]` 双向链接，形成知识网络
- 文件命名：`动词+名词.md`，如 `筛选数据记录.md`
- 每个 skill 至少覆盖 3-5 个最常见的需求

### 10.4 SKILL.md 触发机制

AI 通过 SKILL.md 的 `description` frontmatter 决定是否激活技能，这是**唯一的触发判断依据**。理解触发机制是写好 description 的前提。

**三级加载：**

| 级别 | 内容 | 何时加载 | 大小限制 |
|------|------|---------|---------|
| 元数据 | `name` + `description` | 始终在上下文中 | ~100 词 |
| SKILL.md 正文 | 完整指令 | 技能触发时加载 | <500 行 |
| 捆绑资源 | `references/`、`assets/` | 按需加载 | 无限制 |

**触发逻辑：** AI 根据 description 判断当前用户任务是否需要该技能。简单查询（如"读取文件 X"）可能不触发，复杂多步骤任务可靠触发。

### 10.5 description 编写要点

description 是技能触发率的决定性因素，必须同时完成两件事：

1. **说明技能能做什么**——核心能力
2. **列出触发场景**——什么时候该用，即使用户没明确说

**好的 description 示例（英文）：**

```
When the user wants to query, filter, or transform structured data —
including CSV files, JSON datasets, database exports, and API responses.
Use for data cleaning, format conversion, aggregation, and batch processing.
```

**好的 description 示例（中文）：**

```
当用户想查询、筛选或转换结构化数据时——包括 CSV 文件、JSON 数据集、数据库导出和 API 响应。
用于数据清洗、格式转换、聚合统计和批量处理。覆盖跨数据源工作流：
先导入再清洗、清洗后导出、多源合并分析。
```

**不好的 description：**

```
Data processing skill.
数据处理技能。
```

**编写原则：**
- 包含具体名词（照片、截图、扫描件 / photos, screenshots, scans）而非抽象概念
- 列出边缘场景（多图对比、视频帧 / multi-image comparisons, video frames）扩大覆盖
- 用"即使用户没明确说"的心态来写——宁可多触发，别漏触发
- 避免与其它技能的关键词重叠导致竞争
- description 中英文均可，根据目标 AI 平台选择。英文 description 对国际主流 AI 平台触发更稳定；中文 description 对国内平台（如通义千问、文心一言等）触发更自然。正文用中文，与 description 语言无关

---

## 十一、多 Skill 协同

用户的一个需求可能涉及多个 Skill 协同工作（如「筛选数据后导出报表」涉及数据处理 + 报表生成）。为支持协同，各 Skill 遵循以下约定。

### 11.1 输入输出约定

- 每个 Skill 的默认输出目录统一命名为 `runtime/outputs/`
- 输出文件路径由 `--out` 参数显式指定，方便上游 Skill 的输出直接作为下游 Skill 的输入
- 文本输出直接打印到控制台，结构化数据输出 JSON

### 11.2 跨 Skill 工作流

```
Skill A 输出文件 → Skill B 读取文件 → Skill C 处理并输出
```

示例：筛选数据 → 导出报表：

```bash
# Step 1：从源数据中筛选目标记录
data_tool filter --input source.csv --key "status" --value "active" --out runtime/outputs/active.json

# Step 2：AI 汇总分析（由 AI 助手直接完成，不需要 exe）

# Step 3：生成格式化报表
report_tool generate --data runtime/outputs/active.json --template monthly --out runtime/outputs/report.pdf
```

### 11.3 SKILL.md 中的协同标注

如果一个路由涉及多 Skill，在 SKILL.md 的路由中注明：

```markdown
### 路由 7：筛选后生成报表
**用户说法**：「把活跃用户的数据导出成月度报表」
**路由到**：`references/筛选数据.md`
**选择命令**：`filter` + AI 汇总 + `report generate`
**决策逻辑**：需要数据处理筛选 → AI 汇总 → 报表生成，是三个 Skill 的组合任务。
**需要的其他 Skill**：报表生成
```

### 11.4 环境隔离

- 每个 Skill 的 `.env` 独立，各自声明自己需要的 API Key
- 如果两个 Skill 调用同一个 API，它们共享同一个 Key 名和值
- `references/` 中的跨 Skill 案例注明每个步骤需要哪个 Skill 包
- `runtime/` 由 AI 按需创建和管理，各 Skill 的输入输出通过 `--out` 参数显式衔接，不隐式共享

---

## 十二、常见陷阱

### 12.1 PyInstaller 打包后 .env 找不到

**问题**：打包后 `__file__` 指向 PyInstaller 的临时解压目录，而非 exe 所在目录。

**解决**：用 `getattr(sys, "frozen", False)` 判断运行模式。打包后 `.env` 与 exe 同级都在 `scripts/`，源码时 `__file__` 在 `commands/` 下往上两级到 `scripts/`。

```python
#---------------------------
# 函数说明：获取应用程序所在目录，兼容 PyInstaller 打包路径。
#---------------------------
def get_application_dir():
    if getattr(sys, "frozen", False):
        # 打包后 .env 与 exe 同级，都在 scripts/ 下。
        return os.path.dirname(sys.executable)
    else:
        # 未打包时 __file__ 在 commands/ 下，往上两级到 scripts/。
        return os.path.dirname(os.path.dirname(__file__))
```

### 12.2 Windows 控制台中文乱码

**问题**：PyInstaller 打包后，控制台默认使用 GBK 编码，中文输出变乱码。

**解决**：在 `main.py` 最开头（所有 import 之前）强制 stdout 使用 UTF-8：

```python
import sys
import io

if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

### 12.3 .env 中 Key 值含等号被截断

**问题**：API Key 可能含有 `=` 号（如 Base64 编码的 Token），`split("=")` 会错误截断。

**解决**：用 `split("=", 1)` 只拆分第一个等号：

```python
line_parts = line_text.split("=", 1)
if len(line_parts) < 2:
    continue
env_key = line_parts[0].strip()
env_value = line_parts[1].strip()
```

### 12.4 硬编码路径

**问题**：写死绝对路径（如 `C:\Users\xxx`）或假设当前工作目录的相对路径，换设备就报错。

**解决**：所有路径基于 `get_application_dir()` 动态拼接，不依赖工作目录。

### 12.5 PyInstaller 漏打依赖

**问题**：某些第三方库（如 `dashscope`、`oss2`）不会被 PyInstaller 自动检测到，打包后运行报 `ModuleNotFoundError`。

**解决**：在 `.spec` 文件的 `hiddenimports` 列表中显式声明：

```python
a = Analysis(
    ['scripts/main.py'],
    hiddenimports=['dashscope', 'oss2', 'your_missing_module'],
    ...
)
```

---

> 最后更新：2026-06-24
