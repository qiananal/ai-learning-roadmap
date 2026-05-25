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


