from langchain.agents import initialize_agent, AgentType
from tools import (
    read_coverage_file,
)
from utils import(
    get_coverage_file_path
)
from cluster import analyze_function_code, analyze_function_clusters
import os
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage
class CoverageAnalysisAgent:
    """覆盖率分析智能体类"""
    
    def __init__(self, llm, tools, agent_prompt=None):
        """
        初始化覆盖率分析智能体
        
        Args:
            llm: 语言模型
            tools: 工具列表
            agent_prompt: 智能体提示词（可选，因为initialize_agent使用内置提示策略）
        """
        self.llm = llm
        self.tools = tools
        self.agent_prompt = agent_prompt or self._get_default_prompt()
        
        # 使用initialize_agent创建智能体执行器
        self.agent_executor = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # 适合多参数工具调用
            verbose=True,  # 打印详细执行过程
            handle_parsing_errors=True,  # 处理解析错误
            agent_kwargs={
                'prefix': self.agent_prompt['prefix'],
                'suffix': self.agent_prompt['suffix']
            }
        )
    
    def _get_default_prompt(self):
        """获取默认的提示词配置"""
        prefix = """你是一个模糊测试专家，能够根据目标库模糊测试运行期间的各种指标精确确定何时终止模糊测试活动。

工作流程说明：
1. 首先，使用 get_coverage_file_path 工具，根据用户提供的目标库、模糊测试工具、种子类型和运行迭代生成正确的文件路径。这个函数的输入为一个json格式的str，分别为target_library，fuzzing_tool，seed_type和run_iteration这四个
2. 然后，使用 read_coverage_file 工具和生成的路径来读取覆盖率数据。
3. 分析覆盖率数据以及其他模糊测试指标。

可用工具：
- get_coverage_file_path: 根据参数生成覆盖率文件路径
- read_coverage_file: 从指定文件路径读取覆盖率数据

分析模糊测试终止时，请考虑：
1. 代码覆盖率平台期（覆盖率没有显著增加）
2. 发现的唯一崩溃数量
3. 执行速度和效率
4. 没有新发现的时间花费
5. 资源约束和成本效益

请按照以下步骤思考：
1. 首先获取覆盖率文件路径
2. 读取覆盖率数据
3. 分析数据并给出终止建议
4. 提供详细的分析理由

请用中文回答用户的问题。"""

        suffix = """开始！

问题: {input}
{agent_scratchpad}"""

        return {'prefix': prefix, 'suffix': suffix}
    
    def run_agent(self):
        """运行覆盖率分析智能体"""
        print("=== Fuzzing Terminator Agent ===")
        print("Please input: target fuzzer seed_type turns and stop criteria\n")
        
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]:
                break
                
            result = self.agent_executor.invoke({"input": user_input})
            print("Agent: ", result["output"], "\n")

class FunctionClusterAnalysisAgent:
    """函数总结与聚类分析智能体类"""

    def __init__(self, llm=None, tools=None, agent_prompt=None):
        """
        初始化函数聚类智能体
        
        Args:
            llm: 语言模型（可选，如果不传则自动构造deepseek-chat）
            tools: 工具列表（可选，如果不传则自动构造）
            agent_prompt: 智能体提示词（可选）
        """
        self.llm = llm or self._create_default_llm()
        self.tools = tools
        self.agent_prompt = agent_prompt or self._get_default_prompt()
        
        # 使用initialize_agent创建智能体执行器
        self.agent_executor = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            agent_kwargs={
                'prefix': self.agent_prompt['prefix'],
                'suffix': self.agent_prompt['suffix']
            }
        )
    
    def _create_default_llm(self):
        """创建默认的语言模型"""
        return ChatOpenAI(
            model="deepseek-chat",
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0
        )
    
    
    def _get_default_prompt(self):
        """获取默认的提示词配置"""
        prefix = """你是一个软件分析专家，专门负责自动总结函数定义并分析软件项目中函数之间的聚类关系。

工作流程说明：
1. 首先，使用 analyze_function_code 工具读取目标库的源API文件并生成函数级别的代码总结。(API文件来自目标库如：gif2png中)
2. 然后，使用 analyze_function_clusters 工具分析聚类结果并生成结构化分析。

可用工具：
- analyze_function_code: 读取目标库的API JSON文件并总结所有的函数。
- analyze_function_clusters: 分析聚类结果，提供'analysis'和'exclude_function'字段。

生成最终分析时，请考虑：
1. 分组函数之间的功能相似性。
2. 代码复杂度和算法特征与聚类逻辑的关系。
3. 可能错误分类的函数（exclude_function字段）。
4. 分组背后的内聚性和合理性。
5. 清晰、简洁和结构化的JSON结果。

输出应包括：
- 函数总结JSON和聚类分析JSON的保存路径。
- 对聚类合理性的简短、有充分理由的解释。

请按照以下步骤思考：
1. 首先读取源API文件获取函数定义
2. 然后分析函数聚类结果
3. 综合分析并给出聚类洞察
4. 提供详细的分析理由和排除函数说明

请用中文回答用户的问题。"""

        suffix = """开始！

问题: {input}
{agent_scratchpad}"""

        return {'prefix': prefix, 'suffix': suffix}
    
    
    def run_agent(self):
        """运行函数聚类分析智能体"""
        print("=== Function Cluster Analysis Agent ===")
        print("Please input target project name for analysis (e.g., gif2png, jpeg, libpng)\n")
        
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]:
                break
                
            result = self.agent_executor.invoke({"input": user_input})
            print("Agent: ", result["output"], "\n")

# 使用示例
if __name__ == "__main__":
    # 初始化工具
    tools1 = [
        Tool(
            name="get_coverage_file_path",
            func=get_coverage_file_path,
            description="根据目标库、模糊测试工具、种子类型和运行迭代生成覆盖率文件路径"
        ),
        Tool(
            name="read_coverage_file",
            func=read_coverage_file,
            description="从指定文件路径读取覆盖率数据"
        )
    ]

    tools2 = [
        Tool(
            name="analyze_function_code",
            func=analyze_function_code,
            description="分析目标库中每个函数"
        ),
        Tool(
            name="analyze_function_clusters",
            func=analyze_function_clusters,
            description="分析函数聚类"
        )
    ]
    
    # 初始化LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
        openai_api_base="https://api.deepseek.com/v1",
        temperature=0
    )
    
    # 创建并运行智能体
    #agent = CoverageAnalysisAgent(llm=llm, tools=tools1)
    #agent.run_agent()

    agent = FunctionClusterAnalysisAgent(llm=llm, tools=tools2)
    agent.run_agent()
    #analyze_function_code("gif2png")
    #read_coverage_file("./fuzzer_coverage/gif2png_afl_seed_02_run_01/bb_cov.csv")
