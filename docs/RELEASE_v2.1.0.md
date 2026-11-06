# v2.1.0 — 图文教程、Athena 导入与导出修正

## 中文

- 新增中英文图文教程：实际 Athena 导出菜单、`.chik` 七列格式、权重对照、参数选择和多格式导出。
- 感谢 B 站 UP 主 **倩儿的天使师兄** 的教程分享：[观看完整原视频](https://www.bilibili.com/video/BV1Xsy7YRETN/)，并可在视频页进入博主主页。视频节选保留水印及时间点，不属于 MIT 授权范围。
- 软件说明页增加 GitHub 项目、问题反馈和功能建议入口。
- `.chik` 和 `.xdi` 可直接选择导入，修正原生文件选择框筛选问题。
- 包含 Hama 下载重试、缓存复用、下载文件夹检测和更详细的失败指导。
- 包含 Origin 原生矩阵方向修正：X=k、Y=R，矩阵列=k、行=R。旧 2.0.0 OPJU 请重新导出。

**[中文详细图文教程](https://github.com/369di-cmyk/exafs-wavelet-studio/blob/v2.1.0/docs/TUTORIAL.zh-CN.md)** · [反馈问题 / 建议功能](https://github.com/369di-cmyk/exafs-wavelet-studio/issues)

Windows 用户优先下载 `Setup.exe`；也可完整解压 `Windows.zip` 使用。`Source.zip` 包含源码和图文教程。Hama 不随包分发，首次使用请在引擎页下载或导入。OPJU 导出需要本机安装并激活 Origin，其他格式不需要。

## English

Bilingual illustrated Athena-to-wavelet tutorial, direct CHIK/XDI import, creator credit and GitHub feedback links. Includes setup retries/cache/Downloads detection and the native Origin orientation fix (X=k, Y=R; columns=k, rows=R). Re-export OPJU files created with 2.0.0.

**[Illustrated English guide](https://github.com/369di-cmyk/exafs-wavelet-studio/blob/v2.1.0/docs/TUTORIAL.en.md)** · [Verification record](https://github.com/369di-cmyk/exafs-wavelet-studio/blob/v2.1.0/TEST_REPORT.md)

Use the Windows installer or extract the complete portable ZIP. Hama is acquired independently. Native OPJU needs activated Origin; other formats do not. MIT covers this project's own code, not third-party software or video excerpts. Thanks to **倩儿的天使师兄**; [watch the original video](https://www.bilibili.com/video/BV1Xsy7YRETN/).

Local verification includes actual Athena Fe foil export, real Hama processing and multi-format exports. A previous full integration run passed 41 tests; the subsequent picker regression brings the suite to 42. Release automation runs the suite without external Hama/Origin, validates packages, tests installer extraction and generates SHA-256 checksums. These checks do not independently validate scientific interpretations.
