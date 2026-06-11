import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
import json
import logging
import collections
import concurrent.futures
import time
from functools import partial

import chardet
from codetext.parser.cpp_parser import CppParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_cpp_files(src_folder):
    """
    查找C++源文件和头文件
    """
    src_dic = {'src': [], 'head': []}  # 源代码和头文件
    test_dic = {'src': [], 'head': []}  # 测试代码和头文件
    
    # 源代码文件扩展名
    source_extensions = ('.cpp', '.c', '.cc', '.cxx')
    # 头文件扩展名
    header_extensions = ('.h', '.hpp', '.hh', '.hxx')
    
    for root, dirs, files in os.walk(src_folder):
        # 跳过一些明显不需要的目录
        dirs[:] = [d for d in dirs if d not in ('.git', '.svn', 'build', 'cmake-build')]
        
        for file in files:
            file_path = os.path.join(root, file)
            lower_file = file.lower()
            lower_root = root.lower()
            
            # 判断是否为测试文件
            is_test = 'test' in lower_file or 'test' in lower_root
            target_dict = test_dic if is_test else src_dic
            
            if file.endswith(source_extensions):
                target_dict['src'].append(file_path)
            elif file.endswith(header_extensions):
                target_dict['head'].append(file_path)
    
    return src_dic, test_dic

def process_single_file(file_path, file_type, enable_debug=False):
    """
    处理单个文件的函数（支持源代码和头文件）
    """
    logger.debug(f"Processing {file_type} file: {file_path}")
    
    try:
        # 尝试多种编码读取
        with open(file_path, 'rb') as file:
            raw_data = file.read()
        
        # 检测编码
        detected = chardet.detect(raw_data)
        encoding = detected['encoding'] or 'utf-8'
        
        try:
            code = raw_data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            # 如果检测的编码失败，尝试常见编码
            for enc in ['utf-8', 'latin-1', 'cp1252', 'gbk']:
                try:
                    code = raw_data.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                logger.warning(f"Failed to decode {file_path} with all attempted encodings")
                return file_path, None

        # 解析代码
        fn_def_list, fn_declaration, class_node_list, struct_node_list, include_list, global_variables, enumerate_node_list = CppParser.split_code(code, is_return_node=False)
        
        result = {
            'fn_def_list': fn_def_list,
            'fn_declaration': fn_declaration,
            'class_node_list': class_node_list,
            'struct_node_list': struct_node_list,
            'include_list': include_list,
            "global_variables": global_variables,
            "enumerate_node_list": enumerate_node_list
        }
        
        # 调试输出（可选）
        if enable_debug:
            debug_output_path = f'{file_path}.debug.json'
            try:
                with open(debug_output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.debug(f"Debug output written to {debug_output_path}")
            except Exception as e:
                logger.warning(f"Failed to write debug output for {file_path}: {e}")
        
        logger.info(f"Successfully processed {file_path}: {len(fn_def_list)} defs, {len(fn_declaration)} decls, {len(class_node_list)} classes")
        return file_path, result
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return file_path, None

class APIExtractor:
    def __init__(self, src_folder, output_folder, max_workers=None, enable_debug=False):
        self.src_folder = src_folder
        self.output_results_folder = output_folder
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.enable_debug = enable_debug
    
    def extract_api_from_files(self):
        """
        从源代码文件和头文件提取API
        """
        if not os.path.isdir(self.src_folder):
            logger.error(f"{self.src_folder} does not exist.")
            return None, None
            
        logger.info(f"Extracting API information from source and header files: {self.src_folder}")
        logger.info(f"Using {self.max_workers} workers for parallel processing")
        
        start_time = time.time()
        src_dic, test_dic = find_cpp_files(self.src_folder)    

        logger.info(f"Found {len(src_dic['src'])} source files, {len(src_dic['head'])} header files")
        logger.info(f"Found {len(test_dic['src'])} test source files, {len(test_dic['head'])} test header files")
    
        if not src_dic['src'] and not src_dic['head'] and not test_dic['src'] and not test_dic['head']:
            logger.warning("No C++ files found!")
            self._debug_directory_structure()
            return None, None

        logger.info("Extracting API information from source code and headers...")
        result_src = self._extract_API_parallel(src_dic)
        logger.info("Extracting API information from test code and headers...")
        result_test = self._extract_API_parallel(test_dic)
        
        # 保存结果
        self._save_results(result_src, result_test)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Extraction completed in {elapsed_time:.2f} seconds")
        
        return result_src, result_test

    def _extract_API_parallel(self, src_dic):
        """使用并行处理提取API"""
        result = collections.defaultdict(dict)
        
        # 创建处理函数的部分应用
        process_func = partial(process_single_file, enable_debug=self.enable_debug)
        
        # 处理所有文件类型：源代码和头文件
        for file_type in ['src', 'head']:
            if not src_dic[file_type]:
                logger.info(f"No {file_type} files to process")
                continue
                
            logger.info(f"Processing {len(src_dic[file_type])} {file_type} files in parallel...")
            
            # 使用线程池并行处理
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(process_func, file_path, file_type): file_path 
                    for file_path in src_dic[file_type]
                }
                
                # 收集结果
                completed = 0
                total_files = len(src_dic[file_type])
                
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        file_path, file_result = future.result()
                        if file_result is not None:
                            result[file_type][file_path] = file_result
                    except Exception as e:
                        logger.error(f"Unexpected error processing {file_path}: {e}")
                    
                    completed += 1
                    if completed % 10 == 0:  # 每10个文件报告一次进度
                        logger.info(f"Progress: {completed}/{total_files} {file_type} files processed")

        return result

    def _save_results(self, result_src, result_test):
        """保存结果到文件"""
        os.makedirs(f'{self.output_results_folder}/api', exist_ok=True)
        
        try:
            with open(f'{self.output_results_folder}/api/src_api.json', 'w', encoding='utf-8') as f:
                json.dump(result_src, f, indent=2, ensure_ascii=False)
            with open(f'{self.output_results_folder}/api/test_api.json', 'w', encoding='utf-8') as f:
                json.dump(result_test, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {self.output_results_folder}/api/")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def _debug_directory_structure(self):
        """调试目录结构"""
        logger.debug("Directory structure:")
        for root, dirs, files in os.walk(self.src_folder, topdown=True):
            # 限制深度以避免过多输出
            level = root.replace(self.src_folder, '').count(os.sep)
            if level > 3:
                continue
                
            indent = ' ' * 2 * level
            logger.debug(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 2 * (level + 1)
            # 显示所有C++相关文件
            cpp_files = [f for f in files if f.endswith(('.cpp', '.c', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx'))]
            for file in cpp_files[:10]:  # 只显示前10个文件
                logger.debug(f"{sub_indent}{file}")
            if len(cpp_files) > 10:
                logger.debug(f"{sub_indent}... and {len(cpp_files) - 10} more C++ files")

    def _print_summary(self, result_src, result_test):
        """打印提取摘要"""
        total_functions = 0
        total_classes = 0
        total_structs = 0
        total_source_files = 0
        total_header_files = 0
        
        for result_dict in [result_src, result_test]:
            # 统计源代码文件
            for file_path, data in result_dict.get('src', {}).items():
                total_functions += len(data['fn_def_list']) + len(data['fn_declaration'])
                total_classes += len(data['class_node_list'])
                total_structs += len(data['struct_node_list'])
                total_source_files += 1
            
            # 统计头文件
            for file_path, data in result_dict.get('head', {}).items():
                total_functions += len(data['fn_def_list']) + len(data['fn_declaration'])
                total_classes += len(data['class_node_list'])
                total_structs += len(data['struct_node_list'])
                total_header_files += 1
        
        logger.info("Extraction Summary:")
        logger.info(f"  Total source files processed: {total_source_files}")
        logger.info(f"  Total header files processed: {total_header_files}")
        logger.info(f"  Total functions: {total_functions}")
        logger.info(f"  Total classes: {total_classes}")
        logger.info(f"  Total structs: {total_structs}")

def main(target: str):
    # 配置路径
    src_folder = f"./tosem/source/{target}"
    output_folder = f"./tosem/data/function/{target}"
    
    # 创建提取器并执行提取（处理源代码和头文件）
    extractor = APIExtractor(src_folder, output_folder, max_workers=8, enable_debug=False)
    result_src, result_test = extractor.extract_api_from_files()
    
    if result_src is not None:
        # 打印摘要信息
        extractor._print_summary(result_src, result_test)
    else:
        logger.error("API extraction failed!")

if __name__ == "__main__":
    main("binutils")