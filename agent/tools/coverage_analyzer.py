import pandas as pd
import os
import sys
from pathlib import Path
from langchain.tools import tool
from datetime import datetime
import logging
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

# Configure logging system
def setup_logging(output_dir):
    """Setup logging configuration"""
    log_dir = os.path.join(output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"coverage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

@tool("read_coverage_file", return_direct=True)
def read_coverage_file(file_path: str) -> str:
    """Read and analyze coverage data file (e.g., bb_cov.csv), group by function, use the bb with maximum execution count to represent each function, and generate coverage summary using LLM for each function"""
    try:
        if not os.path.exists(file_path):
            return f"Error: Coverage file '{file_path}' does not exist"
        
        # Create output directory
        output_dir = os.path.join(os.path.dirname(file_path), "llm_coverage_reports")
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup logging
        logger = setup_logging(output_dir)
        
        logger.info(f"Starting coverage file analysis: {file_path}")
        
        # Read data
        logger.info("Reading CSV file...")
        df = pd.read_csv(file_path)
        logger.info(f"Successfully read data: {df.shape[0]} rows × {df.shape[1]} columns")
        
        analysis_report = [
            f"=== Coverage File Analysis ===",
            f"File Path: {file_path}",
            f"Data Shape: {df.shape[0]} rows × {df.shape[1]} columns",
            f"Original Basic Blocks Count: {len(df)}",
            f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Extract time series columns
        time_columns = [col for col in df.columns if 'Execution Count' in col]
        logger.info(f"Found {len(time_columns)} time series columns: {time_columns}")
        
        # Group by function, find the bb with maximum execution count for each function
        logger.info("Grouping data by function...")
        function_groups = df.groupby('Function')
        function_representatives = []
        
        analysis_report.append(f"Number of Functions: {len(function_groups)}")
        analysis_report.append("")
        
        logger.info(f"Found {len(function_groups)} functions, starting to process each function...")
        
        for function_name, group in function_groups:
            # Calculate total execution count for each bb (sum of all time points)
            group['total_executions'] = group[time_columns].sum(axis=1)
            
            # Find the bb with maximum execution count as function representative
            max_execution_idx = group['total_executions'].idxmax()
            representative_row = group.loc[max_execution_idx]
            
            function_representatives.append({
                'function_name': function_name,
                'representative_row': representative_row,
                'bb_count': len(group),
                'max_total_executions': representative_row['total_executions']
            })
            
            logger.debug(f"Function '{function_name}': {len(group)} basic blocks, max execution count: {representative_row['total_executions']}")
        
        logger.info(f"Completed function grouping, found {len(function_representatives)} function representatives")
        
        # Use LLM to generate summary for each function's representative bb
        function_summaries = []
        logger.info("Starting LLM analysis for each function...")
        
        for i, func_info in enumerate(function_representatives, 1):
            function_name = func_info['function_name']
            row = func_info['representative_row']
            bb_count = func_info['bb_count']
            max_total_executions = func_info['max_total_executions']
            
            logger.info(f"[{i}/{len(function_representatives)}] Analyzing function '{function_name}' (contains {bb_count} basic blocks)...")
            
            # Use LLM to generate function coverage summary
            function_summary = generate_llm_function_summary(
                row, function_name, bb_count, max_total_executions, time_columns, logger
            )
            function_summaries.append(function_summary)
            
            # Save individual function's LLM summary
            save_llm_function_summary(function_summary, function_name, output_dir, logger)
            
            logger.info(f"Completed analysis for function '{function_name}'")
        
        logger.info(f"Completed LLM analysis for all functions, generated {len(function_summaries)} summaries")
        
        # Generate main report
        logger.info("Generating main report...")
        main_report = generate_main_report(function_summaries, output_dir, logger)
        analysis_report.extend(main_report)
        
        final_report = "\n".join(analysis_report)
        
        # Save main report
        main_report_path = os.path.join(output_dir, "LLM_COVERAGE_ANALYSIS.md")
        with open(main_report_path, 'w', encoding='utf-8') as f:
            f.write(final_report)
        
        logger.info(f"Main report saved: {main_report_path}")
        logger.info("Coverage analysis completed")
        
        return final_report + f"\n\n=== Report Saved ===" + f"\nLLM analysis reports saved to: {output_dir}" + f"\nMain report: {main_report_path}"
        
    except Exception as e:
        logger.error(f"Error reading coverage file: {str(e)}", exc_info=True)
        return f"Error reading coverage file: {str(e)}"

def generate_llm_function_summary(row, function_name, bb_count, max_total_executions, time_columns, logger):
    """Generate LLM summary for function's representative bb"""
    
    # Prepare coverage data
    coverage_data = []
    for time_col in time_columns:
        execution_count = row[time_col]
        coverage_data.append(f"{time_col}: {execution_count}")
    
    coverage_info = "\n".join(coverage_data)
    
    # Build LLM prompt
    prompt = f"""
Please analyze the following function coverage data and provide a concise summary:

Function Name: {function_name}
Number of Basic Blocks: {bb_count}
Maximum Execution Count (representative basic block): {max_total_executions}

Coverage Time Series Data:
{coverage_info}

Please provide:
1. Brief description of the function's execution pattern
2. Characteristics of execution frequency (e.g., continuously active, intermittent execution, rarely executed, etc.)
3. Any noteworthy observations

Please reply in concise paragraph format.
"""
    
    try:
        logger.debug(f"Calling LLM for function '{function_name}'...")
        
        # Use the pre-configured LLM to generate summary
        message = HumanMessage(content=prompt)
        logger.debug(f"Sent LLM request, prompt length: {len(prompt)} characters")
        
        response = llm.invoke([message])
        summary = response.content.strip()
        
        logger.debug(f"LLM response received successfully, response length: {len(summary)} characters")
        logger.info(f"LLM analysis completed for function '{function_name}'")
        
    except Exception as e:
        error_msg = f"Error generating summary: {str(e)}"
        logger.error(f"LLM call failed - Function: {function_name}, Error: {str(e)}", exc_info=True)
        summary = error_msg
    
    return {
        'function_name': function_name,
        'bb_count': bb_count,
        'max_total_executions': max_total_executions,
        'summary': summary,
        'coverage_data': coverage_data
    }

def save_llm_function_summary(function_summary, function_name, output_dir, logger):
    """Save individual function's LLM summary to file"""
    
    try:
        # Create filename-safe function name
        safe_function_name = "".join(c for c in function_name if c.isalnum() or c in ('_', '-')).rstrip()
        filename = f"function_{safe_function_name}_summary.md"
        file_path = os.path.join(output_dir, filename)
        
        content = [
            f"# Function Coverage Analysis: {function_summary['function_name']}",
            f"",
            f"## Basic Information",
            f"- **Function Name**: {function_summary['function_name']}",
            f"- **Number of Basic Blocks**: {function_summary['bb_count']}",
            f"- **Maximum Execution Count**: {function_summary['max_total_executions']}",
            f"",
            f"## LLM Analysis Summary",
            f"{function_summary['summary']}",
            f"",
            f"## Detailed Coverage Data (Representative Basic Block)",
        ]
        
        for data_line in function_summary['coverage_data']:
            content.append(f"- {data_line}")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
        
        logger.debug(f"Function '{function_name}' summary saved: {file_path}")
        
    except Exception as e:
        logger.error(f"Error saving function '{function_name}' summary: {str(e)}", exc_info=True)

def generate_main_report(function_summaries, output_dir, logger):
    """Generate main report"""
    
    try:
        logger.info(f"Generating main report containing {len(function_summaries)} function summaries")
        
        report = [
            "## Function Coverage Analysis Summary",
            "",
            "### Analysis Overview",
            f"- Total Functions Analyzed: {len(function_summaries)}",
            f"- Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "### Function Analysis Results",
            ""
        ]
        
        # Sort by execution count
        sorted_summaries = sorted(function_summaries, key=lambda x: x['max_total_executions'], reverse=True)
        logger.debug(f"Sorting by execution count completed, highest execution count: {sorted_summaries[0]['max_total_executions'] if sorted_summaries else 0}")
        
        for i, summary in enumerate(sorted_summaries, 1):
            report.extend([
                f"#### {i}. {summary['function_name']}",
                f"- Number of Basic Blocks: {summary['bb_count']}",
                f"- Maximum Execution Count: {summary['max_total_executions']}",
                f"- Analysis Summary: {summary['summary']}",
                ""
            ])
        
        logger.info("Main report content generation completed")
        return report
        
    except Exception as e:
        logger.error(f"Error generating main report: {str(e)}", exc_info=True)
        return [f"Error generating main report: {str(e)}"]