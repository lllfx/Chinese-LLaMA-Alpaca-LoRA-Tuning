# Chinese-LLaMA-Alpaca-LoRA-Tuning
使用LoRA对Chinese-LLaMA-Alpaca进行微调。整体的结构非常简单，构造好相应格式的数据后就可以开始训练。

Facebook官方发布的[LLaMA模型禁止商用](https://github.com/facebookresearch/llama)，并且官方没有正式开源模型权重（虽然网上已经有很多第三方的下载地址）。为了遵循相应的许可，目前暂时无法发布完整的模型权重，敬请各位理解（目前国外也是一样）。自行搜索下载地址。

训练好的实体识别LoRA权重已经位于checkpoint下。

# 依赖

linux操作系统为Ubantu，GPU为A40-48G显存。

```python
mpi4py
transformers==4.28.1
peft==0.3.0
icetk
deepspeed==0.9.2
accelerate
cpm_kernels
sentencepiece==0.1.99
peft=0.3.0
torch=2.0.0 
```

# 说明

## 目录结构

```python
--checkpoint：保存模型
----msra：数据集名称
--------model_adapter
------------train_deepspeed
----------------adapter_model
--------------------adapter_config.json
--------------------adapter_model.bin
--------------------train_args.json
------------train_trainer
----------------adapter_model
--------------------adapter_config.json
--------------------adapter_model.bin
--------------------train_args.json
--model_hub：预训练模型
----7B：英文LLaMA原始权重
----7B-hf：英文权重转换为hugging face格式权重
----chinese-llama-plus-lora-7b：中文llama-7b的lora权重
----chinese-alpaca-plus-lora-7b：中文alpaca-7b的lora权重
----chinese-alpaca-7b：合并lora后的最终的模型
----tokenizer.model：7B文件
----convert_llama_weights_to_hf.py
----merge_llama_with_chinese_lora.py
--data：数据
----msra：数据集名称
--------instruct_data：指令数据
------------dev.txt
------------train.txt
--------ori_data：原始数据
--chat_ner.py：闲聊
--train_deepspeed.py：使用原生deepspeed训练
--train_trainer.py： 使用transformers的Trainer进行训练
--test.py：测试训练好的模型
--predict.py：预测
--process.py：处理数据为instruct_data
--dataset.py：加载数据为相应的格式
--deepspeed.json：deepspeed配置文件，用于trasnformers的Trainer
--config_utils.py：用于用字典定义配置，并接收命令行参数
```

## 转换得到中文alpaca

- 1、下载好7B、[llama-lora](https://huggingface.co/ziqingyang/chinese-llama-plus-lora-7b)、[alpaca-lora](https://huggingface.co/ziqingyang/chinese-alpaca-plus-lora-7b)到model_hub下。进入到model_hub目录下。
- 2、将llama转换为hugging face支持的格式：`python convert_llama_weights_to_hf.py --input_dir ./ --model_size 7B --output_dir ./7B-hf`。如果报错：`If this call came from a _pb2.py file, your generated code is out of date and must be regenerated with protoc >= 3.19.0`则可以`pip install --upgrade protobuf==3.20.1`，然后：`python convert_llama_weights_to_hf.py --input_dir ./ --model_size tokenizer_only --output_dir ./7B-hf`。最终我们可以得到7B-hf。
- 3、合并lora到llama上：`python merge_llama_with_chinese_lora.py --base_model "./7B-hf" --lora_model "./chinese-llama-plus-lora-7b,chinese-alpaca-plus-lora-7b" --output_type "huggingface" --output_dir "./chinese-alpaca-7b" `。最终我们可以得到chinese-alpaca-7b。
- 4、回到主目录，进行闲聊验证是否得到正确的模型：`python chat_ner.py --base_model "./model_hub/chinese-alpaca-7b" --tokenizer_path "./model_hub/chinese-alpaca-7b" --with_prompt --interactive`

## 数据格式

这里我们以命名实体识别任务为例，数据在data/msra下，其中ori_data为原始数据,instruct_data为处理后的数据，数据格式为一条一个样本，具体是：

```python
{"instruct": "你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。", "query": "文本：因有关日寇在京掠夺文物详情，藏界较为重视，也是我们收藏北京史料中的要件之一。", "answer": "日_地名\n京_地名\n北京_地名"}
```

可以按照自己的任务自行构建。

## 一般过程

1、data下新建数据集，用process.py处理数据为instruct_data下的数据。

2、这里使用train_trainer.py进行训练，为了能够让transformers的Trainer在训练的过程中保存lora权重，对Trainer进行相应的修改，参考：https://github.com/huggingface/peft/issues/96 。因为有了config_utils.py，我们可以在字典里面定义相关参数，然后可以在命令行修改参数的值（嵌套参数之间用_分隔）。

```python
args = {
    "data_name": "msra",  # 数据集名称
    "model_dir": "/root/autodl-tmp/chatglm-6b/",  # chatglm-6b地址，修改为自己的路径
    "lora_r": 8,  # lora参数
    "max_seq_length": 128+64,  # 句子最大长度
    "instruct_column": "instruct",  # instruct列名
    "query_column": "query",  # query列名
    "response_column": "answer",  # answer列名
    "train_path": "data/msra/instruct_data/train.txt", # 训练数据，修改为自己数据
    "dev_path": "data/msra/instruct_data/dev.txt",  # 测试数据，修改为自己数据
    "train_batch_size": 12,  # 训练batch_size
    "gradient_accumulation_steps": 1,  # 默认就好
    "save_dir": "。/checkpoint/msra/train_trainer/",  # 保存模型位置，修改为自己的路径
    "num_train_epochs": 1,  # 训练epoch
    "local_rank": -1,  # deepspeed所需，默认就好
    "log_steps": 10,  # 多少步打印一次结果
    "save_steps": 50,  # 多少步保存一次模型
    "deepspeed_json_path": "deepspeed.json" # deepspeed配置
}
```

需要注意的是，Trainer中使用deepspeed要保持deepspeed定义的参数和Trainer里面参数保持一致，比如：deepspeed.json：

```python
{
  "train_micro_batch_size_per_gpu": 12,
  "optimizer": {
    "type": "Adam",
    "params": {
      "lr": 1e-05,
      "betas": [
        0.9,
        0.95
      ],
      "eps": 1e-08,
      "weight_decay": 0.0005
    }
  },
  "fp16": {
    "enabled": true
  },
  "zero_optimization": {
    "stage": 1,
    "offload_optimizer": {
      "device": "cpu",
      "pin_memory": true
    },
    "allgather_partitions": true,
    "allgather_bucket_size": 200000000.0,
    "overlap_comm": true,
    "reduce_scatter": true,
    "reduce_bucket_size": 200000000.0,
    "contiguous_gradients": true
  }
}
```

- train_micro_batch_size_per_gpu和per_device_train_batch_size
- lr和learning_rate
- betas里面和adam_beta1、adam_beta2
- weight_decay和weight_decay
- fp16和fp16

默认的话不用修改这些。

## 训练

```python
deeepspeed train_deepspeed.py 或者 deepspeed train_trainer.py
```

## 测试

修改data_name，运行：`python test.py`

```python
预测： ['开来_人名\n北京开来律师事务所_机构名\n', '越秀_机构名\n', '中国共产党_机构名\n周恩来_人名\n邓颖超_人名\n新华日报_机构名\n', '朝润州_地名\n杨次公政人名\n', '智凤_人名\n', '十五大_机构名\n', '中国中医研究院针灸研究所门诊部白癜风专科_机构名\n刘维林_人名\n', '长安_地名\n', '东方艺术》杂志_机构名\n越秀_地名\n', '袁崇焕_人名\n', '共产党_机构名\n', '北京_地名\n中国_地名\n沪沪线_地名\n', '中国_地名\n', '孙_机构名\n孙毅_人名\n晋察冀_根据地_地名\n', '梁_人名\n', '佛湾_地名\n', '中国_地名\n', '苏伟_人名\n', '中国_地名\n', '蚩尤_人名\n涿鹿_地名\n']

真实： ['开来_人名\n北京开来律师事务所_机构名', '越秀_机构名', '中国共产党_机构名\n周恩来_人名\n邓颖超_人名\n新华日报_机构名', '知润州_人名\n杨次公_人名', '赵智凤_人名', '十五大_机构名', '中国中医研究院针灸研究所门诊部白癜风专科_机构名\n刘维林_人名', '长安_地名', '《东方艺术》杂志_机构名\n越秀_机构名', '袁崇焕_人名', '共产党_机构名', '北京_地名\n中国_地名\n京沪线_地名', '中国_地名', '红军_机构名\n孙毅_人名\n晋察冀抗日根据地_地名', '梁_人名', '佛湾_地名', '中国_地名', '苏伟_人名', '中国_地名', '蚩尤_人名\n涿鹿_地名']
```

## 预测

修改data_name，运行：`python predict.py`

```python
====================================================================================================
文本 >>>  "你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。文本：我们是受到郑振铎先生、阿英先生著作的启示，从个人条件出发，瞄准现代出版史研究的空白，重点集藏解放区、国民党毁禁出版物。"
预测 >>>  郑振铎_人名
阿英_人名
解放_机构名

真实 >>>  郑振铎_人名
阿英_人名
国民党_机构名
文本 >>>  "你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。文本：去年，我们又被评为“北京市首届家庭藏书状元明星户”。"
预测 >>>  北京市_地名

真实 >>>  北京市_地名
文本 >>>  "你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。文本：藏书家、作家姜德明先生在1997年出版的书话专集《文林枝叶》中以“爱书的朋友”为题，详细介绍了我们夫妇的藏品及三口之家以书为友、好乐清贫的逸闻趣事。"
预测 >>>  姜德明_人名

真实 >>>  姜德明_人名
```

## 闲聊

修改data_name，运行：`python chat_ner.py --base_model "./model_hub/chinese-alpaca-7b" --tokenizer_path "./model_hub/chinese-alpaca-7b" --lora_model "./checkpoint/msra/train_trainer/adapter_model" --with_prompt --interactive`

````python
+ 该模式下仅支持单轮问答，无多轮对话能力。
+ 如要进行多轮对话，请使用llama.cpp或llamachat工具。
-------------------------------------------------------------------------------------
+ This mode only supports single-turn QA.
+ If you want to experience multi-turn dialogue, please use llama.cpp or llamachat.
=====================================================================================
Input:你好  
Response:  Hello!


Input:你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。文本：我们是受到郑振铎先生、阿英先生著作的启示，从个人条件出发，瞄准现代出版史研究的空白，重点集藏解放区、国民党毁禁出版物。
Response:  郑振铎_人名
阿英_人名


Input:你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。文本：去年，我们又被评为“北京市首届家庭藏书状元明星户”。
Response:  北京市_地名


Input:你现在是一个实体识别模型，你需要提取文本里面的人名、地名、机构名，如果存在结果，返回'实体_实体类型'，不同实体间用\n分隔。如果没有结果，回答'没有'。文本：藏书家、作家姜德明先生在1997年出版的书话专集《文林枝叶》中以“爱书的朋友”为题，详细介绍了我们夫妇的藏品及三口之家以书为友、好乐清贫的逸闻趣事。
Response:  姜德明_人名
````

原始模型也并没有退化。

## 报错解决

- 安装mpi4py报错

```python
sudo apt-get update
sudo apt-get install openmpi-bin libopenmpi-dev
pip install mpi4py
```

# 补充

- **怎么训练自己的数据？**
	按照instruct_data下的数据结构构造数据，定义好相关参数运行即可。
- **怎么进行预测？**
	在test.py中，预测时可根据自己的任务进行解码。
- **为什么不进行评价指标的计算？**
	只是作了初步的训练，难免效果不太好就不进行评价指标的计算了，可以在test.py里面自行定义。

# 参考

> [liucongg/ChatGLM-Finetuning: 基于ChatGLM-6B模型，进行下游具体任务微调，涉及Freeze、Lora、P-tuning等 (github.com)](https://github.com/liucongg/ChatGLM-Finetuning)
>
> [THUDM/ChatGLM-6B: ChatGLM-6B: An Open Bilingual Dialogue Language Model | 开源双语对话语言模型 (github.com)](https://github.com/THUDM/ChatGLM-6B/projects?query=is%3Aopen)
>
> [huggingface/peft: 🤗 PEFT: State-of-the-art Parameter-Efficient Fine-Tuning. (github.com)](https://github.com/huggingface/peft)
>
> [ymcui/Chinese-LLaMA-Alpaca: 中文LLaMA&Alpaca大语言模型+本地CPU/GPU部署 (Chinese LLaMA & Alpaca LLMs) (github.com)](https://github.com/ymcui/Chinese-LLaMA-Alpaca)
