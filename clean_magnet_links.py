#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理磁力链接文件，去掉每行前面的数字和点号
"""

import re
import glob
import os

def process_magnet_links(input_file, output_file):
    """
    处理磁力链接文件，去掉每行前面的数字和点号
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    try:
        # 读取文件
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 处理每一行
        processed_lines = []
        for line in lines:
            # 使用正则表达式去掉行首的数字和点号
            # 匹配模式：开头是数字，后面跟着点号和空格
            processed_line = re.sub(r'^\d+\.\s*', '', line)
            processed_lines.append(processed_line)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(processed_lines)
        
        print(f"  ✓ 成功处理 {len(processed_lines)} 行")
        print(f"  ✓ 输出文件: {output_file}")
        return True
        
    except Exception as e:
        print(f"  ✗ 处理失败: {e}")
        return False

def process_all_txt_files():
    """
    处理目录中所有的txt文件
    """
    # 获取所有txt文件
    txt_files = glob.glob('*.txt')
    
    # 排除已经处理过的文件
    exclude_files = ['magnet_links_cleaned.txt']
    txt_files = [f for f in txt_files if f not in exclude_files]
    
    print(f"找到 {len(txt_files)} 个txt文件需要处理\n")
    
    success_count = 0
    for txt_file in txt_files:
        print(f"正在处理: {txt_file}")
        output_file = txt_file.replace('.txt', '_cleaned.txt')
        if process_magnet_links(txt_file, output_file):
            success_count += 1
        print()
    
    print(f"=" * 50)
    print(f"处理完成！成功: {success_count}/{len(txt_files)}")
    print(f"=" * 50)

if __name__ == '__main__':
    process_all_txt_files()
