#!/usr/bin/env python
# -*- coding:utf-8 -*-

import logging
import yaml

CONFS = None

def load_confs(confs_path='./confs/config.yaml'):
    # TODO Docstring
    global CONFS
    # 这边是一个判断：看是否有config.yaml这个档案，因为有时候储存格式（文档名）会多加一个 .template
    # try - except 是异常处理机制，except有很多标准异常：IOError：输入/输出操作失败；FloatingPointError：浮点计算错误；……
    if CONFS is None:
        try:
            CONFS = yaml.load(open(confs_path), Loader=yaml.FullLoader)
        except IOError:
            confs_template_path = confs_path + '.template'
            logging.warn(
                'Confs path: {} does not exist. Attempting to load confs template, '
                'from path: {}'.format(confs_path, confs_template_path))
            CONFS = yaml.load(open(confs_template_path))
    return CONFS


def get_conf(conf_name):
    return load_confs()[conf_name]

