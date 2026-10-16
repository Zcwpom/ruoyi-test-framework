"""
最小示例：不依赖若依，验证 pytest 环境是否正常

用法：
    pytest testcase/test_demo_httpbin.py -vs

能跑出 6 passed 就说明：
    ✓ Python 环境正常
    ✓ 虚拟环境正常
    ✓ requests / pytest 依赖正常
    ✓ pytest 收集用例规则正常
    ✓ 参数化正常
问题只可能在"若依没部署"这一件事上。
"""
import pytest
import requests

BASE = "https://httpbin.org"


def test_get():
    r = requests.get(f"{BASE}/get", timeout=10)
    assert r.status_code == 200
    assert r.json()["url"].endswith("/get")


@pytest.mark.parametrize("code", [200, 201, 404, 500])
def test_status_code(code):
    """参数化：一次覆盖 4 种状态码"""
    r = requests.get(f"{BASE}/status/{code}", timeout=10)
    assert r.status_code == code


def test_post_json():
    r = requests.post(f"{BASE}/post", json={"username": "admin"}, timeout=10)
    assert r.status_code == 200
    assert r.json()["json"]["username"] == "admin"
