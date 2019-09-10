import os
import toml
import time
import sys, tempfile, os
import argparse
import shutil
import datetime
import subprocess
import enzyme
import json
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


def get_video_files(path, skip_dirs=()):
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


def edit_chapter_names(all_files, main_folder_name):
    EDITOR = os.environ.get('EDITOR', 'vim')
    # al = OrderedDict(sorted(al.items(), key=lambda x: x[0]))
    # al2 = OrderedDict()
    # for k, (v, t, t2) in sorted(al.items(), key=lambda x: x[0]):
    #     # al2[k] = sorted(v)
    #     # t = sorted(v, key=lambda x: x[0])
    #     al2[k] = sorted(v, key=lambda x: x[0]), t, t2
    al = OrderedDict()
    for k, v in OrderedDict(sorted(all_files.items())).items():
        al[k] = sorted(v.values(), key=lambda x: x[0])

    # al = OrderedDict([(k, (sorted(v, key=lambda x: x[0]), t, t2)) for k, (v, t, t2) in sorted(al.items(), key=lambda x: x[0])])
    initial_message = f"TITLE {main_folder_name}\n"  # if you want to set up the file somehow
    h, e = 0, 0
    ids = OrderedDict()
    for header, entries in al.items():
        initial_message += f'D{h:03} {header}\n'
        # ids[f'D{h:03}'] = (header, t, t2)
        for i, (entry, tt, tt2) in enumerate(entries):
            if i == 0:
                ids[f'D{h:03}'] = (header, tt, tt2)

            # initial_message += f' F{e:03} {entry[:-4]}\n'
            initial_message += f' F{e:03} {entry}\n'
            ids[f'F{e:03}'] = (entry, tt, tt2)
            e += 1
        initial_message += '\n'
        h += 1
    # with tempfile.NamedTemporaryFile(suffix=".tmp") as tf:
    #     tf.write(initial_message.encode())
    #     tf.flush()
    #     print('\nEDITING CHAPTER FILE\n')
    #     subprocess.call([EDITOR, tf.name])
    #
    #     # do the parsing with `tf` using regular File operations.
    #     # for instance:
    #     tf.seek(0)
    #     edited_message = tf.readlines()
    edited_message = initial_message.encode().splitlines()

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
            fname, srts, t = ids[id_]
            new_ids[id_] = (fname, nmsg, srts, t)
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
    return entries

def get_video_info(path):
    main_folder_name = os.path.basename(path.strip(os.sep))

    mkv_tmp = os.path.join(path, 'mkv_tmp')
    srt_names = {}
    all_files = OrderedDict()

    for root, mp4_file, mp4_file_name, srt_files in get_video_files(path, skip_dirs=(mkv_tmp, )):
        mp4_path = os.path.join(root, mp4_file)
        mp4_dir_name = os.path.basename(root)
        if mp4_dir_name not in all_files:
            all_files[mp4_dir_name] = OrderedDict()

        srt_suffixes = []
        for srt_file, srt_suffix in srt_files:
            if srt_suffix not in srt_names:
                ln = input(f'Give language name for "{srt_suffix}" (Default=English): ').strip()
                sn = input(f'Give language short name for "{srt_suffix}" (Default=eng): ').strip()
                lname = ln if ln else 'English'
                sname = sn if sn else 'eng'
                srt_names[srt_suffix] = (lname, sname)
            else:
                lname, sname = srt_names[srt_suffix]
            srt_suffixes.append([srt_file, lname, sname])

        sec = MediaInfo.parse(mp4_path).tracks[0].duration / 1000
        all_files[mp4_dir_name][mp4_file] = (mp4_file_name, srt_suffixes, sec)

    t = OrderedDict()
    for k, v in OrderedDict(sorted(all_files.items(), key=lambda x: x[0])).items():
        t[k] = OrderedDict(sorted(v.items(), key=lambda x: x[0]))
    entries = edit_chapter_names(all_files, main_folder_name)
    return OrderedDict([('title', main_folder_name), ('info', t), ('chapter', entries)])


def main():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-p', '--path', type=str, help='', required=True)
    parser.add_argument('-r', '--refresh', is_flag=True, help='')
    args = parser.parse_args()

    main_folder = os.path.expanduser(args.path)
    info_file = os.path.join(main_folder, 'info.json')

    if not args.refresh and os.path.exists(info_file):
        with open(info_file, 'r') as f:
            info = json.load(f, object_pairs_hook=OrderedDict)
    else:
        info = get_video_info(main_folder)
        with open(info_file, 'w') as f:
            json.dump(info, f, sort_keys=True, indent=4, separators=(',', ': '))


    # print(t)
    # # assert t == info
    for k, v in info['info'].items():
        print(k)
        for kk, vv in v.items():
            print("\t" + kk)
            print("\t\t" + str(vv))


if __name__ == '__main__':
    main()
