配置文件是工程化项目的关键组成部分，它让代码与运行参数分离，方便在不同环境（开发/测试/生产）下切换。

# 一、为什么需要配置文件？

避免硬编码：数据库地址、API密钥、文件路径等不应写在代码里。

环境切换：开发用 localhost，生产用真实域名。

参数调优：模型超参数、重试次数等，修改配置无需改代码。

安全：敏感信息（密码、Token）不提交到 Git。

1. 准备配置文件：config.yaml

YAML 的好处是长得非常像人话，支持层级嵌套。
```python
#config.yaml
database:
  host: "localhost"
  port: 5432
  user: "admin"

app:
  debug: true
  title: "我的酷炫项目"
```

2. 读取配置

在 Python 中，我们通常使用 PyYAML 库。如果没安装，先运行：pip install pyyaml。

基础加载代码

```python
import yaml
def load_config(file_path="config.yaml"):
    with open(file_path, "r", encoding="utf-8") as f:
        # Loader=yaml.FullLoader 是为了安全，防止执行恶意代码
        config = yaml.load(f, Loader=yaml.FullLoader)
    return config

#使用
cfg = load_config()
print(cfg['database']['host'])  # 输出: localhost
```

3. 常见坑与最佳实践

不要提交真实密钥到 Git

在 .gitignore 中加入 config/production.yaml 或 *.secret.yaml。

注意 YAML 的布尔值陷阱

on、yes、no 会被解析为布尔值，字符串需加引号："yes"。

路径问题

配置中的相对路径应相对于项目根目录，可在读取时转换：
```python
project_root = Path(__file__).parent.parent
data_path = project_root / config["data"]["raw_path"]
```



