# 没有 Python 环境时怎么用

这版包不是让公司电脑安装 Python 的。正确用法是：在 GitHub Actions 里自动编译 Windows 便携版，然后在公司电脑上只下载 zip，解压后双击 exe。

## 你最终需要的东西

`AirportWeatherProfiler.exe`

它在这个文件夹里：

```text
dist\AirportWeatherProfiler\AirportWeatherProfiler.exe
```

或者 GitHub Actions 产物里的：

```text
AirportWeatherProfiler-Windows-Portable.zip
```

解压后双击：

```text
AirportWeatherProfiler.exe
```

不需要系统 Python，不需要 pip，不需要管理员权限。

## GitHub 自动构建方法

1. 新建一个 GitHub repo，例如 `airport-weather-profiler`。
2. 把这个 zip 解压后的整个 `airport-weather-profiler` 文件夹内容上传到 repo 根目录。
3. 打开 GitHub repo 页面。
4. 点 `Actions`。
5. 选择 `Build Windows EXE`。
6. 点 `Run workflow`。
7. 等构建完成后，进入本次 workflow run。
8. 在 `Artifacts` 下载 `AirportWeatherProfiler-Windows-Portable`。
9. 解压，双击 `AirportWeatherProfiler.exe`。

## 公司电脑限制说明

如果公司策略允许运行普通 exe，这种方式一般可以用。

如果公司策略禁止运行未知 exe、阻止联网、阻止访问 NOAA/IEM/Meteostat，那么工具本身能打开，但在线下载天气数据会失败。此时可以在家里或另一台电脑跑完，把 `data/weather` 输出文件夹带到公司电脑看报告。

## 为什么不在公司电脑本地打包

本地打包需要 Python、pip、PyInstaller 和依赖库。你的公司电脑不能配置环境，所以本地打包路线不适合。GitHub Actions 相当于让 GitHub 的 Windows 虚拟机替你完成打包。
