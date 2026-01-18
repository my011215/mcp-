# -*- coding: utf-8 -*-
"""
数学计算 MCP 服务器
提供基本的加减乘除运算
"""
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP 服务器
mcp = FastMCP("math")


@mcp.tool()
def add(a: float, b: float) -> Dict[str, Any]:
    """
    计算两个数的和

    参数:
        a: 第一个数字
        b: 第二个数字

    返回:
        包含计算结果的字典
    """
    try:
        result = a + b
        return {
            "operation": "addition",
            "expression": f"{a} + {b}",
            "result": result,
            "formatted": f"{a} + {b} = {result}"
        }
    except Exception as e:
        return {
            "error": f"加法计算失败: {str(e)}",
            "operation": "addition"
        }


@mcp.tool()
def subtract(a: float, b: float) -> Dict[str, Any]:
    """
    计算两个数的差

    参数:
        a: 被减数
        b: 减数

    返回:
        包含计算结果的字典
    """
    try:
        result = a - b
        return {
            "operation": "subtraction",
            "expression": f"{a} - {b}",
            "result": result,
            "formatted": f"{a} - {b} = {result}"
        }
    except Exception as e:
        return {
            "error": f"减法计算失败: {str(e)}",
            "operation": "subtraction"
        }


@mcp.tool()
def multiply(a: float, b: float) -> Dict[str, Any]:
    """
    计算两个数的乘积

    参数:
        a: 第一个因数
        b: 第二个因数

    返回:
        包含计算结果的字典
    """
    try:
        result = a * b
        return {
            "operation": "multiplication",
            "expression": f"{a} × {b}",
            "result": result,
            "formatted": f"{a} × {b} = {result}"
        }
    except Exception as e:
        return {
            "error": f"乘法计算失败: {str(e)}",
            "operation": "multiplication"
        }


@mcp.tool()
def divide(a: float, b: float) -> Dict[str, Any]:
    """
    计算两个数的商

    参数:
        a: 被除数
        b: 除数 (不能为0)

    返回:
        包含计算结果的字典
    """
    try:
        if b == 0:
            return {
                "error": "除数不能为0",
                "operation": "division"
            }

        result = a / b
        return {
            "operation": "division",
            "expression": f"{a} ÷ {b}",
            "result": result,
            "formatted": f"{a} ÷ {b} = {result:.4f}"  # 保留4位小数
        }
    except Exception as e:
        return {
            "error": f"除法计算失败: {str(e)}",
            "operation": "division"
        }


@mcp.tool()
def power(base: float, exponent: float) -> Dict[str, Any]:
    """
    计算幂运算

    参数:
        base: 底数
        exponent: 指数

    返回:
        包含计算结果的字典
    """
    try:
        result = base ** exponent
        return {
            "operation": "power",
            "expression": f"{base}^{exponent}",
            "result": result,
            "formatted": f"{base}^{exponent} = {result}"
        }
    except Exception as e:
        return {
            "error": f"幂运算失败: {str(e)}",
            "operation": "power"
        }


@mcp.tool()
def square_root(number: float) -> Dict[str, Any]:
    """
    计算平方根

    参数:
        number: 非负数

    返回:
        包含计算结果的字典
    """
    try:
        if number < 0:
            return {
                "error": "不能对负数求平方根",
                "operation": "square_root"
            }

        import math
        result = math.sqrt(number)
        return {
            "operation": "square_root",
            "expression": f"√{number}",
            "result": result,
            "formatted": f"√{number} = {result:.4f}"
        }
    except Exception as e:
        return {
            "error": f"平方根计算失败: {str(e)}",
            "operation": "square_root"
        }


@mcp.tool()
def batch_calculate(operations: str) -> Dict[str, Any]:
    """
    批量执行多个计算

    参数:
        operations: 计算表达式，用分号分隔
                  示例: "2+3; 5*4; 10/2"

    返回:
        包含所有计算结果的字典
    """
    try:
        if not operations:
            return {
                "error": "请输入计算表达式",
                "operation": "batch_calculate"
            }

        # 分割表达式
        exp_list = [exp.strip() for exp in operations.split(';') if exp.strip()]
        results = []

        for exp in exp_list:
            try:
                # 安全地计算表达式
                result = eval(exp, {"__builtins__": {}}, {})
                results.append({
                    "expression": exp,
                    "result": result
                })
            except Exception as e:
                results.append({
                    "expression": exp,
                    "error": f"计算失败: {str(e)}"
                })

        return {
            "operation": "batch_calculate",
            "expressions": exp_list,
            "results": results,
            "total": len(results),
            "successful": sum(1 for r in results if "error" not in r)
        }
    except Exception as e:
        return {
            "error": f"批量计算失败: {str(e)}",
            "operation": "batch_calculate"
        }


if __name__ == "__main__":
    print("数学计算服务器启动中...")
    mcp.run(transport='stdio')