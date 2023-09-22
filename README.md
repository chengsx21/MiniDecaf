# MiniDecaf Python 框架

## 依赖

- **Python >= 3.9**
- requirements.txt 里的 python 库，包括 ply 和 argparse。
- RISC-V 运行环境（参见实验指导书）

## 下载 & 配置 & 运行
以 python3.9 为例，其他版本请自行修改。
```
# 下载
git clone --recursive git@github.com:decaf-lang/minidecaf-2023.git
# 配置
cd minidecaf-2023
python3.9 -m pip install -U pip #  升级Python3的默认包管理系统
python3.9 -m pip install -r requirements.txt  ## 安装ply argparse软件包
# 运行编译器
python3.9 main.py --input <testcase.c> [--riscv/--tac/--parse] 
# 例1：编译 return_0.c，并生成AST（抽象语法树）
python3.9 main.py --input minidecaf-tests/testcases/step1/return_0.c --parse
Generating LALR tables
program [
  function [
    type(int)
    identifier(main)
    block [
      return [
        int(0)
      ]
    ]
  ]
]

# 例2，编译 return_0.c，并生成TAC（三地址码）
 python3.9 main.py --input minidecaf-tests/testcases/step1/return_0.c --tac
FUNCTION<main>:
    _T0 = 0
    return _T0

# 例3，编译 return_0.c，并生成RISC-V 32 汇编代码
 python3.9 main.py --input minidecaf-tests/testcases/step1/return_0.c --riscv
    .text
    .global main

main:
    # start of prologue
    addi sp, sp, -48
    # end of prologue

    # start of body
    li t0, 0
    mv a0, t0
    j main_exit
    # end of body

main_exit:
    # start of epilogue
    addi sp, sp, 48
    # end of epilogue

    ret
```

各参数意义如下：

| 参数 | 含义 |
| --- | --- |
| `input` | 输入的 Minidecaf 代码位置 |
| `riscv` | 输出 RISC-V 汇编 |
| `tac` | 输出三地址码 |
| `parse` | 输出抽象语法树 |

## 代码结构

```
minidecaf/
    frontend/       前端（与中端）
        ast/        语法树定义
        lexer/      词法分析
        parser/     语法分析
        type/       类型定义
        symbol/     符号定义
        scope/      作用域定义
        typecheck/  语义分析（符号表构建、类型检查）
        tacgen/     中间代码 TAC 生成
    backend/        后端
        dataflow/   数据流分析
        reg/        寄存器分配
        riscv/      RISC-V 平台相关
    utils/          底层类
        label/      标签定义
        tac/        TAC 定义和基本类
```
