"""YAML / 测试数据 读写与渲染工具"""
import os
import yaml


def _root() -> str:
    """项目根目录（common 的上一级）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_yaml(file_path: str) -> dict:
    """
    读取 YAML 文件，返回 dict

    :param file_path: 相对于项目根目录的路径，如 "config/config.yaml"
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(_root(), file_path)

    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_yaml(file_path: str, data: dict):
    """把 dict 写入 YAML 文件（测试中常用于回写 token、id 等）"""
    if not os.path.isabs(file_path):
        file_path = os.path.join(_root(), file_path)

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def render_data(data: dict, **ctx) -> dict:
    """
    把测试数据里的 {占位符} 替换成实际值。

    用途：解决「测试数据污染」——同一个用例重复运行时，
          固定用户名会冲突，导致用例假失败或假通过。

    例：
        render_data({"userName": "autotest_{uniq}"}, uniq="a1b2c3d4")
        -> {"userName": "autotest_a1b2c3d4"}

    只替换目前支持的字段类型（str）；其它类型原样返回。
    """
    def _render(value):
        if isinstance(value, str):
            for key, val in ctx.items():
                value = value.replace("{" + key + "}", str(val))
        return value

    return {k: _render(v) for k, v in data.items()}


if __name__ == "__main__":
    conf = read_yaml("config/config.yaml")
    print(conf["base_url"])
    print(render_data({"userName": "autotest_{uniq}"}, uniq="abc123"))
