import os
import logging
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools import (
    read_coverage_file,
    analyze_function_clusters,
    read_source_file
)
from utils import(
    get_coverage_file_path
)
from prompts import FUZZING_EXPERT_PROMPT, FUNCTION_CLUSTER_ANALYSIS_PROMPT

# 加载环境变量
load_dotenv()

# 初始化工具列表

tools = [
    read_coverage_file,
    get_coverage_file_path,
    read_source_file,
    analyze_function_clusters,
]

# 初始化 LLM
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

class CoverageAnalysisAgent:
    """覆盖率分析智能体类"""
    
    def __init__(self, llm, tools, agent_prompt):
        """
        初始化覆盖率分析智能体
        
        Args:
            llm: 语言模型
            tools: 工具列表
            agent_prompt: 智能体提示词
        """
        self.llm = llm
        self.tools = tools
        self.agent_prompt = agent_prompt
        self.agent = create_tool_calling_agent(llm, tools, agent_prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=tools, verbose=True)
    
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

class CoverageAnalysisAgent1:
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
        self.agent_prompt = agent_prompt
        
        # 使用initialize_agent创建智能体执行器
        self.agent_executor = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,  # 适合多参数工具调用
            verbose=True,  # 打印详细执行过程
            handle_parsing_errors=True,  # 处理解析错误
            agent_kwargs={
                'prefix': agent_prompt  # 如果提供了自定义提示词，可以设置前缀
            } if agent_prompt else None
        )
    
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

    def __init__(self, agent_prompt=""):
        """
        初始化函数聚类智能体
        自动构造可用工具（read_coverage_file + analyze_function_clusters）

        Args:
            llm: LangChain ChatOpenAI 实例（可选，如果不传则自动构造 deepseek-chat）
        """
        self.llm = llm or ChatOpenAI(
            model="deepseek-chat",
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0
        )

        # 将两个工具纳入 LangChain 工具列表
        self.tools = [read_source_file, analyze_function_clusters]

        # 智能体提示词
        self.agent_prompt = FUNCTION_CLUSTER_ANALYSIS_PROMPT

        # 构造 LangChain Agent
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.agent_prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    # ======================================================
    # 主运行逻辑
    # ======================================================
    def run_agent(self):
        """运行函数聚类智能体"""
        print("\n=== 🔎 Function Cluster Analysis Agent ===")
        print("提示：输入目标库名称（例如 gif2png / jpeg / libpng），输入 exit 退出。\n")

        while True:
            target_project = input("User (项目名)> ").strip()
            if target_project.lower() in ["exit", "quit"]:
                break

            # 构造文件路径
            src_api_path = f"D:\\TEST\\tosem\\data\\function\\{target_project}\\api\\src_api.json"
            cluster_csv_path = f"D:\\TEST\\cluster\\cluster\\{target_project}_k16.csv"

            # === Step 1: 函数总结 ===
            print(f"\n🚀 Step 1: 正在分析函数定义 -> {src_api_path}")
            result1 = read_coverage_file(src_api_path)
            print("✅ 函数总结完成：", result1, "\n")

            # === Step 2: 聚类分析 ===
            print(f"🚀 Step 2: 正在分析聚类结果 -> {cluster_csv_path}")
            result2 = analyze_function_clusters(cluster_csv_path)
            print("✅ 聚类分析完成：", result2, "\n")

            # === 输出最终提示 ===
            print(f"🎯 项目 [{target_project}] 分析总结完毕！")
            print("--------------------------------------------------\n")


if __name__ == "__main__":
    # 覆盖率分析智能体
    coverage_agent = CoverageAnalysisAgent(llm, tools, FUZZING_EXPERT_PROMPT)
    coverage_agent.run_agent()
    #聚类分析智能体
    #cluster_agent = FunctionClusterAnalysisAgent(FUNCTION_CLUSTER_ANALYSIS_PROMPT)
    #cluster_agent.run_agent()

'''
帮我分析gif2png使用afl在非空种子下第1轮的覆盖率数据
评估libpng的模糊测试是否应该终止
检查openssl的覆盖率增长情况
'''

'''
=== 🔎 Function Cluster Analysis Agent ===
提示：输入目标库名称（例如 gif2png / jpeg / libpng），输入 exit 退出。
'''