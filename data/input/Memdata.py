import numpy as np
import os
def gen_random():
    # 要生成的随机整数的数量
    num_integers = 50000

    # 生成随机整数
    random_integers = np.random.randint(low=-2**31, high=2**31, size=num_integers, dtype=np.int32)

    # 获取当前脚本所在的目录
    current_directory =os.path.dirname(__file__)

    # 构建文件路径
    file_path = os.path.join(current_directory, 'random_integers.txt')

    # 将整数写入文件
    with open(file_path, 'w') as file:
        for number in random_integers:
            file.write(f"{number}\n")


def gen_sequence():
    # 要生成的顺序整数的数量
    num_integers = 1000000



    # 获取当前脚本所在的目录
    current_directory =os.path.dirname(__file__)

    # 构建文件路径
    file_path = os.path.join(current_directory, 'Memdata.txt')

    # 将整数写入文件
    with open(file_path, 'w') as file:
        for number in range(num_integers):
            file.write(f"{number}\n")


gen_sequence()