4. 装饰器
一、装饰器原理 —— 用“给手机贴膜”来理解
你有一部 手机（原函数），它本来只能打电话。现在你想给它加一个 手机壳（装饰器），这样它既能打电话，又更耐摔。

装饰器的做法就是：
做一个“贴膜工人”（装饰器函数）
工人把手机拿进去，贴好膜，再还给你一个“带壳的手机”（新函数）
你用这个新手机，既有原功能，又多了一些东西。
代码示例：
*
# 这是一个装饰器（贴膜工人）

*def add_phone_case(func):      # func 是原来的手机
    def wrapper():             # wrapper 是带壳的手机
        print("手机壳已套上")   # 加的额外功能
        func()                 # 原来的打电话功能
        print("手机壳已取下")   # 也可以再加别的
    return wrapper             # 返回带壳的手机*

# 这是一部原始手机（原函数）
def call():
    print("正在打电话...")

# 让贴膜工人加工一下
call_with_case = add_phone_case(call)

# 使用带壳的手机
call_with_case()

执行过程：

call_with_case() 调用新工具。

进入 new_func：

打印“手机壳已套上”

执行 original_func() → 此时 original_func 就是原来的 call，所以打印“正在打电话...”

打印“手机壳已取下”

输出：

text
手机壳已套上
正在打电话...
手机壳已取下

Python 的快捷写法（@语法糖）：
# 1. 装饰器定义（完全一样）
def add_phone_case(func):
    def wrapper():
        print("手机壳已套上")
        func()
        print("手机壳已取下")
    return wrapper

# 2. 使用 @ 语法直接装饰 call 函数
@add_phone_case          # 这行就相当于 call = add_phone_case(call)
def call():
    print("正在打电话...")

# 3. 直接调用 call() 即可，它已经是套壳后的函数了
call()

总结：
装饰器就是在不修改原函数代码的情况下，给函数增加一些新动作。*

格式：
def 我的装饰器(原函数):
    def 包装函数():
        # 前额外动作
        原函数()
        # 后额外动作
    return 包装函数

@我的装饰器
def 要装饰的函数():
    pass