# 部署到 GitHub 和 Streamlit Cloud

## 📋 部署步骤

### 步骤 1：创建 GitHub 仓库

1. **访问 GitHub**
   - 登录 [github.com](https://github.com)
   - 点击右上角 "+" > "New repository"

2. **创建新仓库**
   - Repository name: `exam-system`（或你喜欢的名称）
   - Description: `Online Exam System`
   - 选择 **Public**（Streamlit Cloud 免费版需要公开仓库）
   - 不要勾选 "Initialize with README"
   - 点击 "Create repository"

### 步骤 2：初始化 Git 并推送代码

在项目目录中运行：

```bash
# 初始化 Git
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: RMA Test exam system"

# 添加远程仓库（替换 YOUR_USERNAME 和 YOUR_REPO_NAME）
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 推送到 main 分支
git branch -M main
git push -u origin main
```

### 步骤 3：部署到 Streamlit Cloud

1. **访问 Streamlit Cloud**
   - 访问 [share.streamlit.io](https://share.streamlit.io)
   - 使用 GitHub 账号登录

2. **创建新应用**
   - 点击 "New app"
   - 选择你的仓库
   - Branch: `main`
   - Main file path: `app.py`
   - App URL: 可以自定义（例如：`rma-test`）
   - 点击 "Deploy"

3. **配置 Secrets（重要）**
   - 在应用页面，点击 "Settings" > "Secrets"
   - 将 `.streamlit/secrets.toml` 的内容粘贴进去
   - 点击 "Save"

### 步骤 4：为每个考试主题创建分支

#### 创建新分支（例如：RMA Test）

```bash
# 创建并切换到新分支
git checkout -b rma-test

# 修改 config.json（如果需要不同的配置）
# 然后提交
git add config.json
git commit -m "Add RMA Test configuration"

# 推送到 GitHub
git push -u origin rma-test
```

#### 在 Streamlit Cloud 中部署新分支

1. 在 Streamlit Cloud 中，点击 "Settings"
2. 在 "General" 中，可以创建新的应用实例
3. 或者修改现有应用的 Branch 设置

## 🌳 多分支管理策略

### 推荐结构

```
main (主分支)
├── 通用代码和配置
└── 默认 training

rma-test (RMA 考试分支)
├── 继承 main 的代码
└── 自己的 config.json

training-002 (其他考试分支)
├── 继承 main 的代码
└── 自己的 config.json
```

### 为每个分支创建独立的 Streamlit 应用

1. **在 Streamlit Cloud 创建多个应用**
   - 每个应用对应一个分支
   - 每个应用有不同的 URL

2. **示例：**
   - `rma-test.streamlit.app` → `rma-test` 分支
   - `training-002.streamlit.app` → `training-002` 分支

## 📝 配置文件管理

### 方法一：每个分支有独立的 config.json（推荐）

每个分支维护自己的 `config.json`：

```bash
# 在 rma-test 分支
git checkout rma-test
# 编辑 config.json
git add config.json
git commit -m "Update RMA test config"
git push
```

### 方法二：使用环境变量（高级）

可以在 Streamlit Cloud 的 Secrets 中配置不同的 training。

## 🔒 重要文件保护

确保以下文件不会被提交到 GitHub：

- `.streamlit/secrets.toml` - 包含敏感信息
- `config.json` - 如果包含敏感信息（可选）

已经在 `.gitignore` 中配置了。

## 🚀 快速部署命令

```bash
# 1. 初始化（只需一次）
git init
git add .
git commit -m "Initial commit"

# 2. 添加远程仓库
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 3. 推送主分支
git push -u origin main

# 4. 创建新分支（例如：rma-test）
git checkout -b rma-test
git push -u origin rma-test
```

## 📊 多考试管理流程

### 添加新考试

1. **创建新分支**
   ```bash
   git checkout main
   git checkout -b new-training-name
   ```

2. **更新配置**
   - 编辑 `config.json`
   - 添加新的 training 配置

3. **提交并推送**
   ```bash
   git add config.json
   git commit -m "Add new training: training-name"
   git push -u origin new-training-name
   ```

4. **在 Streamlit Cloud 部署**
   - 创建新应用
   - 选择对应的分支

## ⚠️ 注意事项

1. **Secrets 配置**
   - 每个 Streamlit Cloud 应用都需要单独配置 Secrets
   - 使用相同的 Google Sheets 配置

2. **题库文件**
   - 每个分支可以有不同的题库文件
   - 或者所有分支共享相同的题库文件

3. **结果文件**
   - 每个 training 的结果保存在独立的 Excel 文件
   - Google Sheets 中每个 training 使用不同的 Sheet

## 🎯 最佳实践

1. **主分支（main）**
   - 保持代码的通用版本
   - 包含所有功能的更新

2. **考试分支**
   - 从 main 分支创建
   - 只修改配置，不修改代码
   - 定期从 main 合并更新

3. **命名规范**
   - 分支名：小写，用连字符（例如：`rma-test`）
   - Training ID：保持一致（例如：`training_001`）

