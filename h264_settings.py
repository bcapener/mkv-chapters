import os
import subprocess


def get_media_info(path):
    output = subprocess.check_output(['mediainfo', path]).decode()

    ret = {}
    for section in output.split('\n\n'):
        tmp = section.splitlines()
        section_name = tmp[0].strip().lower()
        section_values = (v.split(':', 1) for v in tmp[1:])

        ret[section_name] = dict((sv[0].strip().lower(), sv[1].strip()) for sv in section_values if len(sv) == 2)
    return ret


def get_args():
    mi = get_media_info('/home/brandon/Videos/mkv_chapters_tmp/Lynda - Organizing JavaScript Functionality/02-Modules.mp4')

    ecoding_settings = {}
    for setting in mi['video']['encoding settings'].split(' / '):
        k, v = setting.split('=', 1)
        ecoding_settings[k] = v


    print(ecoding_settings)
    # ffmpeg -i 13-Task\ #3\ -\ Carousel\ and\ details\ module.mp4 -refs 5 -r ntsc-film -vf scale=1280:720 -c:v libx264 -profile:v main -level:v 3.2 13-Task\ #3\ -\ Carousel\ and\ details\ module2.mp4
    width = mi['video']['width'].replace('pixels', '').replace(' ', '')
    height = mi['video']['height'].replace('pixels', '').replace(' ', '')
    fr_ = mi['video']['frame rate'].split()
    fr = fr_[1].strip('()')
    profile, level = mi['video']['format profile'].lower().split('@l')
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
    args = ['-r', fr, '-profile:v', profile, '-level:v', level]
    for mi_name, ffmpeg_arg_name in lut.items():
        args += [ffmpeg_arg_name, ecoding_settings[mi_name]]
    return args + vf_args

f = '/home/brandon/Videos/mkv_chapters_tmp/Lynda - Organizing JavaScript Functionality/01-Nested scopes.mp4.orig'
# f = '/home/brandon/Videos/mkv_chapters_tmp/Lynda - Organizing JavaScript Functionality/13-Task #3 - Carousel and details module.mp4.orig'
fargs = get_args()
rc = subprocess.call(['ffmpeg', '-i', f] + fargs + [f[:-4]+'2.mp4'])
print(rc)
