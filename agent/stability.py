import json
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

class MultiProjectLLMAnalyzer:
    """多项目LLM稳定性分析器"""
    
    def __init__(self, base_path="D:/TEST/cluster/cluster"):
        self.base_path = base_path
        self.projects = {}
        
    def configure_projects(self, lib_clusters):
        """配置项目信息"""
        for lib_name, cluster_info in lib_clusters.items():
            parts = cluster_info.split('_')
            if len(parts) == 2:
                lib = parts[0]
                k = parts[1]
                self.projects[lib_name] = {
                    'lib': lib,
                    'k': k,
                    'full_name': cluster_info
                }
        return self.projects
    
    def analyze_single_project(self, project_name, max_iter=20):
        """分析单个项目"""
        if project_name not in self.projects:
            print(f"项目 {project_name} 未配置")
            return None
        
        config = self.projects[project_name]
        lib = config['lib']
        k = config['k']
        
        print(f"\n分析项目: {project_name} ({lib}, k={k})")
        print("-" * 40)
        
        # 分析器实例
        analyzer = ProjectAnalyzer(self.base_path, lib, k)
        
        # 加载数据
        iterations = analyzer.load_data(max_iter)
        if iterations == 0:
            print(f"项目 {project_name} 没有数据")
            return None
        
        print(f"加载了 {iterations} 次迭代")
        
        # 计算指标
        metrics_df = analyzer.calculate_metrics()
        func_stability_df = analyzer.analyze_function_stability()
        
        # 生成统计摘要
        summary = analyzer.generate_summary_stats(metrics_df, func_stability_df)
        summary['project_name'] = project_name
        summary['lib'] = lib
        summary['k'] = k
        summary['iterations'] = iterations
        
        return {
            'project_name': project_name,
            'config': config,
            'metrics': metrics_df,
            'stability': func_stability_df,
            'summary': summary
        }
    
    def analyze_all_projects(self, lib_clusters, max_iter=20):
        """分析所有项目"""
        # 配置项目
        self.configure_projects(lib_clusters)
        
        results = {}
        all_summaries = []
        
        for project_name in self.projects.keys():
            result = self.analyze_single_project(project_name, max_iter)
            if result:
                results[project_name] = result
                all_summaries.append(result['summary'])
        
        # 生成对比分析
        if all_summaries:
            comparison_df = self.generate_comparison_table(all_summaries)
            self.generate_comparison_charts(results)
            
            # 保存结果
            self.save_comparison_results(results, comparison_df)
        
        return results
    
    def generate_comparison_table(self, summaries):
        """生成项目对比表"""
        data = []
        for summary in summaries:
            row = {
                'Project': summary['project_name'],
                'Iterations': summary['iterations'],
                'Avg Exclusion Rate (%)': float(summary.get('avg_exclusion_rate', '0%').strip('%')),
                'Avg Consistency': float(summary.get('avg_consistency', '0')),
                'Avg Function Stability': float(summary.get('avg_stability', '0')),
                'High Stable (%)': float(summary.get('high_stable_pct', '0%').strip('%')),
                'Convergence': summary.get('convergence', 'N/A')
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        return df
    
    def generate_comparison_charts(self, results):
        """生成对比图表"""
        if not results:
            return
        
        # 设置图表样式
        plt.style.use('seaborn-v0_8-paper')
        plt.rcParams.update({
            'font.family': 'serif',
            'font.size': 10,
            'axes.labelsize': 11,
            'axes.titlesize': 12,
            'figure.dpi': 300
        })
        
        # 准备数据
        projects = []
        exclusion_rates = []
        consistency_scores = []
        stability_scores = []
        
        for proj_name, result in results.items():
            summary = result['summary']
            projects.append(proj_name)
            exclusion_rates.append(float(summary.get('avg_exclusion_rate', '0%').strip('%')))
            consistency_scores.append(float(summary.get('avg_consistency', '0')))
            stability_scores.append(float(summary.get('avg_stability', '0')))
        
        # 图1: 各项目核心指标对比
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # 排除率对比
        axes[0].bar(projects, exclusion_rates, color='#2E86AB', alpha=0.7)
        axes[0].set_xlabel('Project')
        axes[0].set_ylabel('Avg Exclusion Rate (%)')
        axes[0].set_title('(a) Exclusion Rate Comparison')
        axes[0].tick_params(axis='x', rotation=45)
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # 一致性对比
        axes[1].bar(projects, consistency_scores, color='#A23B72', alpha=0.7)
        axes[1].set_xlabel('Project')
        axes[1].set_ylabel('Avg Consistency Score')
        axes[1].set_title('(b) Consistency Comparison')
        axes[1].tick_params(axis='x', rotation=45)
        axes[1].grid(True, alpha=0.3, axis='y')
        
        # 稳定性对比
        axes[2].bar(projects, stability_scores, color='#4ECDC4', alpha=0.7)
        axes[2].set_xlabel('Project')
        axes[2].set_ylabel('Avg Function Stability')
        axes[2].set_title('(c) Function Stability Comparison')
        axes[2].tick_params(axis='x', rotation=45)
        axes[2].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig('figure4_project_comparison.png', dpi=600, bbox_inches='tight')
        plt.show()
        
        # 图2: 收敛性分布
        fig, ax = plt.subplots(figsize=(8, 5))
        
        convergence_counts = {'Yes': 0, 'Partial': 0, 'No': 0, 'N/A': 0}
        for proj_name, result in results.items():
            convergence = result['summary'].get('convergence', 'N/A')
            convergence_counts[convergence] = convergence_counts.get(convergence, 0) + 1
        
        # 过滤掉计数为0的类别
        convergence_data = {k: v for k, v in convergence_counts.items() if v > 0}
        
        colors = {'Yes': '#96CEB4', 'Partial': '#FFEAA7', 'No': '#FF6B6B', 'N/A': '#CCCCCC'}
        bar_colors = [colors.get(k, '#CCCCCC') for k in convergence_data.keys()]
        
        ax.bar(convergence_data.keys(), convergence_data.values(), 
               color=bar_colors, edgecolor='black', alpha=0.8)
        ax.set_xlabel('Convergence Status')
        ax.set_ylabel('Number of Projects')
        ax.set_title('Project Convergence Distribution')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 在柱子上添加数值
        for i, (category, count) in enumerate(convergence_data.items()):
            ax.text(i, count + 0.1, str(count), ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig('figure5_convergence_distribution.png', dpi=600, bbox_inches='tight')
        plt.show()
    
    def save_comparison_results(self, results, comparison_df):
        """保存对比结果"""
        output_dir = "multi_project_results"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存对比表格
        comparison_df.to_csv(f"{output_dir}/project_comparison.csv", index=False)
        
        # 保存各项目详细结果
        for proj_name, result in results.items():
            proj_dir = f"{output_dir}/{proj_name}"
            os.makedirs(proj_dir, exist_ok=True)
            
            # 保存数据
            result['metrics'].to_csv(f"{proj_dir}/metrics.csv", index=False)
            result['stability'].to_csv(f"{proj_dir}/stability.csv", index=False)
            
            # 保存摘要
            with open(f"{proj_dir}/summary.txt", 'w', encoding='utf-8') as f:
                f.write(f"{proj_name} Analysis Summary\n")
                f.write("=" * 40 + "\n\n")
                for key, value in result['summary'].items():
                    f.write(f"{key}: {value}\n")
        
        # 保存整体报告
        with open(f"{output_dir}/overall_report.txt", 'w', encoding='utf-8') as f:
            f.write("Multi-Project LLM Stability Analysis Report\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total Projects Analyzed: {len(results)}\n\n")
            
            # 计算整体统计
            if not comparison_df.empty:
                f.write("Overall Statistics:\n")
                f.write(f"  - Average Exclusion Rate: {comparison_df['Avg Exclusion Rate (%)'].mean():.2f}%\n")
                f.write(f"  - Average Consistency: {comparison_df['Avg Consistency'].mean():.3f}\n")
                f.write(f"  - Average Stability: {comparison_df['Avg Function Stability'].mean():.3f}\n")
                f.write(f"  - Convergence Rate: {(comparison_df['Convergence'] == 'Yes').sum()}/{len(comparison_df)}\n")
        
        print(f"\n多项目分析结果已保存到: {output_dir}/")


class ProjectAnalyzer:
    """单个项目分析器"""
    
    def __init__(self, base_path, lib, k):
        self.base_path = base_path
        self.lib = lib
        self.k = k
        self.analyses = {}
        self.reassignments = {}
        
    def load_data(self, max_iter):
        """加载项目数据"""
        base_dir = f"{self.base_path}/{self.lib}/{self.k}"
        
        for i in range(1, max_iter + 1):
            iter_dir = f"{base_dir}/iteration_{i}"
            
            if os.path.exists(iter_dir):
                # 分析结果
                analysis_file = f"{iter_dir}/{self.lib}_cluster_analysis_{i}.json"
                if os.path.exists(analysis_file):
                    try:
                        with open(analysis_file, 'r', encoding='utf-8') as f:
                            self.analyses[i] = json.load(f)
                    except:
                        print(f"  警告: 无法读取 {analysis_file}")
                
                # 重新分配结果
                reassign_file = f"{iter_dir}/{self.lib}_reassignment_results_{i}.json"
                if os.path.exists(reassign_file):
                    try:
                        with open(reassign_file, 'r', encoding='utf-8') as f:
                            self.reassignments[i] = json.load(f)
                    except:
                        pass
        
        return len(self.analyses)
    
    def calculate_metrics(self):
        """计算项目指标"""
        metrics = []
        
        for iter_num in sorted(self.analyses.keys()):
            analysis = self.analyses[iter_num]
            
            # 统计排除情况
            total_funcs = 0
            total_exclude = 0
            
            for cluster_data in analysis.values():
                func_count = cluster_data.get('function_count', 0)
                exclude_count = len(cluster_data.get('exclude_function', []))
                total_funcs += func_count
                total_exclude += exclude_count
            
            # 一致性计算
            consistency = 0.0
            if iter_num > 1 and (iter_num-1) in self.analyses:
                consistency = self._calculate_consistency(
                    self.analyses[iter_num-1], analysis
                )
            
            # 重新分配率
            reassign_rate = 0.0
            if iter_num in self.reassignments:
                reassign_data = self.reassignments[iter_num]
                excluded = reassign_data.get('total_excluded_functions', 0)
                reassigned = reassign_data.get('successfully_reassigned', 0)
                if excluded > 0:
                    reassign_rate = reassigned / excluded
            
            metrics.append({
                'iteration': iter_num,
                'exclusion_rate': total_exclude / total_funcs if total_funcs > 0 else 0,
                'consistency_score': consistency,
                'reassignment_rate': reassign_rate
            })
        
        return pd.DataFrame(metrics)
    
    def _calculate_consistency(self, prev_analysis, curr_analysis):
        """计算一致性"""
        similarities = []
        
        for cluster_id in curr_analysis:
            if cluster_id in prev_analysis:
                curr_exclude = set(curr_analysis[cluster_id].get('exclude_function', []))
                prev_exclude = set(prev_analysis[cluster_id].get('exclude_function', []))
                
                if curr_exclude or prev_exclude:
                    intersection = len(curr_exclude & prev_exclude)
                    union = len(curr_exclude | prev_exclude)
                    similarity = intersection / union if union > 0 else 1.0
                    similarities.append(similarity)
        
        return np.mean(similarities) if similarities else 0.0
    
    def analyze_function_stability(self):
        """分析函数稳定性"""
        func_history = defaultdict(list)
        
        for iter_num, analysis in self.analyses.items():
            for cluster_id, cluster_data in analysis.items():
                # 获取函数列表
                functions = []
                if 'functions' in cluster_data:
                    functions = [f['function_name'] for f in cluster_data['functions']]
                elif 'functions_info' in cluster_data:
                    functions = [f['function_name'] for f in cluster_data['functions_info']]
                elif 'functions_list' in cluster_data:
                    functions = cluster_data['functions_list']
                
                excluded = set(cluster_data.get('exclude_function', []))
                
                for func in functions:
                    func_history[func].append({
                        'iteration': iter_num,
                        'cluster': cluster_id,
                        'excluded': func in excluded
                    })
        
        # 计算稳定性
        stability_data = []
        for func, history in func_history.items():
            if len(history) < 2:
                continue
            
            history = sorted(history, key=lambda x: x['iteration'])
            
            # 计算聚类变化
            cluster_changes = 0
            for i in range(1, len(history)):
                if history[i]['cluster'] != history[i-1]['cluster']:
                    cluster_changes += 1
            
            stability_score = 1 - (cluster_changes / (len(history) - 1))
            
            stability_data.append({
                'function': func,
                'stability_score': stability_score,
                'cluster_changes': cluster_changes
            })
        
        return pd.DataFrame(stability_data)
    
    def generate_summary_stats(self, metrics_df, func_stability_df):
        """生成统计摘要"""
        summary = {}
        
        if not metrics_df.empty:
            summary['avg_exclusion_rate'] = f"{metrics_df['exclusion_rate'].mean() * 100:.2f}%"
            summary['avg_consistency'] = f"{metrics_df['consistency_score'].mean():.3f}"
            summary['avg_reassignment'] = f"{metrics_df['reassignment_rate'].mean() * 100:.2f}%"
            
            # 趋势分析
            if len(metrics_df) >= 2:
                excl_slope = self._calculate_slope(metrics_df['exclusion_rate'])
                cons_slope = self._calculate_slope(metrics_df['consistency_score'])
                
                summary['exclusion_trend'] = 'Increasing' if excl_slope > 0.01 else 'Decreasing' if excl_slope < -0.01 else 'Stable'
                summary['consistency_trend'] = 'Increasing' if cons_slope > 0.01 else 'Decreasing' if cons_slope < -0.01 else 'Stable'
        
        if not func_stability_df.empty:
            scores = func_stability_df['stability_score']
            total = len(scores)
            
            high_stable = (scores >= 0.8).sum()
            medium_stable = ((scores >= 0.5) & (scores < 0.8)).sum()
            low_stable = (scores < 0.5).sum()
            
            summary['avg_stability'] = f"{scores.mean():.3f}"
            summary['high_stable_pct'] = f"{high_stable/total*100:.1f}%"
            summary['medium_stable_pct'] = f"{medium_stable/total*100:.1f}%"
            summary['low_stable_pct'] = f"{low_stable/total*100:.1f}%"
        
        # 收敛性分析
        if len(metrics_df) >= 3:
            last_3 = metrics_df.tail(3)
            excl_changes = np.abs(np.diff(last_3['exclusion_rate']))
            avg_change = np.mean(excl_changes) if len(excl_changes) > 0 else 0
            
            if avg_change < 0.02:
                summary['convergence'] = 'Yes'
            elif avg_change < 0.05:
                summary['convergence'] = 'Partial'
            else:
                summary['convergence'] = 'No'
        
        return summary
    
    def _calculate_slope(self, series):
        """计算线性趋势斜率"""
        x = np.arange(len(series))
        return np.polyfit(x, series.values, 1)[0]


# ==================== 主程序 ====================
def main():
    """主函数"""
    print("多项目LLM聚类稳定性分析")
    print("=" * 60)
    
    # 配置项目信息
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
    
    # 创建分析器
    analyzer = MultiProjectLLMAnalyzer(base_path="D:/TEST/cluster/cluster")
    
    # 分析所有项目
    print("开始分析所有项目...")
    results = analyzer.analyze_all_projects(lib_clusters, max_iter=20)
    
    # 打印摘要
    print(f"\n分析完成！共分析了 {len(results)} 个项目")
    print("\n各项目关键指标:")
    print("-" * 60)
    
    for proj_name, result in results.items():
        summary = result['summary']
        print(f"\n{proj_name}:")
        print(f"  排除率: {summary.get('avg_exclusion_rate', 'N/A')}")
        print(f"  一致性: {summary.get('avg_consistency', 'N/A')}")
        print(f"  函数稳定性: {summary.get('avg_stability', 'N/A')}")
        print(f"  收敛状态: {summary.get('convergence', 'N/A')}")


if __name__ == "__main__":
    main()