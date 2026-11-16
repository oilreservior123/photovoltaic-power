# 数据、许可与复现说明

## 公开功率数据

- 数据集：Solar Power Generation Data，发布者Anil，Kaggle。
- 原始入口：https://www.kaggle.com/datasets/anikannal/solar-power-generation-data
- 选取：Plant 1，逆变器`bvBOhCH3iADSZry`，2020-05-15至2020-06-17，15分钟采样。
- 本仓库`public-source.csv`仅保留该逆变器交流功率及同期气象列；缺失时间保留为待识别的空窗，不做向前看插值。
- 数据集许可应以原始页面当前声明为准；发布者信息及原始入口保留供核查。
- 单位：AC_POWER为源交流功率（千瓦）；气温与组件温度为℃；IRRADIATION为千瓦/平方米。场景功率以训练期最大交流功率归一化，再映射177.1千瓦峰值，不代表本地测量。

## 训练协议

预测目标提前1小时；11项功率滞后、3项历史气象、2项时间编码，共16项。按目标时间切分，训练早于2020-06-07、验证06-07至06-11、测试自06-12。缺失窗口删除。标准化参数只由训练集估计。训练期最大功率用于容量映射，避免用测试最大值归一化。

MLP为64/32/16隐层，Adam，180轮，验证最优72轮，随机种子42。`build_data.py`使用round_trip解析CSV避免浮点重新序列化改变优化轨迹。权重推理通过全部560条测试记录逐条校验。复现环境：scikit-learn、numpy、pandas版本见requirements。

`benchmark.json`包含每条测试目标时间、实际/MLP/岭回归/持续性预测、日间标记、输入特征、验证残差、训练历史及校准分位数。`model.json`是实际MLP权重、偏置和标准化参数，不包含Chronos-2或HyperSIGMA权重。

`replay-dispatch.json`是PPT的5完整日离线连续LP回放，200千瓦时/100千瓦储能、相同初始终端50%SOC、固定规则对照、价格与生产负荷为情景假设；以`replay_dispatch.py`复算。它与浏览器的33状态DP合成情景单列，不能混合统计。

## 合成与上传数据

浏览器合成日：正弦太阳几何近似、温度降额、云量扰动及假设污染损失。光谱为清洁板与尘土端元的线性混合机理示意，不代表任何卫星产品。阵列图与巡检路线没有真实经纬度。

`evaluation-template.csv`是合成上传样例。上传只做结果评价，数据不离开浏览器，不参与内置模型训练，不会修改公开测试集。

## 基础模型主源

Chronos-2：https://github.com/amazon-science/chronos-forecasting 、 https://huggingface.co/amazon/chronos-2

HyperSIGMA：https://github.com/WHU-Sigma/HyperSIGMA

此平台只展示拟接入结构；请按各项目许可获取权重和代码。项目新增模块必须独立消融验证。
