# EXAFS Wavelet Studio

[中文说明](README.zh-CN.md) · English

A bilingual Windows desktop interface for Hama wavelet-transform EXAFS analysis, with an official shadcn/ui interface, local processing, actionable diagnostics and selectable scientific exports.

**Hama is external.** This repository and its releases do not contain Hama, its original Wgnuplot executable, its manual or model files. The MIT license covers this application's own code, not Hama or other third-party components.

## Download v2.0.0

- **[Windows installer (recommended)](https://github.com/369di-cmyk/exafs-wavelet-studio/releases/download/v2.0.0/EXAFS_Wavelet_Studio_2.0.0_Setup.exe)**
- [Windows portable ZIP](https://github.com/369di-cmyk/exafs-wavelet-studio/releases/download/v2.0.0/EXAFS_Wavelet_Studio_2.0.0_Windows.zip) · [Source ZIP](https://github.com/369di-cmyk/exafs-wavelet-studio/releases/download/v2.0.0/EXAFS_Wavelet_Studio_2.0.0_Source.zip)
- [Release notes and all downloads](https://github.com/369di-cmyk/exafs-wavelet-studio/releases/tag/v2.0.0)

After installation, download or import Hama from the Hama engine tab. Native Origin project export requires a locally installed and activated Origin.

## Quick start

1. Run the Windows installer, or extract the complete portable ZIP and open `EXAFS_Wavelet_Studio.exe`.
2. Open **Hama engine → Download & configure**. Alternatively, import the official `hama_1.zip`, `hama_fortran.exe`, or its folder. The app verifies and copies the supported engine into your local application cache. No administrator account is required by the installer.
3. Import TXT/DAT/CHI/CSV files containing **k (Å⁻¹) and χ(k)**, or load the clearly marked synthetic demo.
4. Check columns, existing input weighting and measured k bounds, then **Analyze**.
5. Select **Export**, choose one or several formats and select a destination. Each export creates a new timestamped directory.

Windows 10/11 x64, .NET Framework 4.8 and Microsoft Edge WebView2 Runtime are required. They are normally present on current Windows installations. If the window cannot start, the launcher explains the WebView2 requirement. Get WebView2 from [Microsoft](https://developer.microsoft.com/microsoft-edge/webview2/). Python and Node.js are not needed by end users of the packaged app. After Hama has been configured, analysis and ordinary exports work offline. Native OPJU additionally requires working, activated Origin 2018 or newer; tested locally with Origin 2021. Other formats do not require Origin.

## Official Hama sources

- [Hama homepage and authors' instructions](https://www.esrf.fr/UsersAndScience/Experiments/CRG/BM20/Software/Wavelets/HAMA)
- [Official Hama ZIP download](https://www.esrf.fr/files/live/sites/www/files/UsersAndScience/Experiments/CRG/BM20/Software/Wavelets/HAMA/hama_1.zip?download=1)
- Authors identified on the official page: Harald Funke and Marina Chukalina. Follow their documentation for scientific citation.

The supported `hama_fortran.exe` SHA-256 is `f8fa901ca98bee23113d88e9864ed64ece6aa0c9982d1d6a9a4d360e07f8b054`. A changed or damaged executable is not run. Official download availability depends on ESRF and your network; browser download plus import remains available if automatic download is blocked. This app does not mirror or relicense the engine.

## What the compatibility layer does

The official page explicitly requires equidistant sampling. The legacy program also uses files in its current working directory. Its public page does not explicitly state a universal Chinese-path ban.

For every job the app creates a short, writable ASCII directory without spaces; copies the verified engine and prepared input into it; supplies short relative filenames; runs with that directory as the current directory; and cleans it afterwards. Input and output paths may contain Unicode and spaces and may be on different drives. Originals are not edited. If Windows cannot provide a suitable directory, the error explains how to select an ASCII work folder. A small **application-owned** no-op plotting helper handles the legacy plotting invocation; the plots are rendered by Matplotlib. It is not original Wgnuplot.

The app validates finite values, increasing k, column choice, weights, ranges and uniform sampling before running. Linear resampling is opt-in and recorded. No extrapolation is performed. This adapter accepts 20–801 points per selected interval and up to 8 samples per batch; these are adapter limits, not claimed universal Hama limits. Cancellation and timeout stop only the owned job's process tree. The window remains open while an export/install finishes; closing during computation requests cancellation, then close again once stopped.

## Exports

| Option | Contents | Needs Origin? |
|---|---|---|
| PNG / TIFF / SVG | Individual WT maps and comparison; 150/300/600 DPI where applicable | No |
| PDF | Multipage WT maps, weighted signals and parameter/interpretation notes | No |
| TXT / CSV | Prepared k, χ(k), weighted signal; measured-domain WT XYZ | No |
| Excel `.xlsx` | Overview, per-sample signal sheet, R-by-k WT matrix, metadata | No |
| Origin XYZ | Three-column text for Origin import | No |
| Origin `.opju` | Real native project with signal worksheets, WT matrices and editable native heatmaps | **Yes** |
| NPZ | Lossless numerical arrays for Python | No |
| Full Hama grid | Raw extended grid, including k outside the measured interval | No |

Parameters, original Hama run logs and `export_manifest.json` accompany every export. Partial format failures are explicitly reported; successful formats remain available. No fake OPJU is created. The Origin exporter starts a separate COM instance and does not attach to or overwrite an already-open user project. Native Origin graph styling may differ from the app; adjust native graph color ranges consistently for cross-sample comparison. Numeric exports always contain raw, unnormalized values. Figure exports follow the selected palette and normalization; individual raw-intensity figures share the batch maximum. SVG keeps editable labels but rasterizes the dense heatmap.

## Scientific interpretation

Input must already be background-subtracted χ(k); this app is not an Athena μ(E)-processing replacement. Set **existing input k weight** correctly to avoid double weighting. R is **not phase corrected**, and WT peaks are not exact bond lengths or standalone evidence of elemental identity, oxidation state or coordination number. Compare standards and EXAFS fits. Keep preprocessing, wavelet parameters, bounds, weights and color scale consistent. Per-sample normalization is for shape, not absolute intensity. Finite-range boundary features and extended grids are not new experimental information. Built-in demo files are synthetic.

## Troubleshooting

Errors show **where**, **why**, **how to fix**, an error code and expandable raw details in either language. Copy diagnostics locally when needed; review private paths before sharing.

| Problem | Correction |
|---|---|
| Download blocked / HTTP 403 | Open the official download in a browser, then import the ZIP. Check your network/proxy; existing valid engine is retained. |
| Engine verification failed | Redownload the official package. A new upstream binary requires adapter validation; do not bypass the hash check. |
| Non-uniform k | Check the data, then explicitly enable linear resampling or re-export uniform k upstream. |
| Range exceeds a sample | Use Common k range or choose bounds inside every sample. |
| Invalid row / missing cell | Fix the reported physical line; keep consistent column counts and delimiters. |
| Work directory unavailable | Select a writable short ASCII folder, e.g. `D:\EXAFSWork`. |
| OPJU unavailable / failed | Install/activate compatible Origin, dismiss its license dialog and restart. PDF, Excel and XYZ are independent alternatives. |
| Export denied | Close a locked file, check disk space and choose a writable destination. |

Local configuration/engine cache: `%LOCALAPPDATA%\EXAFSWaveletStudio`. No spectra or diagnostics are automatically uploaded. Only the explicit official-download button or external-link buttons use the network.

The installer installs for the current user and does not register a Windows Installed Apps uninstaller. To remove the app, close it, then delete its installation folder and corresponding desktop/Start Menu shortcuts. This preserves configuration, the Hama cache, and separately saved results. Delete the cache folder above separately only if you also want to remove those settings and engine files. Install upgrades into a new version folder; the installer refuses to overwrite existing folders.

## Development and testing

Requires Python 3.12 x64, Node.js 24 LTS/npm, and Windows for the desktop/Hama/Origin integration.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd frontend
npm ci
npm run lint
npm run build
cd ..
.\scripts\build_helper.ps1
.\.venv\Scripts\python.exe app.py
```

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Optional real-engine and local Origin tests, after configuring Hama:
$env:RUN_HAMA_TESTS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# Compile portable distribution and installer; does NOT download/bundle Hama:
.\scripts\build.ps1
```

Fixtures are synthetic input and numerical reference data from a prior direct Hama run, not Hama code. CI tests validation/exports and builds the interface without downloading Hama. See [test report](TEST_REPORT.md) for the actual local verification and limits. See [release notes](CHANGELOG.md), [third-party notices](THIRD_PARTY_NOTICES.md) and [MIT license](LICENSE).

## Publishing this project

Use the prepared source archive or the source allowlist in `scripts/package_release.py`. Do not publish the old v1 package, local engine cache, personal experimental data, `test_artifacts`, virtual environments, or unrelated projects. Third-party code retains its own licenses and notices. This is an independent interface project, not an official ESRF or OriginLab product.
