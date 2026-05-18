封装、继承、多态：
1.封装 —— 把东西装进盒子里，只留按钮
代码例子：

我们做一个“存钱罐”类，里面的钱不能直接拿出来，只能通过“存钱”和“查余额”的方法来操作。
*class PiggyBank:
    def __init__(self):
        self.__money = 0          # __money 前面两个下划线，表示私有（藏起来）

    def save(self, amount):       # 存钱按钮
        if amount > 0:
            self.__money += amount
            print(f"存了 {amount} 元，余额：{self.__money}")

    def get_balance(self):        # 查余额按钮
        print(f"当前余额：{self.__money} 元")

# 使用存钱罐
my_bank = PiggyBank()
my_bank.save(10)      # 输出：存了 10 元，余额：10
my_bank.get_balance() # 输出：当前余额：10 元
# my_bank.__money     # 这句会报错，因为外面看不到私有钱*

2. 继承 —— 孩子像爸妈，但有自己的特点
代码例子：
做一个“动物”父类，再让“猫”和“狗”继承它。
*
class Animal:          # 父类
    def __init__(self, name):
        self.name = name

    def eat(self):
        print(f"{self.name} 正在吃东西")

# 猫继承动物
class Cat(Animal):
    def meow(self):     # 猫自己的方法
        print(f"{self.name} 喵喵叫")

# 狗继承动物
class Dog(Animal):
    def bark(self):     # 狗自己的方法
        print(f"{self.name} 汪汪叫")

# 使用
cat = Cat("咪咪")
cat.eat()     # 继承来的方法，输出：咪咪 正在吃东西
cat.meow()    # 自己的方法，输出：咪咪 喵喵叫

dog = Dog("旺财")
dog.eat()     # 继承来的，输出：旺财 正在吃东西
dog.bark()    # 自己的，输出：旺财 汪汪叫*

3. 多态 —— 同一个命令，不同反应
代码例子：
同样一个“叫”的方法，猫叫出“喵”，狗叫出“汪”。

*python
class Animal:
    def make_sound(self):
        pass   # 父类不写具体内容

class Cat(Animal):
    def make_sound(self):
        print("喵喵喵")

class Dog(Animal):
    def make_sound(self):
        print("汪汪汪")

# 写一个函数，接收任何动物，让它叫
def let_it_speak(animal):
    animal.make_sound()   # 不管传进来的是猫还是狗，都执行自己的叫声

cat = Cat()
dog = Dog()

let_it_speak(cat)   # 输出：喵喵喵
let_it_speak(dog)   # 输出：汪汪汪*

