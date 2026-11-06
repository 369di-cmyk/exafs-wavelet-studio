# 2.0.2

## 2.1.0 — 2026-11-07 (local build)

- Added bilingual illustrated Athena-to-WT guide with attributed video stills, timestamps, enlarged image view, parameter explanations and troubleshooting.
- Verified actual Athena 0.9.26 GUI export: `.chik`, 441 × 7 columns for the bundled Fe foil. Fixed missing `.chik` picker filter; added `.xdi`.
- Explained why Athena plotting weight and signal-column weight differ, and mapped the video's preweighted k³χ + Hama 0 route to app input 3 / calculation 3.
- Retains the download reliability and Origin orientation fixes. No Hama engine, full video or experimental dataset bundled.


- One-click Hama setup now reuses a verified cached engine, then checks completed Hama ZIP/EXE files in Downloads before accessing the network.
- Added up to three attempts using the official ESRF HTTPS download URLs, streamed progress, bounded waits and cancellation.
- Added specific bilingual diagnostics for HTTP denial, timeout, DNS, TLS, proxy authentication, incomplete downloads and HTML error pages. Local diagnostics are saved to last_download.json.
- Added Detect download & import for browser downloads. Every file still requires the pinned engine SHA-256; no Hama is redistributed and TLS verification remains enabled.

中文：优化一键配置，优先复用本机引擎和下载文件，下载失败自动重试，显示进度并支持取消；增加浏览器下载检测和具体错误说明。保留 2.0.1 的 Origin 坐标修复。

# 2.0.1

- Fixed transposed native Origin heatmaps: pywin32 receives rows=R and columns=k without a transpose. Preview, Excel and XYZ data were unaffected.
- Added independent Origin row/column, coordinate and off-diagonal cell validation, plus saved-project regression checks with square and non-square matrices.
- Matched native graph axis limits to the preview. Hama calculations are unchanged.
- Existing v2.0.0 OPJU exports must be exported again; changing axis titles or rotating the rendered image does not repair matrix coordinates.

中文：修复 Origin 原生项目导出中多余的矩阵转置，使横轴 k、纵轴 R 与预览一致。已有 2.0.0 的 OPJU 请重新导出；预览、PDF、图片、Excel 和 XYZ 数据不受此错误影响。增加保存后重新打开的方向与峰位检查。

# 2.0.0

- Rebuilt the desktop interface with official shadcn/ui Radix components; Chinese/English switching and in-app guidance.
- Removed bundled Hama. Added official download, ZIP/EXE/folder import, pinned engine verification and an external per-user cache.
- Isolated jobs in short ASCII work folders, preserving source paths and files; configurable fallback work directory.
- Added bilingual diagnostics with location, cause, correction and copyable technical details.
- Added independently selectable PNG, TIFF, SVG, PDF, TXT, CSV, XLSX, Origin XYZ, real OPJU, NPZ and full-grid exports.
- Origin automation uses a separate instance and checks matrix data before saving; ordinary formats require no Origin installation.
- Added explicit stale-result notice after parameter edits, shared raw color limits and per-format export reporting.
- Added MIT licensing for application code, bilingual documentation, third-party notices, source packaging and automated checks.

中文：2.0 将 Hama 改为用户自行获取，重做双语界面，自动处理路径兼容，增加详细错误说明与多格式导出，并整理了独立开源版本。Hama 算法本身未被修改。
