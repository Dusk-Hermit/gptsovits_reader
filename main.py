# https://googlechromelabs.github.io/chrome-for-testing/#stable
# selenium 4
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import re
import time
import base64
import shutil
import os
import threading
import sounddevice as sd
import soundfile as sf

import threading
import time
import inspect
import ctypes

# 一些全局变量
driver=None
RAW_TEXT_PATH='raw_text.txt'
PROCESSED_TEXT_PATH='processed_text.txt'
TMP_TEXT_PATH='tmp_text.txt'

SHOULD_STOP=False
SHADOW_ROOT=None
LAST_AUDIO_SRC=''
AUDIO_COUNT=0
PLAY_ID=0
WAV_PER_LINE=5
AUDIO_CACHE=20 # 双向的，所以实际缓存数量是这个的两倍
AUDIO_NAME_LEN=6
INFER_THREAD=None
PLAY_THREAD=None

# 权重文件同步搬运到项目位置
# WEIGHTS_BASE目录下是多个文件夹，每个文件夹里面有两个权重文件
GPTSOVITS_BASE=r'D:\repos\GPT-SoVITS-beta0306fix2'
WEIGHTS_BASE=r'E:\GPTsoVITs权重'
AUTO_CONTROL_FLAG='auto_'

def rename_cache_weight(dirname,weight_name):
    return f'{AUTO_CONTROL_FLAG}{dirname}_{weight_name}'

def sync_weight():
    print(f'同步权重文件，从 {WEIGHTS_BASE} 到 {GPTSOVITS_BASE}')
    
    weight_list=os.listdir(WEIGHTS_BASE)
    
    gpt_should_exist_list=[]
    sovits_should_exist_list=[]
    
    for weight in weight_list:
        all_files = []
        for root, dirs, files in os.walk(os.path.join(WEIGHTS_BASE,weight)):
            for file in files:
                all_files.append(os.path.join(root, file))

        gpt_weight_list=[i for i in all_files if i.endswith('.ckpt')]
        sovits_weight_list=[i for i in all_files if i.endswith('.pth')]
        
        gpt_should_exist_list.extend(
            [(i,os.path.join(GPTSOVITS_BASE,'GPT_weights',rename_cache_weight(weight,os.path.basename(i)))) for i in gpt_weight_list]
        )
        sovits_should_exist_list.extend(
            [(i,os.path.join(GPTSOVITS_BASE,'SoVITS_weights',rename_cache_weight(weight,os.path.basename(i)))) for i in sovits_weight_list]
        )
    
    gpt_already_exist_list=os.listdir(os.path.join(GPTSOVITS_BASE,'GPT_weights'))
    gpt_already_exist_list=[os.path.join(GPTSOVITS_BASE,'GPT_weights',i) for i in gpt_already_exist_list]
    sovits_already_exist_list=os.listdir(os.path.join(GPTSOVITS_BASE,'SoVITS_weights'))
    sovits_already_exist_list=[os.path.join(GPTSOVITS_BASE,'SoVITS_weights',i) for i in sovits_already_exist_list]
    
    # 格式化路径
    gpt_already_exist_list=[k.replace('\\','/') for k in gpt_already_exist_list]
    sovits_already_exist_list=[k.replace('\\','/') for k in sovits_already_exist_list]
    gpt_should_exist_list=[(i[0].replace('\\','/'),i[1].replace('\\','/')) for i in gpt_should_exist_list]
    sovits_should_exist_list=[(i[0].replace('\\','/'),i[1].replace('\\','/')) for i in sovits_should_exist_list]
    
    # 对于不是该方法自动管理的权重文件，不做处理
    gpt_already_exist_list=[i for i in gpt_already_exist_list if os.path.basename(i).startswith(AUTO_CONTROL_FLAG)]
    sovits_already_exist_list=[i for i in sovits_already_exist_list if os.path.basename(i).startswith(AUTO_CONTROL_FLAG)]
    
    # print(f'GPT权重文件：\n已存在：{gpt_already_exist_list}\n应存在：{gpt_should_exist_list}')
    # print(f'SoVITS权重文件：\n已存在：{sovits_already_exist_list}\n应存在：{sovits_should_exist_list}')
    
    
    # 删除多余的权重
    for i in gpt_already_exist_list:
        if i not in [j[1] for j in gpt_should_exist_list]:
            os.remove(i)
            print(f'删除多余权重文件 {i}')
    for i in sovits_already_exist_list:
        if i not in [j[1] for j in sovits_should_exist_list]:
            os.remove(i)
            print(f'删除多余权重文件 {i}')
    
    # 复制缺失的权重
    for i in gpt_should_exist_list:
        if i[1] not in gpt_already_exist_list:
            shutil.copy(i[0],i[1])
            print(f'复制权重文件 {i[0]} 到 {i[1]}')
    for i in sovits_should_exist_list:
        if i[1] not in sovits_already_exist_list:
            shutil.copy(i[0],i[1])
            print(f'复制权重文件 {i[0]} 到 {i[1]}')
            
    print('权重文件同步完成')
    print(f'权重文件数量：GPT-{len(gpt_should_exist_list)}，SoVITS-{len(sovits_should_exist_list)}')
    print(f'共有以下一些权重：\n{", ".join(weight_list)}')
    
 
def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
 
def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)
 

def clear_cache():
    if not os.path.exists('audio'):
        os.mkdir('audio')
    clear_folder('audio')

def clear_folder(folder_path):
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"The folder {folder_path} does not exist.")
        return

    # 遍历文件夹中的所有文件和文件夹
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            # 如果是文件，则删除文件
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            # 如果是文件夹，则删除文件夹及其所有内容
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")


def create_driver():
    global driver,SHADOW_ROOT
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    inference_url='http://localhost:9872/'
    driver.get(inference_url)
    # 等待元素加载完成
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'gradio-app'))
        )
        script = """
    var shadowRoot = document.querySelector('gradio-app').shadowRoot;
    return shadowRoot;
    """
        SHADOW_ROOT = driver.execute_script(script)
    except TimeoutError:
        print("元素未找到或加载超时")
        driver.quit()
        exit()

# 播放音频的线程
def audio_player():
    global PLAY_ID
    while True:
        if PLAY_ID<AUDIO_COUNT and not SHOULD_STOP:
            p_play(get_audio_path(PLAY_ID))
            delete_old_audio(PLAY_ID)
            PLAY_ID+=1
        
        if SHOULD_STOP and PLAY_ID==AUDIO_COUNT:
            p_play(get_audio_path(PLAY_ID))
            delete_old_audio(PLAY_ID)
            PLAY_ID+=1
            while True:
                if not SHOULD_STOP:
                    break
                time.sleep(1)
        time.sleep(1)

def audio_player_control():
    global PLAY_THREAD
    while True:
        if not SHOULD_STOP:
            PLAY_THREAD=threading.Thread(target=audio_player)
            PLAY_THREAD.daemon=True
            PLAY_THREAD.start()
            PLAY_THREAD.join()

def start_play_thread_control():
    play_thread_control=threading.Thread(target=audio_player_control)
    play_thread_control.daemon=True
    play_thread_control.start()

def get_audio_path(audio_id):
    return f'audio/audio{str(audio_id).zfill(AUDIO_NAME_LEN)}.wav'

def p_play(audio_path):
    data, samplerate = sf.read(audio_path)
    sd.play(data, samplerate)
    sd.wait() 

def delete_old_audio(audio_id):
    for i in range(audio_id-AUDIO_CACHE):
        audio_path=get_audio_path(i)
        if os.path.exists(audio_path):
            # print(f"delete {audio_path}")
            os.remove(audio_path)

def remove_whitespace(input_string):
    # 使用正则表达式匹配所有空白符，并将其替换为空字符串
    return re.sub(r'\s+', '', input_string)

splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }

def split(todo_text):
    todo_text = todo_text.replace("……", "。").replace("——", "，")
    if todo_text[-1] not in splits:
        todo_text += "。"
    i_split_head = i_split_tail = 0
    len_text = len(todo_text)
    todo_texts = []
    while 1:
        if i_split_head >= len_text:
            break  # 结尾一定有标点，所以直接跳出即可，最后一段在上次已加入
        if todo_text[i_split_head] in splits:
            i_split_head += 1
            todo_texts.append(todo_text[i_split_tail:i_split_head])
            i_split_tail = i_split_head
        else:
            i_split_head += 1
    return todo_texts


def cut2(inp):
    inp = inp.strip("\n")
    inps = split(inp)
    if len(inps) < 2:
        return inp
    opts = []
    summ = 0
    tmp_str = ""
    for i in range(len(inps)):
        summ += len(inps[i])
        tmp_str += inps[i]
        if summ > 50:
            summ = 0
            opts.append(tmp_str)
            tmp_str = ""
    if tmp_str != "":
        opts.append(tmp_str)
    # print(opts)
    if len(opts) > 1 and len(opts[-1]) < 50:  ##如果最后一个太短了，和前一个合一起
        opts[-2] = opts[-2] + opts[-1]
        opts = opts[:-1]
    return "\n".join(opts)


def cut_text(input_string):
    return cut2(input_string)
    # # 用selenium操作网页，得到处理结果
    
    # 需要合成的切分前文本
    # div_element = SHADOW_ROOT.find_element(By.ID, 'component-25')
    # textarea_element = div_element.find_element(By.TAG_NAME, 'textarea')
    # textarea_element.clear()
    # textarea_element.send_keys(input_string)
    
    # 凑50字一切
    # button_element = SHADOW_ROOT.find_element(By.ID, 'component-27')
    # button_element.click()
    
    # 切分后文本
    # div_element = SHADOW_ROOT.find_element(By.ID, 'component-31')
    # textarea_element = div_element.find_element(By.TAG_NAME, 'textarea')
    # time.sleep(3)
    # textarea_content = textarea_element.get_attribute('value')
    # return textarea_content

def process_raw():
    with open(RAW_TEXT_PATH,'r',encoding='utf-8') as f:
        raw_text=f.read()
    to_write=remove_whitespace(raw_text)
    to_write=cut_text(to_write)
    
    
    with open(PROCESSED_TEXT_PATH,'w',encoding='utf-8') as f:
        f.write(to_write)
    with open(TMP_TEXT_PATH,'w',encoding='utf-8') as f:
        f.write(to_write)
        
def p_wait_infer(output_element):
    for i in range(1000):
        if output_element.find_elements(By.TAG_NAME,'audio'):
            break
        time.sleep(1)
    
    if not LAST_AUDIO_SRC:
        return
    for i in range(1000):
        audio_element = output_element.find_elements(By.TAG_NAME,'audio')
        if audio_element:
            audio_src=audio_element[0].get_attribute('src')
            if audio_src!=LAST_AUDIO_SRC:
                break
        time.sleep(1)
    return
    
def p_download_audio(audio_element):
    global AUDIO_COUNT
    global LAST_AUDIO_SRC
    
    audio_src=audio_element[0].get_attribute('src')
    new_audio_path=get_audio_path(AUDIO_COUNT)
    
    if 'file' in audio_src:
        audio_path = audio_src.split('=')[1]
        shutil.copy(audio_path,new_audio_path)
    elif 'base64' in audio_src:
        audio_base64=audio_src.split(',')[1]
        with open(new_audio_path,'wb') as f:
            f.write(base64.b64decode(audio_base64))
    else:
        raise Exception('audio_src error')
    LAST_AUDIO_SRC=audio_src
    AUDIO_COUNT+=1
    return

        
def p_run():
    # 从tmp开始朗读，让一个线程执行。
    # 直到朗读完毕
    # 这个线程应该能够接收到stop信号
    # 这个线程不断循环一个循环体，每一次都重新读取tmp_text.txt的内容
    global SHOULD_STOP
    SHOULD_STOP=False
    
    while not SHOULD_STOP:
        # 不宜超前太多，生成音频太快
        if AUDIO_COUNT-PLAY_ID>AUDIO_CACHE:
            time.sleep(1)
            continue
        
        f=open(TMP_TEXT_PATH,'r',encoding='utf-8')
        
        to_process_list=[]
        for i in range(WAV_PER_LINE):
            line=f.readline()
            if not line:
                SHOULD_STOP=True
                break
            to_process_list.append(line)
        
        if  len(to_process_list):
            input_string='\n'.join([k.strip() for k in to_process_list])
            
            # 需要合成的文本
            div_element = SHADOW_ROOT.find_element(By.ID, 'component-22')
            textarea_element = div_element.find_element(By.TAG_NAME, 'textarea')
            textarea_element.clear()
            textarea_element.send_keys(input_string)
            
            # 合成语音
            button_element = SHADOW_ROOT.find_element(By.ID, 'component-31')
            button_element.click()
            
            # 输出的语音
            output_element = SHADOW_ROOT.find_element(By.ID, 'component-32')
            p_wait_infer(output_element)
            
            audio_element = output_element.find_elements(By.TAG_NAME,'audio')
            p_download_audio(audio_element)

        next_tmp_text=f.read()
        f.close()
        with open(TMP_TEXT_PATH,'w',encoding='utf-8') as f:
            f.write(next_tmp_text)
        
def p_stop():
    global SHOULD_STOP
    SHOULD_STOP=True
    try:
        stop_thread(PLAY_THREAD)
    except Exception as e:
        print(e)
    sd.stop()


if __name__ == "__main__":
    sync_weight()
    
    create_driver()
    clear_cache()
    start_play_thread_control()
    
    while True:
        i=input('选择模式：\n1. 从raw开始从头朗读\n2. 从tmp开始朗读\n3. 暂停\n4. 退出\n')
        if i=='1':
            process_raw()
            INFER_THREAD=threading.Thread(target=p_run)
            INFER_THREAD.daemon=True
            INFER_THREAD.start()
        elif i=='2':
            INFER_THREAD=threading.Thread(target=p_run)
            INFER_THREAD.daemon=True
            INFER_THREAD.start()
        elif i=='3':
            p_stop()
        elif i=='4':
            p_stop()
            driver.quit()
            break