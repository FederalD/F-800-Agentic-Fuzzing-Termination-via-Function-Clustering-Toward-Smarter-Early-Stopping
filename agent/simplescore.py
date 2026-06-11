import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体（如果需要）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 数据加载 ====================
def load_multiple_files(file_paths):
    """加载多个 JSON 文件并识别库名"""
    all_data = {}
    libraries = []
    
    for path_str in file_paths:
        path = Path(path_str)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 提取库名
            for name in ['gif2png', 'jasper', 'libpcap', 'libtiff', 
                         'libxml2', 'nm', 'objdump', 'size']:
                if name in path.parts:
                    lib_name = name
                    break
            else:
                lib_name = path.stem
            
            all_data[lib_name] = data.get(lib_name, data)
            libraries.append(lib_name)
            print(f"✓ Loaded {lib_name} ({path_str})")
        else:
            print(f"✗ File not found: {path_str}")
    
    return all_data, libraries


# ==================== 二分法质量提取 ====================
def extract_binary_quality(all_data, threshold=70):
    """
    将 overall_quality 转换为 Good / Bad
    - Good: ≥threshold
    - Bad:  <threshold
    """
    results = []
    for lib, clusters in all_data.items():
        if not isinstance(clusters, dict):
            continue
        for cid, info in clusters.items():
            if isinstance(info, dict) and 'overall_quality' in info:
                q = info['overall_quality']
                label = 'Good' if q >= threshold else 'Bad'
                results.append({
                    'library': lib, 
                    'quality': label,
                    'score': q,
                    'cluster_id': cid
                })
    return pd.DataFrame(results)


# ==================== 第一种可视化方案（水平堆叠条形图） ====================
def plot_binary_quality_horizontal(df, save_dir='figure'):
    """生成水平堆叠条形图（左右对比）"""
    
    if df.empty:
        print("❌ No data to plot.")
        return
    
    # 创建输出文件夹
    os.makedirs(save_dir, exist_ok=True)
    
    # 库名称映射字典
    target_dict = {
        'gif2png': 'Gif2png', 
        'jasper': 'JasPer',
        'libpcap': 'Libpcap',
        'libtiff': 'LibTIFF',
        'libxml2': 'Libxml2',
        'nm': 'nm',
        'objdump': 'objdump',
        'size': 'size'
    }
    
    df['library_display'] = df['library'].map(target_dict).fillna(df['library'])
    
    # 汇总数据
    summary = df.groupby(['library_display', 'quality']).size().reset_index(name='count')
    pivot = summary.pivot(index='library_display', columns='quality', values='count').fillna(0)
    
    # 确保所有库都存在
    for lib in target_dict.values():
        if lib not in pivot.index:
            pivot.loc[lib] = [0, 0] if 'Good' in pivot.columns and 'Bad' in pivot.columns else 0
    
    # 排序
    ordered_libs = [target_dict[k] for k in target_dict]
    pivot = pivot.reindex(ordered_libs)
    
    # 计算总数和比例（转换为百分比）
    pivot['Total'] = pivot.sum(axis=1)
    pivot['Good_pct'] = (pivot['Good'] / pivot['Total'] * 100).round(1)
    pivot['Bad_pct'] = (pivot['Bad'] / pivot['Total'] * 100).round(1)
    
    # 水平堆叠条形图（左右对比）- 移除主标题
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 左图：数量堆叠图
    ax1 = axes[0]
    bottom = np.zeros(len(pivot))
    colors = {'Good': '#2ecc71', 'Bad': '#e74c3c'}
    
    for quality in ['Good', 'Bad']:
        values = pivot[quality].fillna(0).values
        bars = ax1.barh(pivot.index, values, left=bottom, 
                        color=colors[quality], alpha=0.85, label=quality)
        bottom += values
        
        # 添加数值标签
        for i, (val, bar) in enumerate(zip(values, bars)):
            if val > 0:
                x_pos = bar.get_x() + bar.get_width() / 2
                ax1.text(x_pos, i, f'{int(val)}', 
                        ha='center', va='center', 
                        color='white', fontweight='bold', fontsize=10)
    
    ax1.set_xlabel('Number of Clusters', fontsize=12)
    ax1.set_title('(a)', fontsize=14, pad=10)
    ax1.grid(axis='x', alpha=0.3, linestyle='--')
    
    # 右图：百分比堆叠图
    ax2 = axes[1]
    left = np.zeros(len(pivot))
    
    # 使用百分比值
    for quality, pct_col in [('Good', 'Good_pct'), ('Bad', 'Bad_pct')]:
        values = pivot[pct_col].values / 100  # 转换为0-1用于绘图
        bars = ax2.barh(pivot.index, values, left=left, 
                        color=colors[quality], alpha=0.85, label=quality)
        left += values
        
        # 添加百分比标签
        for i, (val, bar) in enumerate(zip(values, bars)):
            pct_value = pivot[pct_col].values[i]
            if pct_value > 5:  # 只显示大于5%的标签
                x_pos = bar.get_x() + bar.get_width() / 2
                ax2.text(x_pos, i, f'{pct_value:.0f}%', 
                        ha='center', va='center', 
                        color='white', fontweight='bold', fontsize=10)
    
    ax2.set_xlabel('Proportion (%)', fontsize=12)
    ax2.set_title('(b)', fontsize=14, pad=10)
    ax2.set_xlim(0, 1)
    # 将x轴刻度改为百分比
    ax2.set_xticks(np.arange(0, 1.1, 0.2))
    ax2.set_xticklabels([f'{int(x*100)}%' for x in np.arange(0, 1.1, 0.2)])
    ax2.grid(axis='x', alpha=0.3, linestyle='--')
    
    # 将图例移动到顶部横向排列
    for ax in axes:
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), 
                 ncol=2, framealpha=0.9, fancybox=True, shadow=True)
    
    plt.tight_layout()
    # 调整顶部边距为图例留出空间
    plt.subplots_adjust(top=0.88)
    
    save_path = os.path.join(save_dir, 'binary_quality_horizontal.png')
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"📊 Saved figure: {save_path}")
    plt.show()
    
    # 返回统计数据
    summary_stats = pivot[['Good', 'Bad', 'Total']].copy()
    summary_stats['Good_%'] = pivot['Good_pct']
    summary_stats['Bad_%'] = pivot['Bad_pct']
    
    return summary_stats


def plot_simple_binary(df, save_path):
    """简化版二分类图（保留原始函数接口）- 已移除右侧n=标签"""
    if df.empty:
        print("❌ No data to plot.")
        return
    
    # 库名称映射
    target_dict = {
        'gif2png': 'Gif2png', 
        'jasper': 'JasPer',
        'libpcap': 'Libpcap',
        'libtiff': 'LibTIFF',
        'libxml2': 'Libxml2',
        'nm': 'nm',
        'objdump': 'objdump',
        'size': 'size'
    }
    
    df['library_display'] = df['library'].map(target_dict).fillna(df['library'])
    
    # 汇总
    summary = df.groupby(['library_display', 'quality']).size().reset_index(name='count')
    pivot = summary.pivot(index='library_display', columns='quality', values='count').fillna(0)
    
    # 排序
    ordered_libs = [target_dict[k] for k in target_dict]
    pivot = pivot.reindex(ordered_libs)
    
    # 计算比例（转换为百分比）
    pivot['Total'] = pivot.sum(axis=1)
    pivot['Good_pct'] = (pivot['Good'] / pivot['Total'] * 100).round(1)
    pivot['Bad_pct'] = (pivot['Bad'] / pivot['Total'] * 100).round(1)
    
    # 绘图 - 移除标题
    plt.figure(figsize=(10, 6))
    
    # 使用更鲜明的颜色
    colors = {'Good': '#2ecc71', 'Bad': '#e74c3c'}
    
    # 绘制堆叠条形图
    bottom = np.zeros(len(pivot))
    for quality, pct_col in [('Good', 'Good_pct'), ('Bad', 'Bad_pct')]:
        values = pivot[pct_col].values / 100  # 转换为0-1用于绘图
        bars = plt.barh(pivot.index, values, left=bottom, 
                        color=colors[quality], alpha=0.9, 
                        edgecolor='white', linewidth=1,
                        label=quality)
        bottom += values
        
        # 添加标签
        for i, (val, bar) in enumerate(zip(values, bars)):
            pct_value = pivot[pct_col].values[i]
            if pct_value > 5:
                x_pos = bar.get_x() + bar.get_width() / 2
                plt.text(x_pos, i, f'{pct_value:.0f}%', 
                        ha='center', va='center', 
                        color='white', fontweight='bold', fontsize=11)
    
    plt.xlabel('Proportion (%)', fontsize=13, fontweight='bold')
    plt.xlim(0, 1)
    # 将x轴刻度改为百分比
    plt.xticks(np.arange(0, 1.1, 0.2), [f'{int(x*100)}%' for x in np.arange(0, 1.1, 0.2)])
    plt.grid(axis='x', alpha=0.3, linestyle='--')
    
    # 将图例移动到顶部横向排列
    plt.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), 
              ncol=2, framealpha=0.9, fancybox=True, shadow=True)
    
    # 【已移除】不再添加右侧的n=数量信息
    # 原代码中此处有一段添加文本标签的代码，已全部删除
    
    plt.tight_layout()
    # 调整顶部边距为图例留出空间
    plt.subplots_adjust(top=0.92)
    
    # 保存
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"📊 Saved figure: {save_path}")
    plt.show()
    
    return pivot


# ==================== 主程序 ====================
def main():
    print("="*60)
    print("BINARY CLUSTER QUALITY ANALYSIS (Good / Bad)")
    print("="*60)
    
    # 可调节阈值
    THRESHOLD = 70  # 可以调整为其他值，如60, 75, 80等
    
    print(f"📊 Classification threshold: {THRESHOLD} (Good ≥ {THRESHOLD}, Bad < {THRESHOLD})")
    print()

    # 文件路径
    file_paths = [
        "D:\\TEST\\cluster\\cluster\\gif2png\\20\\scores.json",
        "D:\\TEST\\cluster\\cluster\\jasper\\14\\scores.json", 
        "D:\\TEST\\cluster\\cluster\\libpcap\\96\\scores.json",
        "D:\\TEST\\cluster\\cluster\\libtiff\\67\\scores.json",
        "D:\\TEST\\cluster\\cluster\\libxml2\\122\\scores.json",
        "D:\\TEST\\cluster\\cluster\\nm\\77\\scores.json",
        "D:\\TEST\\cluster\\cluster\\objdump\\98\\scores.json",
        "D:\\TEST\\cluster\\cluster\\size\\91\\scores.json"
    ]

    all_data, libs = load_multiple_files(file_paths)
    df = extract_binary_quality(all_data, threshold=THRESHOLD)

    if df.empty:
        print("❌ No valid data found.")
        return

    print(f"\n✅ Loaded {len(df)} cluster records across {len(libs)} libraries.")
    print(f"   Good clusters: {len(df[df['quality']=='Good'])}")
    print(f"   Bad clusters: {len(df[df['quality']=='Bad'])}")
    print()
    
    # 方案A：使用简化版（水平堆叠条形图）- 已移除右侧n=标签
    save_path_simple = os.path.join('figure', f'binary_quality_th{THRESHOLD}.png')
    result_simple = plot_simple_binary(df, save_path_simple)
    
    print("\n📈 SIMPLE SUMMARY TABLE:")
    print(result_simple[['Good', 'Bad']].fillna(0).astype(int))
    
    # 方案B：使用水平堆叠条形图（左右对比）
    print("\n" + "="*60)
    print("🎨 Generating horizontal stacked bar chart...")
    print("="*60)
    
    summary_stats = plot_binary_quality_horizontal(df, save_dir='figure')
    
    print("\n📊 DETAILED STATISTICS:")
    print(summary_stats.round(1))
    
    # 保存统计数据到CSV
    csv_path = os.path.join('figure', 'binary_quality_stats.csv')
    summary_stats.to_csv(csv_path)
    print(f"\n💾 Saved statistics to: {csv_path}")

if __name__ == "__main__":
    main()