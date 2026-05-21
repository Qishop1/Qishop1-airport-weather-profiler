# Airport Weather Profiler UI

这是桌面 GUI 版。正常使用不需要命令行。

## 打开方式

在 Windows 上解压整个文件夹后，双击：

`双击启动机场天气统计器.bat`

也可以双击：

`AirportWeatherProfiler.pyw`

如果 Windows 没有关联 Python，使用 `.bat` 文件。

## 基本用法

1. 打开程序。
2. 在“单机场统计”输入 ICAO，例如 `RJCC`。
3. 选择“过去 10 年”或“过去 20 年”。
4. 保持默认：自动数据源、自动跑道数据库、图表、HTML、PDF。
5. 点击“生成这个机场的完整天气统计”。
6. 完成后右侧会显示图表预览，可以直接打开 HTML/PDF 报告。

## 多机场对比

进入“多机场对比”，输入：

`RJCC RJCJ RJTT`

点击“生成机场对比报告”。

## 批量报告

进入“批量报告”，选择一个 txt 文件，每行一个 ICAO，例如：

RJCC  
RJCJ  
RJTT  

也可以点击“创建示例列表”。

## 高级设置

“数据与输出设置”里可以选择数据源、输出目录、缓存目录、本地 CSV、手工跑道 YAML、风向扇区和是否强制重新下载。

默认设置已经适合普通使用。

## Cancel and progress

The GUI now runs long profile/compare/batch jobs in a separate backend process. The footer progress bar reports the current phase, and the `取消当前任务` button terminates the backend process without closing the UI. Partial cache/output files may remain after a cancellation; rerun with `强制重新下载源数据` only if a cache file looks incomplete.
