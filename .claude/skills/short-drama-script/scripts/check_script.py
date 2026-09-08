#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短剧剧本形式检查器。

用法:
    python3 check_script.py 剧本.md [剧本2.md ...]
    python3 check_script.py 剧本.md --target 90      # 指定单集目标时长(秒)

它只查形式：时长、场景数、台词长度、钩子标记、同框人数、钩子类型是否连续重复。
过了不代表写得好，没过基本上一定有问题。
"""

import argparse
import re
import sys

# 时长模型：台词按中文口语约每秒 4.5 字，另计每句之间的反应停顿、
# 每段动作描写的表演时间、每次转场的切换时间。
CHARS_PER_SECOND = 4.5
SECONDS_PER_DIALOG = 0.8
SECONDS_PER_ACTION = 2.5
SECONDS_PER_SCENE = 2

MAX_LINE_CHARS = 20      # 单句台词上限
MAX_SCENES = 3           # 单集场景数上限
MAX_ON_SCREEN = 4        # 同框有名有姓的人数上限
DURATION_TOLERANCE = 0.35  # 时长偏离目标的容忍比例

EPISODE_RE = re.compile(r'^\s*#*\s*第\s*(\d+)\s*集')
SCENE_RE = re.compile(r'^\s*(\d+)[.、．]\s*(.+)$')
SCENE_HEAD_RE = re.compile(r'[日夜晨昏晚]|/')
CHARS_RE = re.compile(r'^\s*【人物】\s*(.*)$')
HOOK_RE = re.compile(r'^\s*【钩子】\s*(.*)$')
DIALOG_RE = re.compile(r'^\s*([^：:【】\s]{1,10})(（[^）]*）)?\s*[：:]\s*(\S.*)$')
META_KEYS = ('时长', '上集钩子', '场景', '爽点', '人物', '钩子')

HOOK_TYPES = {
    '闯入者': ('推门', '门被', '大门', '走进来', '闯进', '停稳', '车门'),
    '称呼揭穿': ('少爷', '小姐', '师父', '老大', '总裁', '董事长', '叫我', '喊'),
    '物证曝光': ('照片', '短信', '聊天记录', '报告', '文件', '戒指', '录音', '视频'),
    '情感反转': ('签名', '原来', '竟然是', '一直'),
}


def visible_len(text: str) -> int:
    """按可读字符计数，忽略标点和空白——标点不占朗读时间。"""
    return len(re.sub(r'[\s，。！？、；：…—·“”‘’"\'()（）\[\]【】]', '', text))


def parse(path):
    episodes = []
    cur = None
    in_scene = False
    with open(path, encoding='utf-8') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip('\n')
            m = EPISODE_RE.match(line)
            if m:
                cur = {
                    'no': int(m.group(1)), 'line': lineno, 'title': line.strip(),
                    'scenes': [], 'dialogs': [], 'hook': None, 'casts': [],
                    'actions': 0,
                }
                in_scene = False
                episodes.append(cur)
                continue
            if cur is None:
                continue

            m = HOOK_RE.match(line)
            if m:
                cur['hook'] = m.group(1).strip()
                in_scene = False
                continue

            m = CHARS_RE.match(line)
            if m:
                names = [n for n in re.split(r'[、,，\s]+', m.group(1)) if n]
                cur['casts'].append((lineno, names))
                continue

            m = SCENE_RE.match(line)
            if m and SCENE_HEAD_RE.search(m.group(2)):
                cur['scenes'].append((lineno, m.group(2).strip()))
                in_scene = True
                continue

            m = DIALOG_RE.match(line)
            if m and m.group(1) not in META_KEYS:
                cur['dialogs'].append((lineno, m.group(1), m.group(3).strip()))
                continue

            # 只统计场景内的动作描写段落——集头信息块和文末说明不算表演时间。
            if in_scene and line.strip() and not line.lstrip().startswith(
                    ('#', '---', '|', '>', '-', '*', '`')):
                cur['actions'] += 1
    return episodes


def hook_type(text):
    for name, keys in HOOK_TYPES.items():
        if any(k in text for k in keys):
            return name
    return '其他'


def check(path, target):
    episodes = parse(path)
    print(f'\n=== {path} ===')
    if not episodes:
        print('没有解析到任何一集。集头需要形如「第 7 集」的行，见 assets/episode-template.md。')
        return 1

    problems = 0
    prev_hooks = []
    print(f'{"集":>4} {"时长≈":>7} {"场景":>5} {"台词字":>7} {"最长句":>7}  钩子')
    print('-' * 62)

    details = []
    for ep in episodes:
        chars = sum(visible_len(d[2]) for d in ep['dialogs'])
        n_scenes = max(len(ep['scenes']), 1)
        dur = (chars / CHARS_PER_SECOND
               + len(ep['dialogs']) * SECONDS_PER_DIALOG
               + ep['actions'] * SECONDS_PER_ACTION
               + n_scenes * SECONDS_PER_SCENE)
        longest = max(ep['dialogs'], key=lambda d: visible_len(d[2]), default=None)
        longest_len = visible_len(longest[2]) if longest else 0
        htype = hook_type(ep['hook']) if ep['hook'] else '缺失'
        print(f'{ep["no"]:>4} {dur:>6.0f}s {n_scenes:>5} {chars:>7} {longest_len:>7}  {htype}')

        msgs = []
        if not ep['hook']:
            msgs.append('缺【钩子】标记——每集结尾必须打开一个新问号')
        elif visible_len(ep['hook']) < 4:
            msgs.append('钩子过短，可能不是一个能拍的画面或台词')

        if abs(dur - target) > target * DURATION_TOLERANCE:
            verb = '超长' if dur > target else '偏短'
            msgs.append(f'估算时长 {dur:.0f}s {verb}（目标 {target}s）')

        if len(ep['scenes']) > MAX_SCENES:
            msgs.append(f'{len(ep["scenes"])} 个场景，超过 {MAX_SCENES} 个；转场会把节奏切碎')

        over = [(ln, sp, tx) for ln, sp, tx in ep['dialogs'] if visible_len(tx) > MAX_LINE_CHARS]
        for ln, sp, tx in over[:3]:
            msgs.append(f'L{ln} {sp} 的台词 {visible_len(tx)} 字，超过 {MAX_LINE_CHARS} 字：{tx[:24]}…')
        if len(over) > 3:
            msgs.append(f'另有 {len(over) - 3} 句超长台词')

        for ln, names in ep['casts']:
            named = [n for n in names if not re.search(r'若干|等|群|众', n)]
            if len(named) > MAX_ON_SCREEN:
                msgs.append(f'L{ln} 同场 {len(named)} 个有名角色，竖屏放不下，考虑拆场或降为背景')

        if not ep['scenes']:
            msgs.append('没有解析到场景标题行（形如「1. 日 / 内 / 客厅」）')
        if not ep['dialogs']:
            msgs.append('没有解析到台词')

        prev_hooks.append(htype)
        if len(prev_hooks) >= 3 and htype != '其他' and prev_hooks[-3:] == [htype] * 3:
            msgs.append(f'连续三集都是「{htype}」型钩子，观众会开始预判，换一种')

        if msgs:
            details.append((ep['no'], msgs))
            problems += len(msgs)

    if details:
        print('\n需要处理：')
        for no, msgs in details:
            print(f'\n第 {no} 集')
            for m in msgs:
                print(f'  - {m}')
    else:
        print('\n形式检查通过。接下来靠人判断：主角是否主动、爽点有没有观众在场、信息差有没有提前烧掉。')

    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description='短剧剧本形式检查器')
    ap.add_argument('files', nargs='+', help='剧本 markdown 文件')
    ap.add_argument('--target', type=float, default=90, help='单集目标时长（秒），默认 90')
    args = ap.parse_args()
    return max(check(f, args.target) for f in args.files)


if __name__ == '__main__':
    sys.exit(main())
