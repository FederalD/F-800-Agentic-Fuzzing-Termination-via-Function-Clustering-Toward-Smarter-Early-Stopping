import os
import re
import json
import pandas as pd
from cluster import analyze_function_code, analyze_function_clusters2, reassign_excluded_functions2
from coverage import generate_function_coverage, add_execution_counts_to_json_simple, analyze_cluster_coverage_pure_iterative, calculate_coverage_totals

directory_path = './fuzzer_coverage'
#lib_name = ['gif2png', 'jasper', 'libpcap', 'libtiff', 'libxml2', 'nm', 'objdump', 'size']
#lib_name = ['libxml2', 'nm', 'objdump', 'size']
lib_name = ['libtiff']
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
    print(trial)
    print(f'save file{root_directory} to fuzz_cov_data')
    return 


def main():
    """主函数"""
    type = 'deepseek'
    cutoff = '00'
    entries = os.listdir(directory_path)
    files = [entry for entry in entries if os.path.isdir(os.path.join(directory_path, entry))]
    for file in files:
        root_directory = directory_path + '/' + file 
        pattern = r"(?P<target>[A-Za-z0-9]+)_(?P<fuzzer>\w+)_seed_(?P<seed>\d+)_run_(?P<trial>\d+)"
        match = re.match(pattern, file)
        if match :
            if match.group(3) == '01':
                continue
        if match == None:
            pattern1 = r"(?P<target>[A-Za-z0-9]+)_(?P<fuzzer>\w+)_run_(?P<trial>\d+)"
            match = re.match(pattern1, file)
        if match: 
            if match.group(2) == 'eclipser':
                continue                                                                                             
            if match.group(1) not in lib_name:
                continue

            print(root_directory)
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
            converge(root_directory, target, fuzzer, trial, type, cutoff, k)

def cluster_analysis():
    """集群分析函数"""
    for lib in lib_name:
        analyze_function_code(lib)
        analyze_function_clusters1(lib_clusters[lib])
        reassign_excluded_functions1(lib_clusters[lib])
    return

import time
import json
import csv
from datetime import datetime

def cluster_analysis1():
    """集群分析函数"""
    
    # 创建时间记录数据结构
    time_records = {
        'timestamp': datetime.now().isoformat(),
        'libraries': {},
        'summary': {}
    }
    
    for lib in lib_name:
        print(f"\n{'='*60}")
        print(f"开始分析库: {lib}")
        print(f"{'='*60}")
        
        lib_time_records = {
            'analyze_function_clusters2': [],
            'reassign_excluded_functions2': [],
            'iteration_total': [],
            'overall_total': 0
        }
        
        # 使用循环重复执行20次
        repeat_times = 20#20
        total_lib_time = 0
        
        for iteration in range(repeat_times):
            print(f"\n迭代 {iteration + 1}/{repeat_times}")
            
            # 记录 analyze_function_clusters2 执行时间
            start_time = time.time()
            analyze_function_clusters2(lib_clusters[lib], iteration + 1)
            analyze_time = time.time() - start_time
            
            # 记录 reassign_excluded_functions2 执行时间
            start_time = time.time()
            reassign_excluded_functions2(lib_clusters[lib], iteration + 1)
            reassign_time = time.time() - start_time
            
            # 计算本次迭代总时间
            iteration_total = analyze_time + reassign_time
            total_lib_time += iteration_total
            
            # 保存时间记录
            lib_time_records['analyze_function_clusters2'].append(analyze_time)
            lib_time_records['reassign_excluded_functions2'].append(reassign_time)
            lib_time_records['iteration_total'].append(iteration_total)
            
            # 打印本次迭代的时间信息
            print(f"  analyze_function_clusters2: {analyze_time:.4f} 秒")
            print(f"  reassign_excluded_functions2: {reassign_time:.4f} 秒")
            print(f"  迭代总时间: {iteration_total:.4f} 秒")
        
        # 保存库的总时间
        lib_time_records['overall_total'] = total_lib_time
        
        # 计算平均时间
        lib_time_records['avg_analyze'] = sum(lib_time_records['analyze_function_clusters2']) / repeat_times
        lib_time_records['avg_reassign'] = sum(lib_time_records['reassign_excluded_functions2']) / repeat_times
        lib_time_records['avg_iteration'] = sum(lib_time_records['iteration_total']) / repeat_times
        
        # 保存到总记录
        time_records['libraries'][lib] = lib_time_records
        
        # 打印库的汇总信息
        print(f"\n{'='*60}")
        print(f"库 {lib} 汇总:")
        print(f"  总执行时间: {total_lib_time:.4f} 秒")
        print(f"  平均每次迭代: {lib_time_records['avg_iteration']:.4f} 秒")
        print(f"  平均 analyze_function_clusters2: {lib_time_records['avg_analyze']:.4f} 秒")
        print(f"  平均 reassign_excluded_functions2: {lib_time_records['avg_reassign']:.4f} 秒")
        print(f"{'='*60}")
    
    # 计算总体统计信息
    all_analyze_times = []
    all_reassign_times = []
    all_iteration_times = []
    
    for lib in time_records['libraries']:
        all_analyze_times.extend(time_records['libraries'][lib]['analyze_function_clusters2'])
        all_reassign_times.extend(time_records['libraries'][lib]['reassign_excluded_functions2'])
        all_iteration_times.extend(time_records['libraries'][lib]['iteration_total'])
    
    time_records['summary'] = {
        'total_libraries': len(time_records['libraries']),
        'total_iterations': len(all_iteration_times),
        'overall_total_time': sum(all_iteration_times),
        'avg_analyze_time': sum(all_analyze_times) / len(all_analyze_times) if all_analyze_times else 0,
        'avg_reassign_time': sum(all_reassign_times) / len(all_reassign_times) if all_reassign_times else 0,
        'avg_iteration_time': sum(all_iteration_times) / len(all_iteration_times) if all_iteration_times else 0,
        'min_analyze_time': min(all_analyze_times) if all_analyze_times else 0,
        'max_analyze_time': max(all_analyze_times) if all_analyze_times else 0,
        'min_reassign_time': min(all_reassign_times) if all_reassign_times else 0,
        'max_reassign_time': max(all_reassign_times) if all_reassign_times else 0,
    }
    
    # 保存时间数据到文件
    save_time_data(time_records)
    
    return time_records

def save_time_data(time_records):
    """保存时间数据到文件"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 保存为JSON文件（便于程序读取）
    json_filename = f"cluster_analysis_times_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(time_records, f, indent=2, ensure_ascii=False)
    print(f"\n时间数据已保存为JSON文件: {json_filename}")
    
    # 2. 保存为CSV文件（便于Excel打开）
    csv_filename = f"cluster_analysis_times_{timestamp}.csv"
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # 写入总体信息
        writer.writerow(['总体统计'])
        writer.writerow(['总库数', time_records['summary']['total_libraries']])
        writer.writerow(['总迭代次数', time_records['summary']['total_iterations']])
        writer.writerow(['总执行时间(秒)', f"{time_records['summary']['overall_total_time']:.4f}"])
        writer.writerow(['平均analyze时间(秒)', f"{time_records['summary']['avg_analyze_time']:.4f}"])
        writer.writerow(['平均reassign时间(秒)', f"{time_records['summary']['avg_reassign_time']:.4f}"])
        writer.writerow(['平均迭代时间(秒)', f"{time_records['summary']['avg_iteration_time']:.4f}"])
        writer.writerow([])
        
        # 写入每个库的详细信息
        for lib_name, lib_data in time_records['libraries'].items():
            writer.writerow([f'库: {lib_name}'])
            writer.writerow(['迭代', 'analyze_function_clusters2(秒)', 'reassign_excluded_functions2(秒)', '总时间(秒)'])
            
            for i in range(len(lib_data['analyze_function_clusters2'])):
                writer.writerow([
                    i + 1,
                    f"{lib_data['analyze_function_clusters2'][i]:.4f}",
                    f"{lib_data['reassign_excluded_functions2'][i]:.4f}",
                    f"{lib_data['iteration_total'][i]:.4f}"
                ])
            
            # 写入该库的汇总
            writer.writerow(['汇总', 
                           f"平均: {lib_data['avg_analyze']:.4f}",
                           f"平均: {lib_data['avg_reassign']:.4f}",
                           f"总计: {lib_data['overall_total']:.4f}"])
            writer.writerow([])
    
    print(f"时间数据已保存为CSV文件: {csv_filename}")
    
    # 3. 保存简要报告
    report_filename = f"cluster_analysis_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write("集群分析执行时间报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"生成时间: {time_records['timestamp']}\n")
        f.write(f"分析库数量: {time_records['summary']['total_libraries']}\n")
        f.write(f"总迭代次数: {time_records['summary']['total_iterations']}\n")
        f.write(f"总执行时间: {time_records['summary']['overall_total_time']:.2f} 秒\n")
        f.write(f"平均每次迭代: {time_records['summary']['avg_iteration_time']:.4f} 秒\n")
        f.write("\n详细统计:\n")
        f.write(f"  analyze_function_clusters2 平均时间: {time_records['summary']['avg_analyze_time']:.4f} 秒\n")
        f.write(f"  reassign_excluded_functions2 平均时间: {time_records['summary']['avg_reassign_time']:.4f} 秒\n")
        f.write(f"  analyze_function_clusters2 时间范围: [{time_records['summary']['min_analyze_time']:.4f}, {time_records['summary']['max_analyze_time']:.4f}] 秒\n")
        f.write(f"  reassign_excluded_functions2 时间范围: [{time_records['summary']['min_reassign_time']:.4f}, {time_records['summary']['max_reassign_time']:.4f}] 秒\n")
    
    print(f"简要报告已保存为: {report_filename}")
    print(f"所有时间数据文件已保存完成！")



if __name__ == "__main__":
    print("开始...")
    cluster_analysis1()
    #main()