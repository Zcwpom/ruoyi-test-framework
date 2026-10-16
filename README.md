# 若依（RuoYi）接口自动化测试框架

[![接口自动化测试](https://github.com/Zcwpom/ruoyi-test-framework/actions/workflows/test.yml/badge.svg)](https://github.com/Zcwpom/ruoyi-test-framework/actions/workflows/test.yml)

用 **pytest + requests + Allure** 写的接口自动化框架，被测系统是开源的若依后台管理系统。

- **分层设计**：接口定义、用例、测试数据、配置分开，接口变了只改一处
- **49 条用例**：41 通过、1 跳过、7 个已知缺陷备案（**0 失败**）
- **6 个缺陷**都写了报告，并固化成自动化回归用例
- 接了 **GitHub Actions**，每次 push 自动跑

---

## 一、目录结构

```
ruoyi-test-framework/
├── api/                        接口层：一个接口一个方法
├── common/                     工具层：请求封装、日志、YAML 读写
├── config/                     配置层：环境地址、账号
├── data/                       数据层：测试数据（YAML）
│
├── testcase/                   用例层（需要若依后端）
│   ├── conftest.py             fixture 公共夹具
│   ├── test_login.py           登录与鉴权
│   ├── test_user.py            用户管理（含数据驱动）
│   └── test_defect_regression.py   已知缺陷回归（D1 / D7 / D9）
│
├── tests/                      单元测试（不依赖后端，CI 里跑）
│   └── test_desensitize.py     日志和报告的凭证脱敏逻辑
│
├── docs/                       缺陷报告 D10 / D11 / D12
├── .github/workflows/test.yml  CI 配置
├── pytest.ini  requirements.txt  run.py
└── report/  log/               运行产物，不提交
```

### 为什么这么分层

| 层 | 只负责 | 好处 |
|---|---|---|
| **用例层** | 测什么 + 断言 | 一眼看得懂 |
| **接口层** | 接口路径和参数 | 接口变了只改这一处 |
| **工具层** | 与业务无关的工具 | 不重复造轮子 |
| **数据层** | 测试数据 | 改数据不用改代码 |
| **配置层** | 环境和账号 | 换环境只改一个文件 |

**一句话：用例层不关心「怎么发请求」，接口层不关心「测什么」。**

---

## 二、怎么跑起来

### 1. 装依赖

```powershell
cd ruoyi-test-framework
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 起被测系统

需要三个东西在跑：

| 组件 | 端口 | 启动方式 |
|---|---|---|
| MySQL | 3306 | Windows 服务，一般开机自启 |
| Redis | 6379 | `redis-server.exe redis.conf` |
| 若依后端 | 8080 | `java -jar ruoyi-admin\target\ruoyi-admin.jar` |

### 3. 关掉登录验证码

自动化脚本识别不了验证码，跑之前先关掉：

```sql
UPDATE sys_config SET config_value = 'false' WHERE config_key = 'sys.account.captchaEnabled';
```

改完重启后端。

### 4. 跑用例

```powershell
pytest tests/ -v             # 单元测试（不用起后端，先跑这个验证环境）
pytest testcase/ -v          # 接口用例（需要后端）
pytest testcase/ -m smoke    # 只跑冒烟
python run.py                # 全量 + 生成 Allure 报告
```

跑出来大概是这样：

```
================= 41 passed, 1 skipped, 7 xfailed in 12.36s =================
```

### 5. 关于 7 个 xfailed

这 7 条是**已知缺陷的回归用例**。断言写的是「缺陷修好之后应该是什么样」，
所以现在必然失败，用 `xfail` 备案 —— 不算失败，套件保持绿色。

缺陷修好之后它们会变成 `XPASS`，提醒你去掉 `xfail` 标记。

```powershell
pytest testcase/ -v --runxfail    # 强制跑，看真实的失败原因
```

---

## 三、发现的缺陷

| 编号 | 问题 | 严重程度 | 报告 |
|---|---|---|---|
| D10 | 密码传空仍能创建用户 | 中 | [报告](docs/缺陷报告-D10-密码传空仍可创建用户.md) |
| D11 | 用户名含 `<script>` 时返回成功，但入库值被静默改掉 | 低 | [报告](docs/缺陷报告-D11-用户名含脚本标签时被静默修改.md) |
| D12 | 手机号只校验长度、不校验格式 | 低 | [报告](docs/缺陷报告-D12-手机号只校验长度不校验格式.md) |

这三个是写数据驱动用例时发现的，每个都对应一条 `xfail` 用例。

> 另外 6 个（D1 ~ D9）是在 Postman 阶段发现的，见下面的「相关项目」。

---

## 四、CI（GitHub Actions）

每次 push 自动跑三步：

| 步骤 | 命令 | 查什么 |
|---|---|---|
| 语法检查 | `python -m compileall -q ...` | 所有 py 文件能不能编译 |
| 单元测试 | `pytest tests/ -v` | 脱敏逻辑有没有被改坏 |
| 用例收集检查 | `pytest testcase/ --collect-only -q` | import 错误、fixture 名字写错、装饰器参数不合法 |

**接口用例为什么不在 CI 里跑**：它们需要 MySQL + Redis + 8080 后端，CI 机器上没有。
所以只做「收集检查」—— `--collect-only` 只导入和收集、不执行用例，
不用起后端就能发现大部分低级错误。

> 真实项目里也是这么分层的：单元测试每次提交都跑，集成测试跑在专门的机器上。

---

## 五、相关项目

- **[ruoyi-api-test](https://github.com/Zcwpom/ruoyi-api-test)** ——
  同一个被测系统的 Postman 接口测试阶段：37 个接口、110 条断言、测试用例表、
  缺陷报告 D1 / D7 / D9（含截图证据）、Newman 命令行回归、JMeter 性能测试。

> 两个仓库测的是同一个系统，缺陷编号 **D1 ~ D12 连续**。
> 这个仓库是把测试代码化之后的版本。

---

## 六、常见问题

| 现象 | 原因 | 解决 |
|---|---|---|
| 登录返回「验证码错误」 | 验证码没关 | 见第二节第 3 步 |
| `No module named 'api'` | 不在项目根目录 | 必须在根目录执行；确认 `pytest.ini` 里有 `pythonpath = .` |
| 大面积 401 | Token 没拿到 | 看日志里有没有「登录成功，Token = ...」，没有就是若依没起来 |
| 用例之间互相影响 | 数据没清理 | 用 `uniq` 夹具造唯一数据，用 `data_cleanup` 夹具收尾 |
| 收集不到用例 | 命名不符合规则 | 文件必须 `test_*.py`，函数必须 `test_*` |
