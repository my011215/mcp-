# -*- coding: utf-8 -*-
"""
文件读取 MCP 服务器
提供文件内容读取功能
"""
import os
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP

# 初始化 FastMCP 服务器
mcp = FastMCP("VulnReproductionTool")


@mcp.tool()
def read_file_content(file_path: str) -> Dict[str, Any]:
    """
    读取文件内容工具

    Args:
        file_path: 文件路径

    Returns:
        Dict包含文件内容和状态信息
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"文件不存在: {file_path}",
                "content": ""
            }

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "file_size": len(content)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件失败: {str(e)}",
            "content": ""
        }


if __name__ == "__main__":
    print("服务器启动中...")
    mcp.run(transport='stdio')