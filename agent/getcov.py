import os
import glob
import re
import json
import pandas as pd
from cluster import analyze_function_code, analyze_function_clusters1, reassign_excluded_functions1
from coverage import generate_function_coverage, add_execution_counts_to_json_simple, analyze_cluster_coverage_pure_iterative2, calculate_coverage_totals

directory_path = './fuzzer_coverage'
#lib_name = ['libxml2','nm','objdump','size']
lib_name = ['gif2png', 'jasper', 'libpcap', 'libtiff', 'libxml2']
lib_clusters = {'gif2png':'gif2png_20', 'jasper':'jasper_14', 'libpcap':'libpcap_96', 'libtiff':'libtiff_67', 'libxml2':'libxml2_122'}
#lib_name = ['gif2png','jasper','libpcap','libtiff','libxml2','nm','objdump','size']
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
    agent_file = root_directory + "/coverage_list.json"

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
    print(f'save file{root_directory} to fuzz_cov_data')
    return 

def cluster_analysis():
    for lib in lib_name:
        analyze_function_code(lib)
        analyze_function_clusters1(lib_clusters[lib])
        reassign_excluded_functions1(lib_clusters[lib])
    return

def main():
    
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
            output_file_path = root_directory + f"/{k}_enhanced_data.json"
            add_execution_counts_to_json_simple(csv_file_path, json_file_path, output_file_path)
            analyze_cluster_coverage_pure_iterative(root_directory, match.groups(0)[0])
            calculate_coverage_totals(root_directory + "/gif2png_pure_iterative_coverage.json")
            #similar_directory = 'D:/TEST/cluster/cluster_final/size_k92.csv'
            converge(root_directory, target, fuzzer, trial, type, cutoff, k)
        



if __name__ == "__main__":
    cluster_analysis()
    #main()