# 核心原则

使用上下文管理器 (with open(...) as f)：确保文件正确关闭。

使用 pathlib 处理路径：不再用字符串拼接，跨平台安全。

明确指定编码：encoding="utf-8"，避免平台差异。

异常处理：捕获 FileNotFoundError、PermissionError 等。

大文件分块处理：避免一次性读入内存。

## 1. 黄金标准：使用 with open 语句

在早期代码中，可能会看到传统的 open() 和 close() 配合写法。但在现代 Python 中，强烈不建议手动关闭文件。因为如果中间代码报错，文件就会一直被占用，导致内存泄漏。

工程化中 100% 推荐使用 with 语句（上下文管理器），它就像一个全自动安保人员，无论发生什么，只要离开代码块，它一定会安全关闭文件。

```python
with open("file.txt", "r", encoding="utf-8") as f:
    content = f.read()
```
避坑指南： 只要处理中文或包含中文的文件，请务必手动加上 encoding="utf-8"！否则在 Windows 电脑上默认用 GBK 解码，代码一换电脑运行就会疯狂报 UnicodeDecodeError 错。

## 2. 核心读写模式

打开文件的第二参数（mode）决定了你拥有什么权限。
```text
模式            含义            行为特征
"r"         Read（只读）        文件不存在会直接报错。指针在文件开头。
"w"         Write（只写）       文件不存在会自动创建；文件若存在，会直接清空原内容再写。
"a"         Append（追加）      文件不存在会自动创建；文件若存在，新内容会排在老内容后面。
"rb" / "wb" Binary（二进制）    用于读写非文本文件(如图片、模型权重、压缩包),不接受encoding参数。
```
## 3. 工程化高级进阶

在实际的软件工程项目中，单纯的文本读写远远不够。我们通常会面对以下场景：

1. 结构化数据解析（JSON / CSV）

不要自己用 split(",") 去肉眼解析表格或配置，Python 自带了完美的标准库。

读写配置文件（JSON）：
```python
import json

# 写入 JSON
config = {"threshold": 0.85, "device": "cuda", "debug": True}
with open("config.json", "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4)  # indent=4 可以让生成的 json 更好看

# 读取 JSON
with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)
    print(cfg["threshold"])  # 拿到 0.85
```
2. 现代化路径管理：弃用 os.path，改用 pathlib

在工程化中，处理多操作系统（Windows 用 \，Linux 用 /）的路径拼接非常让人头疼。现代 Python 推荐使用 pathlib 库，它把路径当成对象来处理，代码极其优雅。

```python
from pathlib import Path

# 1. 自动拼接路径，不管在什么系统下都不会出错
root_dir = Path("my_project")
data_file = root_dir / "data" / "strawberry.txt"

# 2. 判断文件存不存在，不存在则报错（配合断言）
assert data_file.exists(), f"找不到必要的配置文件: {data_file}"

# 3. 甚至不需要写 with open，一行代码搞定读写（只适合小文件）
data_file.write_text("Hello World", encoding="utf-8")
content = data_file.read_text(encoding="utf-8")
```
3. 缓冲刷新与异常捕获

当我们在代码中执行 f.write() 时，操作系统为了提高效率，并不会立刻把数据写进硬盘，而是先攒在内存的“缓冲区”里。

如果你想强迫它立刻写入硬盘（比如正在写重要的日志，怕突然断电），可以调用 f.flush()。

在严谨的工程中，文件读写通常要包裹 try...except，防止文件被锁死、权限不足或磁盘满载导致程序直接崩溃：
```python
from pathlib import Path

target = Path("important_log.txt")

try:
    with open(target, "a", encoding="utf-8") as f:
        f.write("系统正常运行中...\n")
        f.flush()  # 立刻刷入硬盘
except FileNotFoundError:
    print(f"错误：找不到该路径，请检查文件夹是否存在：{target.parent}")
except PermissionError:
    print(f"错误：没有权限读写该文件：{target}")
except Exception as e:
    print(f"读写过程中发生了未知错误: {e}")
```
