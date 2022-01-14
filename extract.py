import csv
import re
import time
# from types import resolve_bases
# from typing_extensions import final
import chardet
from datetime import datetime
from collections import defaultdict

# from numpy.core.arrayprint import set_string_function
import lib
import ckpe
import jieba.posseg as psg
# import jieba

ckpe_obj = ckpe.ckpe()

major_set = set([i for i in open("major_dict.txt", 'r')])
ethnic_set = set([i for i in open("ethnic_dict.txt", 'r')])
city_set = csv.reader(open('city.csv', 'r'))

city_fix = "市|盟|([藏朝鲜回傈景颇傣壮苗哈尼彝布依侗土家白羌]+族|哈萨克|蒙古|柯尔克孜)+自治州"
pro_fix = "省|市|藏族自治区|回族自治区|维吾尔族自治区|壮族自治区"


# ------------------------------------- 字段提取的组件 -------------------------------------

# 教育经历中去除时间，方便后续提取


def del_date(text: list) -> list:
    # 保存除了时间之外的字符（不能分词再提，这样切太碎了，不好提取）
    words = []
    for text in text:
        if re.search('\d{2,4}', text) is None:
            words.append(text)
        else:
            pass
    return words

# -------- 联系方式 --------


def get_email(text_list):
    # rex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    rex = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    for text in text_list:
        if re.search(rex, text):
            email = re.search(rex, text)
            return email.group(0)
    return ""


def get_tel(text_list):
    rex = r'^([0-9]{3,4}-)?[0-9]{7,8}$'  # r'^([0-9]{3,4}-)?[0-9]{7,8}$'
    for text in text_list:
        if re.search(rex, text):
            zipcode = re.search(rex, text)
            return zipcode.group(0)
    return ""


def get_phone_number(text_list):
    rex = r'1[3|4|5|7|8][0-9]{1}[\-]?[0-9]{4}[\-]?[0-9]{4}'
    for text in text_list:
        if re.search(rex, text):
            zipcode = re.search(rex, text)
            return zipcode.group(0)
    return ""


def get_qq(text_list):
    rex = r'^[1-9]\\d{4,10}'  # 有问题手机号会和qq号码混在一起
    for text in text_list:
        if re.search(rex, text):
            zipcode = re.search(rex, text)
            return zipcode.group(0)
    return ""


# ------------------------------------- 时间 ----------------------------------------------
# 匹配正则表达式
matches = {
    # xxxx年xx(月)-xx月
    1: (r'\d{2,4}%s\d{1,2}%s%s\d{1,2}%s', '%%y%s%%m%s%s%%m%s'),
    2: (r'\d{4}%s\d{1,2}%s%s', '%%y%s%%m%s%s'),
    3: (r'\d{2}%s\d{1,2}%s%s', '%%y%s%%m%s%s'),

    # xxxx(年)-xxxx年
    4: (r'\d{2,4}%s%s\d{2,4}%s', '%%y%s%s%%y%s'),
    5: (r'\d{2,4}%s%s', '%%y%s%s'),

    # xxxx年xx月xx日至今
    6: (r'\d{2,4}%s\d{1,2}%s\d{1,2}%s', '%%y%s%%m%s%%d%s'),

    # xxxx年xx月xx日
    7: (r'\d{4}%s\d{1,2}%s\d{1,2}%s', '%%Y%s%%m%s%%d%s'),
    8: (r'\d{2}%s\d{1,2}%s\d{1,2}%s', '%%y%s%%m%s%%d%s'),

    # xxxx年xx月
    9: (r'\d{4}%s\d{1,2}%s', '%%Y%s%%m%s'),
    10: (r'\d{2}%s\d{1,2}%s', '%%y%s%%m%s'),

    # xxxx年
    11: (r'\d{2}%s', '%%y%s' )
}

# 正则中的%s分割
splits = [
    {1: [('年', '月', '[-\~—至]+', '月'), ('年', '', '[-\~—至]+', '月')]},
    {2: [('年', '月', '[ -\~\—]*至今'), ('-', '', '[ -\~\—]*至今'),
         ('\.', '', '[ -\~\—]*至今'), ('\/', '', '[ -\~\—]*至今')]},
    {3: [('年', '月', '[ -\~\—]*至今')]},

    {4: [('年', '[-\~—至]+', '年'), ('', '[-\~—至]+', '年')]},
    {5: [('年', '[ -\~\—]*至今')]},
    {6: [('年', '月', '日[ -\~\—]*至今'), ('-', '-', '[ -\~\—]*至今'),
         ('\.', '\.', '[ -\~\—]*至今'), ('\/', '\/', '[ -\~\—]*至今')]},

    {7: [('年', '月', '日'), ('\/', '\/', ''), ('\.', '\.', ''), ('-', '-', '')]},
    {8: [('年', '月', '日'), ('\/', '\/', ''), ('\.', '\.', ''), ('-', '-', '')]},

    {9: [('年', '月'), ('\/', ''), ('\.', ''), ('-', '')]},
    {10: [('年', '月')]},

    {11: [('年')]}
]


class TimeFinder(object):

    def __init__(self):
        self.match_item = []
        self.init_match_item()

    def init_match_item(self):
        # 构建穷举正则匹配公式，及提取的字符串转datetime格式映射
        for item in splits:
            for num, value in item.items():
                match = matches[num]
                for sp in value:
                    tmp = []
                    for m in match:
                        tmp.append(m % sp)
                    self.match_item.append(tuple(tmp))

    def parse_time_text(self, text, still_active=False):
        # 处理非xxxx年xx月类型
        res = []
        year0 = re.search('\d{2,4}', text).group()
        text = re.sub(year0, '', text, count=1)
        pre_year = time.strftime("%Y", time.localtime())
        pre_mon = time.strftime("%m", time.localtime())
        if len(year0) == 2:
            year0 = '20' + year0
        # 处理至今类型
        if '今' in text:
            if re.search('\d{1,2}', text) is not None:
                months = re.findall('\d{1,2}', text)
                res.append({'year': year0, 'month': months[0]})
            else:
                res.append({'year': year0, 'month': ''})
            res.append({'year': pre_year, 'month': pre_mon})
            still_active = True
        # 处理
        elif '月' in text or '/' in text or '.' in text:
            months = re.findall('\d{1,2}', text)
            res.append({'year': year0, 'month': months[0]})
            if int(months[1]) > int(pre_mon):
                still_active = True
            res.append({'year': year0, 'month': months[1]})
        # 处理 “年”
        # elif '年' in text:
        #     res.append({'year': year0, 'month': ""})
        #     still_active = False
        # 处理xxxx-xxxx年类型
        else:
            res.append({'year': year0, 'month': ''})
            year1 = re.search('\d{2,4}', text).group()
            if len(year1) == 2:
                year1 = '20' + year1
            if int(year1) > int(pre_year):
                still_active = True
            res.append({'year': year1, 'month': ''})
        return res, still_active

    def find_time(self, text):
        # 格式化text为str类型
        if isinstance(text, bytes):
            encoding = chardet.detect(text)['encoding']
            text = text.decode(encoding)
        # 文本初步清洗
        text = re.sub("[\s\$\^\#\&\*()\%\+\=]", "", text)

        res = []
        pattern = '|'.join([x[0] for x in self.match_item])
        pattern = pattern
        match_list = re.findall(pattern, text)

        still_active = False
        pre_year = time.strftime("%Y", time.localtime())
        pre_mon = time.strftime("%m", time.localtime())

        if not match_list:
            return None
        for match in match_list:
            for item in self.match_item:
                flag = 0
                if (len(item) == 2):
                    try:
                        # 年-月转换 （待改进）
                        date = datetime.strptime(
                            match, item[1].replace('\\', ''))
                        res.append({'year': str(date.year),
                                    'month': str(date.month)})
                        if date.year > int(pre_year) or (
                                date.year == int(pre_year) and
                                date.month > int(pre_mon)):
                            still_active = True
                        flag = 1
                        break
                    except Exception as e:
                        continue
            # 如果出现了时间段的描述，则优先选取时间段，并跳出循环
            if flag == 0:
                res, still_active = self.parse_time_text(match)
            # 至多寻找两个日期
            if len(res) >= 2:
                if int(res[0]["year"]) > int(res[1]["year"]):
                    mid = res[0]
                    res[0] = res[1]
                    res[1] = mid
                elif int(res[0]["year"]) == int(res[1]["year"]):
                    if int(res[0]["month"]) == int(res[1]["month"]):
                        mid = res[0]
                        res[0] = res[1]
                        res[1] = mid
                break
        if not res:
            return None
        return res, still_active

    def find_one_time(self, text) -> list:
        if isinstance(text, bytes):
            encoding = chardet.detect(text)['encoding']
            text = text.decode(encoding)
        # 文本初步清洗
        text = re.sub("[\s\$\^\#\&\*()\%\+\=]", "", text)
        pattern = '|'.join([x[0] for x in self.match_item])
        match = re.findall(pattern, text)
        return match


def score(text: str, ltype: str = "none", date_num: int = 0) -> str:
    info = 0
    des = 0
    # 日期分
    if date_num:
        info = info + 10 * date_num * date_num
    # 文本分
    info = info + len(re.findall("[\t ]", text)) * 2
    if (len(text) <= 10 and
            re.search("[。；！？，、]|\d.[\s]*[\u4e00-\u9fa5]", text) is None):
        info = info + 8
    elif len(text) >= 40:
        des = des + 8
    # 标点分
    des = des + len(re.findall("[。；！？]", text)) * 10
    des = des + len(re.findall("[，、]", text)) * 3
    # 格式分
    if ltype == "info":
        info = info + 5
    elif ltype == "des":
        des = des + 5
    # 返回类型
    if des > info:
        return "des"
    elif info > des:
        return "info"
    else:
        return ltype


timefinder = TimeFinder()


para_sign = "[。，；、\,\！\？\?\!]|\d.[\s]*[\u4e00-\u9fa5]"

# 输入为经1，2步处理后的文本数据（默认：lines），输出分块的文本字段。

# -------------------------------- 联系方式 ------------------------------------


def parse_contact_segment(text_list: list) -> dict:  # list -> dict
    text_list = clean_all(text_list)  # 清洗
    contact_info = {}
    contact_info["phone_number"] = get_phone_number(text_list)
    contact_info["QQ"] = get_qq(text_list)
    contact_info["email"] = get_email(text_list)
    contact_info["home_phone_number"] = get_tel(text_list)
    return contact_info

# -------------------------------- basic info ------------------------------------
# 只用于提取 basic info的提取，不删除第一个元素


def clean_basic(lines: list):  #
    text = []
    for i in lines:
        # 去除空行
        if re.sub("\s", "", i) == "":
            continue
        elif re.sub("\s", "", i) == "":
            continue
        # 去重复行
        else:
            line_elem = re.split("\b[\b]+|\n|\｜|\丨|\|", i)
            for elem in line_elem:
                elem = elem.encode('gbk', errors='ignore').decode(
                    'gbk').encode('utf-8').decode('utf-8')  # 去除GBK字符集以外的，主要用于去掉一些特殊标识符号
                elem = re.sub(r"^[\s]", "", elem)  # 去除字符前的空格
                if elem != "" and elem != " ":
                    text.append(elem)
    text = sorted(set(text), key=text.index)  # 把重复的元素删除，且保留原有的顺序
    return text


def get_name(text_list: list):
    text = " ".join(text_list)
    nr_words = []
    for word, flag in psg.lcut(text):
        if len(word) > 0 and flag is u'nr':
            nr_words.append(word)
    if nr_words != []:
        return nr_words[0]
    else:
        return ""


def get_gender(text_list: list):
    rex = r'性别'
    for text in text_list:
        if re.search(rex, text):
            gender = re.search("男|女", text)
            return gender.group(0)
    return ""


def get_age(text_list: list):
    rex = r'年龄|岁'
    for text in text_list:
        if re.search(rex, text):
            age = re.search("([0-9]{2})",text)
            if age is None:
                return ""
            else:
                return age.group(0)
    return ""


def get_date_of_birth(text_list):
    rex = r'生日|出生'
    for text in text_list:
        if re.search(rex, text):
            if re.search(r"[0-9]", text):
                bir = timefinder.find_one_time(text)[0]
                return bir
    return ""


def get_ethnic(text_list):  # 有问题
    rex = r'民族'
    for text in text_list:
        if re.search(rex, text):
            for ethnic in ethnic_set:
                if ethnic in text:
                    return ethnic
    return ""


def get_political_status(text_list: list):
    rex = r'党员|中共党员|团员|共青团员|预备党员'
    for text in text_list:
        if re.search(rex, text):
            pol = re.search(rex, text)
            return pol.group(0)
    return ""


def find_loc(text: str) -> list:
    # 格式化text为str类型
    if isinstance(text, bytes):
        encoding = chardet.detect(text)['encoding']
        text = text.decode(encoding)
    seg = psg.lcut(text)
    res = {}
    res["city"] = ""
    res["province"] = ""
    c_flag = 0
    p_flag = 0
    for word, flag in seg:
        if flag == "ns" or flag == "nz":
            # 从地点中匹配地级市和省份
            for i, city, province in city_set:
                # 跳过标题
                if i == "1":
                    continue
                if ((word == city or word == re.sub(city_fix, "", city))
                        and c_flag == 0):
                    res["city"] = city
                    res["province"] = province
                    c_flag = p_flag = 1
                    break
                elif ((word == province or
                       word == re.sub(pro_fix, "", province))
                      and p_flag == 0):
                    res["province"] = province
                    p_flag = 1
                    break
        # 根据简历书写习惯，仅匹配第一个地点
        if c_flag == 1 and p_flag == 1:
            break
    return res


# def get_current_location(text_list)->list or str:
#     rex = r'现居住地|所在地|现居|居住地|住址'
#     for text in text_list:
#         if re.search(rex, text):
#             for loc in city_set:        # city set
#                 if loc in text:
#                     return loc
#     return ""

def get_current_location(text_list) -> list or str:
    rex = r'现居住地|所在地|现居|居住地|住址'
    for text in text_list:
        if re.search(rex, text):
            loc = find_loc(text)        # city set
            return loc
    return ""


def get_birthplace(text_list) -> list or str:
    rex = r'籍贯|户籍|出生于'
    for text in text_list:
        if re.search(rex, text):
            loc = find_loc(text)        # city set
            return loc
    return ""


def get_gaokao_number(text_list):
    rex = r'高考分数|高考'
    for text in text_list:
        if re.search(rex, text):
            gaokao = re.search(r"[0-9]{3}", text).group(0)
            return gaokao
    return ""


def parse_basic_segment(text_list: list) -> dict:
    text_list = clean_basic(text_list)  # 清洗
    basic_info = {}
    basic_info["name"] = get_name(text_list)
    basic_info["gender"] = get_gender(text_list)
    basic_info["date_of_birth"] = get_date_of_birth(text_list)
    basic_info["age"] = get_age(text_list)
    basic_info["ethnic"] = get_ethnic(text_list)
    basic_info["political_status"] = get_political_status(text_list)
    basic_info["current_location"] = get_current_location(text_list)
    basic_info["gaokao_number"] = get_gaokao_number(text_list)
    basic_info["birthplace"] = get_birthplace(text_list)
    return basic_info

# -------------------------------- 教育经历 ------------------------------------


def get_school(text_list: list) -> str:
    rex = r'[\u4e00-\u9fff].*(大学|学院|高中|⼤学|University)'
    for text in text_list:
        if re.search(rex, text):
            school = re.search(rex, text)
            return school.group(0)
    return ""


def get_degree(text_list: list) -> str:
    rex = r'博士|MBA|EMBA|硕士|本科|大专|高中|中专|初中|硕⼠|职高|技校|\
        硕士研究生|在职研究生|工程硕士|专业硕士|博士研究生|博士在读|MBA硕士|MBA|EMBA|工商管理硕士|工学学士|访问学者|博士后'
    for text in text_list:
        if re.search(rex, text):
            degree = re.search(rex, text)
            return degree.group(0)
    return ""


def get_major(text_list: list) -> str:
    # text_list = del_date(text_list)  # 感觉删不删日期对后续影响不大
    text_str = ''.join(text_list)
    result_list = []
    for major in major_set:
        for text in text_list:
            if major in text:
                result_list.append(major)
    # 歧义消解 水利 水利水电工程 归并为水利水电工程
    result_list = list(set(result_list))
    for i in range(0, len(result_list)):
        for j in range(0, len(result_list)):
            if i == j:
                continue
            if result_list[i].__contains__(result_list[j]):
                result_list[j] = '!*!!'
#     result_list = drop_null(result_list)
    # 歧序消解
    if len(result_list) > 1:
        result_dic = {}
        for item in result_list:
            index = text_str.find(item)
            # print(index)
            result_dic[item] = index
        result_list = sorted(result_dic.items(),
                             key=lambda d: d[1], reverse=False)
        result_list = [v[0] for v in result_list]

    res = " ".join(result_list)
    return res


def get_gpa(text_list: list):
    gpa = ""
    for text in text_list:
        index = text.find("GPA")
        if index >= 0:
            gpa = (text[index + 4:]).strip()  # 去除首位空格
    return gpa

# 判断时间是否解析到一起了


def is_continue(data_list: list) -> bool:
    d_list = []
    for i in range(len(data_list)-1):
        l = i+1
        d = data_list[l]-data_list[i]
        d_list.append(d)
    dup = set(d_list)
    if len(dup) == 1 and 1 in d_list:
        return True
    else:
        return False


def get_all_school(text_list: list) -> list:
    all_school = []
    rex = r'[\u4e00-\u9fff].*(大学|学院|高中|⼤学|)|.*University'
    for text in text_list:
        if re.search(rex, text):
            school = re.search(rex, text)
            all_school.append(school.group(0))
    return all_school


def get_all_degree(text_list: list) -> list:
    all_degree = []
    rex = r'博士|MBA|EMBA|硕士|本科|大专|高中|中专|初中|硕⼠|职高|技校|\
        硕士研究生|在职研究生|工程硕士|专业硕士|博士研究生|博士在读|MBA硕士|\
        MBA|EMBA|工商管理硕士|工学学士|访问学者|博士后|访问学习|交换'
    for text in text_list:
        if re.search(rex, text):
            degree = re.search(rex, text)
            all_degree.append(degree.group(0))
    return all_degree


def dup_extract(date_pts: list, text: list) -> list:
    degree = get_all_degree(text)
    school = get_all_school(text)
    res = []
    for i in range(len(date_pts)):
        exp = {}
        p = date_pts[i]
        period, exp["still_active"] = timefinder.find_time(text[p])
        if len(period) == 2:
            exp["start_year"] = period[0]["year"]
            exp["start_month"] = period[0]["month"]
            exp["end_year"] = period[1]["year"]
            exp["end_month"] = period[1]["month"]
        else:
            exp["start_year"] = period[0]["year"]
            exp["start_month"] = period[0]["month"]
            exp["end_year"] = period[0]["year"]
            exp["end_month"] = period[0]["month"]
        try:
            exp["school"] = school[i]
        except:
            exp["school"] = ""
        try:
            exp["degree"] = degree[i]
        except:
            exp["degree"] = ""
        res.append(exp)
    return res

# 用于各个分割好的模块的清洗


def clean_all(lines:list):  # 前面已经去过一遍重了，这边其实只要删掉第一个元素就可以了 ,
    text = []
    for i in lines:
        # 去除空行
        if re.sub("\s", "", i) == "":
            continue
        elif re.sub("\s", "", i) == "":
            continue
        # 去重复行
        else:
            line_elem = re.split("\b[\b]+|\n|\｜|\丨|\|", i)
            for elem in line_elem:
                elem = elem.encode('gbk', errors='ignore').decode(
                    'gbk').encode('utf-8').decode('utf-8')  # 去除GBK字符集以外的，主要用于去掉一些特殊标识符号
                elem = re.sub(r"^[\s]", "", elem)  # 去除字符前的空格
                if elem != "" and elem != " ":
                    text.append(elem)
    text = sorted(set(text), key=text.index)  # 把重复的元素删除，且保留原有的顺序
    if text != []:
        del text[0]
    else:
        pass
    return text


def edu_unit_extract(text: list, startl: int, endl: int, bfd: int, has_date=True) -> dict:
    assert startl <= bfd
    assert bfd <= endl
    # 写入经历
    exp = {}
    # 分为info（信息实体）和decription
    exp["info"] = []
    exp["description"] = []

    current_line = endl

    # 提取info
    ltype = "info"
    for j in range(bfd, startl-1, -1):
        if j == bfd:
            period, exp["still_active"] = timefinder.find_time(text[j])
            if len(period) == 2:
                exp["start_year"] = period[0]["year"]
                exp["start_month"] = period[0]["month"]
                exp["end_year"] = period[1]["year"]
                exp["end_month"] = period[1]["month"]
            else:
                exp["start_year"] = period[0]["year"]
                exp["start_month"] = period[0]["month"]
                exp["end_year"] = period[0]["year"]
                exp["end_month"] = period[0]["month"]
            exp["info"].append(text[j])  # 以防日期外还有别的信息
        elif (score(text[j], ltype) == "info" or
              score(text[j], ltype) == "none"):
            exp["info"].append(text[j])
        else:
            break

    # 提取description
    ltype = "none"
    for j in range(bfd+1, endl):
        if score(text[j], ltype) == "info" and ltype == "none":
            exp["info"].append(text[j])
        elif (score(text[j], ltype) == "des" or
              score(text[j], ltype) == "none"):
            ltype = "des"
            exp["description"].append(text[j])
        else:
            current_line = j
            break
    # 从分好的一段一段的经历中抽取
    unit_text = exp["info"] + exp["description"]
    exp["degree"] = get_degree(unit_text)
    exp["major"] = get_major(unit_text)  # 后续要加一个判断是否为双学位
    exp["school"] = get_school(unit_text)

    return exp, current_line


def parse_education_segment(lines: list) -> list:  # segment_dict
    education_text = lines['education_segment']
    text = clean_all(education_text)
    # 计算时间节点
    date_pts = []
    for i in range(len(text)):
        if timefinder.find_time(text[i]) is not None:
            date_num = len(timefinder.find_time(text[i])[0])
            if score(text[i], "none", date_num) == "info":
                date_pts.append(i)
        else:
            continue
    # assert len(date_pts) > 1  # 意义？？？
    # 这边加一个判断 如果出现连续的时间 就导入一个函数 -> res
    if is_continue(date_pts):
        res = dup_extract(date_pts, text)
        return res
    else:
        date_pts.append(len(text))
        # 提取经历
        res = []
        startl = 0
        for i in range(len(date_pts)-1):
            endl = date_pts[i+1]
            exp, startl = edu_unit_extract(text, startl, endl, date_pts[i])
            res.append(exp.copy())
        if len(res) == 0:
            return "nothing"
        else:
            pass
        return res


# def parse_basic_segment(text_list, segment_dict):  # 最后从提取好的模块中抽取出来
#     text_list

# -------------------------------- 工作/实习经历 ------------------------------------


def get_job_content(des_list):  # soft skills
    text = ''.join(des_list)
#     ckpe_obj = ckpe.ckpe()
    key_phrases = ckpe_obj.extract_keyphrase(text)
    return key_phrases

# 出版的公司名称的提取方式 -》有公司界外就提；问题：很多公司名称不是以“公司”结尾的
def get_company_name(info: list) -> str:
    company_name = ""
    key = "公司|局|院|所|协会|中心"
    for i in range(len(info)):
        if len(info[i]) <= 2 or len(info[i]) >= 10:
            continue
        elif re.search(key, info[i][-2:]) is not None:
            company_name = info[i]
            del info[i]
            break
        else:
            continue
    return company_name

# 财政部??
def get_department(info: list) -> str:
    department = ""
    key = "部门|部|科|系"
    for i in range(len(info)):
        if len(info[i]) <= 2 or len(info[i]) >= 10:
            continue
        elif re.search(key, info[i][-2:]) is not None:
            department = info[i]
            del info[i]
            break
        else:
            continue
    return department

# 硬匹配：但是像是“用户研究”就没有办法找到
def get_job_title(info: list) -> str:
    job = ""
    key = "实习生|实习|岗|运营|助教|助理|经理|队员|组员|队长|组长|成员|会长|会员|干事|部长|老师"
    for i in range(len(info)):
        if len(info[i]) <= 2 or len(info[i]) >= 10:
            continue
        elif re.search(key, info[i][-3:]) is not None:
            job = info[i]
            del info[i]
            break
        else:
            continue
    return job


def work_unit_extract(text: list, startl: int, endl: int, bfd: int, has_date=True) -> dict:
    assert startl <= bfd
    assert bfd <= endl
    # 写入经历
    exp = {}
    # 分为info（信息实体）和decription
    exp["info"] = []
    exp["description"] = []

    current_line = endl

    # 提取info
    ltype = "info"
    for j in range(bfd, startl-1, -1):
        if j == bfd:
            period, exp["still_active"] = timefinder.find_time(text[j])
            if len(period) == 2:
                exp["start_year"] = period[0]["year"]
                exp["start_month"] = period[0]["month"]
                exp["end_year"] = period[1]["year"]
                exp["end_month"] = period[1]["month"]
            else:
                exp["start_year"] = period[0]["year"]
                exp["start_month"] = period[0]["month"]
                exp["end_year"] = period[0]["year"]
                exp["end_month"] = period[0]["month"]
            exp["info"].append(text[j])  # 以防日期外还有别的信息
        elif (score(text[j], ltype) == "info" or
              score(text[j], ltype) == "none"):
            exp["info"].append(text[j])
        else:
            break

    # 提取description
    ltype = "none"
    for j in range(bfd+1, endl):
        if score(text[j], ltype) == "info" and ltype == "none":
            exp["info"].append(text[j])
        elif (score(text[j], ltype) == "des" or
              score(text[j], ltype) == "none"):
            ltype = "des"
            exp["description"].append(text[j])
        else:
            current_line = j
            break

    des_text = " ".join(exp["description"])
    exp["city"] = find_loc(des_text)["city"]
    exp["province"] = find_loc(des_text)["province"]
    exp["company_name"] = get_company_name(exp["info"])
    exp["department"] = get_department(exp["info"])
    exp["job_title"] = get_job_title(exp["info"])

    return exp, current_line


def parse_work_segment(lines: list) -> list:  # segment_dict
    work_text = lines['work_segment']
    text = clean_all(work_text)
    # 计算时间节点
    date_pts = []
    for i in range(len(text)):
        if timefinder.find_time(text[i]) is not None:
            date_num = len(timefinder.find_time(text[i])[0])
            if score(text[i], "none", date_num) == "info":
                date_pts.append(i)
        else:
            continue
    date_pts.append(len(text))
    # assert len(date_pts) > 1

    # 提取经历
    res = []
    startl = 0
    for i in range(len(date_pts)-1):
        endl = date_pts[i+1]
        exp, startl = work_unit_extract(text, startl, endl, date_pts[i])
        res.append(exp.copy())
    if len(res) == 0:
        return ""
    else:
        pass
    return res



# -------------------------------- 项目经历 ------------------------------------

# 项目和奖项分级的时候需要
def level_extract(text: str) -> str:
    try:
        nation = "国家级|国级|国家|中国[\S]+项目|国家[\S]+项目|中国[\S]+课题|国家[\S]+课题"
        province = "省级|市级|省市级|省[\S]+项目|省[\S]+课题|市[\S]+项目|市[\S]+课题"

        if re.search(nation, text):
            return "国家级"
        elif re.search(province, text):
            return "省市级"
        else:
            return "校级"
    except:
        return ""


def get_project_name(info: list) -> str:
    title = ""
    max_len = 0
    for i in range(len(info)):
        if len(info[i]) > 5 and len(info[i]) <= 20:
            if len(info[i]) > max_len:
                title = info[i]
                max_len = len(info[i])
        else:
            continue
    return title


def parse_project_segment(lines: list) -> list:  # 用于分割经历（ work 和 project 可以用同一个）
    project_text = lines['project_segment']
    text = clean_all(project_text)
#     print(text)
    # 计算时间节点
    date_pts = []
    for i in range(len(text)):
        if timefinder.find_time(text[i]) is not None:
            date_num = len(timefinder.find_time(text[i])[0])
            if score(text[i], "none", date_num) == "info":
                date_pts.append(i)
        else:
            continue
    date_pts.append(len(text))
    # assert len(date_pts) > 1
    # 提取经历
    res = []
    startl = 0
    for i in range(len(date_pts)-1):
        endl = date_pts[i+1]
        exp, startl = project_unit_extract(
            text, startl, endl, date_pts[i])
        res.append(exp.copy())
    if len(res) == 0:
        return ""
    else:
        pass
    return res



def project_unit_extract(text: list, startl: int, endl: int, bfd: int, has_date=True):
    assert startl <= bfd
    assert bfd <= endl
    # 写入经历
    exp = {}
    # 分为info（信息实体）和decription
    exp["info"] = []
    exp["description"] = []

    current_line = endl

    # 提取info
    ltype = "info"
    for j in range(bfd, startl-1, -1):
        if j == bfd:
            period, exp["still_active"] = timefinder.find_time(text[j])
            if len(period) == 2:
                exp["start_year"] = period[0]["year"]
                exp["start_month"] = period[0]["month"]
                exp["end_year"] = period[1]["year"]
                exp["end_month"] = period[1]["month"]
            else:
                exp["start_year"] = period[0]["year"]
                exp["start_month"] = period[0]["month"]
                exp["end_year"] = period[0]["year"]
                exp["end_month"] = period[0]["month"]
            exp["info"].append(text[j])  # 以防日期外还有别的信息
        elif (score(text[j], ltype) == "info" or
              score(text[j], ltype) == "none"):
            exp["info"].append(text[j])
        else:
            break

    # 提取description
    ltype = "none"
    for j in range(bfd+1, endl):
        if score(text[j], ltype) == "info" and ltype == "none":
            exp["info"].append(text[j])
        elif (score(text[j], ltype) == "des" or
              score(text[j], ltype) == "none"):
            ltype = "des"
            exp["description"].append(text[j])
        else:
            current_line = j
            break

    des_text = " ".join(exp["description"])
    exp["city"] = find_loc(des_text)["city"]
    exp["province"] = find_loc(des_text)["province"]
    exp["project_name"] = get_project_name(exp["info"])
    exp["job_title"] = get_job_title(exp["info"])
    exp["project_level"] = level_extract(exp["project_name"])


    return exp, current_line

# -------------------------------- other ------------------------------------

# 从所有文字中，找切分的关键词


def search_keyword(text, keyword_list):
    for word in keyword_list:
        if word in text:
            return True
    return False

# 用技能表中的技能和解析出来的所有文字来匹配


def get_keyword(field):  #
    keyword_dict = {}
    # extractors 就是几个类别 experience:、 platforms:、 database:等
    for extractor, items_of_interest in lib.get_conf(field).items():
        keyword_dict[extractor] = items_of_interest
    return keyword_dict


class SegmentsOtherBlock():
    def __init__(self):
        self.keyword_dict = get_keyword("other_segment_keywords")
        #
        self.skills_language_keywords = self.keyword_dict['skills_language_keywords']
        self.awards_keywords = self.keyword_dict['awards_keywords']
        self.self_evaluation_keywords = self.keyword_dict['self_evaluation_keywords']
        self.skills_language_segment = []
        self.awards_segment = []
        self.self_evaluation_segment = []

    def load_skills_language_segment(self, text_list):
        # Extract skills_segment
        for i, text in enumerate(text_list):  # 这个就变成了一个序号一个字母了
            flag = False
            if search_keyword(text, self.skills_language_keywords):  # 就是匹配到了一个关键词之后我就一直往下搜索
                self.skills_language_segment.append(text)
                i += 1
                flag = True
                while True and i < len(text_list):  # 加一个判断条件，序号要小于整个文本长度，不然就会报错
                    text = text_list[i]   # 判断有没有出现其他的关键字，没有的话，就加入
                    if not search_keyword(text, self.awards_keywords) and not search_keyword(
                            text, self.self_evaluation_keywords):
                        self.skills_language_segment.append(text)
                    else:
                        break
                    i += 1
            if flag:
                break
        return self.skills_language_segment

    def load_awards_segment(self, text_list):
        # Extract awards_segment
        for i, text in enumerate(text_list):
            flag = False
            if search_keyword(text, self.awards_keywords):
                self.awards_segment.append(text)
                i += 1
                flag = True
                while True and i < len(text_list):
                    text = text_list[i]
                    if not search_keyword(text, self.skills_language_keywords) and not search_keyword(
                            text, self.self_evaluation_keywords):
                        self.awards_segment.append(text)
                    else:
                        break
                    i += 1
            if flag:
                break
        return self.awards_segment

    def load_self_evaluation_segment(self, text_list):
        # Extract Project Segment
        for i, text in enumerate(text_list):
            flag = False
            if search_keyword(text, self.self_evaluation_keywords):
                self.self_evaluation_segment.append(text)
                i += 1             # 计数，标记到第几行
                flag = True
                while True and i < len(text_list):  # 如果有keyword，同时小于整个list
                    text = text_list[i]
                    if not search_keyword(text, self.skills_language_keywords) and not search_keyword(
                            text, self.awards_keywords):
                        self.self_evaluation_segment.append(text)
                    else:
                        break
                    i += 1
            if flag:
                break
        return self.self_evaluation_segment

# skills and language 要从技能和语言这个模块中区分出来


def get_skills(sl_text: list) -> list:
    text = clean_all(sl_text)
    text = ''.join(text)
    skill_words = []
    for word, flag in psg.lcut(text):
        if len(word) > 1 and flag in [u'n', u'eng']:
            skill_words.append(word)
    skill_words = sorted(set(skill_words), key=skill_words.index)
    return skill_words


def get_language(sl_text: list) -> list:
    text = clean_all(sl_text)
    text = ''.join(text)
    language = []
    for word, flag in psg.lcut(text):
        if len(word) > 1 and flag in [u'nz']:
            language.append(word)
    language = sorted(set(language), key=language.index)
    return language

# 把日期的部分去掉

# clean 后会把日期分开
def get_awards(awards_text: list, text_list) -> list:
    # text = clean_all(awards_text)  
    res = []
    for i in awards_text:
        unit = {}
        unit["title"] = i
        unit["level"] = level_extract(i)
        res.append(unit)
    return res


def parse_other_segment(lines: list, text_list) -> dict:
    project_text = lines['other_segment']
    load = SegmentsOtherBlock()
    skills_language_segment = load.load_skills_language_segment(project_text)
    awards_segment = load.load_awards_segment(project_text)
    self_evaluation_segment = load.load_self_evaluation_segment(project_text)

    other_dict = {}

    other_dict["skills"] = get_skills(skills_language_segment)  # get_skills
    other_dict["language"] = get_language(skills_language_segment)
    other_dict["awards"] = get_awards(awards_segment, text_list)  # 全局找奖励
    other_dict["self_evaluation"] = clean_all(
        self_evaluation_segment)  # 把“自我描述”删掉

    return other_dict


# def parse_other_segment(segment_dict):
#     other = {}
#     other_list = segment_dict['other_segment']
#     other["skill"] = other_list
#     return other

# ---------------------

def main(text_list, segment_dict):
    final = {}
    final["contact_token"] = parse_contact_segment(text_list)
    final["education_token"] = parse_education_segment(segment_dict)
    final["work_token"] = parse_work_segment(segment_dict)
    final["project_token"] = parse_project_segment(segment_dict)
    final["other_token"] = parse_other_segment(segment_dict, text_list)
    final["basic_token"] = parse_basic_segment(
        text_list)  # 这个应该放在最后面，因为会有很多之前提取的知识（例如教育经历）
    return final
