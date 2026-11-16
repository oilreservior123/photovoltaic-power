# 现场设备与数据接口契约（拟接入）

当前GitHub Pages应用不提供以下服务，也不下发任何真实命令。任务均为浏览器演练。

## 数据

建议由受控网关经HTTPS/MQTT上传，时间为ISO 8601带时区。保留设备ID、采集时间、接收时间、质量码。功率千瓦，电量千瓦时，SOC百分比，温度℃，风速米/秒，辐照瓦/平方米。

- `POST /api/v1/telemetry`：device_id, timestamp, power_kw, energy_kwh, soc_pct, quality_code。
- `POST /api/v1/weather`：timestamp, ghi_wm2, poa_wm2, module_temp_c, wind_ms, rain_mmh。
- `POST /api/v1/forecast`：model_id, issued_at, horizon_steps, quantiles, past_data, future_weather。预报含issued_at和valid_at，禁止未来实测信息泄漏。
- `POST /api/v1/imagery`：scene_id, sensor, acquired_at, spatial_resolution_m, bands_nm, radiometric_calibration, footprint, reference_panels。大影像使用鉴权对象存储地址，不嵌入浏览器控制命令。

## 任务

`POST /api/v1/missions`需要：task_id、idempotency_key、device_id、mode、region_ids、geo_route、constraints、approval_id、dry_run。

建议状态：planned → approved → running → paused → completed / cancelled / failed。必须有设备回执、心跳、断连保护、急停和人工接管。唯一幂等键防止重复命令，命令时间戳和过期时间防止重放。保存审计记录。

`GET /api/v1/missions/{task_id}`返回status、progress_pct、battery_pct、observed_at、error_code；分清预计状态与真实遥测。

HTTP错误：400格式错误；401未登录；403无设备/现场授权；409设备繁忙或幂等冲突；422天气/SOC/生产约束不满足；503网关离线。控制凭据不得放入公开仓库或前端。

## 现场部署分工

油田提供电参、生产边界和现场许可；算法方提供带版本模型、校准与回放报告；设备方提供SDK、传感器标定和安全互锁。初期只做建议/影子运行，限定区域联合验证后方可闭环。
