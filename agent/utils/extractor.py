import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取父目录
parent_dir = os.path.dirname(current_dir)
# 将父目录添加到 sys.path
sys.path.insert(0, parent_dir)
import json
import logging
import collections

import chardet
from codetext.parser.cpp_parser import CppParser

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_cpp_head_files(src_folder):
    """
    查找C++源文件和头文件
    """
    src_dic = {'src': [], 'head': []}
    test_dic = {'src': [], 'head': []}
    
    for root, dirs, files in os.walk(src_folder):
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith(('.cpp', '.c', '.cc', '.cxx')):
                if 'test' in file.lower() or 'test' in root.lower():
                    test_dic['src'].append(file_path)
                else:
                    src_dic['src'].append(file_path)
            elif file.endswith(('.h', '.hpp', '.hh', '.hxx')):
                if 'test' in file.lower() or 'test' in root.lower():
                    test_dic['head'].append(file_path)
                else:
                    src_dic['head'].append(file_path)
    
    return src_dic, test_dic

class APIExtractor:
    def __init__(self, src_folder, output_folder):
        self.src_folder = src_folder
        self.output_results_folder = output_folder
    
    def extract_api_from_head(self):
        if not os.path.isdir(self.src_folder):
            logger.info(f"{self.src_folder} does not exist.")
            return None, None
            
        logger.info(f"Extracting API information from the source code. {self.src_folder}")
        src_dic, test_dic = find_cpp_head_files(self.src_folder)    

        logger.info(f"Number of source files: {len(src_dic['src'])}")
        logger.info(f"Number of header files: {len(src_dic['head'])}")
    
        if not src_dic['head']:
            logger.warning("No header files found!")
      
            for root, dirs, files in os.walk(self.src_folder):
                logger.debug(f"Directory: {root}")
                for file in files:
                    logger.debug(f"File: {os.path.join(root, file)}")

        logger.info("Extracting API information from the source code.")
        result_src = self._extract_API(src_dic)
        logger.info("Extracting API information from the test code.")
        result_test = self._extract_API(test_dic)
        
        logger.info(f"Store API to {self.output_results_folder}/api/")
        os.makedirs(f'{self.output_results_folder}/api', exist_ok=True)
        
        with open(f'{self.output_results_folder}/api/src_api.json', 'w', encoding='utf-8') as f:
            json.dump(result_src, f, indent=2, ensure_ascii=False)
        with open(f'{self.output_results_folder}/api/test_api.json', 'w', encoding='utf-8') as f:
            json.dump(result_test, f, indent=2, ensure_ascii=False)
            
        return result_src, result_test

    def _extract_API(self, src_dic):
        result = collections.defaultdict(dict)
        for k in ['src', 'head']:
            logger.info(f"Processing {k} files")
            for src in src_dic[k]:
                logger.info(f"Processing file: {src}")
                try:
                    with open(src, 'r', encoding='utf-8') as file:
                        code = file.read()
                except UnicodeDecodeError:
                    with open(src, 'rb') as file:
                        raw = file.read()
                        detected = chardet.detect(raw)
                        encoding = detected['encoding']
                    
                    try:
                        code = raw.decode(encoding)
                    except:
                        logger.error(f"Failed to decode {src} with detected encoding {encoding}. Skipping this file.")
                        continue

                try:
                    fn_def_list, fn_declaraion, class_node_list, struct_node_list, include_list, global_variables, enumerate_node_list = CppParser.split_code(code, is_return_node=False)
                    result[k][src] = {
                        'fn_def_list': fn_def_list,
                        'fn_declaraion': fn_declaraion,
                        'class_node_list': class_node_list,
                        'struct_node_list': struct_node_list,
                        'include_list': include_list,
                        "global_variables": global_variables,
                        "enumerate_node_list": enumerate_node_list
                    }
                    logger.info(f"Successfully processed {src}")
                    logger.info(f"Found {len(fn_def_list)} function definitions, {len(fn_declaraion)} function declarations, {len(class_node_list)} classes, {len(struct_node_list)} structs")
                
                    # 调试输出
                    debug_output_path = f'{src}.debug.json'
                    with open(debug_output_path, 'w', encoding='utf-8') as f:
                        json.dump(result[k][src], f, indent=2, ensure_ascii=False)
                    logger.info(f"Debug output written to {debug_output_path}")
                
                except Exception as e:
                    logger.error(f"Error processing {src}: {str(e)}")
                    continue

        logger.info(f"Finished processing all files. Found data for {len(result['src'])} source files and {len(result['head'])} header files.")
        return result

def main(target: str):
    # 配置路径
    src_folder = f"./tosem/source/{target}"
    output_folder = f"./tosem/data/function/{target}"
    
    # 创建提取器并执行提取
    extractor = APIExtractor(src_folder, output_folder)
    result_src, result_test = extractor.extract_api_from_head()
    
    if result_src is not None:
        logger.info("API extraction completed successfully!")
        
        # 打印摘要信息
        total_functions = 0
        total_classes = 0
        total_structs = 0
        
        for file_type in ['src', 'head']:
            for file_path, data in result_src[file_type].items():
                total_functions += len(data['fn_def_list']) + len(data['fn_declaraion'])
                total_classes += len(data['class_node_list'])
                total_structs += len(data['struct_node_list'])
        
        logger.info(f"Extraction Summary:")
        logger.info(f"  Total functions: {total_functions}")
        logger.info(f"  Total classes: {total_classes}")
        logger.info(f"  Total structs: {total_structs}")
        logger.info(f"  Results saved to: {output_folder}/api/")
    else:
        logger.error("API extraction failed!")

if __name__ == "__main__":
    main("binutils")