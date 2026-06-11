import json
import os

def count_rank_distribution(file_path):
    """统计排名1-5的分布"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 初始化统计
    rank_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "other": 0}
    
    for func_data in data.values():
        selected_cluster = func_data['selected_cluster']
        candidate_clusters = func_data['candidate_clusters']
        
        # 查找选择的聚类在候选列表中的排名
        rank_found = False
        for i, candidate in enumerate(candidate_clusters, 1):
            if candidate['cluster_id'] == selected_cluster:
                if 1 <= i <= 5:
                    rank_counts[i] += 1
                else:
                    rank_counts["other"] += 1
                rank_found = True
                break
        
        if not rank_found:
            rank_counts["other"] += 1
    
    return rank_counts

# 使用示例
file_path = r"D:\TEST\cluster\cluster\size\91\size_reassignment_results.json"

if os.path.exists(file_path):
    counts = count_rank_distribution(file_path)
    total = sum(counts.values())
    
    print("排名分布统计:")
    print(f"总函数数: {total}")
    for i in range(1, 6):
        print(f"最近第{i}名: {counts[i]}个 ({counts[i]/total*100:.1f}%)")
    print(f"其他排名: {counts['other']}个 ({counts['other']/total*100:.1f}%)")
else:
    print(f"文件不存在: {file_path}")