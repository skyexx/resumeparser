#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import logging
import json # save as json
# import pandas as pd
import lib
import convert
import split
import extract

def main():
    """
    Main function documentation template
    :return: None
    :rtype: None
    """
    logging.getLogger().setLevel(logging.INFO)
    
    candidate_file_list = get_candidate_list()

    # for i in candidate_file_list:
    #     diff_type(i)   # 不同格式的解析
    diff_type(candidate_file_list[11]) # 11 马

    return None


def get_candidate_list():  
    '''
    获取简历名字的列表
    :return: observations
    :retype: df
    '''
    logging.info('Get candidate list')

    candidate_file_list = []

    for root, dirs, files in os.walk(lib.get_conf('resume_directory')):
        folder_files = map(lambda x: os.path.join(root, x), files)
        candidate_file_list.extend(folder_files) # 其实没必要转成 pandas 的格式
    return candidate_file_list


AVAILABLE_EXTENSIONS = {'.csv', '.doc', '.docx', '.eml', '.epub', '.gif', '.htm', '.html', '.jpeg', '.jpg', '.json',
                        '.log', '.mp3', '.msg', '.odt', '.ogg', '.pdf', '.png', '.pptx', '.ps', '.psv', '.rtf', '.tff',
                        '.tif', '.tiff', '.tsv', '.txt', '.wav', '.xls', '.xlsx'}

def write_txt_file(text:list, output_txtpath:str):
    with open(output_txtpath, "w", encoding='utf-8') as txt:
        for i in range(len(text)):
            s = str(text[i])
            txt.write(s)      # 自带文件关闭功能，不需要再写 f.close()
            txt.write('\n')   # 换行

# json.dumps（）方法是将字典型数据转化成字符串型数据，而json.dumps （）方法对中文默认使用的ascii编码.如果要输出中文需要指定ensure_ascii=False
def write_json_file(text:dict, output_jsonpath:str):
    with open(output_jsonpath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(text, ensure_ascii=False)+'\n')
        f.close() # 会在目录下生成一个1.json的文件，文件内容是dict数据转成的json数据

def diff_type(file):   # 不同的格式转换
    output_filename = os.path.basename(os.path.splitext(file)[0]) + '.txt'  # 非常好用的路径切割方式
    output_jsonfilename = os.path.basename(os.path.splitext(file)[0]) + '.json'
    output_txtpath = os.path.join('.', 'data', 'output', 'txt', output_filename)  # txt的路径
    output_jsonpath = os.path.join('.', 'data', 'output', 'json', output_jsonfilename) # json path
    endswith = os.path.splitext(file)[1]
    print(output_filename)

    if endswith in AVAILABLE_EXTENSIONS:
        if endswith == '.pdf':
            text_list, page_prop_dict= convert.transform_pdf(file, output_txtpath) # page_prop_dict 后面不会用到
            segment_dict = split.create_pdf_segments(text_list)
            # write_txt_file(segment_dict["education_segment"], output_txtpath2)
            final = extract.main(text_list, segment_dict)
        # elif endswith == '.doc':
        #     output_text = convert.transform_doc(file, output_filepath)
        # elif endswith == '.html':
        #     output_text = convert.transform_html(file, output_filepath)
        # output_text.close()
        print("ok")
        write_json_file(final, output_jsonpath)
    else:
        print('No function to transform!')
    # 写入json文件
    try:
        write_json_file(final, output_jsonpath)
    except:
        return ""  # MacOS 的隐藏文件会有问题
    return None

if __name__ == '__main__':
    main()