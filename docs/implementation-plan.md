# Photovoltaic platform implementation plan

Goal: 发布可运行的光伏预测、调配和协同运维平台。
Architecture: 浏览器静态应用；纯函数计算内核；可追溯公开回放与合成情景分离；GitHub Pages部署。
Tech stack: ES modules, SVG, Python/scikit-learn, Node test runner.
Spec: docs/design.md

Global constraints: 中文单位；模型详情位于右上角；无伪造现场或大模型训练结果；无设备实控；用户授权直接发布指定仓库。
Review focus: 零发电时利用率；终端SOC可比性；极端天气禁止任务；上传XSS和无效数值；部分日期不能冒充完整日。

1. tests/core.test.mjs 先写统计、功率平衡、SOC闭合、设备联锁、CSV质量断言；运行RED；实现src/core.mjs后GREEN。
2. scripts/build_data.py 重现MLP基线，导出data/benchmark.json与model.json；保留按时间切分与日间口径；验证重算指标、样本数量、权重推理。
3. src/charts.mjs、src/app.mjs、styles.css和index.html实现七个空间，主页面显示结论与建议，各模型右上角详情；测试与浏览器复核交互。
4. 文档、CSV模板、接口契约、GitHub Pages工作流与部署；检查生产构建与公开地址。
