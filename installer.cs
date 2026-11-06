// MIT: application-owned, per-user installer. Does not contain or fetch Hama.
using System;
using System.IO;
using System.IO.Compression;
using System.Drawing;
using System.Windows.Forms;
using System.Reflection;
using System.Diagnostics;
using System.Threading.Tasks;

class Installer : Form {
    bool english = false;
    Label heading = new Label(), description = new Label(), status = new Label();
    Button language = new Button(), install = new Button();
    ProgressBar progress = new ProgressBar();
    CheckBox shortcut = new CheckBox();
    bool installing = false;
    string target = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "EXAFS Wavelet Studio 2.0.0");

    string T(string zh, string en) { return english ? en : zh; }
    void Texts() {
        heading.Text = T("安装 EXAFS Wavelet Studio", "Install EXAFS Wavelet Studio");
        description.Text = T("为当前用户安装，无需管理员权限。\nHama 不包含在安装包中；启动后可一键配置。", "Install for the current user; no administrator required.\nHama is not bundled; configure it after launch.");
        language.Text = english ? "中文" : "English";
        install.Text = T("安装并启动", "Install & launch");
        shortcut.Text = T("创建桌面快捷方式", "Create desktop shortcut");
        if (!installing) status.Text = target;
    }
    Installer() {
        Text = "EXAFS Wavelet Studio 2.0.0 Setup";
        ClientSize = new Size(620, 315); StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false;
        Font = new Font("Microsoft YaHei UI", 10);
        heading.SetBounds(25, 25, 470, 35); heading.Font = new Font(Font.FontFamily, 15, FontStyle.Bold);
        language.SetBounds(505, 25, 90, 30);
        description.SetBounds(25, 78, 570, 65);
        shortcut.SetBounds(25, 150, 450, 25); shortcut.Checked = true;
        status.SetBounds(25, 185, 570, 50); status.AutoEllipsis = true;
        progress.SetBounds(25, 242, 390, 22);
        install.SetBounds(430, 235, 165, 42);
        Controls.AddRange(new Control[] {heading, language, description, shortcut, status, progress, install});
        language.Click += delegate { english = !english; Texts(); };
        FormClosing += delegate(object sender, FormClosingEventArgs e) { if (installing) e.Cancel = true; };
        install.Click += async delegate {
            installing = true; install.Enabled = false; language.Enabled = false; shortcut.Enabled = false;
            progress.Style = ProgressBarStyle.Marquee;
            status.Text = T("正在解压并安装，请稍候…", "Extracting and installing, please wait…");
            try {
                await Task.Run(() => InstallFiles(target));
                string executable = Path.Combine(target, "EXAFS_Wavelet_Studio.exe");
                if (shortcut.Checked) Shortcut(executable, Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory));
                Shortcut(executable, Environment.GetFolderPath(Environment.SpecialFolder.Programs));
                Process.Start(new ProcessStartInfo(executable) { WorkingDirectory = target, UseShellExecute = true });
                installing = false; Close();
            } catch (Exception ex) {
                installing = false; install.Enabled = true; language.Enabled = true; shortcut.Enabled = true;
                progress.Style = ProgressBarStyle.Blocks;
                status.Text = T("安装未完成。", "Installation did not complete.");
                MessageBox.Show(T("位置：", "Where: ") + target + "\n\n" + T("原因：", "Why: ") + ex.Message + "\n\n" +
                    T("请关闭正在运行的软件，检查磁盘空间与目录权限。也可以完整解压便携版后直接运行。已有文件不会被覆盖。", "Close the running application and check disk space and folder permissions. Alternatively extract the complete portable ZIP. Existing files are not overwritten."), Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        };
        Texts();
    }
    static void Shortcut(string exe, string folder) {
        Directory.CreateDirectory(folder);
        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
        dynamic link = shell.CreateShortcut(Path.Combine(folder, "EXAFS Wavelet Studio 2.lnk"));
        link.TargetPath = exe; link.WorkingDirectory = Path.GetDirectoryName(exe); link.IconLocation = exe;
        link.Description = "EXAFS Wavelet Studio 2 - bilingual local wavelet analysis"; link.Save();
    }
    static void InstallFiles(string destination) {
        destination = Path.GetFullPath(destination);
        if (Directory.Exists(destination)) throw new IOException("Target folder already exists / 目标目录已存在。请使用已安装版本，或将旧目录另行备份后再安装。");
        string parent = Path.GetDirectoryName(destination);
        Directory.CreateDirectory(parent);
        string staging = Path.Combine(parent, "EXAFS_install_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(staging);
        try {
            using (Stream stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
            using (ZipArchive zip = new ZipArchive(stream, ZipArchiveMode.Read)) {
                foreach (ZipArchiveEntry entry in zip.Entries) {
                    string output = Path.GetFullPath(Path.Combine(staging, entry.FullName));
                    if (!output.StartsWith(staging + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new IOException("Invalid archive path");
                    if (String.IsNullOrEmpty(entry.Name)) { Directory.CreateDirectory(output); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(output));
                    entry.ExtractToFile(output, false);
                }
            }
            if (!File.Exists(Path.Combine(staging, "EXAFS_Wavelet_Studio.exe"))) throw new IOException("Incomplete application package");
            Directory.Move(staging, destination);
        } finally {
            if (Directory.Exists(staging) && Path.GetFullPath(staging).StartsWith(parent + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) Directory.Delete(staging, true);
        }
    }
    [STAThread] static int Main(string[] args) {
        if (args.Length == 2 && args[0] == "--test-install") {
            try { InstallFiles(args[1]); return 0; } catch { return 1; }
        }
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new Installer()); return 0;
    }
}
