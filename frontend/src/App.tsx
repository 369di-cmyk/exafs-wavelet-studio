import { TutorialGuide } from "@/TutorialGuide"
import { useCallback, useEffect, useRef, useState } from "react"
import {
  Activity,
  ArrowDownToLine,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FlaskConical,
  FolderOpen,
  Gauge,
  Info,
  Languages,
  LoaderCircle,
  Play,
  Settings2,
  ShieldCheck,
  Square,
  Trash2,
  Waves,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Field,
  FieldLabel,
  FieldDescription,
  FieldGroup,
  FieldSet,
  FieldLegend,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
  EmptyDescription,
} from "@/components/ui/empty"
import { Separator } from "@/components/ui/separator"
import { Progress } from "@/components/ui/progress"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"

type Language = "zh" | "en"
type Issue = {
  code: string
  where: string
  detail: string
  zh: { title: string; why: string; fix: string }
  en: { title: string; why: string; fix: string }
}
type State = {
  version: string
  engine: { ready: boolean; path: string; sha256: string }
  origin: boolean
  language: Language
  revision: number
  busy: boolean
  phase: string
  done: number
  total: number
  current: string
  elapsed: number
  errors: Issue[]
  export: { folder: string; completed: string[]; errors: Issue[] } | null
  download?: { stage: string; attempt?: number; attempts?: number; received?: number; total?: number } | null
  inputs: { name: string; path: string; rows: number; cols: number }[]
  results: { name: string; metadata: Record<string, unknown> }[]
}
type Reply<T> = { ok: boolean; data: T; error: Issue }
declare global {
  interface Window {
    pywebview?: {
      api: Record<string, (...args: unknown[]) => Promise<Reply<unknown>>>
    }
  }
}
const defaults = {
  k_col: 0,
  chi_col: 1,
  input_weight: 0,
  weight: 2,
  kmin: 2,
  kmax: 12,
  rmin: 0,
  rmax: 5,
  wavelet: "Morlet",
  kappa: 15,
  sigma: 1,
  cauchy_n: 50,
  resample: false,
}
type Settings = typeof defaults
const formats = [
  "png",
  "tiff",
  "svg",
  "pdf",
  "txt",
  "csv",
  "xlsx",
  "origin_xyz",
  "opju",
  "npz",
  "raw",
]

export default function App() {
  const [lang, setLang] = useState<Language>("zh")
  const t = (zh: string, en: string) => (lang === "zh" ? zh : en)
  const [state, setState] = useState<State | null>(null)
  const [tab, setTab] = useState("studio")
  const [settings, setSettings] = useState<Settings>(defaults)
  const [error, setError] = useState<Issue | null>(null)
  const [copied, setCopied] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const [selected, setSelected] = useState(["png", "pdf", "xlsx", "txt"])
  const [dpi, setDpi] = useState("300")
  const [cmap, setCmap] = useState("viridis")
  const [normal, setNormal] = useState(false)
  const [view, setView] = useState("wavelet")
  const [sample, setSample] = useState("-1")
  const [img, setImg] = useState("")
  const [rendering, setRendering] = useState(false)
  const [environment, setEnvironment] = useState<{ work: string } | null>(null)
  const [ready, setReady] = useState(false)
  const [bridgeFailed, setBridgeFailed] = useState(false)
  const [pending, setPending] = useState(false)
  const lastErrors = useRef(""),
    initial = useRef(true)
  const busy = !!state?.busy || pending,
    hasResults = !!state?.results.length
  const update = <K extends keyof Settings>(key: K, value: Settings[K]) =>
    setSettings((old) => ({ ...old, [key]: value }))
  const call = useCallback(
    async <T,>(method: string, ...args: unknown[]): Promise<T | undefined> => {
      try {
        const api = window.pywebview?.api
        if (!api) return
        const response = (await api[method](...args)) as Reply<T>
        if (!response.ok) {
          setCopied(false)
          setError(response.error)
          return
        }
        return response.data
      } catch (e) {
        setError({
          code: "bridge",
          where: method,
          detail: String(e),
          zh: {
            title: "本地程序连接中断",
            why: "窗口与后台之间的调用未完成。",
            fix: "等待当前操作完成；如仍无响应，请重新打开软件。",
          },
          en: {
            title: "Local connection interrupted",
            why: "The desktop bridge did not complete the call.",
            fix: "Wait for the current task. If unresponsive, restart the application.",
          },
        })
      }
    },
    []
  )
  const refresh = useCallback(async () => {
    const next = await call<State>("get_state")
    if (next) {
      setState(next)
      if (initial.current) {
        setLang(next.language)
        initial.current = false
      }
      const key = JSON.stringify(next.errors)
      if (next.errors.length && key !== lastErrors.current) {
        setError(next.errors[0])
        setCopied(false)
      }
      lastErrors.current = key
    }
  }, [call])
  const act = async (method: string, ...args: unknown[]) => {
    setPending(true)
    try {
      await call(method, ...args)
      await refresh()
    } finally {
      setPending(false)
    }
  }
  useEffect(() => {
    const check = () => {
      if (window.pywebview?.api) {
        setReady(true)
        setBridgeFailed(false)
      }
    }
    check()
    window.addEventListener("pywebviewready", check)
    const timer = setInterval(check, 500)
    const timeout = setTimeout(() => {
      if (!window.pywebview?.api) setBridgeFailed(true)
    }, 12000)
    return () => {
      window.removeEventListener("pywebviewready", check)
      clearInterval(timer)
      clearTimeout(timeout)
    }
  }, [])
  useEffect(() => {
    if (!ready) return
    const first = setTimeout(() => void refresh(), 0)
    const id = setInterval(() => void refresh(), 700)
    return () => {
      clearTimeout(first)
      clearInterval(id)
    }
  }, [ready, refresh])
  useEffect(() => {
    document.documentElement.lang = lang === "zh" ? "zh-CN" : "en"
  }, [lang])
  useEffect(() => {
    let active = true
    const timer = setTimeout(() => {
      if (!state?.results.length) {
        setImg("")
        return
      }
      setRendering(true)
      void call<string>(
        "get_preview",
        Number(sample),
        cmap,
        normal,
        view === "signal"
      ).then((value) => {
        if (active) {
          setImg(value || "")
          setRendering(false)
        }
      })
    }, 80)
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [state?.revision, state?.results.length, sample, cmap, normal, view, call])
  const language = (v: string) => {
    if (v) {
      setLang(v as Language)
      void call("set_language", v)
    }
  }
  const numeric = (
    key:
      | "kmin"
      | "kmax"
      | "rmin"
      | "rmax"
      | "kappa"
      | "sigma"
      | "cauchy_n"
      | "k_col"
      | "chi_col",
    label: string,
    step = 0.1
  ) => {
    const col = key === "k_col" || key === "chi_col"
    return (
      <Field>
        <FieldLabel htmlFor={key}>{label}</FieldLabel>
        <Input
          id={key}
          type="number"
          step={step}
          value={
            Number.isNaN(settings[key]) ? "" : settings[key] + (col ? 1 : 0)
          }
          disabled={busy}
          onChange={(e) =>
            update(
              key,
              e.target.value === ""
                ? NaN
                : Number(e.target.value) - (col ? 1 : 0)
            )
          }
        />
      </Field>
    )
  }
  const dropdown = (
    label: string,
    value: string,
    change: (v: string) => void,
    options: { value: string; label: string }[],
    disabled = false
  ) => (
    <Field>
      <FieldLabel>{label}</FieldLabel>
      <Select value={value} onValueChange={change} disabled={disabled}>
        <SelectTrigger aria-label={label} className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectGroup>
            {options.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  )
  const title = (f: string) =>
    f === "origin_xyz"
      ? "Origin XYZ"
      : f === "opju"
        ? "Origin .opju"
        : f === "raw"
          ? t("Hama 完整网格", "Full Hama grid")
          : f.toUpperCase()
  const description = (f: string) =>
    ({
      png: t("通用图片", "Standard image"),
      tiff: t("高分辨率图片", "High-resolution image"),
      svg: t("可编辑标注，热图为位图", "Editable labels; rasterized heatmap"),
      pdf: t("多页图表与参数报告", "Multipage figures & parameters"),
      txt: t("信号 + 小波 XYZ 文本", "Signal + WT XYZ text"),
      csv: t("信号 + 小波 XYZ 表格", "Signal + WT XYZ tables"),
      xlsx: t("Excel 信号、矩阵、参数", "Excel signals, matrices & parameters"),
      origin_xyz: t(
        "可导入 Origin，无需安装 Origin",
        "Importable data; no Origin required"
      ),
      opju: t(
        "原生项目及热图，需要 Origin",
        "Native project & heatmaps; needs Origin"
      ),
      npz: t("无损数组，供 Python 使用", "Lossless arrays for Python"),
      raw: t(
        "含扩展网格，不是新增实测数据",
        "Extended grid; not new measured data"
      ),
    })[f]
  const notes = [
    [
      t("输入数据", "Input data"),
      t(
        "先用 Athena 等软件提取 χ(k)，导入 k（Å⁻¹）与 χ(k)，不要直接导入 μ(E)。支持空格、Tab、逗号分隔；Excel 输入请先另存为 CSV。",
        "First extract χ(k) in Athena or equivalent. Import k (Å⁻¹) and χ(k), not μ(E). Spaces, tabs and commas are supported; save Excel input as CSV first."
      ),
    ],
    [
      t("权重与采样", "Weighting & sampling"),
      t(
        "若输入已为 k²χ(k)，输入权重选 2，避免重复加权。Hama 要求等间隔 k；可主动允许线性重采样，不外推，并记录处理过程。每批最多 8 个样品，每个分析区间 20–801 点。",
        "For k²χ(k), choose input weight 2 to avoid double weighting. Hama requires uniform k; optional linear resampling never extrapolates and is recorded. Up to 8 samples, with 20–801 points per analysis interval."
      ),
    ],
    [
      t("如何解读热图", "Interpreting heatmaps"),
      t(
        "横轴为 k，纵轴为未作相位校正的 R，颜色为小波强度。不同 k 响应可帮助区分相近 R 处的散射贡献。R 峰位不是精确键长；不能单凭热图确定元素、价态或配位数，应结合标准样品和 EXAFS 拟合。",
        "Horizontal k and uncorrected vertical R locate scattering features; color shows WT magnitude. Different k responses can separate contributions at similar R. R peaks are not exact bond lengths; heatmaps alone cannot establish elements, valence or coordination numbers. Use standards and EXAFS fitting."
      ),
    ],
    [
      t("统一比较条件", "Consistent comparisons"),
      t(
        "不同样品应统一预处理、小波参数、k 权重、k/R 区间和色标。各样品分别归一化仅适合比较形状，不能比较绝对强度。有限区间的边界伪影不应当成新结构。",
        "Match preprocessing, wavelet parameters, k weight, k/R bounds and color scale. Per-sample normalization compares shape, not absolute intensity. Finite-range boundary artifacts are not new structures."
      ),
    ],
    [
      t("导出与 Origin", "Exports & Origin"),
      t(
        "PDF、图片、TXT、CSV、Excel 和 Origin XYZ 均不需要 Origin。真正 .opju 需要已安装并激活的 Origin 2018 或更新版；使用独立实例创建，不连接当前打开的项目。每次导出建立新目录，附参数、日志和清单。单个格式失败会明确报告。",
        "PDF, images, TXT, CSV, Excel and Origin XYZ work without Origin. Real .opju needs activated Origin 2018 or newer; a separate instance creates it without attaching to your open project. Each export uses a new directory with parameters, logs and a manifest; individual failures are reported."
      ),
    ],
    [
      t("演示与延伸网格", "Demo & extended grids"),
      t(
        "内置演示是合成信号，不是实验谱。默认视图与标准数值结果裁剪到实测 k 区间；“Hama 完整网格”另含延伸部分，不能将其当作新增实测信息。",
        "The demo is synthetic, not experimental. Standard plots and numbers are cropped to measured k. Full Hama grids additionally contain an extended domain, which is not extra measured information."
      ),
    ],
  ]
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card px-7 py-4">
        <div className="mx-auto flex max-w-[1560px] items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Waves className="size-6" />
            </div>
            <div>
              <div className="font-semibold tracking-tight">
                EXAFS{" "}
                <span className="font-normal text-muted-foreground">
                  Wavelet Studio
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                {t("让小波分析更直观", "A clearer view of your EXAFS")}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline">v{state?.version || "2.1.0"}</Badge>
            <Languages className="size-4 text-muted-foreground" />
            <ToggleGroup
              type="single"
              variant="outline"
              spacing={0}
              value={lang}
              onValueChange={language}
              aria-label="Language / 语言"
            >
              <ToggleGroupItem value="zh">中文</ToggleGroupItem>
              <ToggleGroupItem value="en">English</ToggleGroupItem>
            </ToggleGroup>
          </div>
        </div>
      </header>
      <main className="mx-auto flex max-w-[1560px] flex-col gap-5 px-7 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-medium tracking-widest text-primary">
              WAVELET TRANSFORM · EXAFS
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">
              {t(
                "从信号到局域结构线索",
                "From signal to local-structure insight"
              )}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {t(
                "导入 χ(k)，在 k–R 空间观察散射特征，再按需导出。",
                "Import χ(k), explore scattering features in k–R space, and export what you need."
              )}
            </p>
          </div>
          <Badge variant="secondary">
            <ShieldCheck />
            {state?.engine.ready
              ? t("Hama 已校验 · 本地计算", "Hama verified · local processing")
              : t("首次使用：请配置 Hama", "First run: configure Hama")}
          </Badge>
        </div>
        {!ready && (
          <Alert>
            <LoaderCircle />
            <AlertTitle>
              {bridgeFailed
                ? t("未连接到桌面程序", "Desktop connection unavailable")
                : t("正在连接本地程序…", "Connecting to local application…")}
            </AlertTitle>
            <AlertDescription>
              {bridgeFailed
                ? t(
                    "请通过 EXAFS Wavelet Studio.exe 打开软件。独立浏览器页面无法运行 Hama。",
                    "Launch EXAFS Wavelet Studio.exe. A standalone browser page cannot run Hama."
                  )
                : t(
                    "数据在本机处理，不会上传。",
                    "Your data stays on this computer."
                  )}
            </AlertDescription>
          </Alert>
        )}
        <Tabs value={tab} onValueChange={setTab}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <TabsList>
              <TabsTrigger value="studio">
                <Activity />
                {t("分析工作台", "Studio")}
              </TabsTrigger>
              <TabsTrigger value="engine">
                <Settings2 />
                {t("Hama 引擎", "Hama engine")}
              </TabsTrigger>
              <TabsTrigger value="guide">
                <CircleHelp />
                {t("使用说明", "Guide")}
              </TabsTrigger>
            </TabsList>
            <span className="text-xs text-muted-foreground">
              01 {t("配置引擎", "Engine")} / 02 {t("分析数据", "Analyze")} / 03{" "}
              {t("导出结果", "Export")}
            </span>
          </div>
          <TabsContent value="studio">
            <div className="grid items-start gap-5 lg:grid-cols-[300px_minmax(0,1fr)]">
              <aside className="flex flex-col gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle>{t("分析参数", "Analysis settings")}</CardTitle>
                    <CardDescription>
                      {t(
                        "同一批样品使用相同参数",
                        "One parameter set for the whole batch"
                      )}
                    </CardDescription>
                    <CardAction>
                      <Gauge className="size-5 text-muted-foreground" />
                    </CardAction>
                  </CardHeader>
                  <CardContent>
                    <FieldGroup className="gap-3">
                      <FieldGroup className="grid grid-cols-2 gap-3">
                        {numeric("kmin", t("k 最小值", "k min"))}
                        {numeric("kmax", t("k 最大值", "k max"))}
                      </FieldGroup>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!state?.inputs.length || busy}
                        onClick={async () => {
                          const r = await call<{ kmin: number; kmax: number }>(
                            "common_range",
                            settings.k_col
                          )
                          if (r) setSettings((s) => ({ ...s, ...r }))
                        }}
                      >
                        {t("使用共同 k 范围", "Common k range")}
                      </Button>
                      <FieldGroup className="grid grid-cols-2 gap-3">
                        {numeric("rmin", t("R 最小值 (Å)", "R min (Å)"))}
                        {numeric("rmax", t("R 最大值 (Å)", "R max (Å)"))}
                      </FieldGroup>
                      <Field>
                        <FieldLabel>{t("小波类型", "Wavelet")}</FieldLabel>
                        <ToggleGroup
                          type="single"
                          variant="outline"
                          spacing={0}
                          value={settings.wavelet}
                          onValueChange={(v) => v && update("wavelet", v)}
                          disabled={busy}
                        >
                          <ToggleGroupItem value="Morlet">
                            Morlet
                          </ToggleGroupItem>
                          <ToggleGroupItem value="Cauchy">
                            Cauchy
                          </ToggleGroupItem>
                        </ToggleGroup>
                      </Field>
                      {settings.wavelet === "Morlet" ? (
                        <FieldGroup className="grid grid-cols-2 gap-3">
                          {numeric("kappa", "κ (kappa)", 1)}
                          {numeric("sigma", "σ (sigma)")}
                        </FieldGroup>
                      ) : (
                        numeric(
                          "cauchy_n",
                          t("Cauchy 阶数 n", "Cauchy order n"),
                          1
                        )
                      )}
                      {dropdown(
                        t("计算 k 权重", "Calculation k weight"),
                        String(settings.weight),
                        (v) => update("weight", Number(v)),
                        [0, 1, 2, 3].map((v) => ({
                          value: String(v),
                          label: `k${["⁰", "¹", "²", "³"][v]} χ(k)`,
                        })),
                        busy
                      )}
                    </FieldGroup>
                    <Accordion type="single" collapsible className="mt-4">
                      <AccordionItem value="input">
                        <AccordionTrigger>
                          {t("数据列与预处理", "Columns & preparation")}
                        </AccordionTrigger>
                        <AccordionContent>
                          <FieldGroup className="pt-2">
                            <FieldGroup className="grid grid-cols-2 gap-3">
                              {numeric("k_col", t("k 列号", "k column"), 1)}
                              {numeric(
                                "chi_col",
                                t("信号列号", "Signal column"),
                                1
                              )}
                            </FieldGroup>
                            {dropdown(
                              t("文件已有 k 权重", "Existing input k weight"),
                              String(settings.input_weight),
                              (v) => update("input_weight", Number(v)),
                              [0, 1, 2, 3].map((v) => ({
                                value: String(v),
                                label:
                                  v === 0
                                    ? t(
                                        "0 — 未加权 χ(k)",
                                        "0 — unweighted χ(k)"
                                      )
                                    : String(v),
                              })),
                              busy
                            )}
                            <Field orientation="horizontal">
                              <Checkbox
                                id="resample"
                                checked={settings.resample}
                                disabled={busy}
                                onCheckedChange={(v) =>
                                  update("resample", v === true)
                                }
                              />
                              <FieldLabel htmlFor="resample">
                                {t("允许线性重采样", "Allow linear resampling")}
                              </FieldLabel>
                            </Field>
                            <FieldDescription>
                              {t(
                                "仅对非等间隔 k 生效；不外推。k 单位：Å⁻¹。",
                                "Only for non-uniform k; no extrapolation. k unit: Å⁻¹."
                              )}
                            </FieldDescription>
                          </FieldGroup>
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </CardContent>
                  <CardFooter className="justify-between gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busy}
                      onClick={() => setSettings(defaults)}
                    >
                      {t("恢复默认", "Reset")}
                    </Button>
                    <Button
                      disabled={
                        !state?.inputs.length || !state?.engine.ready || busy
                      }
                      onClick={() => {
                        setSample("-1")
                        void act("analyze", settings)
                      }}
                    >
                      <Play data-icon="inline-start" />
                      {t("开始分析", "Analyze")}
                    </Button>
                  </CardFooter>
                </Card>
                <Alert>
                  <Info />
                  <AlertTitle>{t("分析前检查", "Before you run")}</AlertTitle>
                  <AlertDescription>
                    {t(
                      "输入应为 k 与 χ(k)，不是能量和 μ(E)。信号若已乘过 k²，请将输入权重设为 2。",
                      "Use k and χ(k), not energy and μ(E). For k²χ(k), select existing input weight 2."
                    )}
                  </AlertDescription>
                </Alert>
              </aside>
              <div className="flex min-w-0 flex-col gap-5">
                {hasResults &&
                  JSON.stringify(settings) !==
                    JSON.stringify(state?.results[0].metadata.settings) && (
                    <Alert>
                      <Info />
                      <AlertTitle>
                        {t("参数已改变", "Settings have changed")}
                      </AlertTitle>
                      <AlertDescription>
                        {t(
                          "当前图和导出仍对应上次计算，请重新分析使新参数生效。",
                          "Figures and exports still represent the last run. Analyze again to apply the new settings."
                        )}
                      </AlertDescription>
                    </Alert>
                  )}
                {!state?.engine.ready && (
                  <Alert>
                    <Download />
                    <AlertTitle>
                      {t(
                        "先配置 Hama，之后可离线分析",
                        "Configure Hama once, then work offline"
                      )}
                    </AlertTitle>
                    <AlertDescription className="flex items-center justify-between gap-3">
                      <span>
                        {t(
                          "从 ESRF 官网下载，或导入已有文件。",
                          "Download from ESRF or import an existing file."
                        )}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setTab("engine")}
                      >
                        {t("配置 Hama", "Set up Hama")}
                        <ChevronRight data-icon="inline-end" />
                      </Button>
                    </AlertDescription>
                  </Alert>
                )}
                <Card>
                  <CardHeader>
                    <CardTitle>
                      {t("样品数据", "Samples")} · {state?.inputs.length || 0}/8
                    </CardTitle>
                    <CardDescription>
                      {t(
                        "CHIK / CHI / XDI / TXT / DAT / CSV · 支持中文路径与多文件",
                        "CHIK / CHI / XDI / TXT / DAT / CSV · Unicode paths & multiple files"
                      )}
                    </CardDescription>
                    <CardAction>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={busy || !ready}
                          onClick={() => void act("load_demo")}
                        >
                          <FlaskConical data-icon="inline-start" />
                          {t("载入演示", "Demo")}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy || !ready}
                          onClick={() => void act("choose_data")}
                        >
                          <FolderOpen data-icon="inline-start" />
                          {t("导入数据", "Import")}
                        </Button>
                      </div>
                    </CardAction>
                  </CardHeader>
                  <CardContent>
                    {state?.inputs.length ? (
                      <div className="flex flex-col gap-2">
                        {state.inputs.map((f, i) => (
                          <div
                            key={f.path}
                            className="flex min-w-0 items-center gap-3 rounded-lg border px-3 py-2"
                          >
                            <FileText className="size-4 shrink-0 text-primary" />
                            <div className="min-w-0 flex-1">
                              <div
                                className="truncate font-medium"
                                title={f.path}
                              >
                                {f.name}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {f.rows} {t("行", "rows")} · {f.cols}{" "}
                                {t("列", "columns")}
                                {f.name.includes("SYNTHETIC")
                                  ? " · " +
                                    t(
                                      "合成演示，非实验数据",
                                      "Synthetic, not experimental"
                                    )
                                  : ""}
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              disabled={busy}
                              aria-label={t("移除 ", "Remove ") + f.name}
                              onClick={() => void act("remove_data", i)}
                            >
                              <Trash2 />
                            </Button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty className="py-6">
                        <EmptyHeader>
                          <EmptyMedia variant="icon">
                            <FolderOpen />
                          </EmptyMedia>
                          <EmptyTitle>
                            {t(
                              "导入第一组 χ(k) 数据",
                              "Add your first χ(k) dataset"
                            )}
                          </EmptyTitle>
                          <EmptyDescription>
                            {t(
                              "可多选样品统一比较，也可以先体验合成演示。",
                              "Compare multiple samples or try the synthetic demo."
                            )}
                          </EmptyDescription>
                        </EmptyHeader>
                      </Empty>
                    )}
                  </CardContent>
                  <CardFooter>
                    <span className="text-xs text-muted-foreground">
                      {t(
                        "原始文件保持不变 · 所选区间需要 20–801 个有效点",
                        "Original files are preserved · 20–801 valid points per interval"
                      )}
                    </span>
                  </CardFooter>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>{t("小波分析视图", "Wavelet view")}</CardTitle>
                    <CardDescription>
                      {t(
                        "仅显示实测 k 区间 · R 未作相位校正",
                        "Measured k only · R is not phase corrected"
                      )}
                    </CardDescription>
                    <CardAction>
                      <Button
                        disabled={!hasResults || busy}
                        onClick={() => setExportOpen(true)}
                      >
                        <ArrowDownToLine data-icon="inline-start" />
                        {t("导出结果", "Export")}
                      </Button>
                    </CardAction>
                  </CardHeader>
                  <CardContent>
                    {hasResults ? (
                      <div className="flex flex-col gap-4">
                        <FieldGroup className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                          {dropdown(t("样品", "Sample"), sample, setSample, [
                            {
                              value: "-1",
                              label: t("全部比较", "Compare all"),
                            },
                            ...(state?.results || []).map((r, i) => ({
                              value: String(i),
                              label: r.name,
                            })),
                          ])}
                          {dropdown(t("视图", "View"), view, setView, [
                            {
                              value: "wavelet",
                              label: t("小波热图", "WT heatmap"),
                            },
                            {
                              value: "signal",
                              label: t("加权信号", "Weighted signal"),
                            },
                          ])}
                          {dropdown(
                            t("配色", "Palette"),
                            cmap,
                            setCmap,
                            ["viridis", "turbo", "magma", "cividis"].map(
                              (v) => ({ value: v, label: v })
                            )
                          )}
                          {dropdown(
                            t("色标", "Color scale"),
                            normal ? "norm" : "raw",
                            (v) => setNormal(v === "norm"),
                            [
                              {
                                value: "raw",
                                label: t("统一原始强度", "Shared raw scale"),
                              },
                              {
                                value: "norm",
                                label: t(
                                  "各样品归一化",
                                  "Per-sample normalized"
                                ),
                              },
                            ]
                          )}
                        </FieldGroup>
                        {normal && (
                          <Alert>
                            <Info />
                            <AlertDescription>
                              {t(
                                "归一化只能比较形状；数值导出仍保留原始强度。",
                                "Normalization compares shape only; numeric exports retain raw intensity."
                              )}
                            </AlertDescription>
                          </Alert>
                        )}
                        <div className="relative min-h-48">
                          {rendering && (
                            <Badge
                              variant="secondary"
                              className="absolute top-2 right-2"
                            >
                              {t("绘图中…", "Rendering…")}
                            </Badge>
                          )}
                          {img && (
                            <img
                              src={img}
                              alt={t(
                                "EXAFS 小波变换结果",
                                "EXAFS wavelet transform results"
                              )}
                              className="h-auto w-full rounded-lg"
                            />
                          )}
                        </div>
                      </div>
                    ) : (
                      <Empty className="min-h-60">
                        <EmptyHeader>
                          <EmptyMedia variant="icon">
                            <Waves />
                          </EmptyMedia>
                          <EmptyTitle>
                            {t(
                              "在 k–R 空间发现更多",
                              "Explore your data in k–R space"
                            )}
                          </EmptyTitle>
                          <EmptyDescription>
                            {t(
                              "配置引擎并导入数据后，点击“开始分析”。散射特征将在这里呈现。",
                              "Configure the engine, import data and select Analyze. Scattering features will appear here."
                            )}
                          </EmptyDescription>
                        </EmptyHeader>
                        <Badge variant="outline">
                          Morlet · Cauchy · {t("统一色标", "Shared scale")}
                        </Badge>
                      </Empty>
                    )}
                  </CardContent>
                  <CardFooter className="justify-between gap-3">
                    <span className="text-xs text-muted-foreground">
                      {t(
                        "热图提供结构线索，不能单凭峰形确定元素或配位数。",
                        "Peaks alone do not establish element identity or coordination number."
                      )}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setTab("guide")}
                    >
                      <CircleHelp />
                      {t("如何解读", "Interpretation")}
                    </Button>
                  </CardFooter>
                </Card>
              </div>
            </div>
          </TabsContent>
          <TabsContent value="engine">
            <div className="grid gap-5 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>
                    {t("一键准备 Hama", "Set up Hama in one step")}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      "直接从 ESRF 官方分发页面获取",
                      "Obtain the engine directly from ESRF"
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-5">
                  <Alert>
                    <ShieldCheck />
                    <AlertTitle>
                      {state?.engine.ready
                        ? t(
                            "引擎已配置并通过校验",
                            "Engine configured and verified"
                          )
                        : t("本软件包不包含 Hama", "Hama is not bundled")}
                    </AlertTitle>
                    <AlertDescription>
                      {t(
                        "Hama 由原作者独立提供。本软件提供界面、参数检查和兼容处理。",
                        "Hama is provided separately by its authors. This app provides the interface, checks and compatibility layer."
                      )}
                    </AlertDescription>
                  </Alert>
                  <Button
                    size="lg"
                    disabled={busy || !ready}
                    onClick={() => void act("install_hama")}
                  >
                    <Download data-icon="inline-start" />
                    {state?.engine.ready ? t("检查已配置的 Hama", "Check configured Hama") : t("一键配置 Hama", "Set up Hama")}
                  </Button>
                  <p className="text-sm text-muted-foreground">
                    {t(
                      "先复用已校验的引擎，再检测下载文件夹；需要时从官网下载，失败自动重试（最多 3 次）。无需解压，也不用重复下载。",
                      "Reuse a verified engine or detect it in Downloads first. Otherwise download from ESRF with up to 3 attempts. No extraction or repeated download needed."
                    )}
                  </p>
                  {state?.download && (
                    <Alert aria-live="polite">
                      <Info />
                      <AlertTitle>{t("Hama 配置进度", "Hama setup progress")}</AlertTitle>
                      <AlertDescription>
                        <p>{({
                          checking: t("正在检查本机缓存和下载文件夹…", "Checking cache and Downloads…"),
                          cached: t("已通过校验，直接使用本机引擎，无需联网。", "Verified cached engine reused; no network needed."),
                          imported: t("已找到下载文件并导入，配置完成。", "Downloaded file found and imported. Setup complete."),
                          connecting: t("正在连接 ESRF 官网…", "Connecting to ESRF…"),
                          receiving: t("正在下载…", "Downloading…"),
                          retry: t("上次连接未完成，正在自动重试…", "Previous attempt failed; retrying…"),
                          attempt_failed: t("本次下载失败，正在检查下一步…", "Attempt failed; checking next step…"),
                          local_rejected: t("本机文件未通过校验，继续检查…", "Local file not verified; continuing…"),
                          verifying: t("下载完成，正在校验文件…", "Download complete; verifying…"),
                          complete: t("下载和校验完成，Hama 已就绪。", "Downloaded and verified. Hama is ready."),
                          failed: t("本次配置未完成，请查看下方具体原因和解决方法。", "Setup did not complete. See the error and corrective steps below."),
                        } as Record<string, string>)[state.download.stage]}</p>
                        {state.download.attempt && <p>{t("尝试", "Attempt")} {state.download.attempt} / {state.download.attempts}</p>}
                        {state.download.received !== undefined && <p>{Math.round(state.download.received / 1024)} KB{state.download.total ? ` / ${Math.round(state.download.total / 1024)} KB` : ""}</p>}
                        {state.download.stage === "receiving" && !!state.download.total && <Progress value={Math.min(100, (state.download.received || 0) * 100 / state.download.total)} />}
                        {busy && state.phase === "installing" && <Button variant="outline" onClick={() => void call("cancel")}>{t("取消配置", "Cancel setup")}</Button>}
                      </AlertDescription>
                    </Alert>
                  )}
                  <Separator />
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" disabled={busy || !ready} onClick={() => void act("install_hama", true)}>
                      <Download data-icon="inline-start" />
                      {t("检测下载并导入", "Detect download & import")}
                    </Button>
                    <Button
                      variant="outline"
                      disabled={busy || !ready}
                      onClick={() => void act("choose_hama", false)}
                    >
                      <FolderOpen data-icon="inline-start" />
                      {t("导入 ZIP / EXE", "Import ZIP / EXE")}
                    </Button>
                    <Button
                      variant="outline"
                      disabled={busy || !ready}
                      onClick={() => void act("choose_hama", true)}
                    >
                      {t("选择 Hama 文件夹", "Choose Hama folder")}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t(
                      "自动下载失败时：点下方官网下载链接 → 在浏览器完成下载 → 点“检测下载并导入”。如果另存到了其他文件夹，可手动选择 ZIP / EXE。",
                      "If automatic download fails: open the official link below → finish the browser download → Detect download & import. For files saved elsewhere, choose ZIP / EXE manually."
                    )}
                  </p>
                  {state?.engine.ready && (
                    <div className="rounded-lg bg-muted p-3 text-xs">
                      <p className="mb-2 font-medium">
                        {t("已配置位置", "Configured location")}
                      </p>
                      <p className="break-all text-muted-foreground">
                        {state.engine.path}
                      </p>
                      <p className="mt-3 break-all text-muted-foreground">
                        SHA-256: {state.engine.sha256}
                      </p>
                    </div>
                  )}
                </CardContent>
                <CardFooter className="flex-wrap gap-2">
                  <Button
                    variant="link"
                    onClick={() => void call("open_link", "home")}
                  >
                    {t("Hama 官方主页", "Hama homepage")}
                    <ExternalLink data-icon="inline-end" />
                  </Button>
                  <Button
                    variant="link"
                    onClick={() => void call("open_link", "download")}
                  >
                    {t("官网下载链接", "Official download")}
                    <ExternalLink data-icon="inline-end" />
                  </Button>
                </CardFooter>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>
                    {t(
                      "路径限制，交给软件处理",
                      "Let the app handle path restrictions"
                    )}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      "文件可留在你习惯的位置",
                      "Keep files in their original locations"
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-5">
                  {[
                    [
                      t(
                        "中文、空格、不同文件夹",
                        "Unicode, spaces, separate folders"
                      ),
                      t(
                        "每次计算自动建立短英文工作目录，将引擎和准备后的数据放在同一处，任务结束后清理。",
                        "Each job places the engine and prepared input together in a short ASCII directory, then cleans up afterwards."
                      ),
                    ],
                    [
                      t("无需原版绘图程序", "No legacy plotting dependency"),
                      t(
                        "图像由本软件生成。自有轻量辅助程序处理旧版绘图调用，不包含原版 Wgnuplot。",
                        "This app generates figures. Its own small helper handles legacy plot calls; original Wgnuplot is not included."
                      ),
                    ],
                    [
                      t("自动检查数据条件", "Automatic input validation"),
                      t(
                        "检查等间隔 k、递增顺序、无效值、权重与范围，并给出针对性的修改办法。",
                        "Checks uniform k, ordering, invalid values, weighting and bounds, with specific corrections."
                      ),
                    ],
                  ].map(([a, b]) => (
                    <div key={a} className="flex gap-3">
                      <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-primary" />
                      <div>
                        <h3 className="font-medium">{a}</h3>
                        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                          {b}
                        </p>
                      </div>
                    </div>
                  ))}
                  <Separator />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      disabled={busy || !ready}
                      onClick={async () => {
                        const data = await call<{ work: string }>("environment")
                        if (data) setEnvironment(data)
                        await refresh()
                      }}
                    >
                      {t("检查运行环境", "Check environment")}
                    </Button>
                    <Button
                      variant="outline"
                      disabled={busy || !ready}
                      onClick={() => void act("choose_work_folder")}
                    >
                      {t("指定英文工作目录", "Choose ASCII work folder")}
                    </Button>
                  </div>
                  {environment && (
                    <Alert>
                      <CheckCircle2 />
                      <AlertTitle>
                        {t("工作目录可写", "Work folder is writable")}
                      </AlertTitle>
                      <AlertDescription className="break-all">
                        {environment.work}
                        <br />
                        {t("Origin 自动化：", "Origin automation: ")}
                        {state?.origin
                          ? t(
                              "已检测到，导出时检查许可",
                              "Detected; license checked at export"
                            )
                          : t(
                              "未检测到，可导出其他格式",
                              "Not detected; other formats available"
                            )}
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
                <CardFooter>
                  <span className="text-xs text-muted-foreground">
                    {t(
                      "官网明确要求等间隔采样；中文路径限制未见明确声明，路径隔离是兼容性措施。",
                      "Uniform sampling is officially required. Unicode restrictions are not explicit; path isolation is a compatibility measure."
                    )}
                  </span>
                </CardFooter>
              </Card>
            </div>
          </TabsContent>
          <TabsContent value="guide">
            <TutorialGuide lang={lang} openLink={(kind) => void call("open_link", kind)} />
            <div className="grid gap-5 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle>
                    {t("快速开始与注意事项", "Quick start & essential notes")}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      "配置 Hama → 导入 χ(k) → 分析 → 按需导出",
                      "Configure Hama → Import χ(k) → Analyze → Export"
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Accordion type="multiple" defaultValue={["0", "1"]}>
                    {notes.map(([a, b], i) => (
                      <AccordionItem value={String(i)} key={a}>
                        <AccordionTrigger>{a}</AccordionTrigger>
                        <AccordionContent>{b}</AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                </CardContent>
                <CardFooter>
                  <Button variant="outline" onClick={() => setTab("studio")}>
                    {t("回到工作台", "Back to studio")}
                    <ChevronRight data-icon="inline-end" />
                  </Button>
                </CardFooter>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>
                    {t(
                      "可复现，也尊重原作者",
                      "Reproducible, with attribution"
                    )}
                  </CardTitle>
                  <CardDescription>
                    {t(
                      "参数、引擎来源与许可证边界",
                      "Parameters, engine provenance and licensing"
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">
                  <Alert>
                    <Info />
                    <AlertTitle>
                      {t(
                        "保留参数与处理记录",
                        "Keep parameters and processing records"
                      )}
                    </AlertTitle>
                    <AlertDescription>
                      {t(
                        "导出包含数据来源、SHA-256、参数、重采样记录和引擎日志。分享诊断信息前请检查其中是否包含私人文件路径。",
                        "Exports include source paths, SHA-256, settings, resampling records and engine logs. Review private paths before sharing diagnostics."
                      )}
                    </AlertDescription>
                  </Alert>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {t(
                      "本软件自有代码使用 MIT 许可证。Hama 由 H. Funke / M. Chukalina 等原作者提供，使用及学术引用请参阅官方说明。本软件包不包含 Hama、原版 Wgnuplot 或其手册，也不将 Hama 重新授权为 MIT。",
                      "Application code is MIT licensed. Hama is provided by its original authors, including H. Funke / M. Chukalina; follow official usage and citation guidance. Hama, original Wgnuplot and its manual are not included or relicensed under MIT."
                    )}
                  </p>
                  <Alert>
                    <CircleHelp />
                    <AlertTitle>
                      {t("遇到问题时", "If something goes wrong")}
                    </AlertTitle>
                    <AlertDescription>
                      {t(
                        "错误窗口会分别说明位置、原因、解决方法，可展开原始详情并复制。下载失败可改为手动导入；Origin 失败可先导出 PDF 或数据。",
                        "Errors show location, reason and corrective steps, with expandable, copyable details. Import manually if download fails; use PDF or data formats if Origin export fails."
                      )}
                    </AlertDescription>
                  </Alert>
                </CardContent>
                <CardFooter>
                  <Button
                    variant="link"
                    onClick={() => void call("open_link", "home")}
                  >
                    {t(
                      "原作者说明与学术引用",
                      "Authors’ documentation & citations"
                    )}
                    <ExternalLink data-icon="inline-end" />
                  </Button>
                </CardFooter>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
        {state?.busy && (
          <Card>
            <CardHeader>
              <CardTitle>
                {state.phase === "calculating"
                  ? t("正在分析", "Analyzing")
                  : state.phase === "installing"
                    ? t("正在下载 / 校验引擎", "Downloading / verifying engine")
                    : t("正在导出", "Exporting")}
              </CardTitle>
              <CardDescription>
                {t(
                  "进度按已完成样品或格式计算；单个样品可能需要几分钟。",
                  "Progress counts completed samples or formats; a sample can take several minutes."
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <LoaderCircle className="size-4 animate-spin text-primary" />
                <span className="min-w-0 flex-1 truncate text-sm">
                  {state.current} · {state.done}/{state.total} · {state.elapsed}
                  s
                </span>
                {state.phase === "calculating" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => void call("cancel")}
                  >
                    <Square data-icon="inline-start" />
                    {t("取消", "Cancel")}
                  </Button>
                )}
              </div>
              <Progress
                value={state.total ? (100 * state.done) / state.total : 0}
              />
            </CardContent>
            <CardFooter>
              <span className="text-xs text-muted-foreground">
                {t(
                  "任务运行期间请保持软件打开。",
                  "Keep the app open while the task is running."
                )}
              </span>
            </CardFooter>
          </Card>
        )}
        {!!state?.errors.length && (
          <Alert variant="destructive">
            <Info />
            <AlertTitle>
              {t("有操作未完成", "Some operations did not complete")}
            </AlertTitle>
            <AlertDescription className="flex flex-wrap gap-2">
              {state.errors.map((e, i) => (
                <Button
                  key={i}
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setError(e)
                    setCopied(false)
                  }}
                >
                  {e[lang].title}
                </Button>
              ))}
            </AlertDescription>
          </Alert>
        )}
        {state?.export && (
          <Alert>
            <CheckCircle2 />
            <AlertTitle>
              {state.export.errors.length
                ? t("部分导出完成", "Export partially completed")
                : t("导出完成", "Export complete")}
            </AlertTitle>
            <AlertDescription>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p>
                    {t("已成功：", "Completed: ")}
                    {state.export.completed.map(title).join(" · ") ||
                      t("无", "None")}
                  </p>
                  <p className="text-xs break-all">{state.export.folder}</p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => void call("open_export")}
                >
                  <FolderOpen data-icon="inline-start" />
                  {t("打开文件夹", "Open folder")}
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        )}
        <footer className="flex flex-wrap justify-between gap-3 py-2 text-xs text-muted-foreground">
          <span>
            EXAFS Wavelet Studio ·{" "}
            {t(
              "本地分析 · 可复现导出",
              "Local analysis · Reproducible exports"
            )}
          </span>
          <span>
            {t(
              "界面：shadcn/ui · 计算：用户配置的 Hama",
              "Interface: shadcn/ui · Computation: user-provided Hama"
            )}
          </span>
        </footer>
      </main>
      <Dialog open={exportOpen} onOpenChange={setExportOpen}>
        <DialogContent
          className="max-h-[90vh] overflow-y-auto sm:max-w-2xl"
          showCloseButton={false}
        >
          <DialogHeader>
            <DialogTitle>
              {t("导出你需要的结果", "Export what you need")}
            </DialogTitle>
            <DialogDescription>
              {t(
                "可同时选择多种格式。参数 JSON、日志和清单始终附带。",
                "Select any combination. Parameter JSON, logs and a manifest are always included."
              )}
            </DialogDescription>
          </DialogHeader>
          <FieldGroup>
            <Field>
              <FieldLabel>{t("快速选择", "Quick selection")}</FieldLabel>
              <ToggleGroup
                type="single"
                variant="outline"
                value=""
                onValueChange={(v) => {
                  if (v === "all")
                    setSelected(
                      formats.filter((f) => f !== "opju" || state?.origin)
                    )
                  if (v === "figures") setSelected(["png", "pdf"])
                  if (v === "data") setSelected(["txt", "xlsx", "origin_xyz"])
                  if (v === "originpdf")
                    setSelected(
                      state?.origin ? ["opju", "pdf"] : ["origin_xyz", "pdf"]
                    )
                }}
              >
                <ToggleGroupItem value="all">
                  {t("全部可用", "All available")}
                </ToggleGroupItem>
                <ToggleGroupItem value="figures">
                  {t("图片 + PDF", "Images + PDF")}
                </ToggleGroupItem>
                <ToggleGroupItem value="data">
                  {t("数值数据", "Numeric data")}
                </ToggleGroupItem>
                <ToggleGroupItem value="originpdf">
                  Origin + PDF
                </ToggleGroupItem>
              </ToggleGroup>
            </Field>
            <FieldSet>
              <FieldLegend>{t("文件格式", "File formats")}</FieldLegend>
              <FieldGroup className="grid grid-cols-2 gap-4">
                {formats.map((f) => (
                  <Field
                    key={f}
                    orientation="horizontal"
                    data-disabled={f === "opju" && !state?.origin}
                  >
                    <Checkbox
                      id={"format-" + f}
                      checked={selected.includes(f)}
                      disabled={f === "opju" && !state?.origin}
                      onCheckedChange={(v) =>
                        setSelected((old) =>
                          v === true ? [...old, f] : old.filter((x) => x !== f)
                        )
                      }
                    />
                    <div className="flex flex-col gap-1">
                      <FieldLabel htmlFor={"format-" + f}>
                        {title(f)}
                      </FieldLabel>
                      <FieldDescription>{description(f)}</FieldDescription>
                    </div>
                  </Field>
                ))}
              </FieldGroup>
            </FieldSet>
            {!state?.origin && (
              <Alert>
                <Info />
                <AlertDescription>
                  {t(
                    "未检测到 Origin。可先导出 XYZ 或 Excel；需要 .opju 时安装并激活 Origin 后重启本软件。",
                    "Origin not detected. Export XYZ or Excel, or install and activate Origin and restart for .opju."
                  )}
                </AlertDescription>
              </Alert>
            )}
            {dropdown(
              t("图片分辨率", "Figure resolution"),
              dpi,
              setDpi,
              ["150", "300", "600"].map((v) => ({
                value: v,
                label: v + " DPI",
              }))
            )}
            <FieldDescription>
              {t(
                "导出全部已完成样品。图片采用当前配色与归一化设置，数值仍为原始强度。Origin 使用原生图形样式，可进一步调整。",
                "Exports all completed samples. Images use current palette and normalization; numbers remain raw. Origin uses native graph styling for further editing."
              )}
            </FieldDescription>
          </FieldGroup>
          <DialogFooter>
            <Button variant="outline" onClick={() => setExportOpen(false)}>
              {t("取消", "Cancel")}
            </Button>
            <Button
              disabled={!selected.length || busy}
              onClick={() => {
                setExportOpen(false)
                void act("export", selected, cmap, normal, Number(dpi))
              }}
            >
              <Download data-icon="inline-start" />
              {t("选择文件夹并导出", "Choose folder & export")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <Dialog open={!!error} onOpenChange={(open) => !open && setError(null)}>
        <DialogContent
          className="max-h-[90vh] overflow-y-auto sm:max-w-xl"
          showCloseButton={false}
        >
          <DialogHeader>
            <DialogTitle>{error?.[lang].title}</DialogTitle>
            <DialogDescription>
              {t("错误编号：", "Error code: ")}
              {error?.code}
            </DialogDescription>
          </DialogHeader>
          {error && (
            <div className="flex flex-col gap-4">
              <div>
                <h3 className="mb-1 font-medium">{t("错误在哪里", "Where")}</h3>
                <p className="break-all text-muted-foreground">
                  {error.where || t("当前操作", "Current operation")}
                </p>
              </div>
              <div>
                <h3 className="mb-1 font-medium">{t("为什么出错", "Why")}</h3>
                <p className="leading-relaxed text-muted-foreground">
                  {error[lang].why}
                </p>
              </div>
              <Alert>
                <Info />
                <AlertTitle>{t("应该怎样修改", "How to fix it")}</AlertTitle>
                <AlertDescription>{error[lang].fix}</AlertDescription>
              </Alert>
              {error.detail && (
                <details>
                  <summary className="cursor-pointer">
                    {t(
                      "展开具体位置 / 原始详情",
                      "Exact location / technical details"
                    )}
                  </summary>
                  <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-muted p-3 text-xs break-all whitespace-pre-wrap">
                    {error.detail}
                  </pre>
                </details>
              )}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={async () => {
                await call("copy_diagnostics", error)
                setCopied(true)
              }}
            >
              <Copy data-icon="inline-start" />
              {copied
                ? t("已复制", "Copied")
                : t("复制错误详情", "Copy diagnostics")}
            </Button>
            <Button onClick={() => setError(null)}>
              {t("知道了", "Got it")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
