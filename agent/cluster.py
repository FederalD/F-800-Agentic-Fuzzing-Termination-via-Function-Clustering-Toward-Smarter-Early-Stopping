import os
import json
import csv
import re
import pandas as pd
from collections import defaultdict
from langchain.tools import tool
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# =============================================
# 初始化 LLM
# =============================================
#使用新的
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-e8708e1a901742c2bfa62af92fc61a98",
    temperature=0.7
)
"""


llm = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)
"""
# =============================================
# 工具函数定义
# =============================================
def analyze_function_code(target: str) -> str:
    """
    Read src_api.json file, extract function definitions, and call LLM for multi-dimensional analysis.
    The generated summary will be saved as a JSON file.
    
    Args:
        target: need function analysis
    Returns:
        str: Path to the generated JSON file
    """
    print("wo jin lai le")
    file_path = f"./tosem/data/function/{target}/api/src_api.json"
    # 1. Read JSON file
    if not os.path.exists(file_path):
        return f"File does not exist: {file_path}"

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            src_api_data = json.load(f)
        except json.JSONDecodeError as e:
            return f"JSON parsing error: {str(e)}"

    # 2. Extract function definitions
    api_summary = {}
    if "src" not in src_api_data:
        return "File structure error, missing 'src' field."

    for src_key, src_value in src_api_data["src"].items():
        file_name = src_key.split('\\')[-1]
        for key, value in src_value.items():
            if key == "fn_def_list":
                for func_obj in value:
                    fn_name = func_obj["fn_meta"]["identifier"]
                    fn_id = f"{file_name}_{fn_name}"
                    fn_code = func_obj["fn_code"]
                    api_summary[fn_id] = {
                        "code": fn_code
                    }
    print("wo jin lai le")

    if not api_summary:
        return "No function definitions found in the file."

    # 3. Use LLM for function analysis
    results = {}
    analysis_prompt = (
        "Please analyze the following function code and provide a summary in one natural English paragraph covering the following five dimensions:\n\n"
        "1. Functional category (e.g., image processing, memory management, file operations, utility functions, etc.)\n"
        "2. Code complexity (based on lines of code, number of control structures)\n"
        "3. Algorithm characteristics (algorithm patterns and data processing methods used)\n"
        "4. Performance characteristics (compute-intensive, I/O-intensive, etc.)\n"
        "5. Key features (core technical characteristics of the function)\n\n"
        "Please generate one natural paragraph summarizing the above aspects."
    )

    for fn_name, fn_info in api_summary.items():
        fn_code = fn_info["code"]

        try:
            messages = [
                SystemMessage(content="You are a professional software engineering analyst."),
                HumanMessage(content=f"{analysis_prompt}\n\nFunction name: {fn_name}\nFunction code:\n{fn_code}")
            ]
            response = llm.invoke(messages)
            summary_text = response.content.strip()
        except Exception as e:
            summary_text = f"LLM call failed: {str(e)}"

        print(summary_text)
        results[fn_name] = {
            "summary": summary_text
        }

    # 4. Save JSON results
    save_dir = os.path.dirname(file_path)
    output_path = f"./tosem/data/function/{target}/api/src_api_summary.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    return f"Analysis completed, results saved to: {output_path}"

# =============================================
# 聚类分析工具函数
# =============================================
@tool("analyze_function_clusters1", return_direct=True)
def analyze_function_clusters1(target: str) -> str:
    """
    Read clustering data from function clustering result JSON, combine with previous function summaries,
    and use LLM to analyze each cluster.

    For each cluster, output:
      - analysis: Summary of functional characteristics for this cluster
      - exclude_function: Functions that the model considers potentially misassigned (can be empty)

    Args:
        target: need cluster analysis
    Returns:
        str: Path to cluster analysis result JSON file
    """
    last_underscore_index = target.rfind('_')
    
    # 分割字符串
    first_part = target[:last_underscore_index]
    second_part = target[last_underscore_index + 1:]
    target = first_part
    k = second_part
    print("--------------------------------------")
    # 修改为读取JSON格式的聚类结果
    json_path = f"./cluster/cluster/{target}/{k}/cluster_mapping.json"
    print(json_path)
    # 1. Validate file path
    if not os.path.exists(json_path):
        return f"File does not exist: {json_path}"

    # 2. Read clustering data from JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            clusters_data = json.load(f)
    except Exception as e:
        return f"Error reading clustering JSON file: {str(e)}"

    if not clusters_data:
        return "No clustering data found in JSON file."

    # 3. Load previous function summary file (如果存在)
    summary_path = f"./tosem/data/function/{target}/api/src_api_summary.json"
    fn_summaries = {}
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                fn_summaries = json.load(f)
        except Exception:
            print("Warning: Could not load function summaries, proceeding without them.")

    # 4. Build analysis prompt
    base_prompt = (
        "The following is a set of functions clustered into the same category. Please analyze based on their function names, return types, and parameters:\n\n"
        "1. What is the functional basis of this cluster? (e.g., all perform image parsing, pixel iteration, memory operations, etc.)\n"
        "2. Which functions might be unsuitable for this cluster (if none, return an empty list)?\n"
        "3. Briefly describe the overall purpose and relationship of these functions.\n\n"
        "Please output strictly in the following JSON format:\n"
        "{\n"
        '  "analysis": "This cluster mainly contains... (natural language analysis)",\n'
        '  "exclude_function": ["funcA", "funcB"]\n'
        "}\n"
    )

    results = {}

    # 5. Cluster loop analysis
    for cluster_label, cluster_data in clusters_data.items():
        fn_context = ""
        functions_info = cluster_data.get("functions_info", [])
        
        for func_info in functions_info:
            fn_name = func_info.get("function_name", "")
            return_type = func_info.get("return_type", "")
            parameters = func_info.get("parameters", {})
            file_path = func_info.get("file_path", "")
            
            # Get summary if available
            summary = fn_summaries.get(fn_name, {}).get("summary", "No previous summary available.")
            
            # Build parameter string
            param_str = ", ".join([f"{param_name}: {param_type}" for param_name, param_type in parameters.items()])
            
            fn_context += f"\nFunction: {fn_name}\n"
            fn_context += f"Return type: {return_type}\n"
            fn_context += f"Parameters: {param_str}\n"
            fn_context += f"File: {file_path}\n"
            fn_context += f"Summary: {summary}\n"
            
            # Try to get function code if available
            code_snippet = "Function code not available."
            src_json = "./tosem/data/function/gif2png/api/src_api.json"
            if os.path.exists(src_json):
                try:
                    with open(src_json, "r", encoding="utf-8") as fs:
                        src_data = json.load(fs)
                    
                    # Search for function code in the src data
                    for file_key, file_val in src_data.get("src", {}).items():
                        fn_def_list = file_val.get("fn_def_list", [])
                        for fn_def in fn_def_list:
                            fn_meta = fn_def.get("fn_meta", {})
                            if fn_meta.get("identifier") == fn_name:
                                code_snippet = fn_def.get("fn_code", "Code not found")
                                # Truncate snippet
                                code_snippet = code_snippet[:400] + "..." if len(code_snippet) > 400 else code_snippet
                                break
                except Exception as e:
                    code_snippet = f"Error reading code: {str(e)}"
            
            fn_context += f"Code snippet:\n{code_snippet}\n"
            fn_context += "-" * 50 + "\n"

        try:
            messages = [
                SystemMessage(content="You are a software engineering researcher responsible for source code cluster analysis and understanding."),
                HumanMessage(content=f"{base_prompt}\n\nCluster ID: {cluster_label}\nNumber of functions: {len(functions_info)}\n{fn_context}")
            ]
            response = llm.invoke(messages)
            raw_output = response.content.strip()

            # Parse JSON output
            parsed = {}
            try:
                parsed = json.loads(raw_output)
                # Ensure keys exist
                parsed.setdefault("analysis", "")
                parsed.setdefault("exclude_function", [])
            except Exception as e:
                # Try regex fallback to extract analysis and exclude_function
                analysis_match = re.search(r'"analysis"\s*:\s*"([^"]+)"', raw_output)
                exclude_match = re.search(r'"exclude_function"\s*:\s*(\[.*?\])', raw_output)
                analysis_text = analysis_match.group(1) if analysis_match else raw_output
                exclude_list = json.loads(exclude_match.group(1)) if exclude_match else []
                parsed = {"analysis": analysis_text, "exclude_function": exclude_list}

        except Exception as e:
            parsed = {"analysis": f"LLM call failed: {str(e)}", "exclude_function": []}

        results[cluster_label] = {
            "function_count": len(functions_info),
            "functions": [{"function_name": info["function_name"], "function_id": info["function_id"]} for info in functions_info],
            "analysis": parsed["analysis"],
            "exclude_function": parsed["exclude_function"]
        }

    # 6. Output result JSON file
    output_path = os.path.join(os.path.dirname(json_path), f"{target}_cluster_analysis.json")
    with open(output_path, "w", encoding="utf-8") as wf:
        json.dump(results, wf, ensure_ascii=False, indent=4)

    return f"Cluster analysis completed, results saved to: {output_path}"

@tool("reassign_excluded_functions", return_direct=True)
def reassign_excluded_functions1(target: str) -> str:
    """
    For functions excluded from clusters by LLM analysis, use LLM to reassign them to 
    one of their top 5 closest clusters (excluding the original cluster).
    
    Args:
        target: target project name
    Returns:
        str: Path to reassignment result JSON file
    """
    last_underscore_index = target.rfind('_')
    
    # 分割字符串
    first_part = target[:last_underscore_index]
    second_part = target[last_underscore_index + 1:]
    target = first_part
    k = second_part
    # 1. Load cluster analysis results
    analysis_path = f"./cluster/cluster/{target}/{k}/{target}_cluster_analysis.json"
    if not os.path.exists(analysis_path):
        return f"Cluster analysis file does not exist: {analysis_path}"
    
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_data = json.load(f)
    
    # 2. Load function distance data
    distance_path = f"./cluster/cluster/{target}/{k}/function_cluster_distances.json"
    if not os.path.exists(distance_path):
        return f"Function distance file does not exist: {distance_path}"
    
    with open(distance_path, "r", encoding="utf-8") as f:
        distance_data = json.load(f)
    
    # 3. Load cluster mapping
    cluster_path = f"./cluster/cluster/{target}/{k}/cluster_mapping.json"
    if not os.path.exists(cluster_path):
        return f"Cluster mapping file does not exist: {cluster_path}"
    
    with open(cluster_path, "r", encoding="utf-8") as f:
        cluster_mapping = json.load(f)
    
    # 4. Collect all excluded functions
    excluded_functions = []
    for cluster_id, cluster_analysis in analysis_data.items():
        exclude_list = cluster_analysis.get("exclude_function", [])
        for func_name in exclude_list:
            # Find the function in distance data
            func_data = None
            for func_id, dist_info in distance_data.items():
                if dist_info.get("function_name") == func_name:
                    func_data = {
                        "function_name": func_name,
                        "function_id": func_id,
                        "original_cluster": cluster_id,
                        "distance_info": dist_info
                    }
                    break
            
            if func_data:
                excluded_functions.append(func_data)
    
    if not excluded_functions:
        return "No excluded functions found for reassignment."
    
    print(f"Found {len(excluded_functions)} excluded functions for reassignment:")
    for func in excluded_functions:
        print(f"  - {func['function_name']} (from cluster {func['original_cluster']})")
    
    # 3. Load previous function summary file (如果存在)
    summary_path = f"./tosem/data/function/{target}/api/src_api_summary.json"
    fn_summaries = {}
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                fn_summaries = json.load(f)
        except Exception:
            print("Warning: Could not load function summaries, proceeding without them.")

    # 5. Build reassignment prompt
    base_prompt = (
    "TASK: Reassign an excluded function to the most appropriate alternative cluster.\n\n"
    "CONTEXT:\n"
    "A function was excluded from cluster {original_cluster}. "
    "You must select the best alternative from the candidate clusters below.\n\n"
    "CRITERIA FOR SELECTION:\n"
    "1. Functional similarity with cluster's purpose\n"
    "2. Consistency in parameter and return type patterns\n"
    "3. Overall behavioral alignment\n\n"
    "FUNCTION TO REASSIGN:\n"
    "{function_info}\n\n"
    "CANDIDATE CLUSTERS (excluding original cluster {original_cluster}):\n"
    "{cluster_descriptions}\n\n"
    "OUTPUT REQUIREMENTS:\n"
    "- You MUST output ONLY valid JSON\n"
    "- No additional text, explanations, or formatting\n"
    "- Use exactly this structure:\n"
    "{{\n"
    '  "selected_cluster": "cluster_id",\n'
    '  "reasoning": "your explanation here"\n'
    "}}\n\n"
    "VALID EXAMPLE OUTPUT:\n"
    '{{"selected_cluster": "2", "reasoning": "Matches image processing functions in cluster 2"}}\n\n'
    "Begin your response with '{{' and end with '}}'. No other text."
    )
    
    reassignment_results = {}
    
    # 6. Process each excluded function
    for func_data in excluded_functions:
        func_name = func_data["function_name"]
        func_id = func_data["function_id"]
        original_cluster = func_data["original_cluster"]
        distance_info = func_data["distance_info"]
        
        # Get top 5 closest clusters (excluding original)
        all_distances = distance_info.get("all_distances", {})
        
        # Sort clusters by distance and exclude original
        sorted_clusters = sorted(all_distances.items(), key=lambda x: x[1])
        candidate_clusters = []
        
        for cluster_id, distance in sorted_clusters:
            if str(cluster_id) != str(original_cluster) and len(candidate_clusters) < 5:  # 修复：确保类型一致
                candidate_clusters.append((str(cluster_id), distance))  # 修复：统一为字符串
        
        if not candidate_clusters:
            print(f"No alternative clusters found for {func_name}, keeping original assignment.")
            reassignment_results[func_id] = {
                "function_name": func_name,
                "original_cluster": original_cluster,
                "selected_cluster": original_cluster,
                "reasoning": "No alternative clusters available",
                "candidate_clusters": []
            }
            continue
        
        # Get cluster descriptions for candidate clusters
        cluster_descriptions = ""
        for cluster_id, distance in candidate_clusters:
            cluster_analysis = analysis_data.get(str(cluster_id), {})
            analysis_text = cluster_analysis.get("analysis", "No analysis available")
            function_count = cluster_analysis.get("function_count", 0)
            
            # Get sample functions from the cluster
            cluster_funcs = cluster_mapping.get(str(cluster_id), {}).get("functions_info", [])
            sample_funcs = [f["function_name"] for f in cluster_funcs[:3]]  # Show first 3 functions
            
            cluster_descriptions += f"Cluster {cluster_id} (distance: {distance:.4f}):\n"
            cluster_descriptions += f"  Analysis: {analysis_text}\n"
            cluster_descriptions += f"  Function count: {function_count}\n"
            cluster_descriptions += f"  Sample functions: {', '.join(sample_funcs)}\n\n"
        
        # Build function information
        function_info = f"Function: {func_name}\n"
        function_info += f"Original cluster: {original_cluster}\n"
        function_info += f"File: {distance_info.get('file_path', 'Unknown')}\n"
        
        # Try to get function code and parameters from source data
        src_json = f"./tosem/data/function/{target}/api/src_api.json"
        if os.path.exists(src_json):
            try:
                with open(src_json, "r", encoding="utf-8") as fs:
                    src_data = json.load(fs)
                
                # Search for function in source data
                for file_key, file_val in src_data.get("src", {}).items():
                    fn_def_list = file_val.get("fn_def_list", [])
                    for fn_def in fn_def_list:
                        fn_meta = fn_def.get("fn_meta", {})
                        if fn_meta.get("identifier") == func_name:
                            return_type = fn_meta.get("return_type", "unknown")
                            parameters = fn_meta.get("parameters", {})
                            code_snippet = fn_def.get("fn_code", "")[:300] + "..." if len(fn_def.get("fn_code", "")) > 300 else fn_def.get("fn_code", "")
                            
                            function_info += f"Return type: {return_type}\n"
                            function_info += f"Parameters: {parameters}\n"
                            function_info += f"Code snippet:\n{code_snippet}\n"
                            break
            except Exception as e:
                function_info += f"Error reading function details: {str(e)}\n"
        
        # Call LLM for reassignment decision
        try:
            # 修复：添加缺失的 original_cluster 参数
            prompt = base_prompt.format(
                original_cluster=original_cluster,  # 添加这个参数
                cluster_descriptions=cluster_descriptions,
                function_info=function_info
            )
            
            messages = [
                SystemMessage(content="""You are a JSON-only assistant. You must output exactly and only valid JSON format.

CRITICAL RULES:
1. Your entire response must be a single JSON object
2. No text before or after the JSON
3. No markdown code blocks (no ```json)
4. No additional explanations
5. JSON must contain exactly: "selected_cluster" and "reasoning" fields
6. Both values must be strings

Your response will be parsed by code, so format errors will break the system. Output ONLY the JSON object."""),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            raw_output = response.content.strip()
            
            # Parse LLM response with better error handling
            def safe_parse_llm_response(raw_output):
                """安全解析LLM响应"""
                try:
                    # 清理响应
                    cleaned = raw_output.strip()
                    # 移除可能的markdown代码块
                    if cleaned.startswith('```json'):
                        cleaned = cleaned[7:]
                    if cleaned.startswith('```'):
                        cleaned = cleaned[3:]
                    if cleaned.endswith('```'):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()
                    
                    # 尝试直接解析
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    # 尝试提取JSON对象
                    try:
                        json_match = re.search(r'\{[^{}]*"selected_cluster"[^{}]*\}', cleaned)
                        if json_match:
                            return json.loads(json_match.group())
                    except:
                        pass
                    
                    # 尝试手动提取字段
                    try:
                        cluster_match = re.search(r'"selected_cluster"\s*:\s*"([^"]+)"', cleaned)
                        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', cleaned)
                        if cluster_match:
                            result = {"selected_cluster": cluster_match.group(1)}
                            if reasoning_match:
                                result["reasoning"] = reasoning_match.group(1)
                            else:
                                result["reasoning"] = "从响应中提取"
                            return result
                    except:
                        pass
                    
                    return None
            
            parsed = safe_parse_llm_response(raw_output)
            if parsed and "selected_cluster" in parsed:
                selected_cluster = parsed["selected_cluster"]
                reasoning = parsed.get("reasoning", "No reasoning provided")
                
                # Validate selected cluster is in candidate list
                candidate_ids = [cid for cid, _ in candidate_clusters]
                if selected_cluster not in candidate_ids:
                    selected_cluster = candidate_clusters[0][0]  # Default to closest
                    reasoning = f"Invalid selection, defaulted to closest cluster. {reasoning}"
                
            else:
                # Fallback: choose the closest cluster
                selected_cluster = candidate_clusters[0][0]
                reasoning = f"Failed to parse LLM response, using closest cluster. Raw output: {raw_output[:200]}"
                print(f"LLM response parsing failed for {func_name}: {raw_output}")
            
        except Exception as e:
            # Fallback: choose the closest cluster
            selected_cluster = candidate_clusters[0][0]
            reasoning = f"LLM call failed, using closest cluster. Error: {str(e)}"
            print(f"LLM call failed for {func_name}: {str(e)}")
        
        reassignment_results[func_id] = {
            "function_name": func_name,
            "original_cluster": original_cluster,
            "selected_cluster": selected_cluster,
            "reasoning": reasoning,
            "candidate_clusters": [{"cluster_id": cid, "distance": dist} for cid, dist in candidate_clusters],
            "all_distances": all_distances
        }
        
        print(f"Reassigned {func_name}: {original_cluster} -> {selected_cluster}")
        
        # 添加延迟避免速率限制
        import time
        time.sleep(1)
    
    # 7. Generate updated cluster mapping
    updated_cluster_mapping = cluster_mapping.copy()
    
    # Remove excluded functions from original clusters
    for func_id, reassign_data in reassignment_results.items():
        original_cluster = reassign_data["original_cluster"]
        func_name = reassign_data["function_name"]
        
        # Remove from original cluster
        if str(original_cluster) in updated_cluster_mapping:
            cluster_data = updated_cluster_mapping[str(original_cluster)]
            # Remove from function_ids
            if "function_ids" in cluster_data:
                cluster_data["function_ids"] = [fid for fid in cluster_data["function_ids"] if fid != func_id]  # 修复：直接比较func_id
            # Remove from functions_info
            if "functions_info" in cluster_data:
                cluster_data["functions_info"] = [finfo for finfo in cluster_data["functions_info"] if finfo.get("function_name") != func_name]
            # Update function_count
            cluster_data["function_count"] = len(cluster_data.get("function_ids", []))
    
    # Add to new clusters
    for func_id, reassign_data in reassignment_results.items():
        selected_cluster = reassign_data["selected_cluster"]
        func_name = reassign_data["function_name"]
        
        # Find original function info
        original_info = None
        for cluster_id, cluster_data in cluster_mapping.items():
            for finfo in cluster_data.get("functions_info", []):
                if finfo.get("function_name") == func_name:
                    original_info = finfo
                    break
            if original_info:
                break
        
        if original_info:
            # Add to selected cluster
            if str(selected_cluster) not in updated_cluster_mapping:
                updated_cluster_mapping[str(selected_cluster)] = {
                    "function_count": 0,
                    "function_ids": [],
                    "functions_info": []
                }
            
            cluster_data = updated_cluster_mapping[str(selected_cluster)]
            if func_id not in cluster_data["function_ids"]:
                cluster_data["function_ids"].append(func_id)
                cluster_data["functions_info"].append(original_info)
                cluster_data["function_count"] = len(cluster_data["function_ids"])
    
    # 8. Save results
    output_dir = f"./cluster/cluster/{target}/{k}/"
    
    # Save reassignment results
    reassign_path = os.path.join(output_dir, f"{target}_reassignment_results.json")
    with open(reassign_path, "w", encoding="utf-8") as f:
        json.dump(reassignment_results, f, ensure_ascii=False, indent=4)
    
    # Save updated cluster mapping
    updated_mapping_path = os.path.join(output_dir, f"{target}_updated_cluster_mapping.json")
    with open(updated_mapping_path, "w", encoding="utf-8") as f:
        json.dump(updated_cluster_mapping, f, ensure_ascii=False, indent=4)
    
    # Summary
    summary = {
        "total_excluded_functions": len(excluded_functions),
        "reassignment_summary": {
            str(cluster_id): len([r for r in reassignment_results.values() if r["selected_cluster"] == str(cluster_id)])
            for cluster_id in set(r["selected_cluster"] for r in reassignment_results.values())
        },
        "original_vs_new": [
            {
                "function": r["function_name"],
                "original_cluster": r["original_cluster"],
                "new_cluster": r["selected_cluster"]
            }
            for r in reassignment_results.values()
        ]
    }
    
    summary_path = os.path.join(output_dir, f"{target}_reassignment_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    
    return f"Reassignment completed. Results saved to:\n- {reassign_path}\n- {updated_mapping_path}\n- {summary_path}"

#重复验证函数聚类分析
#@tool("analyze_function_clusters2", return_direct=True)
def analyze_function_clusters2(target: str, iteration: int = None) -> str:
    """
    Read clustering data from function clustering result JSON, combine with previous function summaries,
    and use LLM to analyze each cluster.

    For each cluster, output:
      - analysis: Summary of functional characteristics for this cluster
      - exclude_function: Functions that the model considers potentially misassigned (can be empty)

    Args:
        target: need cluster analysis
        iteration: optional iteration number (if None, will auto-increment)
    Returns:
        str: Path to cluster analysis result JSON file
    """
    last_underscore_index = target.rfind('_')
    
    # 分割字符串
    first_part = target[:last_underscore_index]
    second_part = target[last_underscore_index + 1:]
    target_name = first_part
    k = second_part
    
    print("--------------------------------------")
    print(f"开始分析: {target_name}, k={k}")
    
    # 修改为读取JSON格式的聚类结果
    json_path = f"./cluster/cluster/{target_name}/{k}/cluster_mapping.json"
    print(f"聚类文件路径: {json_path}")
    
    # 1. Validate file path
    if not os.path.exists(json_path):
        return f"File does not exist: {json_path}"

    # 2. Read clustering data from JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            clusters_data = json.load(f)
    except Exception as e:
        return f"Error reading clustering JSON file: {str(e)}"

    if not clusters_data:
        return "No clustering data found in JSON file."

    # 3. Load previous function summary file (如果存在)
    summary_path = f"./tosem/data/function/{target_name}/api/src_api_summary.json"
    fn_summaries = {}
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                fn_summaries = json.load(f)
        except Exception:
            print("Warning: Could not load function summaries, proceeding without them.")

    # 4. Build analysis prompt
    base_prompt = (
        "The following is a set of functions clustered into the same category. Please analyze based on their function names, return types, and parameters:\n\n"
        "1. What is the functional basis of this cluster? (e.g., all perform image parsing, pixel iteration, memory operations, etc.)\n"
        "2. Which functions might be unsuitable for this cluster (if none, return an empty list)?\n"
        "3. Briefly describe the overall purpose and relationship of these functions.\n\n"
        "Please output strictly in the following JSON format:\n"
        "{\n"
        '  "analysis": "This cluster mainly contains... (natural language analysis)",\n'
        '  "exclude_function": ["funcA", "funcB"]\n'
        "}\n"
    )

    # 确定迭代次数
    if iteration is None:
        # 查找已有的迭代文件
        output_dir = f"./cluster/cluster/{target_name}/{k}"
        existing_files = [f for f in os.listdir(output_dir) 
                         if f.startswith(f"{target_name}_cluster_analysis_") and f.endswith(".json")]
        
        # 提取已有迭代次数
        iteration_numbers = []
        for f in existing_files:
            # 匹配 _数字.json 的模式
            match = re.search(r'_(\d+)\.json$', f)
            if match:
                iteration_numbers.append(int(match.group(1)))
        
        # 确定下一个迭代次数
        if iteration_numbers:
            iteration_number = max(iteration_numbers) + 1
        else:
            iteration_number = 1
    else:
        iteration_number = iteration
    
    print(f"当前迭代次数: {iteration_number}")
    
    results = {}
    
    # 5. Cluster loop analysis
    for cluster_label, cluster_data in clusters_data.items():
        fn_context = ""
        functions_info = cluster_data.get("functions_info", [])
        
        for func_info in functions_info:
            fn_name = func_info.get("function_name", "")
            return_type = func_info.get("return_type", "")
            parameters = func_info.get("parameters", {})
            file_path = func_info.get("file_path", "")
            
            # Get summary if available
            summary = fn_summaries.get(fn_name, {}).get("summary", "No previous summary available.")
            
            # Build parameter string
            param_str = ", ".join([f"{param_name}: {param_type}" for param_name, param_type in parameters.items()])
            
            fn_context += f"\nFunction: {fn_name}\n"
            fn_context += f"Return type: {return_type}\n"
            fn_context += f"Parameters: {param_str}\n"
            fn_context += f"File: {file_path}\n"
            fn_context += f"Summary: {summary}\n"
            
            # Try to get function code if available
            code_snippet = "Function code not available."
            src_json = f"./tosem/data/function/{target_name}/api/src_api.json"
            if os.path.exists(src_json):
                try:
                    with open(src_json, "r", encoding="utf-8") as fs:
                        src_data = json.load(fs)
                    
                    # Search for function code in the src data
                    for file_key, file_val in src_data.get("src", {}).items():
                        fn_def_list = file_val.get("fn_def_list", [])
                        for fn_def in fn_def_list:
                            fn_meta = fn_def.get("fn_meta", {})
                            if fn_meta.get("identifier") == fn_name:
                                code_snippet = fn_def.get("fn_code", "Code not found")
                                # Truncate snippet
                                code_snippet = code_snippet[:400] + "..." if len(code_snippet) > 400 else code_snippet
                                break
                except Exception as e:
                    code_snippet = f"Error reading code: {str(e)}"
            
            fn_context += f"Code snippet:\n{code_snippet}\n"
            fn_context += "-" * 50 + "\n"

        try:
            messages = [
                SystemMessage(content="You are a software engineering researcher responsible for source code cluster analysis and understanding."),
                HumanMessage(content=f"{base_prompt}\n\nCluster ID: {cluster_label}\nNumber of functions: {len(functions_info)}\n{fn_context}")
            ]
            response = llm.invoke(messages)
            raw_output = response.content.strip()

            # Parse JSON output
            parsed = {}
            try:
                parsed = json.loads(raw_output)
                # Ensure keys exist
                parsed.setdefault("analysis", "")
                parsed.setdefault("exclude_function", [])
            except Exception as e:
                # Try regex fallback to extract analysis and exclude_function
                analysis_match = re.search(r'"analysis"\s*:\s*"([^"]+)"', raw_output)
                exclude_match = re.search(r'"exclude_function"\s*:\s*(\[.*?\])', raw_output)
                analysis_text = analysis_match.group(1) if analysis_match else raw_output
                exclude_list = json.loads(exclude_match.group(1)) if exclude_match else []
                parsed = {"analysis": analysis_text, "exclude_function": exclude_list}

        except Exception as e:
            parsed = {"analysis": f"LLM call failed: {str(e)}", "exclude_function": []}

        results[cluster_label] = {
            "function_count": len(functions_info),
            "functions": [{"function_name": info["function_name"], "function_id": info["function_id"]} for info in functions_info],
            "analysis": parsed["analysis"],
            "exclude_function": parsed["exclude_function"]
        }
        
        print(f"Cluster {cluster_label}: 分析完成，排除 {len(parsed['exclude_function'])} 个函数")

    # 6. 创建新的文件夹来保存迭代结果
    iteration_dir = f"./cluster/cluster/{target_name}/{k}/iteration_{iteration_number}"
    os.makedirs(iteration_dir, exist_ok=True)
    print(f"创建迭代文件夹: {iteration_dir}")
    
    # 7. Output result JSON file with iteration number
    output_path = f"{iteration_dir}/{target_name}_cluster_analysis_{iteration_number}.json"
    with open(output_path, "w", encoding="utf-8") as wf:
        json.dump(results, wf, ensure_ascii=False, indent=4)

    print(f"第 {iteration_number} 次分析结果保存至: {output_path}")
    
    # 8. 同时生成一个简单的排除函数统计
    exclude_stats = {
        "iteration": iteration_number,
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_excluded_functions": 0,
        "exclusions_by_cluster": {}
    }
    
    total_excluded = 0
    for cluster_label, data in results.items():
        excluded_count = len(data.get("exclude_function", []))
        exclude_stats["exclusions_by_cluster"][cluster_label] = {
            "count": excluded_count,
            "functions": data.get("exclude_function", [])
        }
        total_excluded += excluded_count
    
    exclude_stats["total_excluded_functions"] = total_excluded
    
    # 保存排除统计到迭代文件夹
    stats_path = f"{iteration_dir}/{target_name}_exclude_stats_{iteration_number}.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(exclude_stats, f, ensure_ascii=False, indent=4)
    
    print(f"排除统计保存至: {stats_path}")
    print(f"本次分析共排除 {total_excluded} 个函数")
    
    return f"Cluster analysis iteration {iteration_number} completed, results saved to: {output_path}"
#重复验证函数重新归类
#@tool("reassign_excluded_functions", return_direct=True)
def reassign_excluded_functions2(target: str, iteration: int = None) -> str:
    """
    For functions excluded from clusters by LLM analysis, use LLM to reassign them to 
    one of their top 5 closest clusters (excluding the original cluster).
    
    Args:
        target: target project name
        iteration: optional iteration number (if None, will auto-increment)
    Returns:
        str: Path to reassignment result JSON file
    """
    last_underscore_index = target.rfind('_')
    
    # 分割字符串
    first_part = target[:last_underscore_index]
    second_part = target[last_underscore_index + 1:]
    target_name = first_part
    k = second_part
    
    print("--------------------------------------")
    print(f"开始重新分配排除函数: {target_name}, k={k}")
    
    # 1. 确定迭代次数
    if iteration is None:
        # 查找已有的迭代文件夹
        base_dir = f"./cluster/cluster/{target_name}/{k}/"
        # 查找 iteration_数字 格式的文件夹
        iteration_folders = [f for f in os.listdir(base_dir) 
                           if f.startswith("iteration_") and os.path.isdir(os.path.join(base_dir, f))]
        
        # 提取已有迭代次数
        iteration_numbers = []
        for folder in iteration_folders:
            match = re.search(r'iteration_(\d+)$', folder)
            if match:
                iteration_numbers.append(int(match.group(1)))
        
        # 确定下一个迭代次数
        if iteration_numbers:
            iteration_number = max(iteration_numbers)
            print(f"找到已有的迭代文件夹: {iteration_numbers}, 使用最新迭代: {iteration_number}")
        else:
            iteration_number = 1
            print(f"未找到迭代文件夹，使用迭代: {iteration_number}")
    else:
        iteration_number = iteration
    
    print(f"当前重新分配迭代次数: {iteration_number}")
    
    # 2. 创建/使用迭代文件夹
    iteration_dir = f"./cluster/cluster/{target_name}/{k}/iteration_{iteration_number}"
    os.makedirs(iteration_dir, exist_ok=True)
    print(f"使用迭代文件夹: {iteration_dir}")
    
    # 3. Load cluster analysis results from iteration folder
    # 首先尝试从迭代文件夹中读取分析文件
    analysis_path = f"{iteration_dir}/{target_name}_cluster_analysis_{iteration_number}.json"
    if not os.path.exists(analysis_path):
        # 如果迭代文件夹中没有，尝试使用默认文件
        analysis_path = f"./cluster/cluster/{target_name}/{k}/{target_name}_cluster_analysis.json"
        if not os.path.exists(analysis_path):
            return f"Cluster analysis file does not exist: {analysis_path}"
    
    print(f"使用分析文件: {analysis_path}")
    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_data = json.load(f)
    
    # 4. Load function distance data
    distance_path = f"./cluster/cluster/{target_name}/{k}/function_cluster_distances.json"
    if not os.path.exists(distance_path):
        return f"Function distance file does not exist: {distance_path}"
    
    with open(distance_path, "r", encoding="utf-8") as f:
        distance_data = json.load(f)
    
    # 5. Load cluster mapping
    cluster_path = f"./cluster/cluster/{target_name}/{k}/cluster_mapping.json"
    if not os.path.exists(cluster_path):
        return f"Cluster mapping file does not exist: {cluster_path}"
    
    with open(cluster_path, "r", encoding="utf-8") as f:
        cluster_mapping = json.load(f)
    
    # 6. Collect all excluded functions
    excluded_functions = []
    for cluster_id, cluster_analysis in analysis_data.items():
        exclude_list = cluster_analysis.get("exclude_function", [])
        for func_name in exclude_list:
            # Find the function in distance data
            func_data = None
            for func_id, dist_info in distance_data.items():
                if dist_info.get("function_name") == func_name:
                    func_data = {
                        "function_name": func_name,
                        "function_id": func_id,
                        "original_cluster": cluster_id,
                        "distance_info": dist_info
                    }
                    break
            
            if func_data:
                excluded_functions.append(func_data)
    
    if not excluded_functions:
        print(f"第 {iteration_number} 次: 没有发现需要重新分配的排除函数")
        
        # 即使没有排除函数，也保存结果文件到迭代文件夹中
        # 保存空的结果文件
        reassign_path = f"{iteration_dir}/{target_name}_reassignment_results_{iteration_number}.json"
        empty_results = {
            "iteration": iteration_number,
            "timestamp": pd.Timestamp.now().isoformat(),
            "message": "No excluded functions found for reassignment",
            "excluded_functions_count": 0,
            "reassignment_results": {}
        }
        with open(reassign_path, "w", encoding="utf-8") as f:
            json.dump(empty_results, f, ensure_ascii=False, indent=4)
        
        # 复制原始聚类映射作为更新后的映射
        updated_mapping_path = f"{iteration_dir}/{target_name}_updated_cluster_mapping_{iteration_number}.json"
        with open(updated_mapping_path, "w", encoding="utf-8") as f:
            json.dump(cluster_mapping, f, ensure_ascii=False, indent=4)
        
        print(f"空结果保存至迭代文件夹: {iteration_dir}")
        return f"Reassignment iteration {iteration_number}: No excluded functions found. Empty results saved to {reassign_path}"
    
    print(f"第 {iteration_number} 次: 发现 {len(excluded_functions)} 个需要重新分配的排除函数:")
    for func in excluded_functions:
        print(f"  - {func['function_name']} (来自聚类 {func['original_cluster']})")
    
    # 7. Load previous function summary file (如果存在)
    summary_path = f"./tosem/data/function/{target_name}/api/src_api_summary.json"
    fn_summaries = {}
    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                fn_summaries = json.load(f)
        except Exception:
            print("Warning: Could not load function summaries, proceeding without them.")

    # 8. Build reassignment prompt
    base_prompt = (
    "TASK: Reassign an excluded function to the most appropriate alternative cluster.\n\n"
    "CONTEXT:\n"
    "A function was excluded from cluster {original_cluster}. "
    "You must select the best alternative from the candidate clusters below.\n\n"
    "CRITERIA FOR SELECTION:\n"
    "1. Functional similarity with cluster's purpose\n"
    "2. Consistency in parameter and return type patterns\n"
    "3. Overall behavioral alignment\n\n"
    "FUNCTION TO REASSIGN:\n"
    "{function_info}\n\n"
    "CANDIDATE CLUSTERS (excluding original cluster {original_cluster}):\n"
    "{cluster_descriptions}\n\n"
    "OUTPUT REQUIREMENTS:\n"
    "- You MUST output ONLY valid JSON\n"
    "- No additional text, explanations, or formatting\n"
    "- Use exactly this structure:\n"
    "{{\n"
    '  "selected_cluster": "cluster_id",\n'
    '  "reasoning": "your explanation here"\n'
    "}}\n\n"
    "VALID EXAMPLE OUTPUT:\n"
    '{{"selected_cluster": "2", "reasoning": "Matches image processing functions in cluster 2"}}\n\n'
    "Begin your response with '{{' and end with '}}'. No other text."
    )
    
    reassignment_results = {}
    
    # 9. Process each excluded function
    for idx, func_data in enumerate(excluded_functions, 1):
        func_name = func_data["function_name"]
        func_id = func_data["function_id"]
        original_cluster = func_data["original_cluster"]
        distance_info = func_data["distance_info"]
        
        print(f"[{idx}/{len(excluded_functions)}] 正在处理: {func_name}")
        
        # Get top 5 closest clusters (excluding original)
        all_distances = distance_info.get("all_distances", {})
        
        # Sort clusters by distance and exclude original
        sorted_clusters = sorted(all_distances.items(), key=lambda x: x[1])
        candidate_clusters = []
        
        for cluster_id, distance in sorted_clusters:
            if str(cluster_id) != str(original_cluster) and len(candidate_clusters) < 5:
                candidate_clusters.append((str(cluster_id), distance))
        
        if not candidate_clusters:
            print(f"  {func_name}: 没有找到替代聚类，保持原始分配")
            reassignment_results[func_id] = {
                "function_name": func_name,
                "original_cluster": original_cluster,
                "selected_cluster": original_cluster,
                "reasoning": "No alternative clusters available",
                "candidate_clusters": [],
                "iteration": iteration_number
            }
            continue
        
        # Get cluster descriptions for candidate clusters
        cluster_descriptions = ""
        for cluster_id, distance in candidate_clusters:
            cluster_analysis = analysis_data.get(str(cluster_id), {})
            analysis_text = cluster_analysis.get("analysis", "No analysis available")
            function_count = cluster_analysis.get("function_count", 0)
            
            # Get sample functions from the cluster
            cluster_funcs = cluster_mapping.get(str(cluster_id), {}).get("functions_info", [])
            sample_funcs = [f["function_name"] for f in cluster_funcs[:3]]
            
            cluster_descriptions += f"Cluster {cluster_id} (distance: {distance:.4f}):\n"
            cluster_descriptions += f"  Analysis: {analysis_text}\n"
            cluster_descriptions += f"  Function count: {function_count}\n"
            cluster_descriptions += f"  Sample functions: {', '.join(sample_funcs)}\n\n"
        
        # Build function information
        function_info = f"Function: {func_name}\n"
        function_info += f"Original cluster: {original_cluster}\n"
        function_info += f"File: {distance_info.get('file_path', 'Unknown')}\n"
        
        # Try to get function code and parameters from source data
        src_json = f"./tosem/data/function/{target_name}/api/src_api.json"
        if os.path.exists(src_json):
            try:
                with open(src_json, "r", encoding="utf-8") as fs:
                    src_data = json.load(fs)
                
                # Search for function in source data
                for file_key, file_val in src_data.get("src", {}).items():
                    fn_def_list = file_val.get("fn_def_list", [])
                    for fn_def in fn_def_list:
                        fn_meta = fn_def.get("fn_meta", {})
                        if fn_meta.get("identifier") == func_name:
                            return_type = fn_meta.get("return_type", "unknown")
                            parameters = fn_meta.get("parameters", {})
                            code_snippet = fn_def.get("fn_code", "")[:300] + "..." if len(fn_def.get("fn_code", "")) > 300 else fn_def.get("fn_code", "")
                            
                            function_info += f"Return type: {return_type}\n"
                            function_info += f"Parameters: {parameters}\n"
                            function_info += f"Code snippet:\n{code_snippet}\n"
                            break
            except Exception as e:
                function_info += f"Error reading function details: {str(e)}\n"
        
        # Call LLM for reassignment decision
        try:
            prompt = base_prompt.format(
                original_cluster=original_cluster,
                cluster_descriptions=cluster_descriptions,
                function_info=function_info
            )
            
            messages = [
                SystemMessage(content="""You are a JSON-only assistant. You must output exactly and only valid JSON format.

CRITICAL RULES:
1. Your entire response must be a single JSON object
2. No text before or after the JSON
3. No markdown code blocks (no ```json)
4. No additional explanations
5. JSON must contain exactly: "selected_cluster" and "reasoning" fields
6. Both values must be strings

Your response will be parsed by code, so format errors will break the system. Output ONLY the JSON object."""),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            raw_output = response.content.strip()
            
            # Parse LLM response
            def safe_parse_llm_response(raw_output):
                try:
                    cleaned = raw_output.strip()
                    if cleaned.startswith('```json'):
                        cleaned = cleaned[7:]
                    if cleaned.startswith('```'):
                        cleaned = cleaned[3:]
                    if cleaned.endswith('```'):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()
                    
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    try:
                        json_match = re.search(r'\{[^{}]*"selected_cluster"[^{}]*\}', cleaned)
                        if json_match:
                            return json.loads(json_match.group())
                    except:
                        pass
                    
                    try:
                        cluster_match = re.search(r'"selected_cluster"\s*:\s*"([^"]+)"', cleaned)
                        reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', cleaned)
                        if cluster_match:
                            result = {"selected_cluster": cluster_match.group(1)}
                            if reasoning_match:
                                result["reasoning"] = reasoning_match.group(1)
                            else:
                                result["reasoning"] = "从响应中提取"
                            return result
                    except:
                        pass
                    
                    return None
            
            parsed = safe_parse_llm_response(raw_output)
            if parsed and "selected_cluster" in parsed:
                selected_cluster = parsed["selected_cluster"]
                reasoning = parsed.get("reasoning", "No reasoning provided")
                
                # Validate selected cluster is in candidate list
                candidate_ids = [cid for cid, _ in candidate_clusters]
                if selected_cluster not in candidate_ids:
                    selected_cluster = candidate_clusters[0][0]
                    reasoning = f"Invalid selection, defaulted to closest cluster. {reasoning}"
                
            else:
                selected_cluster = candidate_clusters[0][0]
                reasoning = f"Failed to parse LLM response, using closest cluster. Raw output: {raw_output[:200]}"
                print(f"  {func_name}: LLM响应解析失败")
            
        except Exception as e:
            selected_cluster = candidate_clusters[0][0]
            reasoning = f"LLM call failed, using closest cluster. Error: {str(e)}"
            print(f"  {func_name}: LLM调用失败 - {str(e)}")
        
        reassignment_results[func_id] = {
            "function_name": func_name,
            "original_cluster": original_cluster,
            "selected_cluster": selected_cluster,
            "reasoning": reasoning,
            "candidate_clusters": [{"cluster_id": cid, "distance": dist} for cid, dist in candidate_clusters],
            "all_distances": all_distances,
            "iteration": iteration_number,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        print(f"  {func_name}: {original_cluster} -> {selected_cluster}")
        
        # 添加延迟避免速率限制
        import time
        time.sleep(1)
    
    # 10. Generate updated cluster mapping
    updated_cluster_mapping = cluster_mapping.copy()
    
    # Remove excluded functions from original clusters
    for func_id, reassign_data in reassignment_results.items():
        original_cluster = reassign_data["original_cluster"]
        func_name = reassign_data["function_name"]
        
        # Remove from original cluster
        if str(original_cluster) in updated_cluster_mapping:
            cluster_data = updated_cluster_mapping[str(original_cluster)]
            if "function_ids" in cluster_data:
                cluster_data["function_ids"] = [fid for fid in cluster_data["function_ids"] if fid != func_id]
            if "functions_info" in cluster_data:
                cluster_data["functions_info"] = [finfo for finfo in cluster_data["functions_info"] if finfo.get("function_name") != func_name]
            cluster_data["function_count"] = len(cluster_data.get("function_ids", []))
    
    # Add to new clusters
    for func_id, reassign_data in reassignment_results.items():
        selected_cluster = reassign_data["selected_cluster"]
        func_name = reassign_data["function_name"]
        
        # Find original function info
        original_info = None
        for cluster_id, cluster_data in cluster_mapping.items():
            for finfo in cluster_data.get("functions_info", []):
                if finfo.get("function_name") == func_name:
                    original_info = finfo
                    break
            if original_info:
                break
        
        if original_info:
            # Add to selected cluster
            if str(selected_cluster) not in updated_cluster_mapping:
                updated_cluster_mapping[str(selected_cluster)] = {
                    "function_count": 0,
                    "function_ids": [],
                    "functions_info": []
                }
            
            cluster_data = updated_cluster_mapping[str(selected_cluster)]
            if func_id not in cluster_data["function_ids"]:
                cluster_data["function_ids"].append(func_id)
                cluster_data["functions_info"].append(original_info)
                cluster_data["function_count"] = len(cluster_data["function_ids"])
    
    # 11. Save results to iteration folder
    # Save reassignment results
    reassign_path = f"{iteration_dir}/{target_name}_reassignment_results_{iteration_number}.json"
    reassignment_data = {
        "iteration": iteration_number,
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_excluded_functions": len(excluded_functions),
        "successfully_reassigned": len([r for r in reassignment_results.values() if r["selected_cluster"] != r["original_cluster"]]),
        "reassignment_results": reassignment_results
    }
    with open(reassign_path, "w", encoding="utf-8") as f:
        json.dump(reassignment_data, f, ensure_ascii=False, indent=4)
    
    # Save updated cluster mapping
    updated_mapping_path = f"{iteration_dir}/{target_name}_updated_cluster_mapping_{iteration_number}.json"
    with open(updated_mapping_path, "w", encoding="utf-8") as f:
        json.dump(updated_cluster_mapping, f, ensure_ascii=False, indent=4)
    
    # Save summary
    summary = {
        "iteration": iteration_number,
        "timestamp": pd.Timestamp.now().isoformat(),
        "total_excluded_functions": len(excluded_functions),
        "reassignment_summary": {
            str(cluster_id): len([r for r in reassignment_results.values() if r["selected_cluster"] == str(cluster_id)])
            for cluster_id in set(r["selected_cluster"] for r in reassignment_results.values())
        },
        "original_vs_new": [
            {
                "function": r["function_name"],
                "original_cluster": r["original_cluster"],
                "new_cluster": r["selected_cluster"]
            }
            for r in reassignment_results.values()
        ]
    }
    
    summary_path = f"{iteration_dir}/{target_name}_reassignment_summary_{iteration_number}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=4)
    
    # 12. 生成统计报告
    stats_report = {
        "iteration": iteration_number,
        "timestamp": pd.Timestamp.now().isoformat(),
        "target": target_name,
        "k": k,
        "total_functions_reassigned": len(reassignment_results),
        "functions_kept_in_original": len([r for r in reassignment_results.values() if r["selected_cluster"] == r["original_cluster"]]),
        "functions_moved": len([r for r in reassignment_results.values() if r["selected_cluster"] != r["original_cluster"]]),
        "move_rate": len([r for r in reassignment_results.values() if r["selected_cluster"] != r["original_cluster"]]) / max(len(reassignment_results), 1),
        "cluster_changes": summary["reassignment_summary"]
    }
    
    stats_path = f"{iteration_dir}/{target_name}_reassignment_stats_{iteration_number}.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats_report, f, ensure_ascii=False, indent=4)
    
    print(f"第 {iteration_number} 次重新分配完成:")
    print(f"  排除函数总数: {len(excluded_functions)}")
    print(f"  重新分配数量: {stats_report['functions_moved']}")
    print(f"  保留在原聚类: {stats_report['functions_kept_in_original']}")
    print(f"  移动率: {stats_report['move_rate']:.2%}")
    print(f"  结果文件保存在迭代文件夹:")
    print(f"    - {reassign_path}")
    print(f"    - {updated_mapping_path}")
    print(f"    - {summary_path}")
    print(f"    - {stats_path}")
    
    return f"Reassignment iteration {iteration_number} completed. Results saved to:\n- {reassign_path}\n- {updated_mapping_path}\n- {summary_path}\n- {stats_path}"

if __name__ == "__main__":
    #目标库_聚类个数
    #analyze_function_code("gif2png")
    #analyze_function_clusters1("gif2png_5")
    #reassign_excluded_functions1("gif2png_5")
    #analyze_function_clusters2("gif2png_20", 1)
    reassign_excluded_functions2("gif2png_20", 1)