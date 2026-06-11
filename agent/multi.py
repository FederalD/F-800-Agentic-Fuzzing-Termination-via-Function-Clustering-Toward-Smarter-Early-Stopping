import os
import re
import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
from cluster import analyze_function_code, analyze_function_clusters1, reassign_excluded_functions1
from coverage import generate_function_coverage, add_execution_counts_to_json_simple, analyze_cluster_coverage_pure_iterative, calculate_coverage_totals

directory_path = './fuzzer_coverage'
#lib_name = ['gif2png', 'jasper', 'libpcap', 'libtiff', 'libxml2', 'nm', 'objdump', 'size']
lib_name = ['nm', 'objdump', 'size']
lib_clusters = {'gif2png':'gif2png_20', 'jasper':'jasper_14', 'libpcap':'libpcap_96', 'libtiff':'libtiff_67', 'libxml2':'libxml2_122', 'nm':'nm_77', 'objdump':'objdump_98', 'size':'size_91'}
target_dict = {'gif2png':'Gif2png', 'jasper':'JasPer','libpcap':'Libpcap','libtiff':'LibTIFF','libxml2':'Libxml2','nm':'nm','objdump':'objdump','size':'size'}
fuzzer_dict = {'afl':'AFL', 'aflfast':'AFLFast', 'aflpp':'AFL++', 'aflsmart':'AFLSmart', 'fairfuzz':'FairFuzz', 'honggfuzz':'Honggfuzz', 'mopt_afl':'MOpt-AFL', 'mopt_aflpp':'MOpt-AFL++'}

# 列标题列表
column_names = [
    "Subject", "Fuzzer", "Seed_Type", "Trial_Nr", "Timeout",
    "Model", "Cutoff", "N_Fct_Src_Cov", "N_Fct_Src_All", "Ratio_Fct_Src_Cov",
    "N_Cluster_Cov", "N_Cluster_All", "Ratio_Cluster_Cov",
    "N_LLM_Cluster_Cov", "N_LLM_Cluster_All", "Ratio_LLM_Cluster_Cov",
    "N_Dfc_Src_Cov", "N_Dfc_Src_All", "Ratio_Dfc_Src_Cov",
    #"N_Dfc_Bug_Cov", "N_Dfc_Bug_All", "Ratio_Dfc_Bug_Cov",
    "N_Bug_Trg", "N_Bug_All", "Ratio_Bug_Trg",
    "N_Crash_Trg", "N_Crash_All", "Ratio_Crash_Trg"
]

# 读取 CSV 文件
def read_csv_file(filename):
    return pd.read_csv(filename)

#对三个求一下sum，生成三个list
def converge(root_directory, target, fuzzer, trial, type, cutoff, k):

    exec_file = root_directory + "/fun_cov.csv"
    #dfc_info.csv
    dfc_exec_file = root_directory + "/function_no_id_re3333333333.csv"
    bug_file = root_directory + "/bug_info.csv"
    crash_file = root_directory + "/crash_info.csv"
    #save_file = "cluster_fuzzer_cov_data_part.csv"
    save_file = f"./cluster/cluster/{target}/{k}/cluster_fuzzer_cov_data.csv"
    sim_file = root_directory + '/fun_cov_similar.csv'
    agent_file = root_directory + f"/{k}_coverage_list.json"

    exec_df = read_csv_file(exec_file)
    bug_df = read_csv_file(bug_file)
    crash_df = read_csv_file(crash_file)
    dfc_exec_df = read_csv_file(dfc_exec_file)
    sim_df = read_csv_file(sim_file)
    df = pd.DataFrame(columns = column_names)
    with open(agent_file, 'r', encoding='utf-8') as file:
        agent_list = json.load(file)
    exec_list = []
    bug_list = []
    crash_list = []
    dfc_exec_list = []
    sim_list = []
    
    # 使用MultiIndex.from_product生成所有行索引组合
    #index = pd.MultiIndex.from_product([subjects, fuzzers, seeds, trials, timeouts, models, cuts], names=column_names)
    # 创建DataFrame并分配数据
    #df = pd.DataFrame(index=index)

    tmp_columns = [col for col in exec_df.columns if col.startswith('Execution Count in time')]
    i = 0
    for col in tmp_columns:
        if i == 0:
            i = 1
            continue
        exec_list.append(exec_df[col].sum())
        bug_list.append(bug_df[col].sum())
        crash_list.append(crash_df[col].sum())
        dfc_exec_list.append(dfc_exec_df[col].sum())
        sim_list.append(sim_df[col][sim_df[col] != 0].nunique())
    #print(exec_list)
    # 遍历Timeout列表，为每个值添加一行
    i = 0
    # 使用range生成序列，然后转换为列表
    timeouts = list(range(15, 1440 + 1, 15))
    for timeout in timeouts:
        df = df._append({'Subject': target, 'Fuzzer': fuzzer, 'Seed_Type': 'non-empty', 'Timeout': timeout, 'N_Cluster_Cov': sim_list[i]
        , 'N_Cluster_All': 20, 'N_Fct_Src_Cov': exec_list[i]
        , 'N_LLM_Cluster_Cov': agent_list[i+1], 'N_LLM_Cluster_ALL': exec_list[i]
        , 'N_Fct_Src_All': exec_df.shape[0], 'N_Dfc_Src_Cov': k, 'N_Dfc_Src_All': dfc_exec_df.shape[0], 'N_Bug_Trg': bug_list[i] 
        , 'N_Bug_All': bug_list[95], 'N_Crash_Trg': crash_list[i], 'N_Crash_All': crash_list[95], 'Model': type, 'Trial_Nr': trial, 'Cutoff': cutoff
        }, ignore_index=True)
        i += 1

    if not os.path.exists(save_file):
    # 如果文件不存在，写入时添加 header
        df.to_csv(save_file, mode='w', header=True, index=False)
    else:
    # 如果文件已存在，写入时不添加 header
        df.to_csv(save_file, mode='a', header=False, index=False)
    #df.to_csv(save_file, mode='a', header=False,index = False)#header?
    print(trial)
    print(f'save file{root_directory} to fuzz_cov_data')
    return 

def cluster_analysis():
    """原有的集群分析函数"""
    for lib in lib_name:
        analyze_function_code(lib)
        analyze_function_clusters1(lib_clusters[lib])
        reassign_excluded_functions1(lib_clusters[lib])
    return

def main():
    """原有的主函数"""
    type = 'deepseek'
    cutoff = '00'
    entries = os.listdir(directory_path)
    files = [entry for entry in entries if os.path.isdir(os.path.join(directory_path, entry))]
    for file in files:
        #根据文件名，获取greenfuzz需要的库的信息
        #folder_name = "freetype2_honggfuzz_seed_01_run_04"
        root_directory = directory_path + '/' + file 
        pattern = r"(?P<target>[A-Za-z0-9]+)_(?P<fuzzer>\w+)_seed_(?P<seed>\d+)_run_(?P<trial>\d+)"
        match = re.match(pattern, file)
        if match :
            if match.group(3) == '01':
                continue
        if match == None:#匹配libtiff_aflfast_run_01捕获组只有三个元素
            pattern1 = r"(?P<target>[A-Za-z0-9]+)_(?P<fuzzer>\w+)_run_(?P<trial>\d+)"
            match = re.match(pattern1, file)
        if match: 
            if match.group(2) == 'eclipser':
                continue                                                                                             
            if match.group(1) not in lib_name:
                continue
            #if match.group(2) != 'aflsmart':
            #    continue

            print(root_directory)
            #print("enter file: "+ directory_path + '/' + file)
            target = target_dict[match.groups(0)[0]]
            fuzzer = fuzzer_dict[match.groups(0)[1]]
            trial = int(match.groups('trial')[-1])
            print(int(match.groups('trial')[-1]))

            lib_cluster = lib_clusters[match.groups(0)[0]]
            last_underscore_index = lib_cluster.rfind('_')
    
            # 分割字符串
            first_part = lib_cluster[:last_underscore_index]
            second_part = lib_cluster[last_underscore_index + 1:]
            k = second_part

            generate_function_coverage(file)
            csv_file_path = root_directory + "/function_coverage.csv"
            json_file_path = f"./cluster/cluster/{match.groups(0)[0]}/{k}/{match.groups(0)[0]}_updated_cluster_mapping.json"
            output_file_path = root_directory + "/enhanced_data.json"
            add_execution_counts_to_json_simple(csv_file_path, json_file_path, output_file_path)
            analyze_cluster_coverage_pure_iterative(root_directory, match.groups(0)[0], k)
            calculate_coverage_totals(root_directory + "/gif2png_pure_iterative_coverage.json", k)
            #similar_directory = 'D:/TEST/cluster/cluster_final/size_k92.csv'
            converge(root_directory, target, fuzzer, trial, type, cutoff, k)

# ==================== 14核优化多线程版本 ====================

def cluster_analysis_parallel():
    """多线程集群分析 - 14核优化"""
    print("开始多线程集群分析...")
    print(f"使用 6 个线程并行处理 {len(lib_name)} 个库")
    
    def analyze_lib(lib):
        try:
            print(f"正在分析库: {lib}")
            analyze_function_code(lib)
            analyze_function_clusters1(lib_clusters[lib])
            reassign_excluded_functions1(lib_clusters[lib])
            return f"✓ 完成 {lib} 集群分析"
        except Exception as e:
            return f"✗ 错误 {lib}: {str(e)}"
    
    results = []
    # 14核CPU：使用6个线程处理5个库（充分利用资源）
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(analyze_lib, lib): lib for lib in lib_name}
        for future in as_completed(futures):
            lib = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(result)
            except Exception as e:
                error_msg = f"✗ {lib} 异常: {e}"
                results.append(error_msg)
                print(error_msg)
    
    # 检查是否有失败的分析
    failed_analyses = [r for r in results if '✗' in r]
    if failed_analyses:
        print(f"\n警告: {len(failed_analyses)} 个库的集群分析失败")
        for failed in failed_analyses:
            print(f"  {failed}")
    
    return results

def process_single_directory(file):
    """处理单个目录 - 依赖集群分析结果"""
    root_directory = os.path.join(directory_path, file)
    
    # 文件名解析
    pattern = r"(?P<target>[A-Za-z0-9]+)_(?P<fuzzer>\w+)_seed_(?P<seed>\d+)_run_01"
    match = re.match(pattern, file)
    
    if match and match.group(3) == '01':
        return f"跳过 {file}: seed 01"
    
    if not match:
        pattern1 = r"(?P<target>[A-Za-z0-9]+)_(?P<fuzzer>\w+)_run_01"
        match = re.match(pattern1, file)
    
    if not match:
        return f"跳过 {file}: 文件名不匹配"
    
    if match.group(2) == 'eclipser':
        return f"跳过 {file}: eclipser"
    
    target_name = match.group(1)
    if target_name not in lib_name:
        return f"跳过 {file}: 不在目标库列表中"
    
    print(f"处理: {file}")
    target = target_dict[target_name]
    fuzzer = fuzzer_dict[match.group(2)]
    trial = 1
    k = lib_clusters[target_name].split('_')[-1]
    
    # 检查集群分析结果文件是否存在
    cluster_json_path = f"./cluster/cluster/{target_name}/{k}/{target_name}_updated_cluster_mapping.json"
    if not os.path.exists(cluster_json_path):
        return f"✗ 跳过 {file}: 集群分析结果文件不存在 - {cluster_json_path}"
    
    try:
        # 生成函数覆盖率
        generate_function_coverage(file)
        
        # 处理覆盖率数据
        csv_file_path = os.path.join(root_directory, "function_coverage.csv")
        output_file_path = os.path.join(root_directory, f"{k}_enhanced_data.json")
        
        add_execution_counts_to_json_simple(csv_file_path, cluster_json_path, output_file_path)
        analyze_cluster_coverage_pure_iterative(root_directory, target_name, k)
        calculate_coverage_totals(os.path.join(root_directory, f"{target_name}_{k}_pure_iterative_coverage.json"), k)
        
        # 收敛处理
        converge(root_directory, target, fuzzer, trial, 'deepseek', '00', k)
        return f"✓ 完成 {file}"
        
    except Exception as e:
        return f"✗ 错误 {file}: {str(e)}"

def process_directories_parallel():
    """多线程处理目录 - 14核优化"""
    print("\n开始多线程处理目录...")
    
    entries = os.listdir(directory_path)
    directories = [entry for entry in entries if os.path.isdir(os.path.join(directory_path, entry))]
    
    print(f"发现 {len(directories)} 个目录，使用 8 个线程并行处理")
    
    completed = 0
    errors = 0
    skipped = 0
    
    # 14核CPU：使用8个线程处理目录（留出资源给系统和其他应用）
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_single_directory, dir): dir for dir in directories}
        
        for future in as_completed(futures):
            dir_name = futures[future]
            try:
                result = future.result()
                print(result)
                if "✓ 完成" in result:
                    completed += 1
                elif "✗ 错误" in result:
                    errors += 1
                else:
                    skipped += 1
            except Exception as e:
                error_msg = f"✗ 异常 {dir_name}: {e}"
                print(error_msg)
                errors += 1
    
    return completed, errors, skipped

def main_parallel():
    """多线程主函数 - 14核优化版本"""
    import time
    total_start = time.time()
    
    print("=" * 60)
    print("14核CPU优化多线程处理流程")
    print("=" * 60)
    print(f"CPU核心数: 14")
    print(f"库数量: {len(lib_name)}")
    print(f"集群分析线程数: 6")
    print(f"目录处理线程数: 8")
    print("=" * 60)
    
    # 第一步：多线程集群分析（必须先完成）
    print("\n步骤 1/2: 执行集群分析")
    cluster_start = time.time()
    #cluster_results = cluster_analysis_parallel()
    cluster_time = time.time() - cluster_start
    print(f"集群分析完成，耗时: {cluster_time:.2f} 秒")
    
    # 第二步：多线程处理目录（依赖集群分析结果）
    print("\n步骤 2/2: 处理目录文件")
    dir_start = time.time()
    completed, errors, skipped = process_directories_parallel()
    dir_time = time.time() - dir_start
    
    total_time = time.time() - total_start
    
    # 输出统计结果
    print("\n" + "=" * 60)
    print("处理完成统计")
    print("=" * 60)
    print(f"集群分析耗时: {cluster_time:.2f} 秒")
    print(f"目录处理耗时: {dir_time:.2f} 秒")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"并行加速比: {(cluster_time + dir_time) / total_time:.2f}x")
    print(f"\n处理结果:")
    print(f"  ✓ 成功: {completed}")
    print(f"  ✗ 错误: {errors}")
    print(f"  ⚠ 跳过: {skipped}")
    print(f"  总计: {completed + errors + skipped}")

def main_parallel_aggressive():
    """激进模式 - 最大化利用14核CPU"""
    import time
    total_start = time.time()
    
    print("=" * 60)
    print("14核CPU激进模式多线程处理")
    print("=" * 60)
    print(f"CPU核心数: 14")
    print(f"集群分析线程数: 8")
    print(f"目录处理线程数: 10")
    print("警告: 此模式可能会影响系统响应")
    print("=" * 60)
    
    # 激进模式：使用更多线程
    def cluster_analysis_aggressive():
        print("开始激进模式集群分析...")
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(
                lambda lib: (analyze_function_code(lib), 
                           analyze_function_clusters1(lib_clusters[lib]),
                           reassign_excluded_functions1(lib_clusters[lib]),
                           f"✓ 完成 {lib}")[3], lib): lib for lib in lib_name}
            for future in as_completed(futures):
                lib = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(result)
                except Exception as e:
                    error_msg = f"✗ {lib} 异常: {e}"
                    results.append(error_msg)
                    print(error_msg)
        return results
    
    def process_directories_aggressive():
        entries = os.listdir(directory_path)
        directories = [entry for entry in entries if os.path.isdir(os.path.join(directory_path, entry))]
        print(f"使用14个线程处理 {len(directories)} 个目录")
        
        completed, errors, skipped = 0, 0, 0
        with ThreadPoolExecutor(max_workers=14) as executor:
            futures = {executor.submit(process_single_directory, dir): dir for dir in directories}
            for future in as_completed(futures):
                dir_name = futures[future]
                try:
                    result = future.result()
                    print(result)
                    if "✓ 完成" in result: completed += 1
                    elif "✗ 错误" in result: errors += 1
                    else: skipped += 1
                except Exception as e:
                    print(f"✗ 异常 {dir_name}: {e}")
                    errors += 1
        return completed, errors, skipped
    
    # 执行激进模式
    cluster_start = time.time()
    #cluster_results = cluster_analysis_aggressive()
    cluster_time = time.time() - cluster_start
    
    dir_start = time.time()
    completed, errors, skipped = process_directories_aggressive()
    dir_time = time.time() - dir_start
    
    total_time = time.time() - total_start
    
    print(f"\n激进模式完成:")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"成功: {completed}, 错误: {errors}, 跳过: {skipped}")

if __name__ == "__main__":
    print("14核CPU多线程优化版本")
    print("选择运行模式:")
    print("1. 原有顺序版本")
    print("2. 平衡多线程版本 (推荐)")
    print("3. 激进多线程版本 (最大性能)")
    
    choice = input("请输入选择 (1, 2 或 3, 默认2): ").strip()
    
    if choice == "1":
        print("运行原有顺序版本...")
        cluster_analysis()
        main()
    elif choice == "3":
        print("运行激进多线程版本...")
        main_parallel_aggressive()
    else:
        print("运行平衡多线程版本...")
        main_parallel()