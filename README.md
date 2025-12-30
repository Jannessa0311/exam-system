# 在线考试系统

基于 Streamlit 的在线考试系统，支持多主题考试。

## 🚀 快速开始

### 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run app.py
```

### 部署到 Streamlit Cloud

1. 将代码推送到 GitHub
2. 在 [share.streamlit.io](https://share.streamlit.io) 部署
3. 配置 Secrets（Google Sheets 认证信息）

详细步骤请参考 `DEPLOY.md`

## 📁 项目结构

```
SOP_test/
├── app.py              # 主应用
├── result_manager.py   # 结果管理
├── github_utils.py     # GitHub 工具
├── config.json         # 配置文件
├── requirements.txt    # 依赖
└── .streamlit/
    ├── secrets.toml    # 敏感信息（不提交到 Git）
    └── config.toml     # Streamlit 配置
```

## 🌳 多分支管理

每个考试主题使用一个独立的 Git 分支：

- `main` - 主分支
- `rma-test` - RMA 考试
- `training-002` - 其他考试

每个分支可以有不同的配置和题库文件。

