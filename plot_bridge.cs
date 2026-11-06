// Hama calls WGNUPLOT.EXE for previews. This local no-op bridge lets the GUI
// render Hama's numerical output itself; it does not alter the calculation.
class PlotBridge { static void Main(string[] args) {} }
