from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
import json
import time
import hashlib
from . import pymongo
from bson import binary
from bson.objectid import ObjectId
from . import pyredis


def response(code: int, message: str, data: any = None):
    body = {'code': code, 'message': message, 'data': {}}
    if data is not None:
        if hasattr(data, '__dict__'):
            body['data'] = data.__dict__
        else:
            body['data'] = data
    return HttpResponse(json.dumps(body, sort_keys=True, ensure_ascii=False))


camp_data = []

comment_data = []


# 通用方法：由id从数组中索取数据
def findCampByID(index):
    for item in camp_data:
        if item.get('id') == index:
            return item
    return None


# 通用方法：由id从评论数组中索取数据
def findCommentsByCampID(index):
    comms = []
    for item in comment_data:
        if item.get('campID') == index:
            comms.append(item)
    return comms


# 获取营地的列表
@require_http_methods('GET')
def list(request):
    camps = []
    datas = pymongo.MongoDB.camps.find({}, {"_id": 1, "title": 1, "stars": 1, "desc": 1, "imgs": 1}).sort("time", -1).limit(100)
    for data in datas:
        camps.append({
            "id": str(data["_id"]),
            "title": str(data["title"]),
            "stars": int(data["stars"]),
            "desc": data["desc"],
            "imgs": data["imgs"]
        })
    return response(0, 'ok', camps)


# 按照id获取营地的详情页信息
@require_http_methods('GET')
def detail(request):
    id = request.GET.get("id", "0")

    camp = {}
    # 先查redis(cache)
    # 找到数据就返回；
    detail_page = pyredis.GetCampDetail(id)
    if detail_page is not None:
        print("Found by redis")
        return response(0, "ok", detail_page)

    # 否则继续到mongodb(主数据库)去找，
    # 如果有人评论则删除缓存
    data = pymongo.MongoDB.camps.find_one({"_id": ObjectId(id)})
    if data is None:
        return response(1, "数据不存在")

    camp = {
        "id": str(data["_id"]),
        "user": str(data["user"]),
        "title": str(data["title"]),
        "stars": int(data["stars"]),
        "desc": data["desc"],
        "address": data["address"],
        "lat": data["lat"],
        "lng": data["lng"],
        "comments": data["comments"],
        "time": int(data['time']),
        "imgs": data["imgs"]
    }

    pyredis.SetCampDetail(id, camp)
    print("Found by mongo")
    # print(camp["lat"])
    # print(camp["lng"])
    return response(0, 'ok', camp)


# 按照id获取某个营地对应的comments
@require_http_methods('GET')
def comments(request):
    campID = request.GET.get('campID', "")
    comms = []
    datas = pymongo.MongoDB.comments.find({"campID": campID}).sort("time", -1).limit(10)
    for data in datas:
        comms.append({
            "id": str(data["_id"]),
            "campID": str(data["campID"]),
            "user": data["user"],
            "stars": int(data["stars"]),
            "time": int(data["time"]),
            "desc": data["desc"],
        })
    return response(0, 'ok', comms)


@require_http_methods('POST')
def commentAdd(request):
    if str(request.body, 'utf-8') == '':
        return response(1, 'parameter cannot be empty' )
    param = json.loads(request.body)
    comment = {
        'campID': '',
        'user': '',
        'stars': 0,
        'time': int(time.time()),
        'desc': ''
    }
    if 'campID' not in param or param["campID"] == "":
        return response(1, 'parameter `campID` cannot be empty')

    camp = pymongo.MongoDB.camps.find_one({"_id": ObjectId(param["campID"])})
    if camp is None:
        return response(1, "信息不存在")

    if 'user' not in param or param['user'] == '':
        return response(1, 'parameter `user` cannot be empty')
    if 'stars' not in param:
        return response(1, 'parameter `stars` cannot be empty')
    if 'desc' not in param:
        comment['desc'] = '此用户没有填写评论'

    comment['campID'] = param['campID']
    comment['user'] = param['user']
    comment['stars'] = param['stars']
    comment['desc'] = param['desc']
    pymongo.MongoDB.comments.insert_one(comment)
    # comment_data.append(comment)
    avgStars = int((camp["stars"] * camp["comments"] + comment["stars"]) / (camp["comments"] + 1))
    pymongo.MongoDB.camps.update_one({"_id": ObjectId(param["campID"])}, {"$inc": {"comments": 1}, "$set":{"stars": avgStars}})

    pyredis.DelCampDetail(param["campID"])
    return response(0, 'ok')


# 临时图片变量：dict {type: pic_type, body: pic_body}
pics = {}


# 图片上传接口
@require_http_methods('POST')
def upload(request):
    f = request.FILES['file']

    body = f.read()
    md5 = hashlib.md5(body).hexdigest()
    typ = f.content_type
    img = pymongo.MongoDB.images.find_one({"md5": md5})
    if img is not None:
        print("find md5 image")
        return response(0, "ok", str(img["_id"]))

    # {"_id": ObjetcId("mongo的唯一ID"), "md5": "唯一的标识", "type": 图片类型, "body": 图片的二进制内容}
    data = {"md5": md5, "type": typ, "body": binary.Binary(body)}
    # 查找数据库是否有同样的图片
    ret = pymongo.MongoDB.images.insert_one(data)
    print("Insert Image")
    return response(0, "ok", {"id": str(ret.inserted_id)})


# 图片获取接口
@require_http_methods('GET')
def file(request):
    id = request.GET.get("id", "")

    img = pymongo.MongoDB.images.find_one({"_id": ObjectId(id)})
    if img is None:
        return response(100, "图片不存在")

    return HttpResponse(img['body'], img['type'])


@require_http_methods('POST')
def campAdd(request):
    if str(request.body, 'utf-8') == '':
        return response(1, 'parameter cannot be empty')

    param = json.loads(request.body)
    camp = {
        'user': '',
        'title': '',
        'stars': 0,
        'time': int(time.time()),
        'desc': '',
        'address': '',
        'comments': 0,
        'lat': 0,
        'lng': 0,
        'imgs': []
    }

    # titleName = '{}{}'.format(param['title'], time.time())
    # camp['id'] = hashlib.md5(titleName.encode("utf-8")).hexdigest()

    if 'title' not in param or param['title'] == '':
        return response(1, 'parameter `title` cannot be empty')
    if 'stars' not in param:
        return response(1, 'parameter `stars` cannot be empty')
    if 'desc' not in param:
        camp['desc'] = '暂无评论'
    if 'lat' not in param or 'lng' not in param:
        return response(1, 'parameter `lat` and `lng` must be none empty.')
    if 'imgs' not in param:
        return response(1, 'parameter `imgs` cannot be equal.')

    camp['title'] = param['title']
    camp['user'] = param['user']
    camp['stars'] = param['stars']
    camp['desc'] = param['desc']
    camp['lat'] = param['lat']
    camp['lng'] = param['lng']
    camp['imgs'] = param['imgs']
    camp['address'] = param['address']

    # camp_data.append(camp)
    pymongo.MongoDB.camps.insert_one(camp)
    return response(0, 'ok')