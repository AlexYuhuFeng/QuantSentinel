# QuantSentinel

> **QuantSentinel** 是一个准产品化、面向小团队协作的专业级 Trading Terminal。
> 目标是提供“可部署、可协作、可审计、可扩展、支持多语言”的一体化量化研究与策略执行工作台。

---

## 1. 产品定位

QuantSentinel 面向以下用户角色：

- **研究员（Researcher）**：进行行情探索、因子验证、策略实验与回测。
- **策略工程师（Strategy Engineer）**：开发、评估与优化多策略组合。
- **风控与运维（Risk/Ops）**：监控规则告警、任务运行、系统健康与审计日志。
- **管理员（Admin）**：管理用户、权限、语言、布局模板与系统配置。

核心目标：

1. **可部署**：Docker Compose 一键启动核心服务。
2. **可协作**：多用户、RBAC、任务可追踪、布局可保存。
3. **可审计**：关键操作全量写入 `audit_log`。
4. **可扩展**：插件化策略、参数搜索、任务编排。
5. **多语言**：基于 gettext + Babel，支持 `en` 与 `zh_CN`。

---

## 2. 技术架构（目标标准）

### 2.1 服务拓扑（Docker Compose）

- **web**: Streamlit（交易终端 UI）
- **db**: PostgreSQL（主库）
- **redis**: Redis（Celery broker / cache）
- **worker**: Celery Worker（异步任务执行）
- **beat**: Celery Beat（调度）
- **api（可选）**: FastAPI（健康检查 / 状态 API）

### 2.2 核心技术栈

- Python **3.12+**
- SQLAlchemy **2.0**
- Alembic（数据库迁移）
- Celery + Redis（任务系统）
- Plotly（图形可视化）
- pydantic **v2**
- pytest + coverage（测试与覆盖率）
- ruff（代码质量）
- Babel + gettext（i18n）
- argon2（密码哈希）

### 2.3 质量门禁

- 测试覆盖率硬门禁：
  - `domain + services` **line coverage >= 90%**

---

## 3. 终端 UI/UX 规范（Trading Terminal 风格）

### 3.1 Sidebar

- 仅用于导航（最多 6 项）
- 显示极简系统状态：`DB / Queue / Health`
- 禁止复杂表单

### 3.2 Header Bar

- 左：`QuantSentinel`
- 中：`Global Context (Ticker | Date | Workspace)`
- 右：`Notifications | Language Switch | User Menu`

### 3.3 页面统一结构

每个页面必须包含：

1. Top Toolbar（单行）
2. 主内容区
3. 右侧详情抽屉（不跳页面）

统一状态组件：`loading / empty / error / success`

错误态必须提供可操作入口：

- `Retry`
- `View Logs`

---

## 4. 多语言 i18n（gettext + Babel）

### 4.1 必须支持

- `en`
- `zh_CN`

### 4.2 规范

- 所有 UI 文案必须走 i18n
- 导出报告/快照必须跟随当前语言
- 用户 profile 存储 `default_language`
- 支持右上角即时切换语言
- 提供 `locales/` 与 `.po/.mo` 文件

### 4.3 新增语言流程

1. 在 `locales/` 下新增语言目录（如 `ja/LC_MESSAGES/messages.po`）
2. 使用 Babel 提取/更新消息目录
3. 翻译 `.po` 文案并编译 `.mo`
4. 在语言选择器中注册新语言代码
5. 补充 i18n 切换测试与关键页面快照测试

---

## 5. 用户体系、RBAC 与审计

### 5.1 users 表字段

- `id`
- `username`
- `email`
- `password_hash`（argon2）
- `role`（Admin / Editor / Viewer）
- `default_language`
- `created_at`
- `last_login`

### 5.2 权限矩阵

- **Admin**：全部权限
- **Editor**：数据导入、规则 CRUD、研究与策略
- **Viewer**：只读

### 5.3 audit_log 表字段

- `id`
- `actor_id`
- `action`
- `entity_type`
- `entity_id`
- `payload_json`
- `ts`

### 5.4 审计强制范围

以下操作必须写 `audit_log`：

- `create`
- `update`
- `delete`
- `run`
- `ack`
- `export`

并且 UI 必须按角色隐藏不可执行按钮。

---

## 6. 数据体系（版本化）

### 6.1 主库

- PostgreSQL

### 6.2 核心表

- `instruments`
- `prices_daily`（含 `revision_id`）
- `derived_daily`（含 `recipe_id` + `revision_id`）
- `recipes`
- `alert_rules`
- `alert_events`
- `strategy_projects`
- `strategy_runs`
- `refresh_log`
- `tasks`
- `ui_layout_presets`
- `audit_log`
- `users`

### 6.3 数据版本约束

- 每次 ingestion 生成 `revision_id (UUID)`
- 每次 run 必须记录：
  - `data_revision_id`
  - `code_hash`

---

## 7. 工作台能力

### 7.1 导航（<= 6 项）

1. Market
2. Explore
3. Monitor
4. Research Lab
5. Strategy Lab
6. Admin/Help

### 7.2 Market

- Watchlist 表
- Anomalies 自动扫描（波动/相关性/滞后）
- 右侧抽屉 mini panel

### 7.3 Explore

- 多面板：`Price`、`Returns/Vol`、`Zscore`
- KPI 卡片
- Snapshot 导出（HTML + JSON，含 `data_revision_id + code_hash`）

### 7.4 Monitor

三域：

- Market Signals
- Data Quality
- System Health

7 类规则：

- threshold
- z_score
- volatility
- staleness
- missing_data
- correlation_break
- custom_expression（AST 白名单）

告警治理：

- 去重
- 抑制（silence）
- 聚合

规则创建必须通过 Wizard。

### 7.5 Research Lab

- Project 概念
- Runs 对比
- Walk-forward（>= 2 folds）

指标必须包含：

- return
- sharpe
- sortino
- max_drawdown
- turnover
- hit_rate
- exposure_time
- cost_impact

并强制考虑：

- 交易成本
- 滑点
- 风控（stop-loss / take-profit / max DD stop）

### 7.6 Strategy Lab

- 策略插件系统
- 至少 8 策略族：
  1. MA crossover
  2. Donchian breakout
  3. RSI mean-revert
  4. Zscore mean-revert
  5. Vol breakout
  6. Pairs mean-revert
  7. Seasonal bias
  8. Carry proxy

参数搜索：

- Grid
- Random
- Bayesian
- Early stopping
- Celery 并行

Leaderboard：

- risk-adjusted score
- 稳健性罚分

---

## 8. 后台任务系统（Celery）

必须提供以下任务：

- `refresh_watchlist`
- `refresh_ticker`
- `recompute_derived`
- `run_rules_batch`
- `run_backtest`
- `run_param_search`
- `export_snapshot`

`tasks` 表需可追踪：

- `status`
- `progress`
- `log`

UI 必须显示最近任务。

---

## 9. Command Palette（Ctrl/⌘+K）

支持命令：

- Open ticker
- Create rule
- Run backtest
- Refresh data
- Export snapshot
- Go to workspace

约束：

- 支持 fuzzy search
- 按权限过滤可执行命令
- 操作写 `audit_log`

---

## 10. 快捷键体系

- `g m` -> Market
- `g e` -> Explore
- `g r` -> Research Lab
- `g s` -> Strategy Lab
- `/` -> Search ticker
- `?` -> Shortcut help modal

---

## 11. Layout Presets

用户能力：

- Save layout
- Save as
- Set default
- Delete
- Reset to default

持久化：

- 存储到 `ui_layout_presets`
- `layout_json` 必须包含 `version`
- 加载旧版本布局时自动迁移

---

## 12. 安全表达式（custom_expression）

基于 AST 白名单解析。

允许变量：

- `close`
- `ret`
- `vol`
- `z`
- `ma20`
- `ma60`

允许函数：

- `abs`
- `min`
- `max`

允许运算：

- `+ - * /`
- `> < >= <= ==`
- `and or`
- `()`

禁止：

- `import`
- attribute access
- 未授权函数调用
- `exec/eval`

必须有单元测试验证恶意表达式被拒绝。

---

## 13. 测试与 CI

### 13.1 测试范围

**Unit tests**：

- 指标计算
- 8 策略
- 7 规则
- 表达式安全
- walk-forward
- score 稳定性

**Integration tests**：

- DB 迁移
- Celery enqueue
- RBAC gating
- i18n 切换
- layout preset 保存/加载

覆盖率目标：`>= 90%`

### 13.2 CI（GitHub Actions）

`.github/workflows/ci.yml` 需包含：

1. setup Python 3.12
2. install dev dependencies
3. `ruff check .`
4. `pytest --cov`

---

## 14. 默认管理员账号

> 首次部署建议初始化默认管理员：

- **username**: `admin`
- **password**: `Admin@123456`
- **role**: `Admin`
- **default_language**: `zh_CN`

⚠️ 请在首次登录后立即修改密码，并在生产环境通过环境变量或安全初始化脚本注入凭据。

---

## 15. 本地运行与验证（目标流程）

1. 准备 Docker 与 Docker Compose。
2. 配置 `.env`（数据库、Redis、密钥、默认管理员）。
3. 启动服务：`docker compose up -d --build`
4. 执行 DB migration（Alembic upgrade head）。
5. 初始化基础数据（Admin、角色、系统配置、样例标的）。
6. 打开 Streamlit（`web` 服务）并登录 Admin。
7. 导入行情数据（生成 `revision_id`）。
8. 创建并运行规则（Monitor），确认告警与审计日志。
9. 运行策略/参数搜索（Strategy Lab），查看任务与排行榜。
10. 导出 Explore 快照，切换语言验证 i18n。

---

## 16. 交付目标清单

完成后应可：

- `docker compose up -d`
- 访问 Streamlit
- 默认 Admin 登录
- 导入数据
- 运行规则
- 运行策略
- 导出快照
- 切换语言
- 使用快捷键
- 使用 Command Palette
- 保存布局
- 查看任务日志
- `pytest` 全绿并满足覆盖率门禁

---

## License

Proprietary / Internal Use (可按团队实际要求替换)。
