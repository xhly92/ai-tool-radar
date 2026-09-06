# ai-tool-radar

## 美股机构投研雷达更新

页面： https://xhly92.github.io/ai-tool-radar/us-research-radar-3.html

- GitHub Actions 每小时第 17、47 分钟采集公开来源（调度可能延迟），并发布到 GitHub Pages。
- 页面加载、恢复联网、返回标签页和每五分钟都会读取 `data/research.json`；“立即同步”读取最近的后台结果，不会直接触发抓取。
- 自动来源：J.P. Morgan Making Sense、BofA Global Research Unlocked 官方 RSS、Morgan Stanley Thoughts on the Market 官方节目页、Jefferies 官方 RSS。只覆盖这些公开栏目，不代表完整机构研报库。
- Evercore 暂无稳定的可采集日期条目，显示不可自动更新；受限客户研报保留历史资料，不自动登录。
- 自动条目使用原文标题和摘要，主题为关键词分类；历史整理内容仍保留。页面仅显示最近六个日历月。
- 来源失败时保留已有数据并显示状态；超过 90 分钟未检查显示延迟提示。GitHub 定时任务长期无仓库活动时可能暂停，可在 Actions 重新启用。

本地运行：`pip install -r scripts/requirements.txt`，然后 `python scripts/update_research.py`。
测试：`python -m unittest discover -s scripts -p 'test_*.py'`。
需要手动更新时在 Actions 中运行 **Refresh research and publish Pages**。
