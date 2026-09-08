# dw_novel

竖屏微短剧的创作工作区。

## 短剧剧本 skill

`.claude/skills/short-drama-script/` 是一个 Claude Code skill，覆盖从赛道立项、人物设定、故事大纲、分集表到单集分场剧本的全流程。在本仓库里直接说「帮我写个战神归来题材的短剧」就会自动加载。

```
.claude/skills/short-drama-script/
├── SKILL.md                      主流程与单集写法
├── references/
│   ├── genres.md                 赛道清单与各自的同质化陷阱
│   ├── hooks.md                  钩子与反转类型库
│   └── craft.md                  台词、调度、成本、合规
├── assets/
│   ├── outline-template.md       立项卡 + 人物表 + 分集表模板
│   └── episode-template.md       单集剧本模板与完整示例
└── scripts/check_script.py       剧本形式检查（时长、场景数、台词长度、钩子）
```

检查一份剧本：

```bash
python3 .claude/skills/short-drama-script/scripts/check_script.py 剧本.md --target 90
```
