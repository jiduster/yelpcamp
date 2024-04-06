import redis
import json
from django.conf import settings

if settings.DATABASES['Redis']['OPEN']:
    conn_pool = redis.ConnectionPool(
        host=settings.DATABASES['Redis']['HOST'],
        port=int(settings.DATABASES['Redis']['PORT']),
        decode_responses=True,
    )
    RedisCache = redis.Redis(connection_pool=conn_pool, decode_responses=True)
    RedisCache.ping()
    print("connect redis success")


# 定义一个KEY
def CampDetailKey(id):
    return "camp_detail_%s" % id


# 将数据存入redis
def SetCampDetail(id, detail):
    if settings.DATABASES['Redis']['OPEN']:
        key = CampDetailKey(id)
        value = json.dumps(detail, ensure_ascii=False)
        RedisCache.set(key, value, ex=3600)


# 获取数据内容
def GetCampDetail(id):
    if settings.DATABASES['Redis']['OPEN']:
        key = CampDetailKey(id)
        detail = RedisCache.get(key)
        if detail is not None:
            return json.loads(detail)
    return None


# 删除缓存数据
def DelCampDetail(id):
    key = CampDetailKey(id)
    RedisCache.delete(key)
