# 稳定性测试每日数据自动补齐

每天北京时间 08:00 自动在飞书表格「稳定性测试每日跟踪表」中追加当天18个测试项数据。

## 部署步骤

### 1. 创建 GitHub 仓库
在 GitHub 上创建一个新仓库（public 或 private 均可）。

### 2. 上传文件
将本目录下的所有文件上传到仓库：
```
.
├── .github/workflows/daily-append.yml   # GitHub Actions 定时任务
├── auto_fill.py                          # 自动补齐脚本
└── README.md                             # 说明文档
```

### 3. 配置 Secrets
进入仓库 `Settings → Secrets and variables → Actions → New repository secret`，添加两个 Secret：

| Name | Value |
|------|-------|
| `FEISHU_APP_ID` | `cli_aa88250db7fa9cd9` |
| `FEISHU_APP_SECRET` | （飞书应用 App Secret，见下方获取方式） |

#### 获取 App Secret
1. 打开 [飞书开放平台](https://open.feishu.cn/app) 
2. 找到 lark-cli 创建的应用（App ID: cli_aa88250db7fa9cd9）
3. 在「凭证与基础信息」页面查看 App Secret

### 4. 确认飞书应用权限
确保该飞书应用已开通以下权限（在开放平台应用管理中检查）：
- `sheets:spreadsheet` — 读写表格
- `sheets:spreadsheet:readonly` — 读取表格（备用）

同时确保该应用已被添加为飞书表格的协作者（有编辑权限）。

### 5. 验证
- 手动触发：进入仓库 `Actions` 页面 → 选择「稳定性测试每日数据补齐」→ 点击 `Run workflow`
- 查看日志确认执行成功
- 之后每天北京时间 08:00 自动执行

## 工作原理

1. GitHub Actions 每天 UTC 00:00（北京时间 08:00）触发
2. 脚本通过飞书 API 获取 `tenant_access_token`（应用身份，不依赖用户授权）
3. 读取飞书表格已有日期列表
4. 从 2026/7/14 到今天，找出所有缺失的日期
5. 逐个追加每个缺失日期的18行测试项 + 设置底色
6. 已有数据的日期自动跳过，不会重复

## 手动测试

部署完成后，可在 Actions 页面手动触发一次验证。也可以在本地运行：
```bash
export FEISHU_APP_ID="cli_aa88250db7fa9cd9"
export FEISHU_APP_SECRET="你的App Secret"
python3 auto_fill.py
```
