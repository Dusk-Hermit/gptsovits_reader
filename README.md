# GPT-SoVits webui 包装版

用了一个很蠢的方法（selenium），通过对原项目的webui访问，实现长文本的朗读功能

## 配置
可以用一个conda环境，安装`requirements.txt`
```
pip install requirements.txt
```

## 启动方法

- 先打开`GPT-SoVITS-beta`的`go-webui.bat`（一定要是这个版本的，因为是通过它的webui的元素id来操纵的）
- 然后在推理界面选好权重，开启TTS推理。（这会打开后端，于是我们的selenium会连上这个webui界面）
- `python main.py`启动一个selenium控制的chrome实例（不是chrome没测过）
  - 可以修改文件中的一些全局参数
- 然后选好一些推理参数，比如参考音频和参考音频的台词（必选），以及推理目标语言等一些选项
- 然后再`raw_text.txt`中放上你的小说原文，等想要朗读的文本
- 然后再对话框中输入1（如果在输入3暂停后，重新在这个位置启动，就用输入2），会把小说原文，用这个webui提供的功能进行处理，然后缓存为音频文件，并进行朗读


仅在windows平台测试过能用（主要是用到ctypes来删除线程的操作不知道会不会无法跨平台）




原仓库：https://github.com/RVC-Boss/GPT-SoVITS

个人使用的是20240207的gptsovits整合包