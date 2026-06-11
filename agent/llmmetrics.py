import json
import os
import pandas as pd


# ============================================================
# 库配置
# ============================================================

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

BASE_DIR = r"D:\TEST\cluster\cluster"

MAX_ITERATIONS = 20


# ============================================================
# 读取JSON
# ============================================================

def load_json(path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# cluster-level -> function-level
# ============================================================

def cluster_to_function_mapping(cluster_json_path):

    cluster_data = load_json(cluster_json_path)

    function_mapping = {}

    for cluster_id, cluster_info in cluster_data.items():

        for func_info in cluster_info.get("functions_info", []):

            function_name = func_info["function_name"]

            function_mapping[function_name] = str(cluster_id)

    return function_mapping


# ============================================================
# Ground Truth:
# 最终正确聚类结果
# ============================================================

def build_groundtruth_mapping(lib, main_dir):

    gt_cluster_path = os.path.join(
        main_dir,
        f"{lib}_final_cluster_mapping.json"
    )

    return cluster_to_function_mapping(
        gt_cluster_path
    )


# ============================================================
# 构建原始聚类mapping
# ============================================================

def build_original_mapping(main_dir):

    original_cluster_path = os.path.join(
        main_dir,
        "cluster_mapping.json"
    )

    return cluster_to_function_mapping(
        original_cluster_path
    )


# ============================================================
# 从summary中提取LLM剔除函数
# ============================================================

def extract_removed_functions(summary_path):

    """
    返回：

    removed_functions = {
        func_name: {
            "original_cluster": xxx,
            "new_cluster": xxx
        }
    }
    """

    if not os.path.exists(summary_path):

        return {}

    data = load_json(summary_path)

    removed_functions = {}

    for item in data.get("original_vs_new", []):

        func = item["function"]

        removed_functions[func] = {
            "original_cluster": str(item["original_cluster"]),
            "new_cluster": str(item["new_cluster"])
        }

    return removed_functions


# ============================================================
# 评估LLM剔除效果
# ============================================================

def evaluate_llm_removal(
    gt_mapping,
    original_mapping,
    removed_functions
):

    """
    GroundTruth:
        final_cluster_mapping.json

    Original:
        cluster_mapping.json

    removed_functions:
        summary中的剔除结果

    ========================================================

    TP:
        本不属于原cluster，
        且被LLM成功剔除

    FP:
        本属于原cluster，
        却被LLM错误剔除

    TN:
        本属于原cluster，
        且未被剔除

    FN:
        本不属于原cluster，
        但未被剔除
    """

    TP = TN = FP = FN = 0

    details = []

    all_functions = set(gt_mapping.keys())

    for func in all_functions:

        gt_cluster = gt_mapping[func]

        original_cluster = original_mapping.get(func)

        # ====================================================
        # 是否本来就属于原cluster
        # ====================================================
        actually_should_stay = (
            gt_cluster == original_cluster
        )

        # ====================================================
        # 是否被LLM剔除
        # ====================================================
        llm_removed = (
            func in removed_functions
        )

        # ====================================================
        # TP
        # ====================================================
        if (not actually_should_stay) and llm_removed:

            TP += 1
            result = "TP"

        # ====================================================
        # TN
        # ====================================================
        elif actually_should_stay and (not llm_removed):

            TN += 1
            result = "TN"

        # ====================================================
        # FP
        # ====================================================
        elif actually_should_stay and llm_removed:

            FP += 1
            result = "FP"

        # ====================================================
        # FN
        # ====================================================
        elif (not actually_should_stay) and (not llm_removed):

            FN += 1
            result = "FN"

        else:

            result = "UNKNOWN"

        details.append({
            "function": func,
            "gt_cluster": gt_cluster,
            "original_cluster": original_cluster,
            "llm_removed": llm_removed,
            "result": result
        })

    # ========================================================
    # 指标计算
    # ========================================================

    total = TP + TN + FP + FN

    accuracy = (
        (TP + TN) / total
        if total else 0
    )

    precision = (
        TP / (TP + FP)
        if (TP + FP) else 0
    )

    recall = (
        TP / (TP + FN)
        if (TP + FN) else 0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) else 0
    )

    fpr = (
        FP / (FP + TN)
        if (FP + TN) else 0
    )

    metrics = {
        "TP": TP,
        "TN": TN,
        "FP": FP,
        "FN": FN,
        "Accuracy": round(accuracy, 4),
        "Precision": round(precision, 4),
        "Recall": round(recall, 4),
        "F1-score": round(f1, 4),
        "FPR": round(fpr, 4)
    }

    return metrics, details


# ============================================================
# 主程序
# ============================================================

if __name__ == "__main__":

    all_rows = []

    # ========================================================
    # 遍历8个库
    # ========================================================
    for lib in lib_name:

        print("\n================================================")
        print(f"开始处理: {lib}")
        print("================================================")

        cluster_tag = lib_clusters[lib]

        cluster_num = cluster_tag.split("_")[-1]

        main_dir = os.path.join(
            BASE_DIR,
            lib,
            cluster_num
        )

        # ====================================================
        # Ground Truth
        # ====================================================
        gt_mapping = build_groundtruth_mapping(
            lib,
            main_dir
        )

        # ====================================================
        # 原始聚类
        # ====================================================
        original_mapping = build_original_mapping(
            main_dir
        )

        # ====================================================
        # 遍历20轮
        # ====================================================
        for iteration_id in range(1, MAX_ITERATIONS + 1):

            iteration_dir = os.path.join(
                main_dir,
                f"iteration_{iteration_id}"
            )

            if not os.path.exists(iteration_dir):

                continue

            print("\n----------------------------------------")
            print(f"{lib} | iteration_{iteration_id}")
            print("----------------------------------------")

            # =================================================
            # summary
            # =================================================
            summary_path = os.path.join(
                iteration_dir,
                f"{lib}_reassignment_summary_{iteration_id}.json"
            )

            # =================================================
            # 不存在summary
            # 说明没有剔除
            # =================================================
            if not os.path.exists(summary_path):

                removed_functions = {}

                print("[INFO] 无summary文件")
                print("[INFO] 默认认为没有函数被剔除")

            else:

                removed_functions = extract_removed_functions(
                    summary_path
                )

            # =================================================
            # 评估
            # =================================================
            metrics, details = evaluate_llm_removal(

                gt_mapping=gt_mapping,

                original_mapping=original_mapping,

                removed_functions=removed_functions
            )

            # =================================================
            # 保存detail
            # =================================================
            detail_path = os.path.join(
                iteration_dir,
                f"{lib}_evaluation_details_{iteration_id}.json"
            )

            with open(detail_path, "w", encoding="utf-8") as f:

                json.dump(
                    details,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            # =================================================
            # 保存metrics
            # =================================================
            metrics_path = os.path.join(
                iteration_dir,
                f"{lib}_metrics_{iteration_id}.json"
            )

            with open(metrics_path, "w", encoding="utf-8") as f:

                json.dump(
                    metrics,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            # =================================================
            # 聚合
            # =================================================
            row = {
                "Library": lib,
                "Iteration": iteration_id,
                **metrics
            }

            all_rows.append(row)

            print(metrics)

    # ========================================================
    # DataFrame
    # ========================================================
    df = pd.DataFrame(all_rows)

    metric_keys = [
        "TP",
        "TN",
        "FP",
        "FN",
        "Accuracy",
        "Precision",
        "Recall",
        "F1-score",
        "FPR"
    ]

    # ========================================================
    # 每个库AVG
    # ========================================================
    avg_rows = []

    for lib in lib_name:

        lib_df = df[
            df["Library"] == lib
        ]

        if len(lib_df) == 0:
            continue

        avg_row = {
            "Library": lib,
            "Iteration": "AVG"
        }

        for key in metric_keys:

            avg_row[key] = round(
                lib_df[key].mean(),
                4
            )

        avg_rows.append(avg_row)

    # ========================================================
    # OVERALL AVG
    # ========================================================
    avg_df = pd.DataFrame(avg_rows)

    overall_row = {
        "Library": "OVERALL",
        "Iteration": "AVG"
    }

    for key in metric_keys:

        overall_row[key] = round(
            avg_df[key].mean(),
            4
        )

    avg_rows.append(overall_row)

    # ========================================================
    # 合并
    # ========================================================
    final_df = pd.concat(
        [
            df,
            pd.DataFrame(avg_rows)
        ],
        ignore_index=True
    )

    # ========================================================
    # CSV
    # ========================================================
    csv_output = os.path.join(
        BASE_DIR,
        "llm_cluster_removal_summary.csv"
    )

    final_df.to_csv(
        csv_output,
        index=False
    )

    # ========================================================
    # Markdown
    # ========================================================
    md_output = os.path.join(
        BASE_DIR,
        "llm_cluster_removal_summary.md"
    )

    with open(md_output, "w", encoding="utf-8") as f:

        f.write(
            final_df.to_markdown(index=False)
        )

    # ========================================================
    # 输出
    # ========================================================
    print("\n================================================")
    print("全部处理完成")
    print("================================================")

    print("\nCSV:")
    print(csv_output)

    print("\nMarkdown:")
    print(md_output)

    print("\n================ FINAL RESULT ================")
    print(final_df.to_string(index=False))
    print("================================================")