import json
import os
from copy import deepcopy


def apply_function_reassignment(
    summary_path,
    original_cluster_path,
    updated_cluster_path,
    output_path
):
    """
    根据 reassignment_summary 中的函数再分配结果，
    修复聚类映射并生成最终聚类结果。
    """

    # =========================
    # 读取 JSON
    # =========================
    with open(summary_path, "r", encoding="utf-8") as f:
        reassignment_data = json.load(f)

    with open(original_cluster_path, "r", encoding="utf-8") as f:
        original_cluster_data = json.load(f)

    with open(updated_cluster_path, "r", encoding="utf-8") as f:
        updated_cluster_data = json.load(f)

    # 深拷贝
    final_clusters = deepcopy(updated_cluster_data)

    # =========================
    # 建立函数索引
    # =========================
    function_index = {}

    for cluster_id, cluster_info in original_cluster_data.items():

        for func_info in cluster_info.get("functions_info", []):

            function_name = func_info.get("function_name")

            function_index[function_name] = {
                "cluster_id": cluster_id,
                "function_info": func_info
            }

    # =========================
    # 执行函数再分配
    # =========================
    for item in reassignment_data.get("original_vs_new", []):

        function_name = item["function"]
        original_cluster = item["original_cluster"]
        new_cluster = item["new_cluster"]

        # 未找到函数
        if function_name not in function_index:
            print(f"[WARNING] 未找到函数完整信息: {function_name}")
            continue

        func_info = function_index[function_name]["function_info"]
        function_id = func_info["function_id"]

        # =========================
        # 从原聚类删除
        # =========================
        if original_cluster in final_clusters:

            final_clusters[original_cluster]["functions_info"] = [
                f for f in final_clusters[original_cluster]["functions_info"]
                if f["function_name"] != function_name
            ]

            final_clusters[original_cluster]["function_ids"] = [
                fid for fid in final_clusters[original_cluster]["function_ids"]
                if fid != function_id
            ]

            final_clusters[original_cluster]["function_count"] = len(
                final_clusters[original_cluster]["functions_info"]
            )

        # =========================
        # 添加到新聚类
        # =========================
        if new_cluster not in final_clusters:

            final_clusters[new_cluster] = {
                "function_count": 0,
                "function_ids": [],
                "functions_info": []
            }

        # 避免重复添加
        if function_id not in final_clusters[new_cluster]["function_ids"]:

            final_clusters[new_cluster]["function_ids"].append(function_id)

            final_clusters[new_cluster]["functions_info"].append(func_info)

        # 更新数量
        final_clusters[new_cluster]["function_count"] = len(
            final_clusters[new_cluster]["functions_info"]
        )

        print(f"[INFO] {function_name}: {original_cluster} -> {new_cluster}")

    # =========================
    # 保存结果
    # =========================
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_clusters, f, indent=4, ensure_ascii=False)

    print(f"[SUCCESS] 已保存: {output_path}")

    return output_path


# =====================================================
# 批量修复八个库（主目录 + iteration_1）
# =====================================================

lib_name = [
    'gif2png',
    'jasper',
    'libpcap',
    'libtiff',
    'libxml2',
    'nm',
    'objdump',
    'size'
]

lib_clusters = {
    'gif2png': 'gif2png_20',
    'jasper': 'jasper_14',
    'libpcap': 'libpcap_96',
    'libtiff': 'libtiff_67',
    'libxml2': 'libxml2_122',
    'nm': 'nm_77',
    'objdump': 'objdump_98',
    'size': 'size_91'
}

# 根目录
base_dir = r"D:\TEST\cluster\cluster"

# =====================================================
# 遍历所有库
# =====================================================
for lib in lib_name:

    cluster_tag = lib_clusters[lib]

    # 取聚类编号
    cluster_num = cluster_tag.split("_")[-1]

    # =================================================
    # 需要处理的两个目录：
    # 1. 主目录
    # 2. iteration_1
    # =================================================
    dirs_to_process = [
        os.path.join(base_dir, lib, cluster_num),
        os.path.join(base_dir, lib, cluster_num, "iteration_1")
    ]

    # =================================================
    # 逐目录处理
    # =================================================
    for current_dir in dirs_to_process:

        print("\n===================================")
        print(f"开始处理: {current_dir}")
        print("===================================")

        summary_path = os.path.join(
            current_dir,
            f"{lib}_reassignment_summary.json"
        )

        original_cluster_path = os.path.join(
            current_dir,
            "cluster_mapping.json"
        )

        updated_cluster_path = os.path.join(
            current_dir,
            f"{lib}_updated_cluster_mapping.json"
        )

        output_path = os.path.join(
            current_dir,
            f"{lib}_final_cluster_mapping.json"
        )

        # 文件不存在则跳过
        if not os.path.exists(summary_path):
            print(f"[SKIP] 不存在: {summary_path}")
            continue

        if not os.path.exists(original_cluster_path):
            print(f"[SKIP] 不存在: {original_cluster_path}")
            continue

        if not os.path.exists(updated_cluster_path):
            print(f"[SKIP] 不存在: {updated_cluster_path}")
            continue

        try:

            apply_function_reassignment(
                summary_path=summary_path,
                original_cluster_path=original_cluster_path,
                updated_cluster_path=updated_cluster_path,
                output_path=output_path
            )

        except Exception as e:

            print(f"[ERROR] {current_dir} 处理失败")
            print(e)

print("\n===================================")
print("全部库处理完成")
print("===================================")