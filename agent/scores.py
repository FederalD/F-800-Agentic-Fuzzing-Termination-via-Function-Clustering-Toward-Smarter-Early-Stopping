import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ==================== Data Loading ====================
def load_multiple_files(file_paths):
    """Load data from multiple JSON files"""
    all_data = {}
    libraries = []
    
    for path_str in file_paths:
        try:
            path = Path(path_str)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract library name from path
                parts = path.parts
                lib_name = None
                for part in parts:
                    if part in ['gif2png', 'jasper', 'libpcap', 'libtiff', 
                               'libxml2', 'nm', 'objdump', 'size']:
                        lib_name = part
                        break
                
                if lib_name:
                    if lib_name in data:
                        all_data[lib_name] = data[lib_name]
                        libraries.append(lib_name)
                        print(f"✓ {lib_name}: {len(data[lib_name])} clusters ({path_str})")
                    else:
                        # Try to use file content directly
                        all_data[lib_name] = data
                        libraries.append(lib_name)
                        print(f"✓ {lib_name}: Direct load ({path_str})")
        except Exception as e:
            print(f"✗ Failed to load {path_str}: {e}")
    
    return all_data, libraries

# ==================== Core Analysis ====================
def analyze_cluster_quality(all_data):
    """Analyze cluster quality"""
    analysis = {}
    total_clusters = 0
    
    for lib, clusters in all_data.items():
        if isinstance(clusters, dict):
            scores = []
            for cluster_id, cluster_data in clusters.items():
                if isinstance(cluster_data, dict) and 'overall_quality' in cluster_data:
                    scores.append(cluster_data['overall_quality'])
                elif isinstance(cluster_data, (int, float)):
                    scores.append(cluster_data)
            
            if scores:
                analysis[lib] = {
                    'avg_quality': np.mean(scores),
                    'std_quality': np.std(scores),
                    'min_quality': np.min(scores),
                    'max_quality': np.max(scores),
                    'count': len(scores),
                    'scores': scores
                }
                total_clusters += len(scores)
    
    return analysis, total_clusters

def extract_all_scores(all_data):
    """Extract all score data for analysis"""
    all_scores = []
    score_details = []
    
    for lib, clusters in all_data.items():
        if isinstance(clusters, dict):
            for cluster_id, cluster_data in clusters.items():
                if isinstance(cluster_data, dict):
                    if 'overall_quality' in cluster_data:
                        all_scores.append(cluster_data['overall_quality'])
                        
                        detail = {
                            'library': lib,
                            'cluster_id': cluster_id,
                            'overall_quality': cluster_data.get('overall_quality', 0),
                            'cluster_quality': cluster_data.get('cluster_quality', 0),
                            'llm_analysis': cluster_data.get('llm_analysis', 0),
                            'semantic_consistency': cluster_data.get('semantic_consistency', 0),
                            'boundary_clarity': cluster_data.get('boundary_clarity', 0),
                            'structural_helpfulness': cluster_data.get('structural_helpfulness', 0),
                            'assignment_accuracy': cluster_data.get('assignment_accuracy', 0),
                        }
                        score_details.append(detail)
    
    return all_scores, pd.DataFrame(score_details) if score_details else pd.DataFrame()

# ==================== Visualization ====================
def plot_library_quality_bar(analysis, save_path=None):
    """
    Figure 1: Library Quality Comparison Bar Chart
    Purpose: Quick visual comparison of clustering quality across different software libraries
    """
    if not analysis:
        print("No analysis data available")
        return
    
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
    
    # 获取原始库名
    original_libs = list(analysis.keys())
    
    # 映射库名
    libs = [target_dict.get(lib, lib) for lib in original_libs]
    avg_scores = [analysis[lib]['avg_quality'] for lib in original_libs]
    std_scores = [analysis[lib]['std_quality'] for lib in original_libs]
    counts = [analysis[lib]['count'] for lib in original_libs]
    
    # 计算标准误差 SE = σ / √n
    se_scores = [std / np.sqrt(count) if count > 0 else 0 
                 for std, count in zip(std_scores, counts)]
    
    # Sort by average score (descending)
    # 需要同时排序所有相关数组
    sorted_indices = np.argsort(avg_scores)[::-1]
    
    libs = [libs[i] for i in sorted_indices]
    avg_scores = [avg_scores[i] for i in sorted_indices]
    se_scores = [se_scores[i] for i in sorted_indices]
    counts = [counts[i] for i in sorted_indices]
    original_libs = [original_libs[i] for i in sorted_indices]
    
    plt.figure(figsize=(12, 7))
    
    # Color mapping based on quality score
    colors = []
    for score in avg_scores:
        if score >= 80:
            colors.append('#2ecc71')  # Green - Excellent
        elif score >= 60:
            colors.append('#3498db')  # Blue - Good
        else:
            colors.append('#e74c3c')  # Red - Poor
    
    # Plot bars with error bars
    x_pos = np.arange(len(libs))
    bars = plt.bar(x_pos, avg_scores, color=colors, alpha=0.8, edgecolor='black')
    
    # Add error bars (standard error)
    plt.errorbar(x_pos, avg_scores, yerr=se_scores, fmt='none', 
                 ecolor='black', elinewidth=1.5, capsize=5, capthick=1.5)
    
    # Add value labels on top of bars (只显示平均值±标准误差)
    for i, (bar, score, se) in enumerate(zip(bars, avg_scores, se_scores)):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + se + 1,
                f'{score:.1f} ± {se:.1f}',  # 移除了聚类个数信息
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Statistical significance analysis (使用原始库名进行比较)
    print("\n📊 STATISTICAL SIGNIFICANCE ANALYSIS (Library Quality):")
    print("-" * 50)
    
    # Compare each library with the next one
    for i in range(len(original_libs) - 1):
        # Calculate z-score for comparison
        mean_diff = avg_scores[i] - avg_scores[i + 1]
        se_diff = np.sqrt(se_scores[i]**2 + se_scores[i + 1]**2)
        
        if se_diff > 0:
            z_score = mean_diff / se_diff
            # Rough significance threshold (z > 1.96 for p < 0.05)
            if abs(z_score) > 1.96:
                significance = "✅ SIGNIFICANT"
            elif abs(z_score) > 1.645:
                significance = "⚠️  BORDERLINE"
            else:
                significance = "🔶 NOT SIGNIFICANT"
            
            # 显示映射后的库名
            print(f"{libs[i]:10s} vs {libs[i+1]:10s}: "
                  f"Δ={mean_diff:+.1f}, z={z_score:.2f} {significance}")
            
            # Mark significance on plot (if significant)
            if abs(z_score) > 1.96:
                # Position for significance marker
                x1, x2 = x_pos[i], x_pos[i + 1]
                y = max(avg_scores[i], avg_scores[i + 1]) + max(se_scores[i], se_scores[i + 1]) + 5
                
                # Draw significance line
                plt.plot([x1, x1, x2, x2], [y, y+1, y+1, y], 
                        color='black', linewidth=1.5)
                
                # Add significance asterisk
                plt.text((x1 + x2) / 2, y + 2, '*', ha='center', va='bottom',
                        fontsize=12, fontweight='bold', color='red')
    
    # Reference lines
    plt.axhline(y=80, color='green', linestyle='--', alpha=0.3, label='Excellent (80)')
    plt.axhline(y=60, color='orange', linestyle='--', alpha=0.3, label='Good (60)')
    
    plt.title('Average Cluster Quality by Library (± Standard Error)', fontsize=14, pad=15)
    #plt.xlabel('Software Library', fontsize=12)
    plt.ylabel('Average Quality Score', fontsize=12)
    plt.xticks(x_pos, libs, rotation=45, ha='right')
    plt.ylim(0, 105)
    
    # Add legend for significance markers
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', alpha=0.8, edgecolor='black', label='Excellent (≥80)'),
        Patch(facecolor='#3498db', alpha=0.8, edgecolor='black', label='Good (60-79)'),
        Patch(facecolor='#e74c3c', alpha=0.8, edgecolor='black', label='Poor (<60)'),
        Patch(facecolor='white', alpha=0, label='* = p < 0.05')
    ]
    
    plt.legend(handles=legend_elements, loc='upper right', fontsize=9)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Figure 1 saved: {save_path}")
    
    plt.show()
    
    # Print statistical summary (使用映射后的库名，但保留原始库名在统计摘要中)
    print("\n📈 STATISTICAL SUMMARY (with sample sizes):")
    print("-" * 40)
    for i, (orig_lib, display_lib, avg, se, count) in enumerate(
        zip(original_libs, libs, avg_scores, se_scores, counts), 1):
        # Calculate 95% confidence interval
        ci_low = avg - 1.96 * se if se > 0 else avg
        ci_high = avg + 1.96 * se if se > 0 else avg
        print(f"{i:2d}. {display_lib:10s}: {avg:5.1f} ± {se:4.1f} "
              f"[{ci_low:.1f}-{ci_high:.1f}] (n={count})")
    
    # 返回映射后的库名和对应的分数
    return libs, avg_scores

def plot_quality_distribution_heatmap(all_data, save_path=None):
    """
    Figure 2: Quality Distribution Heatmap
    Purpose: Show distribution of clusters across quality grades for each library
    """
    data_rows = []
    
    for lib, clusters in all_data.items():
        if isinstance(clusters, dict):
            for cluster_id, scores in clusters.items():
                if isinstance(scores, dict) and 'overall_quality' in scores:
                    quality = scores['overall_quality']
                    
                    # Determine quality grade
                    if quality >= 90:
                        level = 'Excellent (90-100)'
                    elif quality >= 75:
                        level = 'Good (75-90)'
                    elif quality >= 60:
                        level = 'Fair (60-75)'
                    else:
                        level = 'Poor (<60)'
                    
                    data_rows.append({'library': lib, 'level': level})
    
    if not data_rows:
        print("Insufficient data for heatmap")
        return None
    
    df = pd.DataFrame(data_rows)
    
    # Create cross-tabulation
    cross_tab = pd.crosstab(df['library'], df['level'])
    
    # Ensure all levels are present
    all_levels = ['Poor (<60)', 'Fair (60-75)', 'Good (75-90)', 'Excellent (90-100)']
    for level in all_levels:
        if level not in cross_tab.columns:
            cross_tab[level] = 0
    
    # Reorder columns
    cross_tab = cross_tab[all_levels]
    
    plt.figure(figsize=(9, 6))
    sns.heatmap(cross_tab, annot=True, fmt='d', cmap='YlOrRd',
                cbar_kws={'label': 'Number of Clusters'})
    
    plt.title('Cluster Quality Grade Distribution by Library', fontsize=14, pad=15)
    plt.xlabel('Quality Grade', fontsize=12)
    plt.ylabel('Software Library', fontsize=12)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Figure 2 saved: {save_path}")
    
    plt.show()
    
    return cross_tab

def plot_llm_vs_cluster_scatter(score_df, save_path=None):
    """
    Figure 3: LLM Analysis Quality vs Cluster Quality Scatter Plot
    Purpose: Compare LLM analysis accuracy with clustering algorithm quality
    """
    if score_df.empty:
        print("No detailed score data available")
        return
    
    plt.figure(figsize=(8, 6))
    
    # Color by library
    libraries = score_df['library'].unique()
    colors = plt.cm.Set2(np.linspace(0, 1, len(libraries)))
    
    for lib, color in zip(libraries, colors):
        lib_data = score_df[score_df['library'] == lib]
        plt.scatter(lib_data['cluster_quality'], lib_data['llm_analysis'],
                   color=color, alpha=0.6, s=60, edgecolors='black', label=lib)
    
    # Diagonal line (y = x)
    plt.plot([0, 100], [0, 100], 'k--', alpha=0.3, label='y = x')
    
    plt.title('LLM Analysis Quality vs Cluster Quality', fontsize=14, pad=15)
    plt.xlabel('Cluster Quality Index', fontsize=12)
    plt.ylabel('LLM Analysis Quality Index', fontsize=12)
    plt.xlim(20, 105)
    plt.ylim(20, 105)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='lower right', fontsize=9)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Figure 3 saved: {save_path}")
    
    plt.show()
    
    # Calculate LLM advantage
    if not score_df.empty:
        score_df['llm_advantage'] = score_df['llm_analysis'] - score_df['cluster_quality']
        avg_advantage = score_df['llm_advantage'].mean()
        
        print(f"\n🤖 LLM Analysis Advantage: Average {avg_advantage:+.1f} points")
        if avg_advantage > 5:
            print("  ✅ LLM analysis quality significantly better than clustering")
        elif avg_advantage < -5:
            print("  ⚠  LLM analysis needs improvement")
        else:
            print("  ⚖️  LLM analysis matches clustering quality well")

def plot_correlation_heatmap(score_df, save_path=None):
    """
    Figure 4: Key Metrics Correlation Heatmap
    Purpose: Show statistical relationships between different evaluation metrics
    """
    if score_df.empty or len(score_df) < 2:
        print("Insufficient data for correlation analysis")
        return
    
    # Select key metrics for correlation analysis
    metrics = [
        'semantic_consistency',
        'boundary_clarity',
        'structural_helpfulness',
        'assignment_accuracy',
        'llm_analysis',
        'overall_quality'
    ]
    
    metric_names = [
        'Semantic\nConsistency',
        'Boundary\nClarity',
        'Structural\nHelpfulness',
        'Assignment\nAccuracy',
        'LLM Analysis\nQuality',
        'Overall\nQuality'
    ]
    
    # Extract relevant columns
    available_metrics = [m for m in metrics if m in score_df.columns]
    if len(available_metrics) < 3:
        print("Not enough metrics available for correlation analysis")
        return
    
    corr_data = score_df[available_metrics]
    correlation_matrix = corr_data.corr()
    
    # Map original metric names to display names
    name_mapping = dict(zip(metrics, metric_names))
    display_names = [name_mapping.get(m, m.replace('_', '\n').title()) 
                    for m in correlation_matrix.columns]
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, square=True, linewidths=1,
                xticklabels=display_names,
                yticklabels=display_names,
                cbar_kws={'label': 'Correlation Coefficient'})
    
    plt.title('Correlation Matrix of Key Quality Metrics', fontsize=14, pad=15)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Figure 4 saved: {save_path}")
    
    plt.show()
    
    # Analyze key correlations
    if 'semantic_consistency' in correlation_matrix.columns and 'overall_quality' in correlation_matrix.columns:
        semantic_corr = correlation_matrix.loc['semantic_consistency', 'overall_quality']
        print(f"\n🔗 Key Metric Correlations:")
        if abs(semantic_corr) > 0.7:
            print(f"  ✅ Semantic Consistency strongly correlated with Overall Quality (r={semantic_corr:.2f})")
        elif abs(semantic_corr) > 0.5:
            print(f"  ⚠  Semantic Consistency moderately correlated with Overall Quality (r={semantic_corr:.2f})")
        else:
            print(f"  🔶 Semantic Consistency weakly correlated with Overall Quality (r={semantic_corr:.2f})")

def plot_quality_boxplot(analysis, save_path=None):
    """
    Figure 5: Quality Score Distribution Boxplot
    Purpose: Show distribution characteristics of quality scores for each library
    """
    if not analysis:
        print("No analysis data available")
        return
    
    # Prepare data for boxplot
    box_data = []
    box_labels = []
    
    for lib in analysis.keys():
        if 'scores' in analysis[lib] and analysis[lib]['scores']:
            box_data.append(analysis[lib]['scores'])
            box_labels.append(lib)
    
    if not box_data:
        print("No score data available for boxplot")
        return
    
    plt.figure(figsize=(10, 6))
    
    # Create boxplot
    bp = plt.boxplot(box_data, labels=box_labels, patch_artist=True)
    
    # Customize box colors
    colors = plt.cm.Set2(np.linspace(0, 1, len(box_labels)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    # Add reference lines
    plt.axhline(y=80, color='green', linestyle='--', alpha=0.3, label='Excellent (80)')
    plt.axhline(y=60, color='orange', linestyle='--', alpha=0.3, label='Good (60)')
    
    plt.title('Cluster Quality Score Distribution by Library', fontsize=14, pad=15)
    plt.xlabel('Software Library', fontsize=12)
    plt.ylabel('Quality Score', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.ylim(0, 105)
    plt.grid(axis='y', alpha=0.3)
    plt.legend()
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Figure 5 saved: {save_path}")
    
    plt.show()

# ==================== Main Program ====================
def main():
    print("="*60)
    print("MULTI-PATH MULTI-LIBRARY CLUSTER QUALITY ANALYSIS")
    print("="*60)
    
    # 1. Define file paths
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
    
    print(f"\n📂 Loading {len(file_paths)} files...")
    
    # 2. Load data
    all_data, libraries = load_multiple_files(file_paths)
    
    if not all_data:
        print("❌ No valid data found")
        return
    
    # 3. Analyze quality
    print(f"\n📈 Analyzing cluster quality...")
    analysis, total_clusters = analyze_cluster_quality(all_data)
    all_scores, score_df = extract_all_scores(all_data)
    
    print(f"   Loaded {len(libraries)} libraries, {total_clusters} total clusters")
    
    # 4. Generate visualizations
    print(f"\n🎨 Generating analysis visualizations...")
    
    # Figure 1: Library Quality Comparison
    libs, lib_scores = plot_library_quality_bar(analysis, "figure1_library_quality.png")
    
    # Figure 2: Quality Distribution Heatmap
    cross_tab = plot_quality_distribution_heatmap(all_data, "figure2_quality_distribution.png")
    
    # Figure 3: LLM vs Cluster Quality
    if not score_df.empty:
        plot_llm_vs_cluster_scatter(score_df, "figure3_llm_vs_cluster.png")
    
    # Figure 4: Correlation Heatmap
    if not score_df.empty:
        plot_correlation_heatmap(score_df, "figure4_correlation_matrix.png")
    
    # Figure 5: Quality Boxplot
    if analysis:
        plot_quality_boxplot(analysis, "figure5_quality_boxplot.png")
    
    # 5. Generate Summary Report
    print("\n" + "="*60)
    print("📋 ANALYSIS REPORT SUMMARY")
    print("="*60)
    
    if all_scores:
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Average Quality: {np.mean(all_scores):.1f} points")
        print(f"  Quality Range: {np.min(all_scores):.1f} - {np.max(all_scores):.1f} points")
        print(f"  Standard Deviation: {np.std(all_scores):.1f} points")
        print(f"  Total Clusters: {len(all_scores)}")
    
    # Library ranking
    if libs and lib_scores:
        print(f"\n🏆 LIBRARY RANKING BY QUALITY:")
        for i, (lib, score) in enumerate(zip(libs, lib_scores), 1):
            status = "✅ Excellent" if score >= 80 else "⚠  Good" if score >= 60 else "❌ Poor"
            count = analysis[lib]['count'] if lib in analysis else 0
            print(f"  {i:2d}. {lib:10s}: {score:5.1f} points ({count:2d} clusters) {status}")
    
    # Quality grade statistics
    if all_scores:
        excellent = sum(1 for s in all_scores if s >= 90)
        good = sum(1 for s in all_scores if 75 <= s < 90)
        fair = sum(1 for s in all_scores if 60 <= s < 75)
        poor = sum(1 for s in all_scores if s < 60)
        
        total = len(all_scores)
        print(f"\n📈 QUALITY GRADE DISTRIBUTION:")
        print(f"  Excellent (≥90): {excellent:3d} clusters ({excellent/total*100:.1f}%)")
        print(f"  Good (75-89): {good:3d} clusters ({good/total*100:.1f}%)")
        print(f"  Fair (60-74): {fair:3d} clusters ({fair/total*100:.1f}%)")
        print(f"  Poor (<60): {poor:3d} clusters ({poor/total*100:.1f}%)")
    
    # Best/Worst libraries
    if analysis:
        best_lib = max(analysis.items(), key=lambda x: x[1]['avg_quality'])
        worst_lib = min(analysis.items(), key=lambda x: x[1]['avg_quality'])
        
        print(f"\n🎯 KEY FINDINGS:")
        print(f"  Best Library: {best_lib[0]} ({best_lib[1]['avg_quality']:.1f} points)")
        print(f"  Worst Library: {worst_lib[0]} ({worst_lib[1]['avg_quality']:.1f} points)")
        print(f"  Quality Gap: {best_lib[1]['avg_quality']-worst_lib[1]['avg_quality']:.1f} points")
        
        # Overall evaluation
        avg_all = np.mean(all_scores) if all_scores else 0
        if avg_all >= 80:
            print(f"\n✅ OVERALL: Excellent clustering quality ({avg_all:.1f} points)")
        elif avg_all >= 70:
            print(f"\n⚠️  OVERALL: Good clustering quality ({avg_all:.1f} points)")
        elif avg_all >= 60:
            print(f"\n🔶 OVERALL: Fair clustering quality ({avg_all:.1f} points)")
        else:
            print(f"\n❌ OVERALL: Poor clustering quality ({avg_all:.1f} points) - Needs optimization")
    
    # Figure descriptions
    print(f"\n📝 GENERATED FIGURES (with interpretations):")
    print("  1. Library Quality Comparison Bar Chart - Compare clustering performance across libraries")
    print("  2. Quality Distribution Heatmap - Show distribution of clusters across quality grades")
    print("  3. LLM vs Cluster Quality Scatter Plot - Assess LLM analysis accuracy")
    print("  4. Correlation Heatmap - Reveal relationships between quality metrics")
    print("  5. Quality Score Boxplot - Display distribution characteristics for each library")
    
    # File information
    print(f"\n💾 LOADED FILES:")
    for path in file_paths:
        p = Path(path)
        if p.exists():
            lib_name = p.parent.parent.name
            print(f"  ✓ {lib_name}: {p.name}")

if __name__ == "__main__":
    main()