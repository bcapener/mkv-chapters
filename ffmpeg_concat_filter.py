import os
import subprocess
import time
import datetime

def get_media_info(path):
    output = subprocess.check_output(['mediainfo', path]).decode()

    ret = {}
    for section in output.split('\n\n'):
        tmp = section.splitlines()
        section_name = tmp[0].strip().lower()
        section_values = (v.split(':', 1) for v in tmp[1:])

        ret[section_name] = dict((sv[0].strip().lower(), sv[1].strip()) for sv in section_values if len(sv) == 2)
    return ret


def get_args(path):
    mi = get_media_info(path)

    # ecoding_settings = {}
    # for setting in mi['video']['encoding settings'].split(' / '):
    #     k, v = setting.split('=', 1)
    #     ecoding_settings[k] = v


    # print(ecoding_settings)
    # ffmpeg -i 13-Task\ #3\ -\ Carousel\ and\ details\ module.mp4 -refs 5 -r ntsc-film -vf scale=1280:720 -c:v libx264 -profile:v main -level:v 3.2 13-Task\ #3\ -\ Carousel\ and\ details\ module2.mp4
    width = mi['video']['width'].replace('pixels', '').replace(' ', '')
    height = mi['video']['height'].replace('pixels', '').replace(' ', '')
    fr_ = mi['video']['frame rate'].split()
    fr = fr_[1].strip('()')
    profile, level = mi['video']['format profile'].lower().split('@l')
    ref_frames = mi['video']['format settings, reference frames'].split()[0]
    lut = {
        'ref': '-refs',
        'cabac': '-coder',
        'keyint': '-g',
        'keyint_min': '-keyint_min',
        'scenecut': '-sc_threshold',
        'bframes': '-bf',
        'b_adapt': '-b_strategy',
        # 'b_bias': '-bframebias',
        # 'b_pyramid': 'flags2'
        'crf': '-crf',
        'vbv_maxrate': '-maxrate',
        # 'vbv_bufsize': '-bufsize',
        'qpmin': '-qmin',
        'qpmax': '-qmax',
        'qpstep': '-qdiff',
        'qcomp': '-qcomp',
        'trellis': '-trellis',
        'ip_ratio': '-i_qfactor',

    }
    vf_args = ['-vf', 'scale={}:{}'.format(width, height)]
    args = ['-profile:v', profile, '-level:v', level, '-refs', ref_frames]
    # for mi_name, ffmpeg_arg_name in lut.items():
    #     args += [ffmpeg_arg_name, ecoding_settings[mi_name]]
    return args  #  + vf_args

def ffmpeg_concat_filter(files, output):
    extra_args = get_args(files[0])
    total_files = len(files)
    file_args = []
    filter_args = ''
    for i, file in enumerate(files):
        file_args += ["-i",  f"{file}"]
        filter_args += f"[{i}:v:0][{i}:a:0]"

    filter_args += f"concat=n={total_files}:v=1:a=1[outv][outa]"
    args = ["ffmpeg"] + file_args + ["-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-level", "4.1", "-tvstd", "NTSC", "-crf", "14", "-c:a", "aac", "-b:a", "128k"] + ['-filter_complex', filter_args, "-map", "[outv]", "-map", "[outa]"] + [output]
    # args = f'ffmpeg {file_args} -filter_complex "{filter_args}" -map "[outv]" -map "[outa]" {output}'
    print(f"args: {args}")

    time.sleep(2)
    start_time = datetime.datetime.now()
    mp4_to_mkv_rc = subprocess.call(args)
    end_time = datetime.datetime.now()
    print(f"Total time: {end_time - start_time}")
    if mp4_to_mkv_rc:
        raise ValueError("FFMPEG Concat Filter Failed")

base_dir = "/home/brandon/Videos/mkv_chapters_tmp/O'Reilly - Beginning Scala Programming/"
path = os.path.join(base_dir, "mkv_tmp")
mp4s_file_names = sorted(os.listdir(path))
mp4s = [os.path.join(path, f) for f in mp4s_file_names]
print(mp4s)

ffmpeg_concat_filter(mp4s, os.path.join(base_dir, "concat_out.mkv"))
