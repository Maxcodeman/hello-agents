from dotenv import load_dotenv
# 加载 .env 文件中的环境变量
load_dotenv()

import os, re
from tavily import TavilyClient
from typing import Dict, Any

def search(query: str) -> str:
    """
    一个基于Tavily的实战网页搜索引擎工具。
    它会智能地解析搜索结果，优先返回高质量的内容摘要。
    """
    print(f"🔍 正在执行 [Tavily] 网页搜索: {query}")
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "错误：TAVILY_API_KEY 未在 .env 文件中配置。"

        client = TavilyClient(api_key=api_key)
        results = client.search(
            query=query,
            search_depth="advanced",   # "basic" 或 "advanced"，advanced 会进行更深入的搜索
            max_results=5,
            include_answer=True,       # 包含一个总结性的短答案
            include_raw_content=False,
        )

        parts = []

        # 优先返回 Tavily 自动生成的总结答案
        if results.get("answer"):
            parts.append(f"📝 总结: {results['answer']}")

        # 返回搜索结果摘要
        if results.get("results"):
            for i, res in enumerate(results["results"][:5]):
                title = res.get("title", "")
                content = res.get("content", "")
                url = res.get("url", "")
                parts.append(f"[{i+1}] {title}\n{content}\n🔗 {url}")

        if parts:
            return "\n\n".join(parts)

        return f"对不起，没有找到关于 '{query}' 的信息。"

    except Exception as e:
        return f"搜索时发生错误: {e}"

def calulate(expression: str) -> str:
    """
    一个安全的计算器工具，用于计算复杂的数学表达式。
    支持加(+)、减(-)、乘(×)、除(÷)、幂(^)、括号等运算。
    """
    print(f"🧮 正在执行 [计算器] 计算: {expression}")
    try:
        # 预处理：替换数学符号和清理输入
        clean = expression.strip()
        # 移除末尾的 "=?" 或 "=" 或 "？" 等后缀
        clean = re.sub(r"[＝=]\s*\??\s*$", "", clean)
        # 替换各种数学符号（× ÷ ^ 等 → * / **）
        replacements = {
            "×": "*", "✕": "*", "✖": "*", "X": "*", "x": "*",
            "÷": "/", "➗": "/",
            "－": "-", "–": "-", "—": "-", "−": "-",
            "＋": "+",
            "（": "(", "）": ")",
            "^": "**",
        }
        for old, new in replacements.items():
            clean = clean.replace(old, new)
        clean = clean.replace(" ", "")  # 最后再去掉所有空格

        # 安全检查：只允许数字、运算符、括号、小数点
        if not re.match(r'^[\d\+\-\*/\(\)\.\*]+$', clean):
            return f"错误：表达式包含不支持的字符。请使用数字和 +、-、×、÷ 运算符。"

        # 安全执行
        result = eval(clean, {"__builtins__": {}}, {})
        return f"{expression.strip().rstrip('=?？')} = {result}"

    except ZeroDivisionError:
        return f"错误：表达式 '{expression}' 中存在除以零的操作。"
    except SyntaxError:
        return f"错误：表达式 '{expression}' 语法错误，请检查括号和运算符。"
    except Exception as e:
        return f"计算时发生错误: {e}"


class ToolExecutor:
    """
    一个工具执行器，负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向工具箱中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告：工具 '{name}' 已存在，将被覆盖。")
        
        self.tools[name] = {"description": description, "func": func}
        print(f"工具 '{name}' 已注册。")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取一个工具的执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串。
        """
        return "\n".join([
            f"- {name}: {info['description']}" 
            for name, info in self.tools.items()
        ])


# --- 工具初始化与使用示例 ---
if __name__ == '__main__':
    # 1. 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)

    # 3. 注册计算器工具
    calulate_description = "一个安全的数学计算器。当你需要执行数学运算时（如加减乘除、幂运算、括号运算），使用此工具。输入应为数学表达式，例如 '(123 + 456) × 789 / 12'。"
    toolExecutor.registerTool("Calculator", calulate_description, calulate)

    # 4. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 5. 测试搜索工具
    # print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    # tool_name = "Search"
    # tool_input = "英伟达最新的GPU型号是什么"
    #
    # tool_function = toolExecutor.getTool(tool_name)
    # if tool_function:
    #     observation = tool_function(tool_input)
    #     print("--- 观察 (Observation) ---")
    #     print(observation)
    # else:
    #     print(f"错误：未找到名为 '{tool_name}' 的工具。")

    # 6. 测试计算器工具
    print("\n--- 执行 Action: Calculator['(123 + 456) × 789 / 12 = ?'] ---")
    tool_name = "Calculator"
    tool_input = "(123 + 456) × 789 / 12 = ?"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        observation = tool_function(tool_input)
        print("--- 计算器输出 ---")
        print(observation)
    else:
        print(f"错误：未找到名为 '{tool_name}' 的工具。")
