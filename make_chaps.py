import os
import time
import sys, tempfile, os
import argparse
import shutil
import datetime
import subprocess
import enzyme
from pymediainfo import MediaInfo
from collections import OrderedDict
from xml.etree.ElementTree import Element, SubElement, Comment, tostring, ElementTree
from pathlib import Path
from typing import Generator, List

DEBUG = False

srt_names = {}

class VideoFile:
    def __init__(self, video_path) -> None:
        self.orig_path: Path = video_path
        self.__srt_paths: List[Path] = []
    
    def add_subtitle(self, file_path):
        self.__srt_paths.append(file_path)
    
    def get_subtitles(self):
        return self.__srt_paths

class MkvVideoFile(VideoFile):
    def __init__(self, video_path) -> None:
        super().__init__(video_path)

    @property
    def duration_sec(self): 
        with open(self.orig_path, 'rb') as f:
            mkv = enzyme.MKV(f)
            return mkv.info.duration.total_seconds()

    @property
    def duration_sec_mediainfo(self): 
        return MediaInfo.parse(self.orig_path).tracks[0].duration / 1000

def format_time(sec):
    hours, remainder = divmod(sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{int(hours):02}:{int(minutes):02}:' + f'{seconds:.3f}'.zfill(6)


def create_mkv_chapters(entries, file_path, allow_nested=False):
    def add_entry(node, st, et, name):
        header_chapter = SubElement(node, 'ChapterAtom')
        start_time = SubElement(header_chapter, 'ChapterTimeStart')
        start_time.text = format_time(st)
        end_time = SubElement(header_chapter, 'ChapterTimeEnd')
        end_time.text = format_time(et)
        chapter_display = SubElement(header_chapter, 'ChapterDisplay')
        chapter_string = SubElement(chapter_display, 'ChapterString')
        chapter_string.text = name
        chapter_lang = SubElement(chapter_display, 'ChapterLanguage')
        chapter_lang.text = 'eng'
        return header_chapter

    chapters = Element('Chapters')
    edition_entry = SubElement(chapters, 'EditionEntry')
    for headers, (stime_tot, etime_tot, subentries) in entries.items():

        if not headers:
            header_chapter = edition_entry
        else:
            # header_chapter = add_entry(edition_entry, stime_tot, etime_tot, headers)
            header_chapter = add_entry(edition_entry, subentries[0][0], subentries[0][1], headers)

        for (stime, etime, subentry) in subentries:
            add_entry((header_chapter if allow_nested else edition_entry), stime, etime, subentry)
            # add_entry(edition_entry, stime, etime, subentry)
            # header_chapter = SubElement(edition_entry, 'ChapterAtom')
            # start_time = SubElement(header_chapter, 'ChapterTimeStart')
            # start_time.text = format_time(stime_tot)
            # end_time = SubElement(header_chapter, 'ChapterTimeEnd')
            # end_time.text = format_time(etime_tot)
            # chapter_display = SubElement(header_chapter, 'ChapterDisplay')
            # chapter_string = SubElement(chapter_display, 'ChapterString')
            # chapter_string.text = headers
            # chapter_lang = SubElement(chapter_display, 'ChapterLanguage')
            # chapter_lang.text = 'eng'

        # for (stime, etime, subentry) in subentries:
        #     if allow_nested:
        #         # header_chapter_ = SubElement(header_chapter, 'ChapterAtom')
        #         header_chapter = add_entry(header_chapter, stime, etime, subentry)
        #     else:
        #         # header_chapter_ = SubElement(edition_entry, 'ChapterAtom')
        #         header_chapter = add_entry(edition_entry, stime, etime, subentry)
            # start_time_ = SubElement(header_chapter_, 'ChapterTimeStart')
            # start_time_.text = format_time(stime)
            # end_time_ = SubElement(header_chapter_, 'ChapterTimeEnd')
            # end_time_.text = format_time(etime)
            # chapter_display_ = SubElement(header_chapter_, 'ChapterDisplay')
            # chapter_string_ = SubElement(chapter_display_, 'ChapterString')
            # chapter_string_.text = subentry
            # chapter_lang_ = SubElement(chapter_display_, 'ChapterLanguage')
            # chapter_lang_.text = 'eng'
    # print(tostring(chapters, encoding='ISO-8859-1').decode('ISO-8859-1'))
    # main_folder = os.path.join('/home', 'brandon', 'Downloads', 'Lynda - Advanced Linux_ The Linux Kernel')  # os.path.join()
    # with open(os.path.join(main_folder, 'test.xml'), 'wb') as f:
    with open(file_path, 'wb') as f:
        f.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n<!DOCTYPE Chapters SYSTEM "matroskachapters.dtd">'.encode('ISO-8859-1'))
        ElementTree(chapters).write(f, encoding='ISO-8859-1', xml_declaration=False)
    # ElementTree(chapters).write(os.path.join(main_folder, 'test.xml'))
    return chapters


# def ffmpeg_concat_filter(files, output):
#     total_files = len(files)
#     file_args = []
#     filter_args = ''
#     for i, file in enumerate(files):
#         file_args += ["-i",  f"{file}"]
#         filter_args += f"[{i}:v:0][{i}:a:0]"
#
#     filter_args += f"concat=n={total_files}:v=1:a=1[outv][outa]"
#     args = ["ffmpeg"] + file_args + ['-filter_complex', filter_args, "-map", '"[outv]"', '"[outa]"', output]
#     # args = f'ffmpeg {file_args} -filter_complex "{filter_args}" -map "[outv]" -map "[outa]" {output}'
#     mp4_to_mkv_rc = subprocess.call(args)
#     if mp4_to_mkv_rc:
#         raise ValueError("FFMPEG Concat Filter Failed")

def ffmpeg_concat_filter(files, output):
    # extra_args = get_args(files[0])
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


def get_video_files(path: Path, temp_path: Path, skip_dirs=()) -> Generator[VideoFile, None, None]:
    path = path.expanduser()
    for root, _, files in os.walk(path):
        root = Path(root)
        if root in skip_dirs:
            continue

        all_srts = sorted([Path(root, f) for f in files if f.endswith('.srt')])
        for file in (VideoFile(Path(root, f)) for f in files if f.endswith(".mp4")):
            for srt in all_srts:
                if srt.stem.startswith(file.orig_path.stem):
                    file.add_subtitle(srt)
            yield file

def convert_to_mkv(input_file: VideoFile, temp_path: Path):
    tmp_file = Path(temp_path, input_file.orig_path.stem + '.mkv')

    i = 1
    while tmp_file.is_file():
        tmp_file = Path(temp_path, input_file.orig_path.stem + f'_{i}.mkv')
        i += 1

    print('\nCONVERTING MP4s to MKVs\n')
    mp4_to_mkv_rc = subprocess.call(['ffmpeg', '-i', input_file.orig_path, '-vcodec', 'copy', '-acodec', 'copy', tmp_file])
    if mp4_to_mkv_rc:
        raise ValueError('Failed converting mp4 to mkv.')
    
    return MkvVideoFile(tmp_file)


def add_subtitles_to_mkv(input_file: MkvVideoFile, subtitles: List[Path]):
    global srt_names
    if not subtitles:
        return

    for srt_file in subtitles:
        if srt_file.suffix not in srt_names:
            ln = input(f'Give language name for "{srt_file.suffix}" (Default=English): ').strip()
            sn = input(f'Give language short name for "{srt_file.suffix}" (Default=eng): ').strip()
            lname = ln if ln else 'English'
            sname = sn if sn else 'eng'
            srt_names[srt_file.suffix] = (lname, sname)

    input_path = input_file.orig_path
    tmp_mkv = Path(input_path.parent, f"{input_path.stem}_tmp{input_path.suffix}")
    cmd = ['mkvmerge', '-o', tmp_mkv, input_file.orig_path]
    for srt_file in subtitles:
        lname, sname = srt_names[srt_file.suffix]
        cmd += ['--language', f'0:{sname}', '--track-name', f'0:{lname}', srt_file]

    print('\nADDING SRT FILES\n')
    add_srt_rc = subprocess.call(cmd)
    if add_srt_rc:
        raise ValueError("failed adding srt file")
    tmp_mkv.rename(input_path)

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--path', type=str, help='', required=True)
    args = parser.parse_args()

    main_folder = Path(args.path).absolute()
    main_folder_name = main_folder.name

    mkv_tmp = Path(main_folder, 'mkv_tmp')

    try:
        shutil.rmtree(mkv_tmp)
    except:
        pass
    mkv_tmp.mkdir()

    al = OrderedDict()
    all_files = OrderedDict()

    for video_file in get_video_files(main_folder, temp_path=mkv_tmp, skip_dirs=(mkv_tmp, )):
        fname = video_file.orig_path.parent.name
        if fname not in all_files:
            all_files[fname] = []
        tmp = []
        total_sec = 0
        total_sec2 = 0
        mkvfile = convert_to_mkv(video_file, mkv_tmp)
        add_subtitles_to_mkv(mkvfile, video_file.get_subtitles())
        sec = mkvfile.duration_sec
        total_sec += sec

        sec2 = mkvfile.duration_sec_mediainfo
        total_sec2 += sec2

        all_files[fname].append(mkvfile)

    EDITOR = os.environ.get('EDITOR', 'vim')

    al = OrderedDict()
    for k, v in OrderedDict(sorted(all_files.items())).items():
        al[k] = sorted(v, key=lambda x: x.orig_path.name)

    initial_message = f"TITLE {main_folder_name}\n" # if you want to set up the file somehow
    h, e = 0, 0
    ids = OrderedDict()
    for header, entries in al.items():
        initial_message += f'D{h:03} {header}\n'

        for i, entry in enumerate(entries):
            tt = entry.duration_sec
            tt2 = entry.duration_sec_mediainfo
            if i == 0:
                ids[f'D{h:03}'] = (header, tt, tt2)

            initial_message += f' F{e:03} {entry.orig_path.name[:-4]}\n'
            ids[f'F{e:03}'] = (entry.orig_path.name, tt, tt2)
            e += 1
        initial_message += '\n'
        h += 1
    if DEBUG:
        edited_message = initial_message.splitlines()
    else:
        with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
            tf.write(initial_message.encode())
            tf.flush()
            print('\nEDITING CHAPTER FILE\n')
            subprocess.call([EDITOR, tf.name])

            # do the parsing with `tf` using regular File operations.
            # for instance:
            tf.seek(0)
            edited_message = tf.readlines()
    new_ids = OrderedDict()
    entries = OrderedDict([('', (None, None, [])), ])
    file_order = []
    curr_header = ''
    hsec = 0
    esec = 0
    for msg in edited_message:
        if DEBUG:
            msg = msg.strip()
        else:
            msg = msg.decode().strip()
        if not msg or msg.startswith('#'):
            continue
        try:
            id_, nmsg = msg.split(' ', maxsplit=1)
        except ValueError:
            tmp = msg.split(' ', maxsplit=1)
            if len(tmp) == 1 and tmp[0].startswith('D'):
                continue
            else:
                raise
        if id_ == 'TITLE':
            pass
        else:
            fname, t, t2 = ids[id_]
            new_ids[id_] = (fname, nmsg, t, t2)
            if id_.startswith('D'):
                curr_header = nmsg
                entries[curr_header] = (hsec, hsec + t, [])
                hsec += t

            elif id_.startswith('F'):
                header_name = curr_header  # if nmsg.startswith(' ') else ''  # if file does not start with a space then it is not under a directory, so no header_name.
                file_order.append(fname)
                entries[header_name][2].append((esec, esec + t, nmsg))
                esec += t
            else:
                raise(ValueError(f'Unknown ID: {id_}, msg: {msg}'))
    chapter_file = os.path.join(main_folder, 'chapters_flat.xml')
    chapter_file_nested = os.path.join(main_folder, 'chapters_nested.xml')
    create_mkv_chapters(entries, chapter_file, allow_nested=False)
    create_mkv_chapters(entries, chapter_file_nested, allow_nested=True)
    combined = os.path.join(mkv_tmp, 'output.mkv')
    combined2 = os.path.join(main_folder, f'{main_folder_name}.mkv')
    # combined2_nested = os.path.join(main_folder, f'{main_folder_name}_nested.mkv')
    cmd = ['mkvmerge', '-o', combined]
    for f in file_order:
        f = os.path.join(mkv_tmp, f)
        cmd.append(f)
        cmd.append('+')
    cmd = cmd[:-1]
    # cmd += ['--chapters', f]
    print(cmd)
    print('\nMERGING FILES\n')
    merge_files_rc = subprocess.call(cmd)
    if merge_files_rc:
        raise ValueError("falied to merge files")

    print('\nADDING CHAPTERS\n')
    print(f'{combined} -> {combined2}')
    add_chapters_rc = subprocess.call(['mkvmerge', '-o', combined2, combined, '--chapters', chapter_file])
    if add_chapters_rc:
        raise ValueError("failed adding chapters")
    # subprocess.call(['mkvmerge', '-o', combined2_nested, combined, '--chapters', chapter_file_nested])
    # for k, v in new_ids.items():
    #     print(f'{k}: {v}')

    # with open(os.path.join(mkv_tmp, 'chapters.txt'), 'w') as f:
    #     for fname, (mkv_files, total_time, total_time2) in sorted(al.items(), key=lambda x: x[0]):
    #         # f.write(f'h|||{fname}|||{format_time(total_time)}\n')
    #         print(f'{fname} -> {total_time} -> {total_time2}')
    #         for tfile, ttime, ttime2 in mkv_files:
    #             # f.write(f'e|||{tfile}|||{format_time(ttime)}\n')
    #             print(f'    {tfile} -> {ttime} -> {ttime2}')


if __name__ == '__main__':
    main()
