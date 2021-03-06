# coding=utf-8
from django.shortcuts import render
from django.http import JsonResponse

from .models import JobField, RankField
from pandas import Series
from mongoengine import connect
from mongoengine.queryset.visitor import Q


# Connect to mongodb
connect("Spider")


def index(request):
    return render(request, 'index.html')

# ----------------
# 数据可视化 Data Visualization
# ----------------


def get_city_ratio(job_info):
    # 获取城市职位数量比例
    # Get the cities ratio of job numbers 
    items = []

    city_count = float(job_info.count())
    cities = job_info.distinct("job_city")

    for city in cities:
        # 不要使用len作为计数方式,实际测试len大概比count慢10倍
        count = job_info(job_city=city).count()
        # round取小数点两位
        ratio = round(float(count / city_count * 100), 2)
        item = [city, ratio]
        items.append(item)

    return items


def get_job_count(job_info, keywords):
    # 获取职位数量
    # Get posts' count
    items = []

    for keyword in keywords:
        count = job_info(key_word=keyword).count()
        item = [keyword, count]
        items.append(item)

    return items


def get_average_salary(job_info, keyword, city):
    # 获取平均工资
    if city != "全国" or city != "异地招聘":
        items = JobField.objects(Q(key_word=keyword) & Q(job_city=city))
    else:
        return 0

    salary_avg = items.average('salary_avg')

    return round(salary_avg, 2)


def get_salary_trend(job_info, keyword, city):
    # 获取工资趋势
    if city != '全国' or city != '异地招聘':
        items = JobField.objects(Q(key_word=keyword) & Q(job_city=city))
    else:
        items = JobField.objects(key_word=keyword)

    salary_trend_list = []

    dates = items.distinct("create_time")
    for day in dates:
        # day = day.strftime('%Y-%m-%d')
        item = items(__raw__={'create_time': day})
        salary_avg = item.average('salary_avg')
        salary_trend = [day, round(salary_avg, 2)]
        salary_trend_list.append(salary_trend)
 
    salary_trend = dict(salary_trend_list)
    salary_trend = Series(salary_trend)
    return salary_trend


def data_viewer(request, city='东莞'):
    # 数据显示
    job_info = JobField.objects
    keywords = job_info.distinct("key_word")

    kd_salary = {kd: get_average_salary(job_info, kd, city)
                 for kd in keywords if get_average_salary(job_info, kd, city)}

    kd_salary = Series(kd_salary)
    kd_salary = kd_salary.sort_values()[::-1][:25]
    # 为了减少运算量
    # top_keyword = list(kd_salary.index)

    frame = Series(kd_salary)
    series = {index: frame[index] for index in frame.index}
    series = Series(series)

    items = get_city_ratio(job_info)

    job_count_rank = dict(get_job_count(job_info, keywords))
    job_count_rank = Series(job_count_rank)

    context = {
        'cities': items[:20],
        'series': series.sort_values()[::-1][:25],
        'keyword_dict': kd_salary,
        'top_job_counts': job_count_rank.sort_values()[::-1][:25],
        'city': city,
    }
    return render(request, 'data_viewer.html', context)


def get_trend_by_word(request):
    # use Ajax to reduce dom
    keyword = request.GET['keyword']
    city = request.GET['city']

    keyword = str(keyword)
    city = str(city)

    # 获取工资趋势
    if city != '全国' or city != '异地招聘':
        # pattern = r'^(' + city + '|' + city + ')'
        items = JobField.objects(Q(key_word=keyword) & Q(job_city=city))
    else:
        items = JobField.objects(key_word=keyword)

    salary_trend_list = []

    dates = items.distinct("create_time")
    for day in dates:
        item = items(__raw__={'create_time': day})
        salary_avg = item.average('salary_avg')
        salary_trend = [str(day)[0:10], round(salary_avg, 2)]
        salary_trend_list.append(salary_trend)
    salary_trend_list = Series(salary_trend_list).sort_index()[::-1]

    salary_trend = {'type': 'line', 'name': keyword, 'data': [i for i in salary_trend_list]}

    return JsonResponse(salary_trend, safe=False)


def language_trend(request):
    items = RankField.objects
    ratio_list = []
    for item in items:
        name = item.name
        ratio = round(float(item.ratio[:-1]), 2)
        ratio_list.append([name, ratio])
    top = RankField.objects.filter()[0]
    return render(request, 'lang_trend.html', {'ranking': items, 'top': top, 'ratio_list': ratio_list})
