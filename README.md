# GPT-SoVits webui 包装版

用了一个很蠢的方法（selenium），通过对原项目的webui访问，实现长文本的朗读功能

## 配置
可以用一个conda环境，安装`requirements.txt`
```
pip install requirements.txt
```

## 启动方法

- 在`main.py`的`WEIGHTS_BASE`所指定的文件夹下，可以放一些以角色命名的文件夹，里面存放角色的权重文件
- 打开`GPT-SoVITS-beta`的`go-webui.bat`（一定要是这个版本的，因为是通过它的webui的元素id来操纵的）
- 然后在推理界面选好权重，开启TTS推理。（这会打开后端，于是我们的selenium会连上这个webui界面）
- `python main.py`启动一个selenium控制的chrome实例（不是chrome没测过）
  - 可以修改文件中的一些全局参数
- 然后选好一些推理参数，比如参考音频和参考音频的台词，以及推理目标语言等一些选项
- 然后再`raw_text.txt`中放上你的小说原文，等想要朗读的文本
- 然后再对话框中输入1（如果在输入3暂停后，重新在这个位置启动，就用输入2），会把小说原文，用这个webui提供的功能进行处理，然后缓存为音频文件，并进行朗读


仅在windows平台测试过能用（主要是用到ctypes来删除线程的操作不知道会不会无法跨平台）




原仓库：https://github.com/RVC-Boss/GPT-SoVITS

现在兼容的是`GPT-SoVITS-beta0306fix2`版本的整合包


可以在自己的某个文件夹`WEIGHTS_BASE`中（修改`main.py`的对应位置），按照角色文件夹，分别存储权重文件。`main.py`执行时会把这里的权重文件同步（也会同步删除情况）到gptsovits项目的两个权重文件夹下
比如你的`WEIGHTS_BASE`对应的文件夹下，是这样的结构
```
├─伊甸
│  │  infer_config.json
│  │  伊甸-e10.ckpt
│  │  伊甸_e100_s6500.pth
│  │
│  └─refer_audio
│      ├─emotion_8
│      │      啊，真抱歉，你已经等了很久了吗？.wav
│      │
│      └─emotion_9
│              所以，阿波尼亚女士究竟是一个怎样的人？对于这个问题，我或许无法给出一个有价值的回答。.wav
│
├─克拉拉
│  │  克拉拉-e10.ckpt
│  │  克拉拉_e15_s1050.pth
│  │  训练日志.log
│  │
│  └─参考音频
│      │  说话-娜塔莎姐姐说克拉拉也是医生呢，是机器伙伴的医生。.wav
│      │
│      ├─中立
│      │      【中立】——我们…可以在帕斯卡的核心中加一道「锁」。.wav
│      │      【中立】…咦？大家是有什么要紧的事要找史瓦罗先生吗？克拉拉可以帮你们带话…….wav
│      │      【中立】…嗯，克拉拉修过很多东西，但还是第一次碰到这么复杂的装置。.wav
```