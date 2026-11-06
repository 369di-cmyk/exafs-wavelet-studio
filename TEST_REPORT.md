# Verification report / 测试记录

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
