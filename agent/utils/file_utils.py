import json
def get_coverage_file_path1(target_library: str, fuzzer_tool: str, seed_type: str, run_iteration: str) -> str:
    """根据目标库、模糊测试工具、种子类型和运行迭代生成覆盖率文件路径
    
    Args:
        target_library: 目标库名称 (e.g., gif2png)
        fuzzer_tool: 模糊测试工具 (e.g., afl)  
        seed_type: 种子类型 (01 for empty, 02 for non-empty)
        run_iteration: 运行迭代 (e.g., 01, 02)
        
    Returns:
        完整的文件路径字符串
    """
    # 确保run_iteration是2位格式
    if len(run_iteration) == 1:
        run_iteration = f"0{run_iteration}"
    
    file_path = f"./fuzzer_coverage/{target_library}_{fuzzer_tool}_seed_{seed_type}_run_{run_iteration}/bb_cov.csv"
    return file_path

# 修复后的工具函数
def get_coverage_file_path(params_str: str) -> str:
    """
    根据参数生成覆盖率文件路径。
    输入应该是JSON字符串格式。
    """
    try:
        # 解析JSON参数
        params = json.loads(params_str)
        
        target_library = params.get('target_library', 'unknown')
        fuzzer_tool = params.get('fuzzing_tool', 'unknown')
        seed_type = params.get('seed_type', 'unknown')
        run_iteration = params.get('run_iteration', '1')
        
        # 生成文件路径
        if len(run_iteration) == 1:
            run_iteration = f"0{run_iteration}"
    
        file_path = f"./fuzzer_coverage/{target_library}_{fuzzer_tool}_seed_{seed_type}_run_{run_iteration}/bb_cov.csv"
        return f"覆盖率文件路径: {file_path}"
        
    except json.JSONDecodeError:
        # 如果JSON解析失败，尝试直接使用字符串
        return f"覆盖率文件路径: /fuzzing_results/{params_str}/coverage.json"