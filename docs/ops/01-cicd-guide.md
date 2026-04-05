# CozyMemory CI/CD 配置指南

**文档编号**: OPS-CICD-001  
**版本**: 1.0  
**创建日期**: 2026-04-05  
**运维负责人**: 运维团队

---

## 1. CI/CD 架构概览

### 1.1 流水线设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│                     (zinohome/CozyMemory)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub Actions Workflows                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   CI.yml     │  │  CD (auto)   │  │daily-scan.yml│          │
│  │  (代码提交)   │  │  (合并 main)  │  │  (每日扫描)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GitHub Container Registry                  │
│                  (ghcr.io/zinohome/CozyMemory)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        部署环境                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   Staging    │  │  Production  │                            │
│  │  (预发布环境) │  │  (生产环境)   │                            │
│  └──────────────┘  └──────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 流水线详解

### 2.1 CI 流水线 (.github/workflows/ci.yml)

**触发条件**:
- `push` 到 `main` 或 `develop` 分支
- `pull_request` 到 `main` 或 `develop` 分支

**工作流程**:

```
开发者推送代码/创建 PR
        ↓
┌───────────────────┐
│  1. 代码质量检查   │ ← 失败则终止
│   - isort         │
│   - black         │
│   - flake8        │
│   - mypy          │
└───────────────────┘
        ↓
┌───────────────────┐
│  2. 单元测试       │ ← 覆盖率 <80% 则失败
│   - pytest        │
│   - coverage      │
└───────────────────┘
        ↓
┌───────────────────┐
│  3. 集成测试       │ ← 仅 PR 触发
│   - Docker Compose│
│   - API 测试       │
└───────────────────┘
        ↓
┌───────────────────┐
│  4. 安全扫描       │
│   - bandit        │
│   - safety        │
└───────────────────┘
        ↓
┌───────────────────┐
│  5. 构建 Docker    │ ← 仅 main 分支
│   - 多阶段构建     │
│   - 推送 GHCR     │
└───────────────────┘
        ↓
┌───────────────────┐
│  6. 部署 Staging   │ ← 自动
│   - Kubernetes    │
└───────────────────┘
        ↓
┌───────────────────┐
│  7. 部署 Production│ ← 人工审批
│   - Kubernetes    │
└───────────────────┘
```

**Jobs 说明**:

| Job | 运行时长 | 说明 |
|-----|---------|------|
| `lint` | ~5 分钟 | 代码格式/类型检查 |
| `test` | ~10 分钟 | 单元测试 + 覆盖率 |
| `integration-test` | ~15 分钟 | 集成测试 (仅 PR) |
| `security` | ~5 分钟 | 安全漏洞扫描 |
| `build-docker` | ~10 分钟 | 构建并推送镜像 (仅 main) |
| `deploy-staging` | ~5 分钟 | 部署到 Staging (仅 main) |
| `deploy-production` | ~5 分钟 | 部署到生产 (需审批) |

---

### 2.2 每日扫描流水线 (.github/workflows/daily-scan.yml)

**触发条件**:
- 每天 02:00 UTC (北京时间 10:00)
- 支持手动触发 (`workflow_dispatch`)

**工作流程**:

```
定时触发 (02:00 UTC)
        ↓
┌───────────────────┐
│  1. 依赖漏洞扫描   │
│   - safety        │
│   - pip-audit     │
└───────────────────┘
        ↓
┌───────────────────┐
│  2. 代码质量扫描   │
│   - SonarCloud    │
│   - 覆盖率报告     │
└───────────────────┘
        ↓
┌───────────────────┐
│  3. 生成日报       │
│   - Markdown 报告  │
│   - 上传 artifact  │
└───────────────────┘
```

---

## 3. 环境配置

### 3.1 GitHub Environments

需要在 GitHub 仓库配置 2 个环境：

#### Staging 环境
```yaml
环境名称：staging
URL: https://staging-api.cozymemory.com
保护规则:
  - 需要审查者：否
  - 等待计时器：无
环境变量:
  - APP_ENV: staging
  - DATABASE_URL: (Secret)
  - REDIS_URL: (Secret)
```

#### Production 环境
```yaml
环境名称：production
URL: https://api.cozymemory.com
保护规则:
  - 需要审查者：是 (张老师)
  - 等待计时器：无
环境变量:
  - APP_ENV: production
  - DATABASE_URL: (Secret)
  - REDIS_URL: (Secret)
```

### 3.2 配置 Secrets

在 GitHub 仓库 Settings → Secrets and variables → Actions 中配置：

| Secret 名称 | 说明 | 示例值 |
|-----------|------|--------|
| `SONAR_TOKEN` | SonarCloud 令牌 | `sqp_xxx` |
| `DATABASE_URL` | 生产数据库连接 | `postgresql://...` |
| `REDIS_URL` | Redis 连接 | `redis://...` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-xxx` |

---

## 4. Docker 镜像

### 4.1 镜像标签策略

```yaml
标签格式:
  - :latest          # main 分支最新构建
  - :main            # main 分支
  - :develop         # develop 分支
  - :<git-sha>       # 具体提交 (如 :a1b2c3d)
  - :v1.0.0          # 语义化版本标签
```

### 4.2 镜像拉取

```bash
# 拉取最新生产镜像
docker pull ghcr.io/zinohome/cozymemory:latest

# 拉取特定版本
docker pull ghcr.io/zinohome/cozymemory:v1.0.0

# 拉取特定提交
docker pull ghcr.io/zinohome/cozymemory:a1b2c3d
```

---

## 5. 部署流程

### 5.1 自动部署到 Staging

**触发**: PR 合并到 `main` 分支

**流程**:
1. CI 流水线所有检查通过 ✅
2. 构建 Docker 镜像并推送 GHCR
3. 自动部署到 Staging 环境
4. 运行冒烟测试
5. 发送通知到微信

**通知内容**:
```
🚀 CozyMemory 部署通知

环境：Staging
版本：v1.0.0-a1b2c3d
时间：2026-04-05 12:00:00
状态：✅ 成功

访问：
- API: https://staging-api.cozymemory.com
- 文档：https://staging-api.cozymemory.com/docs
```

---

### 5.2 人工审批部署到 Production

**触发**: Staging 部署成功后

**流程**:
1. GitHub 发送审批通知给张老师
2. 张老师在 GitHub 点击 "Review deployments" → "Approve and deploy"
3. 自动部署到生产环境
4. 运行冒烟测试
5. 发送通知到微信

**审批界面**:
```
┌─────────────────────────────────────────┐
│  部署到 production 等待审批              │
├─────────────────────────────────────────┤
│  环境：production                        │
│  版本：v1.0.0-a1b2c3d                    │
│  请求者：蟹小五                          │
│  时间：2026-04-05 12:00:00              │
├─────────────────────────────────────────┤
│  [✅ Approve and deploy]  [❌ Reject]   │
└─────────────────────────────────────────┘
```

---

## 6. 监控与告警

### 6.1 流水线状态监控

**Dashboard**: https://github.com/zinohome/CozyMemory/actions

**关键指标**:
- 构建成功率：>95%
- 平均构建时长：<30 分钟
- 部署频率：按需
- 部署失败率：<5%

### 6.2 告警规则

| 告警类型 | 触发条件 | 通知方式 |
|---------|---------|---------|
| CI 失败 | main 分支构建失败 | 微信 |
| 部署失败 | 生产部署失败 | 微信 + 电话 |
| 安全漏洞 | 发现高危漏洞 | 微信 + 邮件 |
| 覆盖率下降 | 覆盖率 <80% | 微信 |

---

## 7. 故障排查

### 7.1 CI 失败排查流程

```
CI 失败
    ↓
1. 查看 GitHub Actions 日志
   - 定位失败的 Job
   - 查看具体错误信息
    ↓
2. 本地复现
   - git checkout <branch>
   - 运行失败的检查命令
    ↓
3. 修复问题
   - 代码问题 → 修改代码
   - 配置问题 → 更新配置
   - 环境问题 → 联系运维
    ↓
4. 重新推送代码
   - git commit -m "fix: ..."
   - git push
    ↓
5. 验证 CI 通过
```

### 7.2 常见错误

#### 错误 1: 代码格式检查失败
```
❌ black 检查失败
Please run 'black src/ tests/' to fix formatting issues.
```

**解决**:
```bash
black src/ tests/
git add .
git commit -m "style: 代码格式化"
git push
```

#### 错误 2: 单元测试覆盖率不足
```
❌ FAIL Required test coverage of 80% not reached.
Name                     Stmts   Miss  Cover
--------------------------------------------
src/api/main.py             50      20    60%
```

**解决**:
```bash
# 查看具体未覆盖的行
pytest --cov=src --cov-report=term-missing

# 补充单元测试
# 重新推送
```

#### 错误 3: Docker 构建失败
```
❌ ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**解决**:
```bash
# 检查 requirements.txt 语法
# 检查依赖是否兼容 Python 3.11
# 本地构建测试
docker build -t cozymemory:test .
```

---

## 8. 最佳实践

### 8.1 提交规范

```bash
# ✅ 好的提交
git commit -m "feat(adapter): 添加 Memobase 适配器"
git commit -m "fix(cache): 修复 Redis 连接超时问题"
git commit -m "test: 添加单元测试"

# ❌ 不好的提交
git commit -m "更新代码"
git commit -m "fix bug"
```

### 8.2 PR 规范

**PR 标题**:
```
feat: 添加 Memobase 适配器
fix: 修复缓存 TTL 问题
```

**PR 描述**:
```markdown
## 变更描述
添加 Memobase 适配器实现

## 关联 Issue
Closes #123

## 测试计划
- [x] 单元测试通过
- [x] 集成测试通过
- [x] 手动测试完成
```

### 8.3 分支管理

```
main (受保护)
  ↑
develop (开发分支)
  ↑
feature/* (功能分支，从 develop 切出)
  ↑
bugfix/* (修复分支，从 develop 切出)
  ↑
hotfix/* (紧急修复，从 main 切出)
```

---

## 9. 成本估算

### 9.1 GitHub Actions 用量

| 套餐 | 免费额度 | 超出价格 |
|------|---------|---------|
| Free | 2000 分钟/月 | $0.008/分钟 |
| Team | 3000 分钟/月 | $0.008/分钟 |
| Pro | 50000 分钟/月 | $0.008/分钟 |

**预估用量**:
- CI 流水线：15 分钟/次 × 20 次/月 = 300 分钟
- 每日扫描：15 分钟/次 × 30 次/月 = 450 分钟
- **总计**: 750 分钟/月 (Free 套餐足够)

### 9.2 GHCR 存储

| 套餐 | 免费额度 | 超出价格 |
|------|---------|---------|
| 所有 | 500MB | $0.25/GB/月 |

**预估用量**:
- Docker 镜像：500MB × 3 版本 = 1.5GB
- **总计**: 1.5GB (超出 1GB，约 $0.25/月)

---

## 10. 附录

### 10.1 参考文档

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [Docker 多阶段构建](https://docs.docker.com/develop/develop-images/multistage-build/)
- [SonarCloud 配置](https://sonarcloud.io/)

### 10.2 相关文件

- [ci.yml](../.github/workflows/ci.yml) - CI 流水线配置
- [daily-scan.yml](../.github/workflows/daily-scan.yml) - 每日扫描配置
- [Dockerfile](../Dockerfile) - Docker 镜像构建
- [pyproject.toml](../pyproject.toml) - Python 项目配置

---

**审批**

| 角色 | 姓名 | 签字 | 日期 |
|------|------|------|------|
| 运维负责人 | | | 2026-04-05 |
| 技术负责人 | 蟹小五 | | 2026-04-05 |

---

**版本历史**

| 版本 | 日期 | 作者 | 变更描述 |
|------|------|------|---------|
| 1.0 | 2026-04-05 | 蟹小五 | 初始版本 |
