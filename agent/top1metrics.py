import json
import os
from copy import deepcopy
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
# JSON读取
# ============================================================

def load_json(path):

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 保存JSON
# ============================================================

def save_json(data, path):

    with open(path, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# cluster -> function mapping
# ============================================================

def cluster_to_function_mapping(cluster_json_path):

    cluster_data = load_json(cluster_json_path)

    function_mapping = {}

    for cluster_id, cluster_info in cluster_data.items():

        for func_info in cluster_info.get("functions_info", []):

            function_name = func_info["function_name"]

            function_mapping[function_name] = {
                "cluster_id": str(cluster_id),
                **func_info
            }

    return function_mapping


# ============================================================
# 保存function mapping
# ============================================================

def save_function_mapping(mapping, path):

    save_json(mapping, path)


# ============================================================
# 构建函数索引
# ============================================================

def build_function_index(cluster_data):

    function_index = {}

    for cluster_id, cluster_info in cluster_data.items():

        for func_info in cluster_info.get("functions_info", []):

            function_name = func_info["function_name"]

            function_index[function_name] = {
                "cluster_id": str(cluster_id),
                "function_info": func_info
            }

    return function_index


# ============================================================
# 使用 Top1 最近聚类 修复聚类结果
# ============================================================

def apply_top1_reassignment(

    reassignment_result_path,
    original_cluster_path,
    output_cluster_path
):

    """
    使用：

        candidate_clusters[0]

    作为最终聚类结果
    """

    # ========================================================
    # 原始聚类
    # ========================================================

    original_cluster_data = load_json(
        original_cluster_path
    )

    final_clusters = deepcopy(
        original_cluster_data
    )

    # ========================================================
    # 建立函数索引
    # ========================================================

    function_index = build_function_index(
        original_cluster_data
    )

    # ========================================================
    # reassignment 文件不存在
    # 说明没有函数被剔除
    # ========================================================

    if not os.path.exists(
        reassignment_result_path
    ):

        save_json(
            final_clusters,
            output_cluster_path
        )

        print("[INFO] 无 reassignment 文件")
        print("[INFO] 直接使用原始聚类")

        return output_cluster_path

    # ========================================================
    # 读取 reassignment
    # ========================================================

    data = load_json(
        reassignment_result_path
    )

    reassignment_results = data.get(
        "reassignment_results",
        {}
    )

    # ========================================================
    # 遍历函数
    # ========================================================

    for _, item in reassignment_results.items():

        function_name = item["function_name"]

        original_cluster = str(
            item["original_cluster"]
        )

        candidate_clusters = item.get(
            "candidate_clusters",
            []
        )

        # ====================================================
        # 无候选
        # ====================================================

        if len(candidate_clusters) == 0:

            print(
                f"[WARNING] "
                f"{function_name} 无候选cluster"
            )

            continue

        # ====================================================
        # Top1 最近聚类
        # ====================================================

        top1_cluster = str(
            candidate_clusters[0]["cluster_id"]
        )

        # ====================================================
        # 如果Top1仍然是原cluster
        # 不进行迁移
        # ====================================================

        if top1_cluster == original_cluster:

            print(
                f"[SKIP] {function_name} "
                f"Top1仍为原cluster"
            )

            continue

        # ====================================================
        # 函数不存在
        # ====================================================

        if function_name not in function_index:

            print(
                f"[WARNING] 未找到函数:"
                f"{function_name}"
            )

            continue

        func_info = function_index[
            function_name
        ]["function_info"]

        function_id = func_info["function_id"]

        # ====================================================
        # 从旧cluster删除
        # ====================================================

        if original_cluster in final_clusters:

            final_clusters[
                original_cluster
            ]["functions_info"] = [

                f for f in
                final_clusters[
                    original_cluster
                ]["functions_info"]

                if f["function_name"]
                != function_name
            ]

            final_clusters[
                original_cluster
            ]["function_ids"] = [

                fid for fid in
                final_clusters[
                    original_cluster
                ]["function_ids"]

                if fid != function_id
            ]

            final_clusters[
                original_cluster
            ]["function_count"] = len(

                final_clusters[
                    original_cluster
                ]["functions_info"]
            )

        # ====================================================
        # 新cluster不存在
        # ====================================================

        if top1_cluster not in final_clusters:

            final_clusters[top1_cluster] = {
                "function_count": 0,
                "function_ids": [],
                "functions_info": []
            }

        # ====================================================
        # 避免重复添加
        # ====================================================

        if function_id not in final_clusters[
            top1_cluster
        ]["function_ids"]:

            final_clusters[
                top1_cluster
            ]["function_ids"].append(
                function_id
            )

            final_clusters[
                top1_cluster
            ]["functions_info"].append(
                func_info
            )

        final_clusters[
            top1_cluster
        ]["function_count"] = len(

            final_clusters[
                top1_cluster
            ]["functions_info"]
        )

        print(
            f"[MOVE] {function_name}: "
            f"{original_cluster} -> "
            f"{top1_cluster}"
        )

    # ========================================================
    # 保存修复后的聚类
    # ========================================================

    save_json(
        final_clusters,
        output_cluster_path
    )

    return output_cluster_path


# ============================================================
# 评估
# ============================================================

def evaluate_mapping(

    gt_mapping,
    pred_mapping
):

    """
    统计：

        cluster是否一致
    """

    TP = TN = FP = FN = 0

    details = []

    all_functions = set(
        gt_mapping.keys()
    )

    for func in all_functions:

        if func not in pred_mapping:

            continue

        gt_cluster = str(
            gt_mapping[func]["cluster_id"]
        )

        pred_cluster = str(
            pred_mapping[func]["cluster_id"]
        )

        # ====================================================
        # 是否正确
        # ====================================================

        correct = (
            gt_cluster == pred_cluster
        )

        if correct:

            TP += 1
            result = "TP"

        else:

            FP += 1
            result = "FP"

        details.append({

            "function": func,
            "gt_cluster": gt_cluster,
            "pred_cluster": pred_cluster,
            "result": result
        })

    # ========================================================
    # 指标
    # ========================================================

    total = TP + FP

    accuracy = (
        TP / total
        if total else 0
    )

    precision = (
        TP / (TP + FP)
        if (TP + FP) else 0
    )

    recall = precision

    f1 = (
        2 * precision * recall /
        (precision + recall)

        if (precision + recall)
        else 0
    )

    fpr = (
        FP / total
        if total else 0
    )

    metrics = {

        "TP": TP,
        "TN": TN,
        "FP": FP,
        "FN": FN,

        "Accuracy": round(
            accuracy,
            4
        ),

        "Precision": round(
            precision,
            4
        ),

        "Recall": round(
            recall,
            4
        ),

        "F1-score": round(
            f1,
            4
        ),

        "FPR": round(
            fpr,
            4
        )
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
        # GroundTruth function mapping
        # ====================================================

        gt_function_path = os.path.join(

            main_dir,

            f"{lib}_final_cluster_mapping_function_mapping.json"
        )

        gt_mapping = load_json(
            gt_function_path
        )

        # ====================================================
        # 原始聚类
        # ====================================================

        original_cluster_path = os.path.join(

            main_dir,
            "cluster_mapping.json"
        )

        # ====================================================
        # 遍历20轮
        # ====================================================

        for iteration_id in range(
            1,
            MAX_ITERATIONS + 1
        ):

            iteration_dir = os.path.join(

                main_dir,
                f"iteration_{iteration_id}"
            )

            if not os.path.exists(
                iteration_dir
            ):

                continue

            print("\n----------------------------------------")
            print(
                f"{lib} | "
                f"iteration_{iteration_id}"
            )
            print("----------------------------------------")

            # =================================================
            # reassignment results
            # =================================================

            reassignment_result_path = os.path.join(

                iteration_dir,

                f"{lib}_reassignment_results_{iteration_id}.json"
            )

            # =================================================
            # 输出文件
            # =================================================

            final_cluster_path = os.path.join(

                iteration_dir,

                f"{lib}_top1_final_cluster_mapping_{iteration_id}.json"
            )

            function_mapping_path = os.path.join(

                iteration_dir,

                f"{lib}_top1_function_mapping_{iteration_id}.json"
            )

            detail_path = os.path.join(

                iteration_dir,

                f"{lib}_top1_evaluation_details_{iteration_id}.json"
            )

            metrics_path = os.path.join(

                iteration_dir,

                f"{lib}_top1_metrics_{iteration_id}.json"
            )

            # =================================================
            # Step1:
            # 使用Top1修复聚类
            # =================================================

            apply_top1_reassignment(

                reassignment_result_path=
                reassignment_result_path,

                original_cluster_path=
                original_cluster_path,

                output_cluster_path=
                final_cluster_path
            )

            # =================================================
            # Step2:
            # cluster -> function
            # =================================================

            pred_mapping = cluster_to_function_mapping(

                final_cluster_path
            )

            save_function_mapping(

                pred_mapping,
                function_mapping_path
            )

            # =================================================
            # Step3:
            # 与GroundTruth比较
            # =================================================

            metrics, details = evaluate_mapping(

                gt_mapping=
                gt_mapping,

                pred_mapping=
                pred_mapping
            )

            # =================================================
            # 保存details
            # =================================================

            save_json(
                details,
                detail_path
            )

            # =================================================
            # 保存metrics
            # =================================================

            save_json(
                metrics,
                metrics_path
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

        "top1_cluster_refinement_summary.csv"
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

        "top1_cluster_refinement_summary.md"
    )

    with open(
        md_output,
        "w",
        encoding="utf-8"
    ) as f:

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