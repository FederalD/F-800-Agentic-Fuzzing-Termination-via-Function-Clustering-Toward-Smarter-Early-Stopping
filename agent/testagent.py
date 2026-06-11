import os
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage

# 建议的依赖版本，注意：由于langchain更新较快，具体版本可能需要调整
# pip install langchain==0.3.25 langchain-community==0.3.26 langchain-openai==0.1.8
# 确保你的 deepseek-api 密钥已设置
os.environ["DEEPSEEK_API_KEY"] = "sk-7c3634d99eae479598d59200c2d5fde4"

# 1. 自定义工具函数
def get_weather(location: str) -> str:
    """
    根据城市名获取天气信息。
    在实际应用中，这里可以调用天气API。
    """
    # 模拟返回数据
    weather_data = {
        "北京": "北京今天天气晴朗，气温25℃，微风。",
        "上海": "上海今天多云转晴，气温23℃，东南风2级。",
        "广州": "广州今天有阵雨，气温28℃，湿度85%。",
        "深圳": "深圳今天晴间多云，气温26℃，微风。"
    }
    return weather_data.get(location, f"{location}的天气信息暂时无法获取。")

def calculate_expression(expression: str) -> str:
    """
    计算数学表达式。
    注意：此方法会直接执行字符串形式的数学表达式，生产环境请谨慎使用。
    """
    try:
        # 安全检查：只允许数字、基本运算符和括号
        allowed_chars = set('0123456789+-*/(). ')
        if not all(c in allowed_chars for c in expression):
            return "错误：表达式包含不允许的字符"
        
        result = eval(expression)
        return f"表达式 `{expression}` 的计算结果是: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

def temperature_converter(temp_c: str) -> str:
    """
    将摄氏度转换为华氏度。
    """
    try:
        celsius = float(temp_c)
        fahrenheit = (celsius * 9/5) + 32
        return f"{celsius}摄氏度 = {fahrenheit:.2f}华氏度"
    except ValueError:
        return "错误：请输入有效的温度数值"

# 2. 将函数封装成 LangChain Tool
tools = [
    Tool(
        name="Weather",
        func=get_weather,
        description="当需要查询某个城市的天气时使用此工具。输入应为城市名称。"
    ),
    Tool(
        name="Calculator",
        func=calculate_expression,
        description="当需要计算数学表达式时使用此工具，例如：'3 + 5 * 2'。输入应为有效的数学表达式字符串。"
    ),
    Tool(
        name="TemperatureConverter",
        func=temperature_converter,
        description="当需要将摄氏度转换为华氏度时使用此工具。输入应为温度数值。"
    )
]

# 3. 自定义系统提示词
CUSTOM_PREFIX = """你是一个智能助手，拥有以下工具可以使用：

{tools}

当你需要回答涉及以下领域的问题时，请务必使用相应的工具：
1. 天气查询 - 使用 Weather 工具
2. 数学计算 - 使用 Calculator 工具  
3. 温度转换 - 使用 TemperatureConverter 工具

请按照以下步骤思考：
1. 分析用户问题，确定是否需要使用工具
2. 如果需要使用工具，选择正确的工具并确定输入参数
3. 根据工具返回的结果给出最终答案
4. 如果工具执行失败，尝试其他方法或向用户说明情况

请用中文回答用户的问题。如果用户的问题涉及多个方面，请分步骤处理。

注意：对于数学计算，请确保表达式是安全的，只包含数字和基本运算符。
"""

CUSTOM_SUFFIX = """开始！

问题: {input}
{agent_scratchpad}"""
"""
替换"""
"""
llm = ChatOpenAI(
            model="gpt-4o",
            openai_api_base="https://api2.aigcbest.top/v1",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.7,
            timeout=30
        )

# 4. 初始化 DeepSeek 模型
"""
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base="https://api.deepseek.com/v1",
    temperature=0,
    max_tokens=2048
)

# 5. 初始化带有自定义提示词的Agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    agent_kwargs={
        'prefix': CUSTOM_PREFIX,
        'suffix': CUSTOM_SUFFIX,
    }
)

# 6. 高级功能：带记忆的对话
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent_with_memory = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    memory=memory,
    agent_kwargs={
        'prefix': CUSTOM_PREFIX,
        'suffix': CUSTOM_SUFFIX,
    }
)

# 7. 使用Agent的多种方式
if __name__ == "__main__":
    print("=== 基础示例 ===")
    
    # 示例1: 查询天气
    print("\n=== 示例1: 查询天气 ===")
    result1 = agent.run("北京今天的天气怎么样？")
    print(f"回答: {result1}")
    
    # 示例2: 数学计算
    print("\n=== 示例2: 数学计算 ===")
    result2 = agent.run("计算一下 (125 + 375) * 2 等于多少？")
    print(f"回答: {result2}")
    
    # 示例3: 复杂任务（需要多个工具）
    print("\n=== 示例3: 复杂任务 ===")
    result3 = agent.run("如果上海今天是晴天，那么计算一下20度摄氏度相当于多少华氏度？")
    print(f"回答: {result3}")
    
    # 示例4: 带记忆的对话
    print("\n=== 示例4: 带记忆的对话 ===")
    queries = [
        "北京天气如何？",
        "那上海呢？",  # 这里会记住上下文中的"天气"上下文
        "把25摄氏度转换成华氏度"
    ]
    
    for query in queries:
        print(f"\n用户: {query}")
        result = agent_with_memory.run(query)
        print(f"助手: {result}")
    
    # 示例5: 错误处理
    print("\n=== 示例5: 错误处理示例 ===")
    try:
        result5 = agent.run("计算一下 2 / 0 等于多少？")
        print(f"回答: {result5}")
    except Exception as e:
        print(f"错误: {e}")

    # 示例6: 多步骤推理
    print("\n=== 示例6: 多步骤推理 ===")
    complex_query = """
    请帮我完成以下任务：
    1. 先查询广州的天气
    2. 然后计算 (100 - 32) × 5/9 的结果
    3. 最后告诉我30摄氏度是多少华氏度
    """
    result6 = agent.run(complex_query)
    print(f"回答: {result6}")