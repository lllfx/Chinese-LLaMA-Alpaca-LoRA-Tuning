import json

instruct = "你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。"

entity_type_dict = {
    'LOC': "地名",
    'ORG': "机构名",
    'PER': "人名",
}


def deal_data(file_path, t_file_path):
    with open(t_file_path, 'w', encoding='utf-8') as fp:
        for line in open(file_path, 'r', encoding='utf-8').readlines():
            data = json.loads(line.strip())
            # {"instruct": "你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。", "query": "文本：登上蚩尤北寨，放眼南望，排列成阵的蚩尤三寨，自南而北一字排开，相距各约半里之遥，高低如浅丘，并列雄峙，隔壑相望，毗连相护；", "answer": "蚩尤北寨_地名\n蚩尤_地名"}
            answer = []
            for entity in data['entity_list']:
                answer.append('{}_{}'.format(entity['entity'], entity_type_dict[entity['entity_type']]))
            if len(answer) <= 0:
                answer.append("没有")
            res = {
                'instruct': instruct,
                'query': '文本：{}'.format(data['text']),
                'answer': '\n'.join(answer)
            }
            print(json.dumps(res, ensure_ascii=False), file=fp)


import os

if not os.path.exists('data/msra/instruct_data'):
    os.mkdir('data/msra/instruct_data')
deal_data('data/msra/ori_data/msra_1000.txt', 'data/msra/instruct_data/dev.txt')
deal_data('data/msra/ori_data/msra_train.txt', 'data/msra/instruct_data/train.txt')
