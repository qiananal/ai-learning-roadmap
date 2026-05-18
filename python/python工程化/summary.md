总结：Python 工程化学习路线图

# 1. 文件结构

标准布局：main.py + utils/（工具） + models/（业务实体） + data/（数据） + logs/（日志） + config.yaml。

核心原则：main.py 只做入口；utils 放无业务逻辑的通用函数；models 放领域模型；services 放流程编排。

工具：用 cookiecutter 或 pyscaffold 快速生成模板。

# 2. 配置文件管理（YAML）

格式：config.yaml，支持嵌套、列表、注释。

读取：yaml.safe_load()，不要用 load()（安全）。

环境分离：default.yaml + development.yaml + production.yaml，通过环境变量 APP_ENV 选择。

敏感信息：密码、密钥用环境变量 ${DB_PASS}，代码中 os.getenv() 覆盖。

验证：用 pydantic 做类型和约束校验。

# 3. 日志系统

三要素：Logger（入口+级别） + Handler（去向） + Formatter（格式）。

级别：DEBUG < INFO < WARNING < ERROR < CRITICAL。

最佳实践：

开发环境：控制台 INFO + 文件 DEBUG

生产环境：仅文件 INFO + 轮转（RotatingFileHandler）

快速模板：setup_logger(name, log_file) 函数，自动创建目录，添加控制台和文件两个 handler。

异常记录：logger.exception("msg") 自动记录堆栈。

# 4. 数据目录管理

标准子目录：raw/（原始数据，只读）、processed/（清洗后）、interim/（中间结果）、cache/（可随时删除）、results/（输出）。

路径处理：始终用 pathlib.Path，基于项目根目录解析相对路径。

自动化：Path.mkdir(parents=True, exist_ok=True) 确保目录存在。

缓存模式：检查 cache/ 中文件是否存在，若不存在则计算并保存。

# 5. 核心模块划分（models / utils / services）

依赖方向：main → services → models → utils（单向，不可反向）。

utils：纯函数、I/O 封装、配置加载、日志初始化。不能导入 models。

models：业务实体（dataclass/pydantic）、模型封装。可以导入 utils。

services：跨多个 models 的业务流程（如训练流水线）。可以导入 utils 和 models。

判断法：这段代码能否复制到另一个项目直接用？能→utils；是否代表项目核心概念？是→models；是否编排多个实体？是→services。

# 6. 单元测试（pytest）

命名：测试文件 test_*.py，测试函数 test_*。

结构：Arrange（准备） → Act（调用） → Assert（断言）。

fixture：复用测试数据（如 sample_email）。

mock：用 mocker.patch 模拟外部依赖（数据库、网络、文件系统）。

异常测试：with pytest.raises(ExpectedException):

覆盖率：pytest --cov=myproject tests/，目标核心逻辑 80% 以上。

# 7. 依赖管理

虚拟环境：python -m venv venv → source venv/bin/activate → 每个项目独立。

声明文件 vs 锁文件：

声明文件（requirements.in / pyproject.toml）：写版本范围，如 torch>=2.0,<2.2。

锁文件（requirements.txt / poetry.lock）：精确版本，如 torch==2.1.0。

工具选择：

轻量级：pip-tools（pip-compile + pip-sync）

一站式：poetry（自动虚拟环境、锁定、打包）

科学计算：conda（可管理 CUDA、C 库）

最佳实践：提交锁文件，不提交虚拟环境目录；定期更新依赖。

# 8. 命令行入口设计

工具层级：

sys.argv：只适合 1-2 个参数。

argparse：标准库，功能完整（位置参数、选项、子命令）。

click / typer：装饰器风格，代码更简洁。

结构：main.py 只解析参数、加载配置、调用 services 中的主函数。

常用模式：--config 指定配置文件，命令行参数覆盖配置值。

子命令示例：python cli.py train --epochs 10 和 python cli.py eval --model model.pkl。

# 9. 代码格式与检查

现代工具链：

ruff：替代 flake8、isort、autoflake，极快。ruff check . --fix + ruff format .

mypy：静态类型检查（可选，推荐）。

pre-commit：在 git commit 前自动运行以上检查。

配置集中：所有工具的配置写在 pyproject.toml 中。

CI：GitHub Actions 等自动运行 ruff 和 mypy，不通过则禁止合并。

目标：统一风格，自动发现低级错误。

# 10. 打包与发布

现代标准：pyproject.toml（PEP 621）声明元数据，构建后端用 setuptools 或 hatchling。

推荐目录布局：src/包名/ 下放源码。

安装方式：

pip install -e .：可编辑模式（开发）。

pip install .：普通安装。

构建分发包：python -m build → 生成 dist/*.whl 和 *.tar.gz。

发布：twine upload dist/* 上传到 PyPI。

替代方案：poetry 一站式管理（poetry build + poetry publish）。

版本号：语义化版本 MAJOR.MINOR.PATCH，单一来源（写在 __init__.py 或 pyproject.toml）。