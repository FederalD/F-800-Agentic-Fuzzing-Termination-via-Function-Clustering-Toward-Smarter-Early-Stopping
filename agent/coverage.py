import pandas as pd
import os
import numpy as np
from langchain.tools import tool


#./fuzzer_coverage/gif2png_afl_seed_02_run_01/bb_cov.csv
def generate_function_coverage(target: str):
    """
    生成函数覆盖率文件并保存到指定文件
    对于每个函数，取其中所有basic block执行次数的最大值作为该函数的执行次数
    """
    input_file = f"./fuzzer_coverage/{target}/bb_cov.csv"
    output_file = f"./fuzzer_coverage/{target}/function_coverage.csv"

    if os.path.exists(output_file):
        print(f"文件 {output_file} 已存在，退出函数。")
        return  # 退出当前函数
    # 读取数据
    df = pd.read_csv(input_file)
    
    # 生成函数ID：文件名 + 函数名
    # 从Address中提取文件名（去掉路径，只保留文件名）
    df['File'] = df['Address'].apply(lambda x: x.split('/')[-1] if '/' in x else x)
    df['Function_ID'] = df['File'] + ':' + df['Function']
    
    # 按Function_ID分组，求每个时间点执行次数的最大值
    execution_cols = [col for col in df.columns if 'Execution Count' in col]
    function_coverage = df.groupby('Function_ID')[execution_cols].max().reset_index()
    
    # 保存文件（只包含Function_ID和执行次数列）
    function_coverage.to_csv(output_file, index=False)
    
    #print(f"函数覆盖率文件已保存到: {output_file}")
    #print(f"共处理 {len(function_coverage)} 个函数")
    #print("示例函数:")
    #for i, row in function_coverage.head(5).iterrows():
        #print(f"  {row['Function_ID']}")
    
    return function_coverage

import os
import csv
import json
import re
from collections import defaultdict
from langchain.schema import HumanMessage, SystemMessage

import pandas as pd
import json

def add_execution_counts_to_json_simple(csv_file_path, json_file_path, output_file_path):
    """
    简化版本：将CSV文件中的执行次数数据添加到JSON格式中
    """
    #csv_file_path="./fuzzer_coverage/gif2png_afl_seed_02_run_01/function_coverage.csv",
    #json_file_path="./cluster/cluster/gif2png/20/gif2png_updated_cluster_mapping.json", 
    #output_file_path="./fuzzer_coverage/gif2png_afl_seed_02_run_01/20_enhanced_data.json"
    #
    #
    # 从文件读取JSON数据
    with open(json_file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    if os.path.exists(output_file_path):
        print(f"文件 {output_file_path} 已存在，退出函数。")
        return  # 退出当前函数
    # 读取CSV文件
    df = pd.read_csv(csv_file_path)
    
    # 获取时间列
    time_columns = df.columns[1:]
    
    # 为每个聚类添加执行次数数据
    for cluster_id, cluster_info in json_data.items():
        execution_counts_by_time = [[] for _ in range(len(time_columns))]
        
        for function_info in cluster_info["functions_info"]:
            # 转换function_id格式
            function_id = function_info["function_id"]
            
            # 提取文件名和函数名
            parts = function_id.split('\\')
            if len(parts) >= 2:
                file_func_part = parts[-1]
                last_underscore = file_func_part.rfind('_')
                if last_underscore != -1:
                    filename = file_func_part[:last_underscore]
                    function_name = file_func_part[last_underscore + 1:]
                    csv_function_id = f"{filename}:{function_name}"
                else:
                    csv_function_id = f"{file_func_part}:"
            else:
                last_underscore = function_id.rfind('_')
                if last_underscore != -1:
                    filename = function_id[:last_underscore]
                    function_name = function_id[last_underscore + 1:]
                    csv_function_id = f"{filename}:{function_name}"
                else:
                    csv_function_id = f"{function_id}:"

            file_path = function_info["file_path"]
            file_name = os.path.basename(file_path)
            name_function = function_info["function_name"]
            index_function = f"{file_name}:{name_function}" 

            # 查找匹配的数据
            #matching_rows = df[df['Function_ID'] == csv_function_id]
            matching_rows = df[df['Function_ID'] == index_function]
            
            if not matching_rows.empty:
                execution_counts = matching_rows.iloc[0, 1:].tolist()
                for i, count in enumerate(execution_counts):
                    execution_counts_by_time[i].append({
                        "function_id": function_info["function_id"],#index_function
                        "execution_count": int(count)
                    })
            else:
                for i in range(len(time_columns)):
                    execution_counts_by_time[i].append({
                        "function_id": function_info["function_id"],
                        "execution_count": 0
                    })
        
        cluster_info["execution_counts_by_time"] = [
            {
                "timestamp": time_col.replace("Execution Count in time_", ""),
                "function_executions": execution_counts_by_time[i]
            }
            for i, time_col in enumerate(time_columns)
        ]
    
    # 保存结果
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_data

import json
import os
from langchain.schema import SystemMessage, HumanMessage
from langchain.chat_models import ChatOpenAI
import re

import json
import os
from langchain.schema import SystemMessage, HumanMessage
from langchain.chat_models import ChatOpenAI
import re

#@tool("analyze_cluster_coverage_pure_iterative", return_direct=True)
def analyze_cluster_coverage_pure_iterative(root_directory: str, target: str, k: int) -> str:
    """
    Analyze cluster coverage at each timestamp iteratively, using only execution data and previous coverage decisions.
    Does not use previous cluster analysis results.
    
    For each timestamp, output:
      - coverage: 0 or 1 indicating whether the cluster is covered
      - reason: Explanation for the coverage decision
      - updated_context: Updated context for next timestamp analysis
    
    Args:
        target: Target project name
    Returns:
        str: Path to coverage analysis result JSON file
    """
    # 1. Read the enhanced clustering data with execution counts
    json_path = root_directory + f"/{k}_enhanced_data.json"
    
    if not os.path.exists(json_path):
        return f"File does not exist: {json_path}"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            clusters_data = json.load(f)
    except Exception as e:
        return f"Error reading enhanced JSON file: {str(e)}"

    if not clusters_data:
        return "No clustering data found in JSON file."

    output_dir = os.path.dirname(json_path)
    output_path = os.path.join(output_dir, f"{target}_{k}_pure_iterative_coverage.json")

    if os.path.exists(output_path):
        print(f"文件 {output_path} 已存在，退出函数。")
        return  # 退出当前函数
    # 2. Initialize LLM (不使用之前的聚类分析结果)
    llm = ChatOpenAI(
        model="deepseek-chat",
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=0
    )

    results = {}

    # 3. Analyze each cluster
    for cluster_id, cluster_data in clusters_data.items():#读的是添加覆盖率数据的json文件
        print(f"Analyzing cluster {cluster_id}...")
        
        # Get execution counts by time
        execution_counts_by_time = cluster_data.get("execution_counts_by_time", [])
        
        cluster_results = {
            "cluster_id": cluster_id,
            "function_count": cluster_data.get("function_count", 0),
            "function_ids": cluster_data.get("function_ids", []),
            "timeline_analysis": []
        }
        
        #加入函数总结
        summary_path = f"./tosem/data/function/{target}/api/src_api_summary.json"
        fn_summaries = {}
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    fn_summaries = json.load(f)
            except Exception:
                print("Warning: Could not load function summaries, proceeding without them.")

        fn_summary = ""

        for function_id in cluster_data["function_ids"]:
            #file_name = src_key.split('\\')[-1]

            fn_name = function_id.split("\\")[-1]
            #full_name = fn_name.split("_")[-1]
            fn_sum = fn_summaries[fn_name]
            fn_summary += f"{fn_name}:{fn_sum}"

        # Initialize cumulative context with basic cluster info only
        cumulative_context = f"Cluster {cluster_id} contains {cluster_data.get('function_count', 0)} functions.\n"
        cumulative_context += f"The cluster contains these function, these are function summary: {fn_summary}.\n"
        cumulative_context += "Starting temporal coverage analysis based on execution patterns only.\n\n"
        
        #print(cumulative_context)

        # Track previous coverage decision and reason
        previous_coverage = None
        previous_reason = "Initial state - beginning temporal analysis"
        
        # 存储前三个时间点的覆盖决策
        last_three_coverages = []
        
        # 4. Analyze each timestamp iteratively
        for i, time_point in enumerate(execution_counts_by_time):
            timestamp = time_point["timestamp"]
            function_executions = time_point["function_executions"]
            
            # Calculate statistics for this timestamp
            total_executions = sum([func["execution_count"] for func in function_executions])
            active_functions = [func for func in function_executions if func["execution_count"] > 0]
            active_count = len(active_functions)
            
            # Get function names for active functions
            active_function_names = [func['function_id'] for func in active_functions]
            
            # Build execution context for current timestamp
            execution_context = f"=== Current Timestamp: {timestamp} ===\n"
            execution_context += f"Total executions: {total_executions:,}\n"
            execution_context += f"Active functions: {active_count}/{len(function_executions)}\n"
            
            if active_functions:
                execution_context += "Active function details:\n"
                for func in active_functions:
                    execution_context += f"  - {func['function_id']}: {func['execution_count']:,} executions\n"
            else:
                execution_context += "No active functions at this timestamp.\n"
            
            # Build previous context for iterative analysis
            previous_context = ""
            if previous_coverage is not None:
                previous_context = f"Previous Coverage Decision: {previous_coverage}\n"
                previous_context += f"Previous Analysis: {previous_reason}\n"
            else:
                previous_context = "First timestamp analysis - no previous coverage history.\n"
            
            # 检查前三个时间点的覆盖情况
            if len(last_three_coverages) >= 3 and all(cov == 1 for cov in last_three_coverages[-3:]):
                # 前三个时间点都为1，直接设置为1，不进行LLM询问
                coverage = 1
                reason = "Automatic coverage: previous three timestamps were all covered, indicating sustained cluster activity"
                updated_context = cumulative_context  # 保持上下文不变
                
                #print(f"  {timestamp}: AUTO-COVERED (previous 3 timestamps all covered)")
            elif len(last_three_coverages) >= 33 and all(cov == 0 for cov in last_three_coverages[-33:]):
               # 前三个时间点都为1，直接设置为1，不进行LLM询问
                coverage = 0
                reason = "Automatic coverage: previous 8 hours were all not covered, indicating sustained cluster activity"
                updated_context = cumulative_context  # 保持上下文不变
                
                #print(f"  {timestamp}: AUTO-NOT-COVERED (previous 8 hours all not covered)")
            else:
                # 正常进行LLM分析
                # Build prompt for pure iterative coverage analysis
                coverage_prompt = (
                    "Analyze whether this function cluster is 'covered' at the current timestamp based on execution patterns.\n"
                    "Coverage means the cluster is actively being used or tested.\n\n"
                    "ANALYSIS HISTORY:\n"
                    f"{cumulative_context}"
                    f"{previous_context}"
                    "\nCURRENT EXECUTION DATA:\n"
                    f"{execution_context}"
                    "\nANALYSIS APPROACH:\n"
                    "1. Compare current execution pattern with previous coverage decisions\n"
                    "2. Look for significant changes in execution activity\n"
                    "3. Evaluate if there is meaningful functional activity\n"
                    "4. Consider the proportion of active functions and execution intensity\n"
                    "5. Identify patterns or trends in cluster usage\n\n"
                    "COVERAGE INDICATORS:\n"
                    "- Coverage=1: Significant execution activity, multiple active functions, or core functions being exercised\n"
                    "- Coverage=0: Minimal or no execution, only background activity, or insufficient functional usage\n\n"
                    "OUTPUT REQUIREMENTS:\n"
                    "Output strictly in JSON format:\n"
                    "{\n"
                    '  "coverage": 0 or 1,\n'
                    '  "reason": "Clear explanation considering execution patterns and historical context",\n'
                    '  "updated_context": "Concise summary for next timestamp analysis (max 3 sentences)"\n'
                    "}\n"
                )
                
                try:
                    messages = [
                        SystemMessage(content="You are a software execution pattern analyst. You analyze function execution timelines to determine when code clusters are actively used. Focus on execution patterns, not functional semantics."),
                        HumanMessage(content=coverage_prompt)
                    ]
                    response = llm.invoke(messages)
                    raw_output = response.content.strip()

                    # Parse JSON output
                    try:
                        coverage_data = json.loads(raw_output)
                        # Ensure required fields with defaults
                        coverage = coverage_data.get("coverage", 0)
                        reason = coverage_data.get("reason", "Analysis incomplete")
                        updated_context = coverage_data.get("updated_context", cumulative_context)
                        
                    except Exception as e:
                        # Fallback parsing with regex
                        coverage_match = re.search(r'"coverage"\s*:\s*([01])', raw_output)
                        reason_match = re.search(r'"reason"\s*:\s*"([^"]+)"', raw_output)
                        context_match = re.search(r'"updated_context"\s*:\s*"([^"]+)"', raw_output)
                        
                        coverage = int(coverage_match.group(1)) if coverage_match else 0
                        reason = reason_match.group(1) if reason_match else f"Failed to parse response: {str(e)}"
                        updated_context = context_match.group(1) if context_match else cumulative_context

                    coverage_status = "COVERED" if coverage == 1 else "NOT COVERED"
                    #print(f"  {timestamp}: {coverage_status} (active: {active_count}/{len(function_executions)}, total: {total_executions:,})")
                    
                except Exception as e:
                    print(f"  Error analyzing timestamp {timestamp}: {str(e)}")
                    # 分析失败时设置为0
                    coverage = 0
                    reason = f"Analysis failed: {str(e)}"
                    updated_context = cumulative_context

            # 更新前33个时间点的覆盖记录
            if len(last_three_coverages) >= 33:
                last_three_coverages.pop(0)  # 移除最旧的时间点
            last_three_coverages.append(coverage)
            
            # Update for next iteration
            previous_coverage = coverage
            previous_reason = reason
            cumulative_context = updated_context
            
            # Add to results
            time_analysis = {
                "timestamp": timestamp,
                "coverage": coverage,
                "reason": reason,
                "execution_summary": {
                    "total_executions": total_executions,
                    "active_functions": active_count,
                    "total_functions": len(function_executions),
                    "active_function_names": active_function_names,
                    "execution_intensity": "high" if total_executions > 1000000 else "medium" if total_executions > 1000 else "low"
                },
                "iterative_context": previous_context.strip(),
                "analysis_method": "auto" if len(last_three_coverages) >= 3 and all(cov == 1 for cov in last_three_coverages[-3:]) and coverage == 1 else "llm"
            }
            
            cluster_results["timeline_analysis"].append(time_analysis)

        results[cluster_id] = cluster_results

    # 5. Calculate overall statistics
    overall_stats = {
        "total_clusters": len(results),
        "total_timestamps": len(execution_counts_by_time) if clusters_data else 0,
        "analysis_method": "pure_iterative_execution_analysis",
        "coverage_summary": {}
    }
    
    # Calculate coverage statistics for each cluster
    for cluster_id, cluster_result in results.items():
        coverage_decisions = [point["coverage"] for point in cluster_result["timeline_analysis"]]
        coverage_rate = sum(coverage_decisions) / len(coverage_decisions) if coverage_decisions else 0
        
        # Find coverage transitions and patterns
        coverage_transitions = 0
        max_coverage_streak = 0
        current_streak = 0
        
        # 统计自动分析和LLM分析的次数
        auto_analysis_count = sum(1 for point in cluster_result["timeline_analysis"] if point.get("analysis_method") == "auto")
        llm_analysis_count = sum(1 for point in cluster_result["timeline_analysis"] if point.get("analysis_method") == "llm")
        
        for i in range(len(coverage_decisions)):
            if coverage_decisions[i] == 1:
                current_streak += 1
                max_coverage_streak = max(max_coverage_streak, current_streak)
            else:
                current_streak = 0
                
            if i > 0 and coverage_decisions[i] != coverage_decisions[i-1]:
                coverage_transitions += 1
        
        # Calculate average active functions during covered periods
        covered_periods = [i for i, cov in enumerate(coverage_decisions) if cov == 1]
        avg_active_during_coverage = 0
        if covered_periods:
            active_counts = [cluster_result["timeline_analysis"][i]["execution_summary"]["active_functions"] for i in covered_periods]
            avg_active_during_coverage = sum(active_counts) / len(active_counts)
        
        overall_stats["coverage_summary"][cluster_id] = {
            "coverage_rate": round(coverage_rate, 3),
            "covered_timestamps": sum(coverage_decisions),
            "total_timestamps": len(coverage_decisions),
            "coverage_transitions": coverage_transitions,
            "final_coverage": coverage_decisions[-1] if coverage_decisions else 0,
            "max_coverage_streak": max_coverage_streak,
            "avg_active_functions_during_coverage": round(avg_active_during_coverage, 1),
            "auto_analysis_count": auto_analysis_count,
            "llm_analysis_count": llm_analysis_count
        }

    # 6. Save results
    output_data = {
        "target": target,
        "analysis_timestamp": os.path.getmtime(json_path),
        "analysis_notes": "Pure iterative analysis based only on execution patterns, no prior cluster semantics used. Auto-coverage applied when previous 3 timestamps are covered.",
        "overall_statistics": overall_stats,
        "cluster_analysis": results
    }
    
    
    try:
        with open(output_path, "w", encoding="utf-8") as wf:
            json.dump(output_data, wf, ensure_ascii=False, indent=2)
        return f"Pure iterative coverage analysis completed, results saved to: {output_path}"
    except Exception as e:
        return f"Error saving results: {str(e)}"

def calculate_coverage_totals(coverage_analysis_file: str, k: int) -> list:
    """
    统计每个时间点被覆盖的聚类总数
    
    Args:
        coverage_analysis_file: 覆盖率分析结果JSON文件路径
        
    Returns:
        list: 每个时间点的被覆盖聚类总数列表
    """
    output_dir = os.path.dirname(coverage_analysis_file)
    output_path = os.path.join(output_dir, f"{k}_coverage_list.json")

    if os.path.exists(output_path):
        print(f"文件 {output_path} 已存在，退出函数。")
        return  # 退出当前函数
    try:
        with open(coverage_analysis_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading coverage analysis file: {e}")
        return []
    
    # 获取所有聚类
    cluster_analysis = data.get("cluster_analysis", {})
    if not cluster_analysis:
        print("No cluster analysis data found")
        return []
    
    # 获取时间点数量（假设所有聚类的时间点数量相同）
    first_cluster = next(iter(cluster_analysis.values()))
    timeline_analysis = first_cluster.get("timeline_analysis", [])
    num_timestamps = len(timeline_analysis)
    
    # 初始化每个时间点的覆盖总数列表
    coverage_totals = [0] * num_timestamps
    
    # 统计每个时间点的覆盖聚类数
    for cluster_id, cluster_data in cluster_analysis.items():
        timeline_analysis = cluster_data.get("timeline_analysis", [])
        
        for i, time_point in enumerate(timeline_analysis):
            if i < num_timestamps:  # 确保不越界
                if time_point.get("coverage", 0) == 1:
                    coverage_totals[i] += 1
    

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(coverage_totals, f, indent=2)
        print(f"Coverage totals saved to: {output_dir}")
    except Exception as e:
        print(f"Error saving file: {e}")

    return coverage_totals

# 使用示例
if __name__ == "__main__":
    # 生成函数覆盖率文件
    id = "gif2png_afl_seed_02_run_01"
    result_df = generate_function_coverage(id)
    

    result = add_execution_counts_to_json_simple(
        csv_file_path="./fuzzer_coverage/gif2png_afl_seed_02_run_01/function_coverage.csv",
        json_file_path="./cluster/cluster/gif2png/20/gif2png_updated_cluster_mapping.json", 
        output_file_path="./fuzzer_coverage/gif2png_afl_seed_02_run_01/20_enhanced_data.json"
    )

    analyze_cluster_coverage_pure_iterative("./fuzzer_coverage/gif2png_afl_seed_02_run_01", "gif2png", 20)
    calculate_coverage_totals("./fuzzer_coverage/gif2png_afl_seed_02_run_01/gif2png_20_pure_iterative_coverage.json", 20)