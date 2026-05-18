import argparse
#1. 召唤分拣怪兽
parser = argparse.ArgumentParser(description="草莓采摘分拣机")

#2. 规则：必须告诉我名字，可以选填数量，可选填熟没熟
parser.add_argument("name", type=str, help="草莓品种")
parser.add_argument("--count", type=int, default=1, help="数量")
parser.add_argument("--ripe", action="store_true", help="是否成熟")

#3. 闭上眼让怪兽分拣
args = parser.parse_args()

#4. 看看分拣出来的结果
print("--- 分拣报告 ---")
print(f"品种: {args.name}")
print(f"数量: {args.count}")
print(f"熟了吗: {args.ripe}")