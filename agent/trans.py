import json
import os

def transform_json_keys(json_data):
    """将JSON数据的键转换为路径的最后一部分"""
    transformed = {}
    for key, value in json_data.items():
        # 使用os.path.basename获取路径的最后一部分
        new_key = os.path.basename(key)
        transformed[new_key] = value
    return transformed

# 从文件读取JSON数据
input_file = './tosem/data/function/size/api/src_api_summary.json'  # 替换为你的输入文件路径
output_file = './tosem/data/function/size/api/new_src_api_summary.json'  # 替换为你想要的输出文件路径

try:
    # 读取原始JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换键名
    transformed_data = transform_json_keys(data)
    
    # 保存转换后的数据到新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_data, f, indent=2, ensure_ascii=False)
    
    print(f"转换完成！结果已保存到 {output_file}")
    
    # 打印转换前后的键名对比
    print("\n转换前后键名对比：")
    for old_key, new_key in zip(data.keys(), transformed_data.keys()):
        print(f"原键: {old_key}")
        print(f"新键: {new_key}")
        print("---")

except FileNotFoundError:
    print(f"错误：找不到文件 {input_file}")
except json.JSONDecodeError:
    print(f"错误：文件 {input_file} 不是有效的JSON格式")
except Exception as e:
    print(f"发生错误：{e}")