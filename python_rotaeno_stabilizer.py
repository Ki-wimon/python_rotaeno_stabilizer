import cv2
import numpy as np
from tqdm import tqdm
import glob
import os
import subprocess
import time


def add_audio_to_video(video_file, audio_source, output_file):
    command = [
        'ffmpeg',
        '-i', video_file,  # 输入的视频文件
        '-i', audio_source,  # 输入的音频来源文件
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        output_file  # 输出的文件名
    ]
    subprocess.call(command)


def find_mp4_videos():
    '''
    寻找videos目录下的全部mp4文件
    :return: 视频列表
    '''
    dir = os.path.join(os.getcwd(), 'videos')  # 指向videos目录
    videos = []
    for file_path in glob.glob(os.path.join(dir, '*.mp4')):
        if os.path.isfile(file_path):
            relative_path = os.path.relpath(file_path, dir)
            videos.append(relative_path)
    return videos


def convert_vfr_to_cfr(input_path, output_path, target_framerate=59.97):
    """
    VFR转CFR

    :param input_path: 视频路径.
    :param output_path: 输出路径.
    :param target_framerate: 目标帧率，默认59.97fps.
    :return: None
    """

    cmd = [
        'ffmpeg',
        '-i', input_path,
        '-vf', f'fps={target_framerate}',
        '-c:a', 'copy',  # Copy audio stream without re-encoding
        output_path
    ]

    subprocess.run(cmd)


def get_video_duration(video_path):
    '''

    :param video_path: 视频路径
    :return: 时长
    '''
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)


def compute_rotation(left_color, right_color, center_color, sample_color):
    '''
    根据画面四个角的颜色来计算画面旋转角度
    :param left_color:
    :param right_color:
    :param center_color:
    :param sample_color:
    :return: 旋转角度
    '''
    OffsetDegree = 180.0

    centerDist = np.linalg.norm(np.array(center_color) - np.array(sample_color))
    leftLength = np.linalg.norm(np.array(left_color) - np.array(center_color))
    leftDist = np.linalg.norm(np.array(left_color) - np.array(sample_color))
    rightDist = np.linalg.norm(np.array(right_color) - np.array(sample_color))

    dir = -1 if leftDist < rightDist else 1
    if leftLength == 0:
        angle = OffsetDegree  # 或其他合适的默认值
    else:
        angle = (centerDist - leftLength) / leftLength * 180.0 * dir + OffsetDegree

    # 注意，如果旋转方向是相反的，只需返回-angle即可
    return -angle

def compute_rotation_v2(top_left_color, top_right_color, bottom_left_color, bottom_right_color):
    '''
    根据画面四个角的颜色来计算画面旋转角度
    :param top_left_color: 左上角的颜色 (RGB)
    :param top_right_color: 右上角的颜色 (RGB)
    :param bottom_left_color: 左下角的颜色 (RGB)
    :param bottom_right_color: 右下角的颜色 (RGB)
    :return: 旋转角度
    '''
    # 将RGB值转换为0或1
    def convert_color_to_binary(color):
        array = [1 if c >= 255/2 else 0 for c in color]
        return array[::-1]

    # 将四个角的颜色转换为二进制
    binary_top_left = convert_color_to_binary(top_left_color)
    binary_top_right = convert_color_to_binary(top_right_color)
    binary_bottom_left = convert_color_to_binary(bottom_left_color)
    binary_bottom_right = convert_color_to_binary(bottom_right_color)
    # print("binary_top_left:", binary_top_left)
    # print("binary_top_right:", binary_top_right)
    # print("binary_bottom_left:", binary_bottom_left)
    # print("binary_bottom_right:", binary_bottom_right)

    # 将二进制颜色值转换为角度
    color_to_degree = (binary_top_left[0] * 2048 + binary_top_left[1] * 1024 + binary_top_left[2] * 512 +
                      binary_top_right[0] * 256 + binary_top_right[1] * 128 + binary_top_right[2] * 64 +
                      binary_bottom_left[0] * 32 + binary_bottom_left[1] * 16 + binary_bottom_left[2] * 8 +
                      binary_bottom_right[0] * 4 + binary_bottom_right[1] * 2 + binary_bottom_right[2])
    rotation_degree = color_to_degree / 4096 * -360

    return -rotation_degree


def render(video,type="v2"):
    '''

    :param video: 视频文件名
    :param type: 视频类型，填v1/v2，默认为v2
    :return: 无返回值，在output文件夹输出渲染完毕的视频
    '''
    video_dir = os.path.join(os.getcwd(), 'videos', video)
    video_file_name = os.path.basename(video)  # 获取不带路径的文件名
    video_name = os.path.splitext(video_file_name)[0]

    cap = cv2.VideoCapture(video_dir)
    # fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
    fps = cap.get(cv2.CAP_PROP_FPS)
    print("fps:", fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    output_path = os.path.join(os.getcwd(), 'output', f'{video_name}_stb.mp4')  # 指定输出路径
    cfr_output_path = os.path.join(os.getcwd(), 'videos', f'{video_name}_cfr.mp4')  # 指定输出路径

    print("正在将视频转换为CFR视频……")
    convert_vfr_to_cfr(video_dir, cfr_output_path, fps)
    cap2 = cv2.VideoCapture(cfr_output_path)

    out = cv2.VideoWriter(output_path, fourcc, fps, (int(cap.get(3)), int(cap.get(4))))

    frame_count = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))

    # 使用tqdm展示进度
    for _ in tqdm(range(frame_count), desc="Processing video"):
        ret, frame = cap2.read()
        if ret:
            height, width, channels = frame.shape

            # Sample colors
            O = 5
            S = 3
            bottom_left = frame[height - O:height - O + S, O:O + S].mean(axis=(0, 1))
            top_left = frame[O:O + S, O:O + S].mean(axis=(0, 1))
            bottom_right = frame[height - O:height - O + S, width - O:width - O + S].mean(axis=(0, 1))
            top_right = frame[O:O + S, width - O:width - O + S].mean(axis=(0, 1))

            if type == 'v2':
                angle = compute_rotation_v2(top_left, top_right, bottom_left, bottom_right)
            else:
                angle = compute_rotation(top_left, bottom_right, top_right, bottom_left)
            # print(angle)
            # Rotate frame
            M = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
            rotated_frame = cv2.warpAffine(frame, M, (width, height))

            out.write(rotated_frame)
            # time.sleep(1 / fps)
        else:
            print("Error reading frame")

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # 用这个方法添加音频，但是目前视频时长不匹配，会导致音画不同步(需要安装ffmpeg)
    add_audio_to_video(output_path, video_dir, f'output/{video_name}_with_audio.mp4')

def render_square(video,type="v2", square=True): # 渲染方形视频
    '''

    :param video: 视频文件名
    :param type: 视频类型，填v1/v2，默认为v2
    :return: 无返回值，在output文件夹输出渲染完毕的视频
    '''
    if os.path.isabs(video):
        video_dir = video
    else:
        video_dir = os.path.join(os.getcwd(), 'videos', video)

    video_file_name = os.path.basename(video)  # 获取不带路径的文件名
    video_name = os.path.splitext(video_file_name)[0]
    if square:
        video_name = video_name + '_square'

    cap = cv2.VideoCapture(video_dir)
    # fps = round(cap.get(cv2.CAP_PROP_FPS), 2)
    fps = cap.get(cv2.CAP_PROP_FPS)
    print("fps:", fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    output_path = os.path.join(os.getcwd(), 'output', f'{video_name}_stb.mp4')  # 指定输出路径
    cfr_output_path = os.path.join(os.getcwd(), 'videos', f'{video_name}_cfr.mp4')  # 指定输出路径

    print("正在将视频转换为CFR视频……")
    convert_vfr_to_cfr(video_dir, cfr_output_path, fps)
    cap2 = cv2.VideoCapture(cfr_output_path)

    if square: # 方形
        out = cv2.VideoWriter(output_path, fourcc, fps, (max(int(cap.get(3)), int(cap.get(4))), max(int(cap.get(3)), int(cap.get(4)))))
    else:
        out = cv2.VideoWriter(output_path, fourcc, fps, (int(cap.get(3)), int(cap.get(4))))

    frame_count = int(cap2.get(cv2.CAP_PROP_FRAME_COUNT))

    # 使用tqdm展示进度
    for _ in tqdm(range(frame_count), desc="Processing video"):
        ret, frame = cap2.read()
        if ret:
            height, width, channels = frame.shape

            # Sample colors
            O = 5
            S = 3
            bottom_left = frame[height - O:height - O + S, O:O + S].mean(axis=(0, 1))
            top_left = frame[O:O + S, O:O + S].mean(axis=(0, 1))
            bottom_right = frame[height - O:height - O + S, width - O:width - O + S].mean(axis=(0, 1))
            top_right = frame[O:O + S, width - O:width - O + S].mean(axis=(0, 1))

            if type == 'v2':
                angle = compute_rotation_v2(top_left, top_right, bottom_left, bottom_right)
            else:
                angle = compute_rotation(top_left, bottom_right, top_right, bottom_left)
            # print(angle)
            # Rotate frame
            if square: # 方形渲染
                max_size = max(height, width)
                expanded_frame = np.zeros((max_size, max_size, 3), dtype='uint8')
                expanded_frame[(max_size - height)//2:(max_size - height)//2 + height, (max_size - width)//2:(max_size - width)//2 + width] = frame
                M = cv2.getRotationMatrix2D((max_size / 2, max_size / 2), angle, 1)
                rotated_frame = cv2.warpAffine(expanded_frame, M, (max_size, max_size))
            else:
                M = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
                rotated_frame = cv2.warpAffine(frame, M, (width, height))

            out.write(rotated_frame)
            # time.sleep(1 / fps)
        else:
            print("Error reading frame")

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    # 用这个方法添加音频，但是目前视频时长不匹配，会导致音画不同步(需要安装ffmpeg)
    add_audio_to_video(output_path, video_dir, f'output/{video_name}_with_audio.mp4')
