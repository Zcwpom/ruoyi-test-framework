# -*- coding: utf-8 -*-
"""
脱敏逻辑单元测试

特点：不依赖若依后端，可以在 CI 里独立运行（接口用例需要后端，跑不了）。

运行：
    pytest tests/ -v
"""
from common.request_util import _mask, mask_text, desensitize

TOKEN = ("eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJhZG1pbiIsImxvZ2luX3VzZXJfa2V5IjoiM2MwMWU4NjAtZDMyZS00NmZl"
         "LWI5YzItYTBhMDU4MjBmODAzIn0.abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG")


# ============================================================
# 一、JSON 结构脱敏
# ============================================================

def test_json_token_masked():
    """登录响应里的 token 必须被遮住"""
    out = desensitize('{"msg":"操作成功","code":200,"token":"' + TOKEN + '"}')
    assert TOKEN not in out, "完整 token 泄露到输出里了"
    assert "已脱敏" in out


def test_json_normal_fields_untouched():
    """脱敏不能误伤正常字段"""
    out = desensitize('{"msg":"操作成功","code":200,"total":2}')
    assert "操作成功" in out
    assert "200" in out
    assert "total" in out


def test_login_body_password_masked():
    """登录请求体里的 password 必须被遮住，但 username 要保留"""
    out = desensitize('{"username":"admin","password":"admin123","code":"","uuid":""}')
    assert "admin123" not in out, "密码泄露"
    assert "admin" in out, "用户名被误遮了"


def test_long_password_masked():
    """超长密码（test_login.py 参数化里的 58 字符密码）也要遮住"""
    pwd = "admin123" + " " * 50
    out = desensitize('{"username":"admin","password":"' + pwd + '"}')
    assert pwd not in out


def test_nested_password_masked():
    """嵌套结构（列表里对象）里的密码也要遮住"""
    out = desensitize('{"rows":[{"userId":1,"password":"p@ss1234"},'
                      '{"userId":2,"password":"p@ss5678"}]}')
    assert "p@ss1234" not in out
    assert "p@ss5678" not in out


def test_multiple_sensitive_keys_masked():
    """多个敏感字段同时出现都要遮住"""
    out = desensitize('{"token":"AAAAAAAAAAAAAAAAAAAA",'
                      '"secret":"BBBBBBBBBBBBBBBB","password":"CCCCCCCCCC"}')
    assert "AAAAAAAAAAAAAAAAAAAA" not in out
    assert "BBBBBBBBBBBBBBBB" not in out
    assert "CCCCCCCCCC" not in out


# ============================================================
# 二、边界情况
# ============================================================

def test_empty_values_not_crash():
    """空值和 null 不能让程序报错"""
    out = desensitize('{"token":"","password":null,"code":200}')
    assert "200" in out


def test_short_value_fully_starred():
    """短值（<=8 位）应全部打星，不留前 4 位"""
    assert _mask("abc") == "***"
    assert _mask("12345678") == "********"
    assert _mask("") == ""
    assert _mask(None) == ""


def test_long_value_keeps_prefix_and_length():
    """长值保留前 4 位 + 标注长度，但拿不到完整值"""
    m = _mask(TOKEN)
    assert m.startswith(TOKEN[:4])
    assert str(len(TOKEN)) in m
    assert TOKEN not in m


# ============================================================
# 三、非 JSON 文本（正则兜底）
# ============================================================

def test_kv_style_masked():
    """token=xxx 这种 form / query 写法"""
    out = mask_text("token=" + TOKEN + " password=admin123")
    assert TOKEN not in out
    assert "admin123" not in out


def test_authorization_header_masked():
    """Authorization: Bearer xxx 这种请求头写法"""
    out = mask_text("Authorization: Bearer " + TOKEN)
    assert TOKEN not in out


def test_form_data_masked():
    """form 表单数据里的密码"""
    out = mask_text("username=admin&password=admin123&code=&uuid=")
    assert "admin123" not in out
    assert "username=admin" in out, "普通字段被误遮了"


# ============================================================
# 四、关键顺序：先脱敏、再截断
# ============================================================

def test_mask_before_truncate():
    """
    日志行是 mask_text(...)[:500]，顺序不能反。
    反过来的话，超长响应被截断后正则匹配不到收尾的引号，token 会漏出去。
    """
    long_body = ('{"msg":"ok","code":200,"token":"' + TOKEN + '","extra":"'
                 + "x" * 3000 + '"}')
    log_line = mask_text(long_body)[:500]
    assert TOKEN not in log_line, "截断后 token 泄露"
    assert len(log_line) == 500
