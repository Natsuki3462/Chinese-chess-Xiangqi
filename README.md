# XiangqiFloat

置顶半透明的桌面浮窗，用肉眼复刻真实对局、由本地 Pikafish 实时提示最佳着法。

纯本地运行：不截图、不识别、不联网、不上传任何东西。

---

## 功能

- **9×10 交叉点棋盘**，自绘：楚河汉界、九宫斜线、双线外框
- **圆形棋子 + 汉字**：帅仕相马车炮兵 / 将士象马车炮卒，红黑分色
- **两种走子方式**：点起点→点终点，或按住棋子直接拖到目标点
- **引擎建议箭头**：绿色 = 当前局面的最佳着法；灰色 = 上一轮遗留（重新分析中）
- **空格一键采纳**，或打开 `A` 自动采纳开关
- **撤销 / 重做 / 回退到第 N 步**，历史条点任意一步跳转
- **中文记谱**：炮二平五、马八进七、车九进一
- **四档分析强度** + 自适应思考时间
- 无级透明度、置顶、紧凑模式、低优先级不抢 CPU

## 快捷键

| 键 | 作用 |
| --- | --- |
| `空格` | 采纳引擎建议 |
| `Ctrl+Z` / `Ctrl+Y` | 撤销 / 重做 |
| `F` | 翻转视角 |
| `N` | 新开一局 |
| `Esc` | 取消选中 |
| `↑` / `↓` | 透明度 ±2% |
| `Ctrl+滚轮` | 任意位置调透明度 |
| `Ctrl+1` ~ `Ctrl+4` | 切换分析强度：轻快 / 均衡 / 深度 / 极限 |
| 双击顶栏 | 紧凑模式 |

---

## 快速开始

```bash
git clone <本仓库地址>
cd Chinese-chess-Xiangqi
```

**第 1 步：放引擎**

仓库不含二进制（引擎 6.7MB + 权重 49MB）。需要两个文件，缺一不可：

1. 从 <https://github.com/official-pikafish/Pikafish/releases> 下载
   `Pikafish.2026-09-06.7z`，解压后把 exe 改名为 `pikafish.exe`
2. 从同一个包内取出 `pikafish.nnue`（权重）

两个文件都放进 `engine/` 目录，**必须同目录**——引擎默认在自己的目录找权重，找不到会直接退出。

> 国内网络拉 GitHub Release 常卡住，可用镜像前缀：
> `https://ghfast.top/https://github.com/official-pikafish/Pikafish/releases/download/Pikafish-2026-09-06/Pikafish.2026-09-06.7z`

**第 2 步：装依赖**

双击 `install.bat`：建虚拟环境、装 PyQt6 / cchess、检查引擎、跑 FEN 兼容性验证。
所有内容都落在本文件夹内，不污染系统 Python、不写注册表。

**第 3 步：启动**

双击 `run.bat`（或 `run-debug.bat` 带控制台日志）。选择执红/执黑，之后循环：
看到对手走子 → 在浮窗上复刻 → 等箭头 → `空格` 采纳。

---

## 分析强度

档位越高越强，代价是箭头来得越慢。默认「均衡」。

| 档位 | 限时 | 线程 | Hash | 走子→箭头 | 实测深度 |
| --- | --- | --- | --- | --- | --- |
| 轻快 | 300ms | 2 | 128MB | ≈0.5s | 19 ~ 20 |
| **均衡（默认）** | 800ms | 4 | 256MB | ≈1.0s | 21 ~ 23 |
| 深度 | 1500ms | 6 | 512MB | ≈1.7s | 23 ~ 24 |
| 极限 | 3000ms | 8 | 1024MB | ≈3.2s | 27 ~ 28 |

用的是 `go movetime` 而不是 `go depth`：实测 `go depth 22` 要 1500~1950ms，
而 `movetime 800` 就能到 21~23 层——限时搜索靠迭代深化，同等时间下更深。

**自适应思考时间**（默认开）：按局面难度在基础值 ×0.4~2.5 之间浮动。
残局 +0.55、被将军 +0.30、选择多 +0.18、评估跳变 >1.0 再 +0.35；
中局强制着法（≤8 步可走）−0.25。

---

## 三条核心机制

**1. 人眼替代 CV —— 只输入对手着法**
浮窗镜像真实对局，你只需复刻对手那一步；自己的着法由引擎建议后一键采纳。

**2. 局面归 cchess，计算归 Pikafish**
`cchess.ChessBoard` 是唯一真源。局面一变 → 防抖 220ms → 触发引擎限时分析。
每次局面变化 `version += 1`，分析结果带着 version 回传，对不上号就丢弃。

**3. 只在己方回合分析**
对手回合不跑引擎、不出箭头——既省 CPU，也不把对手的最佳着法摆出来。

## 实现要点

- **自写 UCI 循环**：`chess.engine.SimpleEngine` 不能驱动 Pikafish。
  它下发的是 8×8 国际象棋 FEN，Pikafish 返回中国象棋着法后 python-chess 解析失败，
  且 info 流不终止导致 future 永不 resolve、进程卡死。
  所以用 `subprocess` + 读线程自己实现，保留打断、版本号、空闲零占用。
- **真合法着法**：cchess 的 `create_moves()` 只做几何校验，不过滤「送将」。
  直接用于是会出现"走完自己被吃将"、而且将死永远判不出来。
  这里逐着试走一遍剔除（3ms / 44 着），顺带覆盖飞将规则。
- **将军判定**：cchess 的 `is_checking()` 语义是「我正在将军对方」，
  与"我被将军"相反，所以自己实现 `_in_check_on()`。
- **箭头两态**：绿色 = 本局面建议；灰色 = 上一轮遗留。
  走子瞬间箭头不消失，新结果到达无缝替换；撤销回到原位若仍合法则立刻转绿。
- **中文记谱**：红方从右往左数一~九，黑方 1~9；
  马/相/仕的「进/退」跟**目标路数**，车/炮/兵跟**步数**；
  同路同兵种用「前/后」前缀。

## 目录结构

```
Chinese-chess-Xiangqi/
├─ run.bat / run-debug.bat    启动
├─ install.bat                一次性安装
├─ requirements.txt
├─ config.json                窗口与引擎参数（首次运行生成，不入库）
├─ app/
│  ├─ main.py                 入口
│  ├─ config.py               预设与配置持久化
│  ├─ session.py              规则状态机 + 中文记谱
│  ├─ engine_worker.py        Pikafish UCI 子线程
│  ├─ board_view.py           9×10 交叉点棋盘
│  ├─ pieces.py               圆形棋子 + 汉字
│  ├─ float_window.py         浮窗 / 工具条 / 历史 / 设置
│  └─ theme.py                配色与样式
├─ engine/                    放入 pikafish.exe 与 pikafish.nnue
└─ tools/                     验证脚本
```

## 自检脚本

```bash
.venv\Scripts\python.exe tools\validate_fen.py    # FEN 能否被 Pikafish 接受
.venv\Scripts\python.exe tools\validate_loop.py   # 引擎闭环 12 步
.venv\Scripts\python.exe tools\check_rules.py     # 将军/将死/飞将/送将过滤/记谱
.venv\Scripts\python.exe tools\check_pixels.py    # 棋盘像素级校验
.venv\Scripts\python.exe tools\shot.py            # 界面交互回归 + 截图
```

---

## 合规边界（重要）

本软件**仅用于个人复盘、离线对局分析、自建环境练习**。

在在线对战平台使用引擎辅助属于违规行为，会破坏对局公平。本软件不面向、也不适配该场景，
并且刻意不包含任何图像识别、屏幕读取、自动输入/注入能力 —— 局面完全由用户自己输入。

Pikafish 的权重许可同样声明：仅限合法用途，用于在线作弊等超范围使用由使用者自行承担后果。

---

## 第三方组件与许可

| 组件 | 版本 | 许可 |
| --- | --- | --- |
| [Pikafish](https://github.com/official-pikafish/Pikafish) | 2026-09-06 | GPLv3（见 `engine/Copying.txt`） |
| [Pikafish 权重](https://github.com/official-pikafish/Networks) | — | 见 `engine/NNUE-License.md` |
| [cchess](https://github.com/walker8088/cchess) | ≥1.25 | LGPL-3.0-or-later |
| [PyQt6](https://riverbankcomputing.com/software/pyqt/) | ≥6.6 | GPLv3 / 商业双许可 |

本项目整体以 **GPLv3** 发布，完整文本见 [LICENSE](LICENSE)。

> 引擎与权重不随仓库分发，请按上方「第 1 步」自行下载。
> 仓库内保留 `engine/Copying.txt` 与 `engine/NNUE-License.md`，是其许可要求的随附文件。
