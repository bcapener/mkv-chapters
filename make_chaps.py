import os
import time
import sys, tempfile, os
import argparse
import shutil
import datetime
import subprocess
import enzyme
# import srtmerge
from pymediainfo import MediaInfo
from collections import OrderedDict, defaultdict
from xml.etree.ElementTree import Element, SubElement, Comment, tostring, ElementTree

DEBUG = False

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

def get_video_files(path, skip_dirs=()):
    # mp4s = []
    for root, dirs, files in os.walk(os.path.expanduser(path)):
        if root in skip_dirs:
            continue
        all_srts = sorted([f for f in files if f.endswith('.srt')])
        for f in files:
            file_name, file_ext = (f.rsplit('.', 1) + [""])[:2]
            if file_ext != 'mp4':
                continue
            srt_files = []
            for srt in all_srts:
                if srt.startswith(file_name):
                    srt_suffix = srt[len(file_name):-4]
                    srt_files.append((srt, srt_suffix))
            yield root, f, file_name, srt_files
    #         mp4s.append((root, f, srt_files))
    # return mp4s

def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--path', type=str, help='', required=True)
    args = parser.parse_args()

    main_folder = args.path
    main_folder_name = os.path.basename(main_folder.strip(os.sep))

    # mkv_out = os.path.join(main_folder, 'mkv_out')
    mkv_tmp = os.path.join(main_folder, 'mkv_tmp')

    # try:
    #     shutil.rmtree(mkv_out)
    # except:
    #     pass
    try:
        shutil.rmtree(mkv_tmp)
    except:
        pass
    # os.mkdir(mkv_out)
    os.mkdir(mkv_tmp)
    al = OrderedDict()
    all_files = OrderedDict()
    tmp_files = []

    srt_names = {}
    for root, mp4_file, mp4_file_name, srt_files in get_video_files(main_folder, skip_dirs=(mkv_tmp, )):
        mp4_path = os.path.join(root, mp4_file)
        fname = os.path.basename(root)
        if fname not in all_files:
            all_files[fname] = []
        tmp = []
        total_sec = 0
        total_sec2 = 0

        srt_suffixes = []
        for srt_file, srt_suffix in srt_files:
            # srt_suffix = srt_file[len(mp4_file_name):-4]
            srt_suffixes.append((srt_file, srt_suffix))
            if srt_suffix not in srt_names:
                ln = input(f'Give language name for "{srt_suffix}" (Default=English): ').strip()
                sn = input(f'Give language short name for "{srt_suffix}" (Default=eng): ').strip()
                lname = ln if ln else 'English'
                sname = sn if sn else 'eng'
                srt_names[srt_suffix] = (lname, sname)

        tmp_file = os.path.join(mkv_tmp, mp4_file_name + '.mkv')
        srt_tmp_file = os.path.join(mkv_tmp, mp4_file_name + '_srt.mkv')

        i = 1
        while os.path.isfile(tmp_file):
            tmp_file = os.path.join(mkv_tmp, mp4_file_name + f'_{i}.mkv')
            srt_tmp_file = os.path.join(mkv_tmp, mp4_file_name + f'_{i}_srt.mkv')
            i += 1

        print('\nCONVERTING MP4s to MKVs\n')
        mp4_to_mkv_rc = subprocess.call(['ffmpeg', '-i', mp4_path, '-vcodec', 'copy', '-acodec', 'copy', tmp_file])
        if mp4_to_mkv_rc:
            raise ValueError('Failed converting mp4 to mkv.')

        if srt_suffixes:
            cmd = ['mkvmerge', '-o', srt_tmp_file, tmp_file]
            for srt_file, srt_suffix in srt_suffixes:
                lname, sname = srt_names[srt_suffix]
                cmd += ['--language', f'0:{sname}', '--track-name', f'0:{lname}', os.path.join(root, srt_file)]

            print('\nADDING SRT FILES\n')
            add_srt_rc = subprocess.call(cmd)
            if add_srt_rc:
                raise ValueError("failed adding srt file")
            shutil.move(srt_tmp_file, tmp_file)
        # else:
        #     shutil.copyfile(tmp_file, srt_tmp_file)

        with open(tmp_file, 'rb') as f:
            mkv = enzyme.MKV(f)
            sec = mkv.info.duration.total_seconds()
            total_sec += sec

        sec2 = MediaInfo.parse(tmp_file).tracks[0].duration / 1000
        total_sec2 += sec2

        # tmp.append((os.path.basename(tmp_file), sec, sec2))
        # tmp_files.append(tmp_file)

        all_files[fname].append((os.path.basename(tmp_file), sec, sec2))
        # al[fname] = (tmp, tmp[0][1], tmp[0][2])
    # for root, dirs, files in os.walk(main_folder):
    #     if root in [mkv_tmp, mkv_out]:
    #         continue
    #     fname = os.path.basename(root)
    #     all_srts = sorted([f for f in files if f.endswith('.srt')])
    #     mp4s = []
    #     for f in files:
    #         if not f.endswith('.mp4'):
    #             continue
    #         found_srts = []
    #         for srt in all_srts:
    #             if srt.startswith(f[:-4]):
    #                 found_srts.append(srt)
    #         mp4s.append((f, found_srts))
    #
    #     # mp4s = sorted([f for f in files if f.endswith('.mp4')])
    #     if not mp4s:
    #         continue
    #     all_files[fname] = []
    #     tmp = []
    #     total_sec = 0
    #     total_sec2 = 0
    #     for mp4_file, srt_files in mp4s:
    #         # srt_files = []
    #         name = mp4_file[:-4]
    #         mp4_path = os.path.join(root, mp4_file)
    #         # if srt_files:
    #         srt_suffixes = []
    #         for srt_file in srt_files:
    #             srt_path = os.path.join(root, srt_file)
    #             srt_suffix = srt_file[len(name):-4]
    #             srt_suffixes.append((srt_file, srt_suffix))
    #             if srt_suffix not in srt_names:
    #                 ln = input(f'Give language name for "{srt_suffix}" (Default=English): ').strip()
    #                 sn = input(f'Give language short name for "{srt_suffix}" (Default=eng): ').strip()
    #                 lname = ln if ln else 'English'
    #                 sname = sn if sn else 'eng'
    #                 srt_names[srt_suffix] = (lname, sname)
    #             # print(srt_suffix)
    #         # srt_path = os.path.join(root, name + '-en.srt')
    #         # srts = [os.path.join(root, s) for s in all_srts if s.startswith(name)]
    #         tmp_file = os.path.join(mkv_tmp, name + '.mkv')
    #         srt_tmp_file = os.path.join(mkv_out, name + '.mkv')
    #         i = 1
    #         while os.path.isfile(tmp_file):
    #             tmp_file = os.path.join(mkv_tmp, name + f'_{i}.mkv')
    #             srt_tmp_file = os.path.join(mkv_out, name + f'_{i}.mkv')
    #             i += 1
    #         # all_files[fname].append((tmp_file, srts))
    #         # srt_tmp_file = os.path.join(mkv_out, name + '.mkv')
    #
    #         print('\nCONVERTING MP4s to MKVs\n')
    #         mp4_to_mkv_rc = subprocess.call(['ffmpeg', '-i', mp4_path, '-vcodec', 'copy', '-acodec', 'copy', tmp_file])
    #         if mp4_to_mkv_rc:
    #             raise ValueError('Failed converting mp4 to mkv.')
    #         if srt_suffixes:
    #             cmd = ['mkvmerge', '-o', srt_tmp_file, tmp_file]
    #             for srt_file, srt_suffix in srt_suffixes:
    #                 lname, sname = srt_names[srt_suffix]
    #                 cmd += ['--language', f'0:{sname}', '--track-name', f'0:{lname}', os.path.join(root, srt_file)]
    #
    #             print('\nADDING SRT FILES\n')
    #             add_srt_rc = subprocess.call(cmd)
    #             if add_srt_rc:
    #                 raise ValueError("failed adding srt file")
    #         else:
    #             shutil.copyfile(tmp_file, srt_tmp_file)
    #         with open(tmp_file, 'rb') as f:
    #             mkv = enzyme.MKV(f)
    #             sec = mkv.info.duration.total_seconds()
    #             total_sec += sec
    #         sec2 = MediaInfo.parse(tmp_file).tracks[0].duration / 1000
    #         total_sec2 += sec2
    #         tmp.append((os.path.basename(tmp_file), sec, sec2))
    #         tmp_files.append(tmp_file)
    #     al[fname] = (tmp, tmp[0][1], tmp[0][2])

    # ffmpeg_concat_filter(tmp_files, output=os.path.join(main_folder, 'concat_output.mkv'))
    # return
    # for fname, mkv_files in sorted(all_files.items(), key=lambda x: x[0]):
    #     print(f'{fname}')
    #     for f, ss in mkv_files:
    #         print(f'    {f}')
    #         for s in ss:
    #             print(f'        {s}')
    EDITOR = os.environ.get('EDITOR', 'vim')
    # al = OrderedDict(sorted(al.items(), key=lambda x: x[0])) 
    # al2 = OrderedDict()
    # for k, (v, t, t2) in sorted(al.items(), key=lambda x: x[0]):
    #     # al2[k] = sorted(v)
    #     # t = sorted(v, key=lambda x: x[0])
    #     al2[k] = sorted(v, key=lambda x: x[0]), t, t2
    al = OrderedDict()
    for k, v in OrderedDict(sorted(all_files.items())).items():
        al[k] = sorted(v, key=lambda x: x[0])

    # al = OrderedDict([(k, (sorted(v, key=lambda x: x[0]), t, t2)) for k, (v, t, t2) in sorted(al.items(), key=lambda x: x[0])])
    initial_message = f"TITLE {main_folder_name}\n" # if you want to set up the file somehow
    h, e = 0, 0
    ids = OrderedDict()
    for header, entries in al.items():
        initial_message += f'D{h:03} {header}\n'
        # ids[f'D{h:03}'] = (header, t, t2)
        for i, (entry, tt, tt2) in enumerate(entries):
            if i == 0:
                ids[f'D{h:03}'] = (header, tt, tt2)

            initial_message += f' F{e:03} {entry[:-4]}\n'
            ids[f'F{e:03}'] = (entry, tt, tt2)
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
    # t = '0:00:01.440000'
    # import datetime
    # import time
    # d = datetime.datetime.strptime(t, '%H:%M:%S.%f') - datetime.datetime(1900,1,1)
    # # d = time.strptime(t, '%H:%M:%S.%f')
    # print(d.total_seconds())
    main()
