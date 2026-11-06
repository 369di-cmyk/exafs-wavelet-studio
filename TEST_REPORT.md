# Verification report / 测试记录

## 2.1.0 Athena export and illustrated guide / 实测导出与图文教程

Date: 2026-11-07. Version 2.1.0 verification record.

- Final documentation/link update: frontend lint and production build passed; 42 tests completed successfully (5 external integration tests skipped in this rerun). Mocked all five project/video/feedback link actions; checked feedback query encoding/version and every local tutorial/README image and file link. Detailed bilingual Markdown guides include seven images, attribution and feedback links. Earlier full external integration evidence is listed below.

- Used the actual Athena 0.9.26 GUI with its bundled Fe foil standard: File → Save current group as… → χ(k). The default extension is `.chik`, not necessarily `.chi`.
- Actual export: XDI/1.0 comments, 441 rows × 7 columns, k=0..22 Å⁻¹, step 0.05. Columns: k, chi, k*chi, k²*chi, k³*chi, FT window, energy. Athena.kweight=2 does not weight the second column.
- SHA-256 of the exported test input: 8a1d26668da162d73a7b864996a5810a3bbae5923881110117737247a31befd8. Input hash unchanged after processing. This experimental standard and its project are not bundled.
- Real Hama test with k=2..12, Morlet 15/1, weight 2: 201 selected points, finite nonzero 201×201 WT. PDF, XLSX, TXT, Origin XYZ, OPJU and PNG succeeded. The three preweighted Athena columns recover the same chi within export precision.
- Full suite: **41/41 passed, no skips, 80.658 seconds**, RUN_HAMA_TESTS=1 and RUN_ORIGIN_TESTS=1. Includes original-engine numerical comparison, Unicode paths, all formats, and Origin asymmetric coordinate checks after reopen.
- Subsequent GUI testing found an invalid file-filter description containing parentheses. Fixed it and added a real pywebview filter-parser regression. The targeted studio suite passed 29 tests (4 integration cases skipped in that targeted rerun; they passed in the full run). Total suite now contains 42 tests. No scientific calculation changed after the full run.
- Actual GUI retest: picker lists .chik; imported Fe_foil.chik as 441 rows × 7 columns; clicked Analyze and observed the WT preview. Export selections, Chinese/English guide, image loading, enlargement and Escape close were visually checked.
- Four unchanged stills from the supplied 9:36 video are attributed with timestamps and excluded from MIT. Two local studio screenshots and one local Athena screenshot supplement them.
- Huasuan webpage remained behind site verification; its article text was not read or used as verified evidence. Tutorial uses local tests, Athena official documentation, Hama manual and observed video frames.

中文：已实测Athena导出→软件导入→Hama计算→多格式导出。修复.chik筛选遗漏及筛选说明括号问题；详细图文教程含截图来源、时间点、参数对照和中英文说明。


## 2.0.2 setup reliability / 一键配置优化

- **40 tests passed in 62.703 seconds** with RUN_HAMA_TESTS=1, including the Origin orientation regression and all real Hama integration checks.
- Added download tests for cache reuse without network, local ZIP detection, retry after timeout, HTTP 403, TLS failure, DNS/proxy classification, HTML error pages, truncated/oversized responses, hash mismatch, cancellation and redirect boundaries.
- A real fresh setup through DesktopApi downloaded the official ZIP and verified the pinned engine hash in 1.33 seconds on this connection. A simulated offline repeat reused the cache without issuing a request. This timing is not a download-speed guarantee.
- Live probes reproduced HTTP 403 with a generic browser User-Agent, while the standard download-client header succeeded. Both official URL forms were checked. No historical error log existed in the previous version, so this is not proof of the cause of every earlier failure.
- Frontend ESLint and TypeScript/Vite build passed. Local diagnostic records now retain attempt stages and specific error codes; no certificate bypass, third-party mirror or bundled Hama was added.

中文：40 项测试通过，真实官网下载与断网缓存复用通过；增加重试、下载检测、进度与取消，并细分错误原因。网络/官网不可用时仍可能失败，浏览器下载后导入作为备用路径。

## 2.0.1 orientation correction / 坐标方向修复

Date: 2026-11-06. Local patch; not yet published to GitHub Releases.

- Reproduced the 2.0.0 defect in Origin 2021 with a 3-row by 5-column marker matrix: pywin32 PutMatrix takes nested rows. The old transpose produced 5 rows and 3 columns while retaining k/R axis labels.
- Fixed export to retain rows=R, columns=k. Added runtime checks of dimensions, mapped coordinate endpoints and actual matrix cells through LabTalk, independently of COM GetMatrix/PutMatrix round-trip.
- **28 automated tests passed in 64.800 seconds**, with RUN_HAMA_TESTS=1. Includes real Hama reference, all 11 formats, and square/non-square orientation regression checks after OPJU reopen. Marker peak k=8, R=0 remains at that coordinate, with increasing graph axes and matching limits.
- Frontend ESLint and TypeScript/Vite production build passed using Node 24.
- The older 2.0.0 checks below did NOT establish graph orientation: their transposed readback repeated the same incorrect assumption. Their orientation assurance is superseded by this correction.
- Preview, PDF/images, Excel, XYZ and Hama computation are unchanged. Existing 2.0.0 native OPJU files must be re-exported.

中文：已确认旧版本原生 Origin 导出有多余转置。新测试直接读取 Origin 单元格、坐标范围，并验证非对称峰在保存重开后的实际位置，避免只做数组读写往返的旧测试盲点。28 项测试通过；旧 OPJU 请重新导出。

## Historical 2.0.0 verification / 2.0.0 历史记录

Version: 2.0.0 · Date: 2026-11-06

Environment: Windows 11 x64 (22621), Python 3.12.14, Node.js 24.22.1, Microsoft Edge WebView2, OriginPro 2021. Hama was acquired externally; no Hama program is included in the release.

## Completed / 已完成

- **27 automated tests passed** (`python -m unittest discover -s tests -v`, `RUN_HAMA_TESTS=1`, 31.788 seconds in the final full run).
- Compared the Hama adapter with a prior direct, interactive Hama reference: all **271,201 XYZ rows matched exactly**, not merely the displayed figure.
- Ran real Morlet and Cauchy calculations from a **Chinese directory containing spaces and a long subfolder**, separate from the engine. Source bytes were unchanged.
- Exercised actual cancellation and timeout; owned job processes terminate and temporary folders are cleaned.
- Checked invalid row details, missing cells, column counts, duplicate k, NaN, energy-column mistakes, range violations, weighting, point limits and opt-in resampling.
- Checked malformed/duplicate-member ZIPs, traversal names, invalid executable hashes and simulated network failure. Invalid engine inputs are not installed or executed.
- **Official ESRF download succeeded**, retrieving the 555,255-byte ZIP and the expected executable hash. Fixed an observed HTTP 403 by using a download-client-compatible request. Website/network availability remains external.
- Exported **all 11 selectable formats** for two synthetic spectra: PNG, TIFF, SVG, PDF, TXT, CSV, XLSX, Origin XYZ, OPJU, NPZ and full Hama grid. No format failed in the successful integration run.
- Reopened XLSX and verified matrix values and both axes; round-tripped TXT and NPZ values. Tested Excel formula-like sample names as literal strings.
- Reopened the real **OPJU in a separate Origin COM instance**, checked both WT matrices against calculated values and confirmed native graph pages. Fixed the Origin 2021 project-file lock before temporary-directory cleanup.
- Confirmed a simulated Origin failure is reported as **partial export**, retaining successful selected formats. Unselected formats are not produced and repeat exports use different directories.
- Verified shared raw figure color limits and that display normalization does not modify numerical arrays.
- PDF parser confirmed three pages for a two-sample report; PNG dimensions checked.
- Frontend TypeScript/build and ESLint passed. Production dependency audit: **0 reported vulnerabilities** at check time. The full development-tool tree still reports 15 advisories (2 low, 13 moderate); these tools are not shipped as runtime services. This is not a claim of a comprehensive security audit.
- Desktop UI inspected in Chinese and English; language switching, synthetic sample loading, actual Hama computation and multi-format export dialog exercised.
- Completed the installed app's full **Origin + PDF** UI workflow, including the native folder picker. The UI reported both formats complete and the destination contained the OPJU, PDF, manifest, sample parameters and logs.
- Installer extraction was tested in a Chinese folder containing spaces: all 1,081 payload files matched the portable archive by SHA-256. Attempting installation into the existing folder was refused without altering the installed executable. The installed desktop app launched and calculated two synthetic spectra successfully.
- Deliberately selected an excessive k range in the installed UI: it displayed the cause and correction guidance. The Common k range action corrected the interval. An additional API check confirmed that validation errors now show the offending sample path directly in the location field.

## Boundaries / 验证边界

The above validates software behavior and agreement with the existing Hama executable. It does not independently establish the physical correctness of Hama, validate a scientific interpretation, or certify experimental data quality. Real Hama tests use synthetic data. No other Origin version, a clean Windows 10 installation, every corporate proxy, antivirus configuration, Unicode account name or disabled-8.3 filesystem has been exhaustively tested. When automatic path selection fails, the UI provides an explicit work-folder selection and detailed correction guidance.

Native Origin graphs use Origin's own style; their color limits should be adjusted consistently when making comparisons there. Standard exported numerical values are unnormalized. Installed Origin licensing and the availability of the official download are external requirements.

中文：以上测试确认软件运行、数值一致性和导出文件可读取，不等于实验结论或 Hama 算法的独立科学验证。所有数值验证使用合成数据。未穷尽测试所有 Windows/Origin 版本和网络环境。
