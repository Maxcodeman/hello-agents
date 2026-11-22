from hello_agents import ReflectionAgent, HelloAgentsLLM, ToolRegistry, Config, Message

MY_REFLECTION_PROMPT = ""

DEFAULT_PROMPTS = {
    "initial": """
请根据以下要求完成任务:

任务: {task}

请提供一个完整、准确的回答。
""",
    "reflect": """
请仔细审查以下回答，并找出可能的问题或改进空间:

# 原始任务:
{task}

# 当前回答:
{content}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。
""",
    "refine": """
请根据反馈意见改进你的回答:

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。
"""
}

from typing import Optional, List, Tuple
class MyReflectionAgent(ReflectionAgent):
    """
    重写Reflection Agent - 反思智能体
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        # tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 3,
        custom_prompt: Optional[str] = None
    ):
        super().__init__(name, llm, system_prompt, config)
        # self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.current_history: List[str] = []
        self.prompt_template = custom_prompt if custom_prompt else DEFAULT_PROMPTS
        print(f"✅ {name} 初始化完成，最大步数: {max_steps}")

    def run(self, input_text: str, **kwargs) -> str:
        """运行Reflection Agent"""
        print(f"\n--- 开始处理任务 ---\n任务: {input_text}")

        # --- 1. 初始执行 ---
        print("\n--- 正在进行初始尝试 ---")
        initial_prompt = self.prompt_template["initial"].format(task=input_text)
        initial_answer = self._get_llm_response(initial_prompt)
        print(f"初始尝试结果:\n{initial_answer}")
        self.memory.add_record("execution", initial_answer)

        for i in range(self.max_steps):
            print(f"\n--- 第 {i + 1}/{self.max_iterations} 轮迭代 ---")

            # 反思
            print("\n-> 正在进行反思...")
            last_answer = self.memory.get_last_execution()
            reflect_prompt = self.prompt_template["reflect"].format(task=input_text, content=last_answer)
            feedback = self._get_llm_response(reflect_prompt)
            print(f"反思结果:\n{feedback}")
            self.memory.add_record("reflection", feedback)

            # 检查是否需要停止
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                print("\n✅ 反思认为代码已无需改进，任务完成。")
                break

            # 优化
            print("\n-> 正在进行优化...")
            refine_prompt = self.prompt_template["refine"].format(task=input_text, last_attempt=last_answer, feedback=feedback)
            refine_answer = self._get_llm_response(refine_prompt)
            print(f"优化结果:\n{refine_answer}")
            self.memory.add_record("execution", refine_answer)

        final_answer = self.memory.get_last_execution()
        print(f"\n--- 运行结束 ---\n最终生成的答案:\n{final_answer}")
        return final_answer

    def _get_llm_response(self, prompt: str) -> str:
        """一个辅助方法，用于调用LLM并获取完整的流式响应。"""
        messages = [{"role": "user", "content": prompt}]
        # 确保能处理生成器可能返回None的情况
        response_text = self.llm.invoke(messages=messages) or ""
        return response_text