## threading.Lock() 线程锁与多线程并发读写冲突

### 1. 为什么会有“并发读写冲突”？（从记账的故事说起）

假设你和你的合伙人一起开了一家水果店，店里只有一本纸质的“账本”（相当于我们的 user_portfolio.json），里面记录着当前的可用资金。

📊 账本初始状态：
```text
{ "account_balance": 100.0 }
```

有一天，发生了这样一幕：

合伙人 A 准备记账：他想“买入 20 块钱的草莓”。他拿起账本看了一眼，心里默念：“哦，现在还剩 100 块。”（读操作，耗时 $1\text{ms}$）。

合伙人 B 突然插队：就在合伙人 A 刚看清 100 块、还没来得及落笔的这 $1\text{ms}$ 间隙里，合伙人 B 突然冲过来，说他“卖出了 50 块钱的橙子”。他也看了一眼账本：“哦，现在剩 100 块。”

合伙人 B 落笔写入：合伙人 B 算了一下 $100 + 50 = 150$，迅速在账本上写下 $150$ 并合上账本（写覆盖）。

合伙人 A 回过神落笔：此时合伙人 A 回过神来，他脑子里记住的余额还是第 1 步看到的 100 块！他算了一下 $100 - 20 = 80$，于是他重新翻开账本，直接写下 $80$ 并合上账本。

#### 🚨 物理崩坏发生：

水果店原本应该是：$100（初始） + 50（卖橙） - 20（买草莓） = 130$ 块。
但现在，账本上的数字变成了 80 块！整整 50 块钱凭空消失了！

这就是经典的 竞态条件（Race Condition）。在计算机中，前台用户在 Streamlit 上点击“买入/卖出股票”更新资产，和后台守护线程定时请求通达信更新市值并写回文件，就是这两个并行的“合伙人”。如果不加锁，你的钱就会在系统的脏写中凭空蒸发！

### 2. ⚠️ 面试天坑：既然 Python 有 GIL 锁，为什么还要用 threading.Lock？

这是全网 Python 开发面试中通过率最低、也是最能区分“调包侠”与“科班正规军”的一个硬核考点。

#### 💡 核心考点拆解：

##### 1. GIL（Global Interpreter Lock，全局解释器锁）是什么？

GIL 是 Python 解释器（CPython）在 C 语言底层 挂的一把安全锁。它的存在是为了保证：在任意一个微小的物理时间片内，只有一个 CPU 核心在执行 Python 的字节码指令。它保护的是 Python 解释器本身的内存安全（防止垃圾回收 GC 机制崩坏），而不是你的业务代码安全！

##### 2. 为什么 GIL 无法保护我们的文件和业务数据？

因为 “读文件 $\rightarrow$ 修改数据 $\rightarrow$ 写回文件” 在 Python 底层并不是一个“一句话就能干完”的原子操作。

当你在 Python 中写下：
```text
portfolio["account_balance"] -= 20.0
```

在 Python 底层，这行代码会被编译成 4 条字节码指令：
```text
1. LOAD_FAST (把可用现金余额读进 CPU 寄存器)
2. LOAD_CONST (加载数字 20.0)
3. BINARY_SUBTRACT (在 CPU 中做减法运算)
4. STORE_FAST (将算好的结果写回内存)
```

操作系统和 GIL 的无情切片：

当线程 A 刚执行完第 1 步（把 100 块读进寄存器），GIL 的时间片到了。操作系统会强制剥夺线程 A 的执行权，把控制权交给线程 B。线程 B 同样执行了这 4 步，把余额改成了 150。当线程 A 重新拿回执行权时，它直接从第 2 步（寄存器里还是100）开始执行减法，算完写回，直接覆盖了线程 B 的努力。

#### 🎯 黄金结论：

GIL 保证的是： 在你执行第 1 步指令的这几个纳秒里，别的人不准来抢 CPU。

threading.Lock() 保证的是： 在我把这 4 步指令全部执行完，并且把数据稳稳当当地写回硬盘文件之前，任何人都不能碰这个账本！

### 3. 🛡️ 工业级防爆代码：用 Python 实现一个高可用的读写安全舱

在你的 core_tools.py 内部，面对前后台多线程高频更新 user_portfolio.json 的隐患，你设计了以下这套绝对防脏读、防文件损坏的防御性代码：

```python
import json
import os
import threading
import time

# 1. 🔒 声明一个全局并发硬锁
PORTFOLIO_FILE_LOCK = threading.Lock()
PORTFOLIO_FILE_PATH = "data/user_portfolio.json"

def safe_update_portfolio(action: str, stock_code: str, price: float, quantity: int) -> dict:
    """
    【工业级并发安全记账舱】
    通过显式线程锁 (threading.Lock)，彻底消除了脏读、写覆盖以及高频写写冲突。
    """
    # 2. 🛡️ 强制加锁排队
    # with 语句会在进入时自动调用 PORTFOLIO_FILE_LOCK.acquire()
    # 无论中间发生什么报错崩溃，退出时都会自动调用 PORTFOLIO_FILE_LOCK.release()，绝不引发死锁！
    with PORTFOLIO_FILE_LOCK:
        print(f"🔒 [线程锁锁定] 线程 {threading.get_ident()} 抢占了账本，开始安全更新...")
        
        # 3. 防御性编程：如果账本文件损坏或不存在，初始化一个标准空账本
        if not os.path.exists(PORTFOLIO_FILE_PATH) or os.path.getsize(PORTFOLIO_FILE_PATH) == 0:
            initial_data = {"account_balance": 500000.0, "holdings": []}
            with open(PORTFOLIO_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=4)
        
        # 4. 读操作（此时哪怕后台线程想来读，也会被锁死在 blocking 状态，防止读取到写到一半的“脏数据”）
        try:
            with open(PORTFOLIO_FILE_PATH, "r", encoding="utf-8") as f:
                portfolio = json.load(f)
        except json.JSONDecodeError:
            # 🩺 容错自愈：万一之前由于外部停电或强行终止导致文件半写损坏，启动降级恢复
            print("🚨 [账本损坏警告] 发现 JSON 数据格式崩溃，启动自动重建防线！")
            portfolio = {"account_balance": 500000.0, "holdings": []}

        # 5. 纯内存逻辑计算
        balance = float(portfolio.get("account_balance", 0.0))
        holdings = portfolio.get("holdings", [])
        total_cost = price * quantity
        
        if action == "BUY":
            if balance < total_cost:
                return {"status": "ERROR", "message": "账户资金不足！"}
            
            # 扣减现金，增加持仓
            portfolio["account_balance"] = round(balance - total_cost, 2)
            # 篇幅限制，此处省略具体的持仓成本均摊合并逻辑...
            holdings.append({"stock_code": stock_code, "buy_price": price, "quantity": quantity})
            
        elif action == "SELL":
            # 篇幅限制，此处省略卖出扣减持仓、增加现金逻辑...
            pass

        # 6. 写回物理文件
        # 🌟 核心防损坏操作：采用“先写临时文件，再原子替换”的方法，杜绝写了一半突然断网导致的 JSON 文件彻底损坏
        temp_file_path = PORTFOLIO_FILE_PATH + ".tmp"
        with open(temp_file_path, "w", encoding="utf-8") as f_temp:
            json.dump(portfolio, f_temp, ensure_ascii=False, indent=4)
        
        # 操作系统级的原子文件替换，完美免疫任何半写损坏
        os.replace(temp_file_path, PORTFOLIO_FILE_PATH)
        
        print(f"🔓 [线程锁释放] 线程 {threading.get_ident()} 安全落盘完毕，释放账本。")
        return {"status": "SUCCESS", "current_balance": portfolio["account_balance"]}

# ==========================================
# 🧪 仿真测试：开启 5 个并发线程同时疯狂改写账本
# ==========================================
def stress_test_concurrent_writes():
    threads = []
    for i in range(5):
        t = threading.Thread(
            target=safe_update_portfolio, 
            args=("BUY", "002594", 250.0, 100),
            name=f"Worker_Thread_{i}"
        )
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()

if __name__ == "__main__":
    stress_test_concurrent_writes()
```

### 4. 🧠 高频地狱考点：什么是“死锁（Deadlock）”？如何防范？

死锁是所有并发开发中最难调试的 Bug，也是面试官筛选高阶工程师的王牌考点。

#### 1. 什么是死锁？

简单来说就是：“两个保镖互相掐着对方的脖子，谁都不放手。”

线程 A 抢到了 锁 A（可用现金锁），准备去抢 锁 B（个股持仓锁）。

同一毫秒内，线程 B 抢到了 锁 B（个股持仓锁），准备去抢 锁 A（可用现金锁）。

结果：

线程 A 抱着锁 A 在等锁 B；线程 B 抱着锁 B 在等锁 A。两个线程同时进入无限期挂起状态（Blocked），系统瞬间死机卡死，不耗 CPU 但没有任何响应！

#### 2.项目使用的防范策略（面试时如何装高手？）：

严格限制锁的粒度：我的系统中尽量只用一把全局大锁，避免嵌套使用多把锁。

严格锁的申请顺序（Lock Ordering）：如果真的必须用多把锁，规定所有的线程必须严格按照先抢锁 A、后抢锁 B 的顺序去申请，彻底阻断环路等待。

使用带有超时退出的超时锁：绝对不用无限死等的 lock.acquire()，而是使用 lock.acquire(timeout=3.0)。3秒钟如果抢不到，说明可能发生了锁竞争或潜在死锁，直接抛出异常并熔断，退回安全状态。

### 🎯 5. 技术面试现场：面试官的“剥皮追问”你怎么接？

#### 追问 1：Python 既然有了 GIL 锁，为什么还要用 threading.Lock？

满分回答： “这是一个非常经典的误区。GIL 锁保护的是 CPython 解释器本身的内部状态安全（主要是防止垃圾回收的引用计数器在多线程下错乱导致内存泄漏），它并不是业务层面的数据锁。

GIL 只有在执行一条单步的字节码指令时是安全的。但是，我们业务层面对文件的修改，往往包含了‘读取文件数据、内存计算修改、写入物理磁盘’等多个步骤。

在这些步骤之间，Python 进程完全可能被操作系统强制剥夺执行权进行线程上下文切换。这就导致了‘读写覆盖（Race Condition）’和‘脏读（Dirty Read）’。

因此，我们必须使用业务层的 threading.Lock()，将整个‘读-改-写’的多步操作，强行封装成一个原子性的执行单元（Critical Section），才能保证多线程环境下的数据安全。”

#### 追问 2：如果两个线程并发去改写一个 JSON 文件，不加锁，底层到底会发生什么惨剧？

你的满分回答： > “底层会直接发生两类不可逆的物理故障：

第一类是 ‘数据丢失与覆盖’。当线程 A 还没将改写完的数据完全刷盘时，线程 B 捞出了老版本的数据，并在稍后写回，导致线程 A 的写入彻底丢失，账面余额发生错乱。

第二类是 ‘JSON 格式物理损坏（JSONDecodeError）’。在操作系统层面，写文件是一个向磁盘 I/O 缓冲区灌入字节流的过程。

如果线程 A 正在灌入 1024 字节的 JSON 字符串，中途 CPU 切给线程 B 强行写入 512 字节，这会导致磁盘缓冲区内的数据发生混杂，最终刷盘的文件长成像 { "account_balance": 100{ "stock_code" 这样被切成两截的畸形字符串。当系统下一次重新启动调用 json.load() 时，就会报出毁灭性的 Expecting value: line 1 column 1 异常，导致整个系统的财务账本彻底损毁。”