from pymongo import MongoClient
from django.conf import settings

client = MongoClient(
    host=settings.DATABASES['MongoDB']['HOST'],
    port=int(settings.DATABASES['MongoDB']['PORT']),
)

MongoDB = client[settings.DATABASES['MongoDB']['NAME']]
MongoDB.command('ping')

print('connect mongodb success')