from dataclasses import dataclass
from typing import Optional


# {
#     "_id": "5e589915419f0d5891d504e3",
#     "title": "写给大忙人看的操作系统",
#     "description": "如果你平时工作比较忙，但是还想专注于基础的话，建议看看这一篇，会带你有全新的认识。",
#     "authorId": {
#         "_id": "5ca2dd8afd80e72ce02ebd1c",
#         "customerName": "cxuan",
#         "customerTitle": "Java开发工程师",
#         "thumbImage": "https://images.gitbook.cn/5d4c5980-54fb-11e9-b7a7-d13cadd0a4c3"
#     },
#     "price": 0,
#     "tags": [
#         {
#             "_id": "5d8b88d068f48b27a7ee9b5e",
#             "tagname": "计算机网络"
#         }
#     ],
#     "activityType": 0,
#     "category": {
#         "_id": "5d8b7c3786194a1921979122",
#         "categoryName": "后端"
#     },
#     "totalReadersNum": 89
# }

@dataclass(frozen=True)
class Response:
    id: int
    title: str
    description: str
    author: str
    price: float
    tags: Optional[str]


class Demo:
    p = Post(id="str", owner="hehe", editor="hehe", text="133")
    p.id = "233"


if __name__ == '__main__':
    d = Demo
    d.id = 2
    print(d())
