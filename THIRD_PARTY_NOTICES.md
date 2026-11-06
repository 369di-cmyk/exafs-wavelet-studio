# Third-party notices / 第三方说明

The root MIT license applies to application-authored code. Third-party components retain their respective licenses and copyright notices. Full collected license texts for the exact build environment accompany binary distributions in `THIRD_PARTY_LICENSES.txt`.

根目录 MIT 许可证适用于本软件自有代码。第三方组件保留自己的许可证和版权声明。二进制发布包附带本次构建环境收集的完整许可文本 `THIRD_PARTY_LICENSES.txt`。

- **Hama**: external user-provided/officially downloaded executable. No license or redistribution right is inferred from public download availability. Not included in source, portable package or installer. [Official page](https://www.esrf.fr/UsersAndScience/Experiments/CRG/BM20/Software/Wavelets/HAMA).
- **Original Wgnuplot and Hama manual/model files**: not included. `plot_bridge.cs` is this application's own no-op helper and is compiled separately. It is copied under the legacy expected helper filename only in a temporary job folder.
- **shadcn/ui**: MIT, Copyright (c) 2023 shadcn. Official CLI-generated components in `frontend/src/components/ui`; local changes and composition are tracked in this project. [Project license](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md).
- **React / React DOM / Radix UI / Lucide / Tailwind CSS / associated frontend utilities**: see exact installed package licenses collected by the release script. Build-time tools are not application services and are not shipped as Node.js installations.
- **Geist font**: SIL Open Font License; collected from the installed font package.
- **Python runtime and Python packages** including NumPy, Matplotlib, openpyxl, pywebview, pythonnet, pywin32, Pillow and their dependencies: see collected distribution license files. PyInstaller is used as a build tool with its bootloader distribution exception.
- **Microsoft Edge WebView2**: a separately installed Microsoft runtime. The pywebview WebView2 SDK assemblies are accompanied by their packaged notices where provided. [Microsoft WebView2 distribution documentation](https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution).
- **Origin/OriginPro**: optional separately installed commercial software. No Origin executable, OriginExt library or license is bundled. COM calls invoke the user's installation only when native OPJU is requested. [Origin COM documentation](https://docs.originlab.com/com/).

This project does not claim endorsement by ESRF, the Hama authors, OriginLab, Microsoft or shadcn/ui.

## shadcn/ui MIT notice

MIT License

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


## Tutorial screenshots / 教程截图

`frontend/public/tutorial/video-52.png`, `video-98.png`, `video-350.png`, and `video-415.png` are selected stills from the user-supplied local copy of 《一分钟速成Wavelet-transform ▏XAS同步辐射-小波变换处理EXAFS数据》, https://www.bilibili.com/video/BV1Xsy7YRETN/ . On-screen attribution: 倩儿的天使师兄. Timestamps: 00:52, 01:38, 05:50, 06:55. Original credits are retained; these excerpts illustrate and discuss specific software operations. Rights remain with their original owners; these images are **excluded from the MIT license**. No full video is distributed.

`athena-menu.png` is a local screenshot of Athena 0.9.26 using its bundled Fe foil example. Athena interface and third-party marks remain with their owners. No user experimental data or Athena project is bundled.

视频截图不属于本软件自有代码，不适用 MIT；完整视频不随软件分发。教程文字为重新撰写，区分视频演示、官方文档和本机实测。

`studio-result.png` and `studio-export.png` are locally captured app screenshots showing the bundled Fe foil standard workflow. They contain no user experimental dataset.

Special thanks / 特别感谢 Bilibili UP 主 倩儿的天使师兄 for the tutorial. Watch the full original video at https://www.bilibili.com/video/BV1Xsy7YRETN/ ; the creator profile is accessible by clicking their name on the video page.
