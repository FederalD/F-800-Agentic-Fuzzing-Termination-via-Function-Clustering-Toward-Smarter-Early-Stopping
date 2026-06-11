import os
import json
import csv
import re
from collections import defaultdict
from langchain.tools import tool
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# =============================================
# 初始化 LLM
# =============================================
llm = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

# =============================================
# 工具函数定义
# =============================================
def read_source_file(target: str) -> str:
    """
    Read src_api.json file, extract function definitions, and call LLM for multi-dimensional analysis.
    The generated summary will be saved as a JSON file.
    
    Args:
        target: need function analysis
    Returns:
        str: Path to the generated JSON file
    """
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
        for key, value in src_value.items():
            if key == "fn_def_list":
                for func_obj in value:
                    fn_name = func_obj["fn_meta"]["identifier"]
                    fn_code = func_obj["fn_code"]
                    api_summary[fn_name] = {
                        "code": fn_code
                    }

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

        results[fn_name] = {
            "summary": summary_text
        }

    # 4. Save JSON results
    save_dir = os.path.dirname(file_path)
    output_path = os.path.join(save_dir, "src_api_summary.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    return f"Analysis completed, results saved to: {output_path}"

# =============================================
# 聚类分析工具函数
# =============================================
@tool("analyze_function_clusters", return_direct=True)
def analyze_function_clusters(target: str) -> str:
    """
    Read clustering data from function clustering result CSV, combine with previous function summaries,
    and use LLM to analyze each cluster.

    For each cluster, output:
      - analysis: Summary of functional characteristics for this cluster
      - exclude_function: Functions that the model considers potentially misassigned (can be empty)

    Args:
        target: need cluster analysis
    Returns:
        str: Path to cluster analysis result JSON file
    """
    csv_path = f"./cluster/cluster/{target}.csv"
    # 1. Validate file path
    if not os.path.exists(csv_path):
        return f"File does not exist: {csv_path}"

    # 2. Read clustering data
    clusters = defaultdict(list)
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            cluster_label = row.get("Cluster", "").strip()
            fn_name = row.get("Function", "").strip()
            fn_address = row.get("Address", "").strip()
            clusters[cluster_label].append({
                "id": row.get("ID", "").strip(),
                "function": fn_name,
                "address": fn_address
            })

    if not clusters:
        return "No clustering data found in CSV file."

    # 3. Load previous function summary file
    summary_path = "D:\\TEST\\tosem\\data\\function\\gif2png\\api\\src_api_summary.json"
    if not os.path.exists(summary_path):
        return f"Previous function summary file does not exist: {summary_path}"

    with open(summary_path, "r", encoding="utf-8") as f:
        fn_summaries = json.load(f)

    # 4. Build analysis prompt
    base_prompt = (
        "The following is a set of functions clustered into the same category. Please analyze based on their functional descriptions and code:\n\n"
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
    for cluster_label, funcs in clusters.items():
        fn_context = ""
        for fdata in funcs:
            fn_name = fdata["function"]
            summary = fn_summaries.get(fn_name, {}).get("summary", "No previous summary available.")
            code_snippet = "Function code not found."

            # Try to read function source code
            src_json = "D:\\TEST\\tosem\\data\\function\\gif2png\\api\\src_api.json"
            if os.path.exists(src_json):
                try:
                    with open(src_json, "r", encoding="utf-8") as fs:
                        src_data = json.load(fs)
                    for _, src_val in src_data.get("src", {}).items():
                        for k, v in src_val.items():
                            if k == "fn_def_list":
                                for item in v:
                                    if item["fn_meta"]["identifier"] == fn_name:
                                        code_snippet = item["fn_code"]
                                        break
                    # Truncate snippet
                    code_snippet = code_snippet[:400] + "..." if len(code_snippet) > 400 else code_snippet
                except Exception:
                    pass

            fn_context += f"\nFunction name: {fn_name}\nSummary: {summary}\nCode:\n{code_snippet}\n"

        try:
            messages = [
                SystemMessage(content="You are a software engineering researcher responsible for source code cluster analysis and understanding."),
                HumanMessage(content=f"{base_prompt}\n\nCluster ID: {cluster_label}\n{fn_context}")
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
            except Exception:
                # Try regex fallback to extract analysis and exclude_function
                analysis_match = re.search(r'"analysis"\s*:\s*"([^"]+)"', raw_output)
                exclude_match = re.search(r'"exclude_function"\s*:\s*(\[.*?\])', raw_output)
                analysis_text = analysis_match.group(1) if analysis_match else raw_output
                exclude_list = json.loads(exclude_match.group(1)) if exclude_match else []
                parsed = {"analysis": analysis_text, "exclude_function": exclude_list}

        except Exception as e:
            parsed = {"analysis": f"LLM call failed: {str(e)}", "exclude_function": []}

        results[cluster_label] = {
            "functions": funcs,
            "analysis": parsed["analysis"],
            "exclude_function": parsed["exclude_function"]
        }

    # 6. Output result JSON file
    output_path = os.path.join(os.path.dirname(csv_path), "gif2png_cluster_analysis.json")
    with open(output_path, "w", encoding="utf-8") as wf:
        json.dump(results, wf, ensure_ascii=False, indent=4)

    return f"Cluster analysis completed, results saved to: {output_path}"

if __name__ == "__main__":
    read_source_file("gif2png")