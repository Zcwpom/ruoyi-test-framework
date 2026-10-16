# 若依（RuoYi）接口自动化测试框架

[![接口自动化测试](https://github.com/Zcwpom/ruoyi-test-framework/actions/workflows/test.yml/badge.svg)](https://github.com/Zcwpom/ruoyi-test-framework/actions/workflows/test.yml)

> 分层设计的 pytest + requests + Allure 接口自动化框架
> **这是你简历上的主力作品**

---

## 一、目录结构

```
ruoyi-test/
├── api/                        # 【接口层】封装每个接口的请求路径和参数
│   ├── login_api.py            #   登录模块
│   └── user_api.py             #   用户管理模块
│
├── common/                     # 【公共层】与业务无关的工具
│   ├── request_util.py         #   requests 二次封装（日志/超时/Token 统一处理）
│   ├── logger_util.py          #   日志（控制台 + 文件滚动）
│   └── yaml_util.py            #   读 YAML 配置和测试数据
│
├── config/                     # 【配置层】环境、账号、数据库
│   └── config.yaml
│
├── data/                       # 【数据层】测试数据（数据驱动）
│   └── user_data.yaml
│
├── testcase/                   # 【用例层】只写"测什么"（需要若依后端）
│   ├── conftest.py             #   fixture 公共夹具
│   ├── test_login.py
│   └── test_user.py
│
├── tests/                      # 【单元测试】不依赖后端，CI 里独立运行
│   └── test_desensitize.py     #   日志/报告的凭证脱敏逻辑
│
├── .github/workflows/          # 【CI】GitHub Actions
│   └── test.yml                #   每次 push 自动跑单元测试 + 用例收集检查
│
├── report/                     # 测试报告（自动生成）
├── log/                        # 运行日志（自动生成）
├── pytest.ini                  # pytest 配置
├── requirements.txt
└── run.py                      # 一键执行入口
```

### 为什么这么分层（面试必问）

| 层 | 职责 | 好处 |
|---|---|---|
| **用例层** | 只描述测试逻辑和断言 | 用例可读，不懂技术的人也能看懂 |
| **接口层** | 只描述接口路径和参数 | 接口变了只改一处，所有用例自动跟着变 |
| **公共层** | 工具方法 | 不重复造轮子 |
| **数据层** | 测试数据 | **改数据不用改代码**（数据驱动） |
| **配置层** | 环境和账号 | 换环境只改一个文件 |

**一句话总结**：**用例层不关心"怎么发请求"，接口层不关心"测什么"。**

---

## 二、环境准备

### 1. 复制项目到纯英文路径

```
把 ruoyi-test-framework 复制到  E:\code\ruoyi-test\
```
> ⚠️ **不要放在中文路径下**（如 `E:\学习\`），会导致各种诡异报错。

### 2. 装依赖

```cmd
cd /d E:\code\ruoyi-test
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 装 Allure（生成报告用）

```
1. 下载：https://github.com/allure-framework/allure2/releases
2. 解压到 C:\allure
3. 把 C:\allure\bin 加进系统环境变量 PATH
4. 验证：allure --version
```
> 不装也能跑用例，只是没有可视化报告（run.py 里已做了容错）。

### 4. 确认被测系统在跑

```cmd
docker ps
```
应该能看到若依的 MySQL 和 Redis 容器。后端 8080 前端 80 都要起。

---

## 三、⚠️ 跑之前必须先关验证码（否则登录必失败）

若依默认开启登录验证码，自动化脚本识别不了。**两个办法选一个：**

### 办法 A：改参数配置（推荐）

```
登录若依 → 系统管理 → 参数设置 → 找到 sys.account.captchaEnabled
→ 把值改成 false → 保存
→ 清 Redis 缓存（重启后端 或 系统监控 → 缓存监控 → 清空）
```

### 办法 B：改 application.yml

```yaml
# ruoyi-admin/src/main/resources/application.yml
captcha:
  enabled: false
```
改完重启后端。

### 办法 C：实在关不掉

手动登录一次，从浏览器 F12 → Network → 找 `/login` 请求 → 复制返回的 `token` → 填到 `config/config.yaml` 里，跳过自动登录。

> 这个"验证码阻碍自动化"的问题**本身就是个很好的面试话题**：
> "我做接口自动化时遇到验证码拦截，解决方案是……"

---

## 四、跑起来

```cmd
cd /d E:\code\ruoyi-test
venv\Scripts\activate

python run.py                      # 全部用例 + 生成报告
python run.py -m smoke             # 只跑冒烟
python run.py -k login             # 只跑登录相关
python run.py testcase/test_user.py -vs   # 只跑某个文件
```

**期望输出：**
```
testcase/test_login.py::TestLogin::test_login_success PASSED
testcase/test_login.py::TestLogin::test_get_info_after_login PASSED
...
========================= 30 passed in 12.45s =========================
```

---

## 五、学习路径（按这个顺序看代码，别乱翻）

| 顺序 | 文件 | 学什么 |
|---|---|---|
| 1 | `config/config.yaml` | 配置怎么放 |
| 2 | `common/yaml_util.py` | 怎么读 YAML（最简单，10 行） |
| 3 | `common/logger_util.py` | 日志怎么封装 |
| 4 | `common/request_util.py` | **重点**：requests 二次封装、Session、Token |
| 5 | `api/login_api.py` | **重点**：接口层怎么写 |
| 6 | `testcase/conftest.py` | **最重点**：fixture、scope、yield |
| 7 | `testcase/test_login.py` | **重点**：参数化、断言、越权测试 |
| 8 | `testcase/test_user.py` | **重点**：CRUD 闭环、数据驱动 |
| 9 | `data/user_data.yaml` | 数据驱动怎么落地 |
| 10 | `pytest.ini` | pytest 配置项 |
| 11 | `run.py` | 一键执行 + 报告 |

### 必须掌握的 5 个 pytest 概念（面试高频）

| 概念 | 在哪看 | 面试会怎么问 |
|---|---|---|
| **fixture** | `conftest.py` | fixture 是什么？和 setup/teardown 什么区别？ |
| **scope** | `conftest.py` | 4 种 scope 的区别？为什么登录用 session？ |
| **conftest.py** | `conftest.py` | conftest 的作用？能放几个？ |
| **parametrize** | `test_login.py` | 参数化怎么写？怎么配合数据驱动？ |
| **assert** | 全部 | pytest 断言和 unittest 有什么区别？ |
| **mark** | `pytest.ini` | 怎么只跑冒烟用例？ |

---

## 六、下一步：把它变成你自己的

跑通之后，**别停在这里**。按这个顺序加东西：

### 第一周：补全模块
- [ ] 加 `api/role_api.py`（角色管理）+ `testcase/test_role.py`
- [ ] 加 `api/dept_api.py`（部门管理）
- [ ] 加 `api/menu_api.py`（菜单管理）

### 第二周：加深度
- [ ] `common/mysql_util.py` —— 用 pymysql 查数据库校验数据（**面试加分**）
- [ ] 加数据权限测试（不同角色 Token 看到的数据条数不同）
- [ ] 加**越权测试**（低权限 Token 调高权限接口）★ 最有价值
- [ ] 加关联接口的场景串联（新增用户 → 分配角色 → 查权限）

### 第三周：工程化
- [x] Git 提交，写 README
- [x] **GitHub Actions 持续集成**（见第九节）—— 每次 push 自动跑
- [ ] 依赖后端的接口用例也接进 CI（要先用 services 起 MySQL/Redis + 编译若依）
- [ ] 加邮件/钉钉通知
- [ ] pytest-xdist 并行执行（`python run.py -n 4`）

---

## 七、这个框架怎么讲进简历

```
接口自动化测试框架 | Python + pytest + requests + Allure
· 采用分层设计（api / testcase / data / common / config），实现用例与接口
  定义解耦，接口变更时只需修改 api 层
· 基于 requests 二次封装请求工具类，统一处理 base_url、超时、Token 注入
  与请求响应日志，便于问题追溯
· 使用 pytest fixture 管理会话级登录态，避免每个用例重复登录
· 通过 conftest.py 沉淀公共夹具与全局配置，实现测试数据与代码分离
· 采用 YAML 数据驱动，覆盖新增用户的 8 种异常场景
· 集成 Allure 生成可视化测试报告，支持 Jenkins 持续集成与定时回归
· 设计越权测试用例：使用低权限账号 Token 直接请求高权限接口，验证后端
  权限校验的有效性（而非仅依赖前端按钮隐藏）

产出：30+ 条接口用例，覆盖登录、用户管理模块的正常流、异常流与边界场景
```

> ⚠️ **上面的内容必须真的做出来才能写。** 数字改成你自己的真实数字。

---

## 八、常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 登录返回 `验证码错误` | 验证码没关 | 见第三节 |
| `ModuleNotFoundError: No module named 'api'` | 工作目录不对 | 必须在项目根目录执行；确认 `pytest.ini` 里有 `pythonpath = .` |
| 401 / 403 | Token 失效或没带上 | 检查 `conftest.py` 登录是否成功 |
| `assert_ok` 报 500 | 业务校验失败 | 看日志里 `← 500` 后面的 msg |
| 用例之间互相影响 | 数据没清理 | 用时间戳生成唯一用户名（见 `TestUserCrud.USER_NAME`） |
| pytest 收集不到用例 | 命名不符合规则 | 文件必须 `test_*.py`，函数必须 `test_*` |

---

## 九、CI 持续集成（GitHub Actions）

### 1. 为什么只跑一部分用例

| 用例类型 | 需要若依后端？ | CI 里跑吗 |
|---|---|---|
| `tests/` 单元测试（脱敏逻辑） | ❌ 不需要 | ✅ **每次提交都跑** |
| `testcase/` 接口用例 | ✅ 需要 MySQL + Redis + 8080 | ❌ 跑不了，只做「收集检查」 |

**真实公司里也是这么分层的**：单元测试每次提交都跑（几十秒出结果），
集成测试跑在专门的机器上，或者按需手动触发。

### 2. CI 里做三件事

| 步骤 | 命令 | 查什么 |
|---|---|---|
| 语法检查 | `python -m compileall -q ...` | 所有 py 文件能不能编译 |
| 单元测试 | `pytest tests/ -v` | 脱敏逻辑有没有被改坏 |
| **用例收集检查** | `pytest testcase/ --collect-only -q` | 语法错误、import 错误、fixture 名字写错、装饰器参数不合法 |

> 第三条最实用：**`--collect-only` 只做「导入 + 收集」，不执行用例**，
> 所以不用起后端，就能发现大部分低级错误。

### 3. 什么时候跑

- 每次 `git push` 自动跑
- 提 Pull Request 时自动跑
- 也可以在仓库页 → **Actions** → 选这个 workflow → **Run workflow** 手动触发

### 4. 怎么看结果

- README 顶部的徽章：**绿色 = 通过，红色 = 失败**
- 点徽章进 Actions 页面，能看到每一步的完整日志

### 5. 一个真实的坑

workflow 里固定用 **Python 3.12** ——
`requirements.txt` 里的版本（pytest 8.3.4 / requests 2.32.3）在 3.12 上验证过。
**换别的版本可能装不上依赖**，所以版本要钉死。

### 6. ⚠️ 徽章地址要改成你自己的

README 顶部那个徽章，我按 `Zcwpom/ruoyi-test-framework` 填的。
**如果你建仓库时用了别的名字，把这两处改掉：**

```
https://github.com/<你的用户名>/<仓库名>/actions/workflows/test.yml/badge.svg
```
