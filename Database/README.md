# 实战沙盒选择——SQLite

因为我们是在 Windows 本地开发，且目标是以最快的速度、零污染地掌握 SQL 数据库的底层增删改查核心命令。如果现在去配一个企业级的 MySQL，我们需要去 Windows 注册服务、配端口、配用户权限，大半天时间就全耗在装软件上了。

所以，我们选择大厂在嵌入式设备、边缘计算端（如自动驾驶车载电脑、农业无人机控制器、手机 App 内部）使用率 100% 的明星数据库：SQLite。

它最大的魔力在于：它不需要安装任何单独的数据库软件！ Python 官方直接内置了它的驱动。它运行时不需要开任何后台进程，所有的表、数据，都会变成你文件夹下一个普普通通的 .db 文件，但它支持 100% 标准的关系型数据库 SQL 语法。

## 新建一个没有任何业务代码的干净 Python 文件，名字叫 db_test.py。
```python
import sqlite3

# 1️⃣ 第一步：建连接
# 这行代码会在你当前文件夹下，凭空创造一个叫 "sandbox.db" 的储物柜文件
conn = sqlite3.connect("sandbox.db")

# 2️⃣ 第二步：拿皮尺（游标 Cursor）
# 游标就是你在数据库里指点江山的那根手指头，执行命令全靠它
cursor = conn.cursor()

# 3️⃣ 第三步：下达 SQL 军令（今天我们要先建一张表）
# 关系型数据库规矩大，存数据前，必须用 CREATE TABLE 语法把表的外壳（列名、类型）定死！
cursor.execute("""
CREATE TABLE IF NOT EXISTS test_strawberry (
    id TEXT PRIMARY KEY,        -- 第一列：名字叫 id，类型是文本，且是主键（不能重复）
    weight REAL,                -- 第二列：名字叫 weight，类型是实数/浮点数
    shape TEXT                  -- 第三列：名字叫 shape，类型是文本
);
""")

# 4️⃣ 第四步：签字画押，关闭大门
# 只有 commit 了，数据才真正写进硬盘；最后记得把门关上
conn.commit()
conn.close()

print("🎉 恭喜！你人生的第一个 SQL 数据库文件和数据表已经成功诞生！")

```
成功运行后，你会发现你的项目文件夹里凭空多出了一个叫 sandbox.db 的二进制文件。这就代表数据库引擎已经成功在你的硬盘里安家了。

# 如何用标准 SQL 语句“塞数据”？

在关系型数据库中，插入数据的标准语法长这样，它就像一个严丝合缝的对齐游戏：

```SQL
INSERT INTO 表的名字 (列名1, 列名2, 列名3) VALUES (值1, 值2, 值3);
```
规矩一：前面的列名顺序，必须和后面的值顺序绝对一一对应。

规矩二：在 SQL 语法里，如果是文本（TEXT），必须用单引号 '...' 包起来；如果是数字（REAL/INTEGER），直接写就行。

# 如何用标准 SQL 语句“查数据”？

在关系型数据库中，读取数据的标准语法长这样：

```SQL
SELECT 列名1, 列名2 FROM 表的名字 WHERE 限制条件;
```
如果你想把箱子里所有的列名一股脑全部捞出来，SQL 给你提供了一个快捷极简的星号通配符（*）：SELECT * FROM test_strawberry;

如果你只想找特定的人，可以用 WHERE 加限制条件，比如：WHERE id = '001';

代码示例:
```python
import sqlite3

# 1️⃣ 第一步：建立连接，搬出我们的指点江山手游标
conn = sqlite3.connect("sandbox.db")
cursor = conn.cursor()

# 2️⃣ 第二步：下达 SELECT 查询军令
# 用 * 代表把 id, weight, shape 三列全要了，并且精准拦截 id 叫 '001' 的这一行
cursor.execute("SELECT * FROM test_strawberry WHERE id = '001';")

# 3️⃣ 第三步：核心动作！伸手把查到的数据拿过来（fetchall / fetchone）
# execute 只是让游标指针指到了那里，我们需要用 fetchone() 真正把这一行数据“抓”到 Python 变量里
row = cursor.fetchone()

# 4️⃣ 第四步：关闭大门
conn.close()

# 5️⃣ 看看抓出来的东西长啥样
print("📥 数据库密室里吐出来的原始数据是：", row)

if row:
    # row 是一个标准的 Python 元组 (Tuple)
    print(f"🍓 提取成功 -> 草莓编号: {row[0]}, 重量: {row[1]}g, 形状: {row[2]}")
else:
    print("⚠️ 数据库空空如也，没找到该编号的草莓！")
```
# 多数据联动与条件大筛选

为了让你在本地开发机上真刀真枪地体会到“从几万条数据里瞬间过滤出次品”的爽快感，我们需要让我们的沙盒里多住进几颗不同的草莓。

现在，我们要在你的 sandbox.db 里同时塞入 3 颗性格迥异的草莓，然后用你刚刚学会的 WHERE ... OR ... 语法把它们过滤出来。

🛠️ 上机互动演练：批量塞入并过滤
请打开你的 db_test.py，把里面的代码清空，换成下面这段“多样本插入与高级筛选综合演练”的代码。请仔细阅读我写在里面的每一行注释：

```Python
import sqlite3

# 1️⃣ 第一步：建连接，拿手游标
conn = sqlite3.connect("sandbox.db")
cursor = conn.cursor()

# 2️⃣ 第二步：为了防止重复运行报错，我们每次运行前，先清空这张旧表（大厂测试常用技巧）
cursor.execute("DELETE FROM test_strawberry;")

# 3️⃣ 第三步：连续塞入 3 颗不同的草莓数据（A级、B级、超重畸形果）
# 样本 001：完美的锥形小草莓 (12.5g)
cursor.execute("INSERT INTO test_strawberry (id, weight, shape) VALUES ('001', 12.5, 'Cone');")
# 样本 002：稍大一点的畸形草莓 (18.2g)
cursor.execute("INSERT INTO test_strawberry (id, weight, shape) VALUES ('002', 18.2, 'Wedge');")
# 样本 003：超级巨大的完美特级草莓 (32.4g)
cursor.execute("INSERT INTO test_strawberry (id, weight, shape) VALUES ('003', 32.4, 'Cone');")

conn.commit() # 签字画押，3颗草莓落盘！

# 4️⃣ 第四步：下达你刚刚写出的高级筛选军令！
# 任务：筛选出【重量 > 20.0g】或者【形状是畸形 Wedge】的所有草莓
sql_query = "SELECT * FROM test_strawberry WHERE weight > 20.0 OR shape = 'Wedge';"
cursor.execute(sql_query)

# 5️⃣ 第五步：抓取所有符合条件的结果
# 注意：之前我们只抓一个用 fetchone()，现在符合条件的可能有多行，必须用 fetchall() 抓取一个列表！
all_rows = cursor.fetchall()

# 6️⃣ 关闭大门
conn.close()

# 7️⃣ 打印看结果
print("📥 经过高级 SQL 筛选后，符合次品或特级特征的草莓有：")
for row in all_rows:
    print(f"🎯 命中目标 -> 编号: {row[0]}, 重量: {row[1]}g, 形状: {row[2]}")
```

# 终极缝合：把 SQLite 焊进你的 hetero-multimodal-service 项目
既然你已经通过本地沙盒彻底吃透了建表、插入、查询的底层逻辑，那现在我们就要遵守承诺：不再无脑复制粘贴，而是让你清清楚楚、明明白白地看着我们是怎么把数据库组件优雅地缝进你的真实草莓项目的。

我们在真正的 app/main.py 里，只需要做 3 个极简动作：

## 🛠️ 动作一：在最顶层，创建“常驻项目”的数据库大表
原本在 lifespan 启动时，我们用 pandas 把 Excel 读进了内存。现在，我们在这个地方顺便把数据库连接上，并下一道标准的建表军令（CREATE TABLE）。

请打开你的 app/main.py，找到 async def lifespan 里面读取 Excel 的那段代码（大约在第 55 行），在它的正下方，加入我们的数据库建表初始化代码。

你要加入的动作长这样（请理解每一行）：

```Python
    # ---------------- 🌟 动作一：初始化我们的工业级 SQLite 质检大数据库 ----------------
    db_path = os.path.join(BASE_DIR, "data_file", "gamut_production.db")
    try:
        # 连接数据库（如果不存在，会自动在 data_file 目录下新建 gamut_production.db）
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 建立一张完全体的、具备持久化能力的质检大表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS strawberry_eval_records (
            strawberry_id TEXT PRIMARY KEY,        -- 草莓唯一编号 (主键，防重复)
            file_name TEXT,                       -- 上传的点云文件名
            predicted_grade TEXT,                 -- 神经网络预测形状级别
            predicted_weight REAL,                -- 神经网络预测重量
            true_grade TEXT,                      -- 表格记录的真实形状
            true_weight REAL,                     -- 表格记录的真实重量
            absolute_error REAL,                  -- 系统计算出的绝对误差
            llm_diagnostic_report TEXT            -- 大模型现场手写写的专家诊断报告
        );
        """)
        conn.commit()
        conn.close()
        
        # 把数据库路径存入内存储物柜，方便后面的接口直接调用
        ml_models["db_path"] = db_path
        logger.info("🗄️ [SQLite 数据库] 工业级持久化质检大表初始化/连接成功！")
    except Exception as db_init_error:
        logger.error(f"❌ [SQLite 数据库] 初始化失败: {str(db_init_error)}")

```

## 🛠️ 动作二：在路由函数最后，把数据持久化（INSERT）
正如你刚刚所说，在 /predict/3d 算出误差、大模型写完报告之后，立刻执行插入。

请在 app/main.py 里往下翻，找到 /predict/3d 接口的末尾，在 return 返回给前端之前（大约在第 155 行），把数据死死地焊进硬盘里。

你要加入的动作长这样（请理解每一行）：

```Python
        # ==================== 🌟 动作二：将本次实验的全部战果焊进 SQLite 数据库 ====================
        if "db_path" in ml_models:
            try:
                conn = sqlite3.connect(ml_models["db_path"])
                cursor = conn.cursor()
                
                # 采用大厂标准的 UPSERT (INSERT OR REPLACE) 语法：
                # 如果这个草莓编号是第一次检测，直接塞入；如果是重复检测，直接用最新的预测和报告覆盖它！
                db_sql = """
                INSERT OR REPLACE INTO strawberry_eval_records 
                (strawberry_id, file_name, predicted_grade, predicted_weight, true_grade, true_weight, absolute_error, llm_diagnostic_report)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """
                
                # 安全地把我们热乎乎的变量值，一一对齐填坑塞进去
                cursor.execute(db_sql, (
                    strawberry_id, 
                    file.filename, 
                    final_grade, 
                    round(final_weight, 3), 
                    true_shape, 
                    true_weight if isinstance(true_weight, (int, float)) else None, 
                    weight_error if isinstance(weight_error, (int, float)) else None, 
                    expert_report
                ))
                conn.commit()
                conn.close()
                logger.info(f"💾 [数据落盘成功] 样本 {strawberry_id} 的全链路多模态指标已被持久化写入数据库！")
            except Exception as db_insert_error:
                logger.error(f"❌ [数据落盘失败] 原因: {str(db_insert_error)}")
        # ===================================================================================
```

## 🛠️ 动作三：开辟全新的“工人历史记录查询通道”（SELECT）
既然数据都进去了，工人们在网页上怎么看呢？我们顺手在代码最底部，增加一个全新的、专门用来给车间主管和导师展示历史数据的 GET /history 接口。

请在你的 app/main.py 的最最最底部（在 if __name__ == "__main__": 的正上方），另起一行，用你最熟悉的 SELECT 语法，为网关开辟查询大门：

```Python
# ==================== 🌟 动作三：开辟全新的历史大盘数据 SELECT 查询通道 ====================
@app.get("/history", summary="从 SQLite 数据库捞出历史上所有不合格的质检诊断记录")
async def get_history(min_error: float = 0.0):
    """
    车间主管和导师专用的监控接口：
    可以通过输入 min_error 参数（比如输入 2.0），一键捞出历史上所有绝对误差大于 2g 的糟糕预测记录！
    """
    if "db_path" not in ml_models:
        raise HTTPException(status_code=500, detail="数据库未正常连接")
        
    try:
        conn = sqlite3.connect(ml_models["db_path"])
        cursor = conn.cursor()
        
        # 熟练运用你刚刚学到的 SELECT * FROM ... WHERE ... 语法
        # 动态找出绝对误差大于用户输入阈值的所有历史记录，并按照误差从大到小排序（DESC）
        sql_query = "SELECT * FROM strawberry_eval_records WHERE absolute_error >= ? ORDER BY absolute_error DESC;"
        cursor.execute(sql_query, (min_error,))
        
        all_logs = cursor.fetchall()
        conn.close()
        
        # 把数据库里的规矩元组，打包成漂亮的人类大白话字典列表返回给网页
        history_list = []
        for row in all_logs:
            history_list.append({
                "strawberry_id": row[0],
                "file_name": row[1],
                "predicted_metrics": {"grade": row[2], "weight_grams": row[3]},
                "ground_truth_metrics": {"true_grade": row[4], "true_weight_grams": row[5]},
                "absolute_error_grams": row[6],
                "llm_expert_report": row[7]
            })
            
        return {
            "status": "success",
            "total_records_found": len(history_list),
            "filtering_criteria": f"absolute_error >= {min_error}g",
            "data": history_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取历史数据库失败: {str(e)}")
```

🚀 终极涅槃点火，见证工业闭环！
因为你在代码最顶上已经加上了 import sqlite3（Python 内置），所以不需要额外 pip 任何东西。

现在，在你的终端里最后一次骄傲地拉起大闸：

```PowerShell

python main.py
```

看着终端里闪过这行惊艳的日志：🗄️ [SQLite 数据库] 工业级持久化质检大表初始化/连接成功！

打开浏览器访问 /docs 页面，再次上传你的 strawberry001.ply 并 Execute！

返回成功后，刷新你的 Swagger 网页。你会神奇地发现，网页上凭空多出了一个蓝色的 GET /history 接口！

点击它，展开 Try it out，在 min_error 里输入 0.0，然后点击 Execute。

这一瞬间，你会看到你刚刚上传的那颗草莓、它的预测克数、绝对误差、以及大模型现场手写的质检指南，全部整整齐齐地以标准数据库报表的形式，被你用 SELECT 语法完美地从硬盘里召唤了出来！


# SQL 数据库专属超细复盘

## 1. 核心招式语法与项目实例对照表


## 2. Python 操作数据库的“标准四部曲”底层原理
我们在 main.py 和 app_dashboard.py 里，每次碰数据库，都雷打不动地执行了以下代码流程。面试官非常看重你是否懂这四步的底层 I/O 逻辑

```python
# 1. 建立连接 (Connection)
conn = sqlite3.connect("gamut_production.db") 
# 原理：在 Python 进程与硬盘的 .db 二进制文件之间，拉起一条专属的数据传输高架桥。

# 2. 铸造游标 (Cursor)
cursor = conn.cursor()
# 原理：游标就是你在数据库里指点江山的那根“黄金手指头”。SQL 语句是一串文本，Python 无法直接执行，必须把这串文本套在游标手指头上，送进高架桥。

# 3. 执行军令 (Execute)
cursor.execute("SELECT * FROM ... WHERE id = ?;", (strawberry_id,))
# 原理：让手指头在数据库里划定范围、翻箱倒柜。
# 企业级防线：严禁使用字符串拼接（f"id='{id}'"），必须用 ? 占位符元组传参！大厂叫防止“SQL注入攻击（SQL Injection）”。

# 4. 签字画押并关闭 (Commit & Close)
conn.commit()
conn.close()
# 原理：执行完写操作（INSERT/UPDATE）后，数据其实还悬浮在内存缓冲区。只有执行 commit()，操作系统才会把数据狠狠砸进硬盘。最后执行 close() 拆掉高架桥，释放内存。
```

## 3. SQL 实际会遇到的企业级生产问题

### 问题：数据库锁死异常（database is locked）

真实场景：流水线高频开工，FastAPI 一秒钟写 50 次，这时候你刚好在大屏上点了一下“确认一键校准真值”触发了 UPDATE。

工程原因：SQLite 是轻量级数据库，为了保证数据不写烂，它写数据时会拉起“文件级排他锁（Exclusive Lock）”。当大屏占用锁时，FastAPI 进不去，超时后就会直接抛出报错拒绝服务。

大厂避坑：在本地初始化连接时，必须加上自旋等待参数：sqlite3.connect(DB_PATH, timeout=20.0)。这代表让抢不到锁的进程在门口乖乖站队等候 20 秒，而不是当场崩溃。如果业务量进一步飙升，则必须将数据库平滑迁移到支持“行级锁（Row-level Lock）”的工业级 MySQL 或 PostgreSQL 上。



# 高频面试拷问（Interview QA）
### Q1：在流水线高并发环境下，为什么用 INSERT OR REPLACE（UPSERT）而不是普通的 INSERT？

大厂业务痛点：若发生相机误扫、物理重传，同一颗草莓编号（主键 PRIMARY KEY）会触发唯一性冲突报错（IntegrityError）。若用普通 INSERT，后端网关会直接抛出 500 崩溃，导致流水线软件卡死、自动化停工。

高可用解法：INSERT OR REPLACE 保证了接口的幂等性（Idempotency）。主键冲突时，它会自动原子化地“擦除旧记录 + 覆盖写入新数据”，系统全天候不宕机。

### Q2：当 FastAPI 网关正在高频写入，大屏同时在执行 UPDATE 修改，高并发数据撞车了怎么弄？

SQLite 边缘端策略：SQLite 采用粗暴的文件级写锁（File Lock），写操作时锁死整个文件。

大厂后端需配置 busy_timeout 机制，让未抢到锁的进程自旋重试，防范 database is locked 异常。互联网大厂演进方案：线上系统会平滑迁移至 MySQL 或 PostgreSQL，利用行级锁（Row Lock）实现“你改你的 001，我插我的 002”，互不干扰。若同时改同一行，则引入基于 Version 版本号的乐观锁（Optimistic Locking），利用 CAS（Compare-And-Swap）机制实现无锁高并发控制。