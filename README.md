# Wechat For Macos Version Archive
收集官网 Mac 微信版本并保存至release。

**[按版本号倒序查看全部 Releases（含直接下载链接）](RELEASES.md)**

## 更新日志
* 2026.2.12：使用python重写脚本，移除冗余文件和代码。在`4.0.5`版本后，之前获取精确版本号的规则失效，目前已修复；未来如果继续出现无法获取精确版本号则会自动采用大版本+build的形式（如`v4.0.0+build.12345`）。

* 2024.10.1：通过转换dmg为img后解压，获取精确的微信版本号（例如：3.8.9.xx）；在此之前，后两位小版本号无法获取，所以通过添加更新日期后缀来区分大版本中的小版本，需在下载前自行判断。

项目使用 Github Action 每天自动检测微信**官网新版本更新**，计算 Hash/MD5 值并推送至仓库 Release。

本 fork 的发布标签、标题、安装包和校验文件名均在完整版本号后附加安装包内
`Info.plist` 的 `CFBundleVersion` 构建号。例如 `4.1.13.63_269631`。
工作流每天 UTC 07:00 自动检查；也可以在 Actions 中手动运行。GitHub fork
默认可能禁用工作流，须在仓库 Actions 页面启用后定时任务才会生效。

历史版本可在 macOS 上用 `python3 scripts/sync_upstream_releases.py` 从上游同步。
脚本逐个下载、核对上游 SHA-256、只读挂载并读取构建号，发布后清理临时文件；
重复运行会跳过已同步的完整 Release。先用 `--dry-run` 查看范围，或用
`--tag 4.1.13.63`、`--offset 0 --limit 10` 选择一部分。历史发布说明保留上游
信息，并记录原 Release 地址；旧版本若无法读取构建号，会报告失败而不会猜测。

项目仅抓取官网的Mac安装包，并不包含App Store中的版本。

各版本更新日志可参见官网 [changelog](https://weixin.qq.com/cgi-bin/readtemplate?lang=zh_CN&t=weixin_faq_list&head=true)

相关项目：
- [微信 Windows 64 位 3.0 版本存档](https://github.com/tom-snow/wechat-windows-versions)
- [微信 Windows 32 位 3.0 版本存档](https://github.com/tom-snow/wechat-windows-versions-x86)
- [微信 Mac 3.0 & 4.0 版本存档](https://github.com/zsbai/wechat-versions)


*如有问题/侵权，请直接提交 issue 告知。*
