class Vehicle:            # 父类
    def __init__(self, brand):
        self.brand = brand
        self.__fuel = 0   # 私有燃料

    def add_fuel(self, amount):
        if amount > 0:
            self.__fuel += amount
            print(f"加了 {amount} 升油，现在油量：{self.__fuel}")

    def drive(self):      # 多态方法，子类自己实现
        pass

class Car(Vehicle):
    def drive(self):
        print(f"{self.brand} 汽车 开动，四个轮子跑得快")

class Bike(Vehicle):
    def drive(self):
        print(f"{self.brand} 自行车 蹬脚踏板，两个轮子慢慢骑")

# 使用
my_car = Car("比亚迪")
my_car.add_fuel(20)    # 封装：通过方法加油
my_car.drive()         # 多态：输出“比亚迪 汽车 开动...”

my_bike = Bike("凤凰")
# my_bike.add_fuel(5)  # 自行车没有油，这句会报错，因为没有 add_fuel 方法（自行车没有继承它，或者我们没写）
# 不过自行车可以有自己的加力方式，这里只是展示
my_bike.drive()        # 输出“凤凰 自行车 蹬脚踏板...”

# 注意：Bike 类没有定义 add_fuel，所以调用会错，这没关系，说明继承是可以选择性的。


