"""
一键执行入口

用法：
    python run.py                  # 跑全部用例 + 生成并打开报告
    python run.py -m smoke         # 只跑冒烟
    python run.py -k login         # 只跑名字含 login 的用例
    python run.py -n 4             # 4 个进程并行（需 pytest-xdist）
"""
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.abspath(__file__))
ALLURE_RESULTS = os.path.join(ROOT, "report", "allure-results")
ALLURE_REPORT = os.path.join(ROOT, "report", "allure-report")


def main():
    print("=" * 60)
    print("  若依接口自动化测试")
    print("=" * 60)

    # 1. 清理上次结果
    shutil.rmtree(ALLURE_RESULTS, ignore_errors=True)
    shutil.rmtree(ALLURE_REPORT, ignore_errors=True)

    # 2. 执行 pytest（命令行参数透传，如 -m smoke / -k login）
    args = sys.argv[1:] or ["-vs"]
    if "--alluredir" not in " ".join(args):
        args += ["--alluredir", ALLURE_RESULTS]
    pytest.main(args)

    # 3. 生成 Allure 报告
    print("\n生成 Allure 报告 ...")
    code = os.system(f'allure generate "{ALLURE_RESULTS}" -o "{ALLURE_REPORT}" --clean')
    if code != 0:
        print("\n[提示] allure 命令不可用。")
        print("  1) 装 Allure：https://github.com/allure-framework/allure2/releases")
        print("  2) 解压后把 bin 目录加进 PATH")
        print("  3) 或者直接看命令行输出即可，不影响用例执行")
        return

    # 4. 打开报告
    os.system(f'allure open "{ALLURE_REPORT}"')


if __name__ == "__main__":
    main()
