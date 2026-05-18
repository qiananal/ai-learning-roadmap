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