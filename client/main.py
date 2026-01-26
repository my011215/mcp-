# -*- coding: utf-8 -*-
"""
智能数学计算 MCP 客户端 - 使用 Qwen 大模型自动推理调用工具
修复版本：解决Unicode编码问题
"""
import asyncio
import sys
import json
import os
import re
from typing import Dict, Any, List, Optional
from contextlib import AsyncExitStack
from openai import OpenAI

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


class SmartClient:
    """智能MCP客户端 - 使用Qwen大模型自动"""

    DEFAULT_API_KEY = "sk-ae1c06a8e9e241e398fe1e3ce8e7043e"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DEFAULT_MODEL_NAME = "qwen-plus-2025-07-28"

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME,
                 api_key: str = DEFAULT_API_KEY,
                 base_url: str = DEFAULT_BASE_URL):
        self.exit_stack = AsyncExitStack()
        self.session = None

        self.api_key = api_key or self.DEFAULT_API_KEY

        # 初始化OpenAI客户端
        self.ai_client = OpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

        self.model_name = model_name
        self.conversation_history = []
        self.available_tools = []

    def _clean_unicode_text(self, text: str) -> str:
        """清理文本中的异常Unicode字符"""
        if not text:
            return text

        # 替换或移除异常的Unicode字符
        # 保留常见的中文和ASCII字符
        cleaned = re.sub(r'[\ud800-\udfff]', '', text)  # 移除代理对字符
        cleaned = re.sub(r'[^\u0000-\uFFFF]', '', cleaned)  # 移除非BMP字符
        cleaned = cleaned.encode('utf-8', 'ignore').decode('utf-8')

        return cleaned

    def _clean_message_content(self, content):
        """清理消息内容"""
        if isinstance(content, str):
            return self._clean_unicode_text(content)
        elif isinstance(content, list):
            cleaned = []
            for item in content:
                if isinstance(item, dict) and 'text' in item:
                    item['text'] = self._clean_unicode_text(item['text'])
                cleaned.append(item)
            return cleaned
        return content

    def _clean_conversation_history(self):
        """清理对话历史中的异常字符"""
        cleaned_history = []
        for message in self.conversation_history:
            cleaned_message = message.copy()
            if 'content' in cleaned_message and cleaned_message['content']:
                cleaned_message['content'] = self._clean_message_content(cleaned_message['content'])
            cleaned_history.append(cleaned_message)
        self.conversation_history = cleaned_history

    async def connect_to_server(self, server_script_path: str):
        """连接到数学计算MCP服务器"""
        if not server_script_path.endswith('.py'):
            print("错误: 服务器脚本必须是 .py 文件")
            return False

        server_params = StdioServerParameters(
            command="uv",
            args=["run", server_script_path],
            env=None
        )

        print(f"正在连接到服务器: {server_script_path}...")

        try:
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.read_pipe, self.write_pipe = stdio_transport
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.read_pipe, self.write_pipe)
            )
            await self.session.initialize()

            await self._load_available_tools()
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _load_available_tools(self):
        """加载可用的工具"""
        try:
            response = await self.session.list_tools()
            self.available_tools = []

            for tool in response.tools:
                tool_info = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": self._clean_unicode_text(tool.description) if hasattr(tool,
                                                                                             'description') else f"执行{tool.name}操作",
                        "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                self.available_tools.append(tool_info)

            print(f"\n已加载 {len(self.available_tools)} 个工具:")
            for tool in self.available_tools:
                print(f"  • {tool['function']['name']}")
            print()

        except Exception as e:
            print(f"加载工具失败: {e}")
            self.available_tools = []

    async def _call_tool(self, tool_name: str, arguments: Dict) -> Dict[str, Any]:
        """调用工具并处理结果"""
        print(f"\n🤖 调用工具: {tool_name}({arguments})")

        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)

            if hasattr(result, 'content') and result.content:
                text_content = result.content[0]
                if hasattr(text_content, 'text'):
                    try:
                        tool_result = json.loads(text_content.text)
                        print(f"📊 工具调用结果: {tool_result.get('formatted', tool_result.get('result', '计算完成'))}")
                        return tool_result
                    except json.JSONDecodeError:
                        cleaned_text = self._clean_unicode_text(text_content.text)
                        print(f"📊 文本结果: {cleaned_text}")
                        return {"text": cleaned_text}

            return {"status": "success", "tool": tool_name}

        except Exception as e:
            print(f"工具调用失败: {e}")
            return {"status": "error", "tool": tool_name, "error": str(e)}

    async def _process_with_ai(self, user_query: str) -> str:
        """使用Qwen大模型处理用户查询"""
        print(f"\n🧠 AI分析中...")

        # 清理对话历史
        self._clean_conversation_history()

        # 清理用户输入
        cleaned_query = self._clean_unicode_text(user_query)

        # 准备消息
        messages = []

        # 添加上下文（如果有历史）
        if self.conversation_history:
            # 只保留最近的3条历史记录，避免过长
            recent_history = self.conversation_history[-6:]  # 3轮对话
            messages.extend(recent_history)

        # 添加当前查询
        messages.append({
            "role": "user",
            "content": cleaned_query
        })

        # 准备工具描述
        available_tools = []
        for tool_info in self.available_tools:
            # print(tool_info)
            tool_name = tool_info["function"]["name"]
            tool_description = tool_info["function"]["description"]
            parameters = tool_info["function"]["parameters"]

            # # 根据工具类型设置参数schema
            # if tool_name == "read_file_content":
            #     parameters = {
            #         "type": "object",
            #         "properties": {
            #             "file_path": {"type": "string", "description": "文件路径"}
            #         },
            #         "required": ["file_path"]
            #     }
            # else:
            #     parameters = {"type": "object", "properties": {}}

            available_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_description,
                    "parameters": parameters
                }
            })

        try:
            # 调用API
            print("发送给模型messages：", messages)
            print("发送给模型工具信息：", available_tools)
            response = self.ai_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=available_tools if available_tools else None,
                tool_choice="auto" if available_tools else None,
                extra_body={"enable_thinking": False}
            )

            message = response.choices[0].message

            # 清理AI回复
            if message.content:
                cleaned_content = self._clean_unicode_text(message.content)
                print(f"\n💭 AI回复: {cleaned_content}")

            # 处理工具调用
            if hasattr(message, 'tool_calls') and message.tool_calls:
                print("模型返回原始工具调用信息：", message.tool_calls)
                # 执行工具调用
                tool_results = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name

                    try:
                        # 解析参数
                        arguments_str = tool_call.function.arguments
                        if arguments_str:
                            # 清理参数字符串
                            arguments_str = self._clean_unicode_text(arguments_str)
                            arguments = json.loads(arguments_str)
                        else:
                            # 根据问题推断参数
                            arguments = ""

                        print(f"🔧 执行 {tool_name}，参数: {arguments}")

                        # 调用工具
                        tool_result = await self._call_tool(tool_name, arguments)
                        print("调用工具原始结果：", tool_result)

                        # 清理工具结果
                        cleaned_result = {}
                        for key, value in tool_result.items():
                            if isinstance(value, str):
                                cleaned_result[key] = self._clean_unicode_text(value)
                            else:
                                cleaned_result[key] = value

                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "result": cleaned_result
                        })

                    except Exception as e:
                        print(f"⚠️ 执行工具 {tool_name} 失败: {e}")
                        continue

                # 更新对话历史
                self.conversation_history.append({
                    "role": "user",
                    "content": cleaned_query
                })

                # 如果有工具调用结果，让AI总结
                if tool_results:
                    # 构造工具调用消息
                    tool_call_messages = []
                    for result in tool_results:
                        tool_call_messages.append({
                            "type": "function",
                            "function": result["name"],
                            "result": json.dumps(result["result"], ensure_ascii=False)
                        })

                    # 重新调用AI进行总结
                    summary_messages = messages.copy()
                    summary_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": self._clean_unicode_text(
                                        tc.function.arguments) if tc.function.arguments else "{}"
                                }
                            } for tc in message.tool_calls
                        ]
                    })

                    for result in tool_results:
                        summary_messages.append({
                            "role": "tool",
                            "tool_call_id": result["tool_call_id"],
                            "content": json.dumps(result["result"], ensure_ascii=False)
                        })

                    try:
                        print("再次发送给模型信息：", summary_messages)
                        summary_response = self.ai_client.chat.completions.create(
                            model=self.model_name,
                            messages=summary_messages,
                            extra_body={"enable_thinking": False}
                        )

                        summary = self._clean_unicode_text(summary_response.choices[0].message.content)
                        print(f"\n💡 总结: {summary}")

                        self.conversation_history.append({
                            "role": "assistant",
                            "content": summary
                        })

                        return summary
                    except Exception as e:
                        print(f"总结失败: {e}")
                        # 返回原始结果
                        result_texts = []
                        for result in tool_results:
                            tool_result = result["result"]
                            if "formatted" in tool_result:
                                result_texts.append(tool_result["formatted"])
                            elif "result" in tool_result:
                                result_texts.append(str(tool_result["result"]))

                        if result_texts:
                            final_result = "，".join(result_texts)
                            print(f"\n📊 最终结果: {final_result}")
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": final_result
                            })
                            return final_result

                return "计算完成"

            else:
                # 没有工具调用，直接返回AI回复
                print("没有工具调用，直接返回AI回复")
                if message.content:
                    cleaned_response = self._clean_unicode_text(message.content)
                    self.conversation_history.append({
                        "role": "user",
                        "content": cleaned_query
                    })
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": cleaned_response
                    })
                    return cleaned_response

            return "AI处理完成"

        except Exception as e:
            print(f"AI处理失败: {e}")
            return f"处理失败: {str(e)}"

    async def chat_mode(self):
        """进入智能聊天模式"""
        print("\n" + "=" * 50)
        print("🤖 数学计算客户端已启动！")
        print("💡 你可以用自然语言提问，例如：")
        print("   • '计算123+678等于多少'")
        print("   • '退出' 或 'quit' 结束对话")
        print("=" * 50 + "\n")

        # 重置对话历史，避免历史问题
        self.conversation_history = []

        while True:
            try:
                user_input = input("\n👤 你的问题: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['退出', 'quit', 'exit', 'q']:
                    print("\n再见！👋")
                    break

                # 使用AI处理查询
                response = await self._process_with_ai(user_input)
                print(f"\n💡 最终回答: {response}")

            except KeyboardInterrupt:
                print("\n\n会话被中断。")
                break
            except Exception as e:
                print(f"\n发生错误: {e}")
                import traceback
                traceback.print_exc()

    async def close(self):
        """关闭客户端连接"""
        try:
            await self.exit_stack.aclose()
            print("已关闭客户端连接")
        except Exception as e:
            print(f"关闭连接时发生错误: {e}")


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <server_script_path>")
        print("示例: python main.py math_server.py")
        return

    server_script_path = sys.argv[1]

    # 创建客户端
    client = SmartClient(
        model_name="qwen-plus-2025-07-28",
        api_key="sk-ae1c06a8e9e241e398fe1e3ce8e7043e",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    try:
        connected = await client.connect_to_server(server_script_path)
        if not connected:
            return

        print("\n" + "=" * 50)
        print("🤖 智能数学助手")
        print("=" * 50)

        await client.chat_mode()

    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行时发生错误: {e}")
        import traceback

        traceback.print_exc()