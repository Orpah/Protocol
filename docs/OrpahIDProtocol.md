# Orpah ID 协议规范 v1.17

> **Orpah ID**（*Orpah Identity*）是一个"无认证 Wi-Fi 寻人"协议：client（佩戴终端）向周围的 router（接入点）发送身份/位置信号，router 不要求 client 认证即可转发到 server，server 根据多个 router 的接收情况判定 client 大致位置。本协议即 *Orpah ID Protocol*。
>
> 本协议定义 Orpah ID 的**码号（SN）规范**与**数据真实性（数字签名）**部分。
>
> **传输层无关**：本协议可承载于任何链路，包括 Wi-Fi HaLow（802.11ah）、普通 802.11 Wi-Fi、以太网等。文档中出现的硬件示例（CH32V203 + T-Halow STA + ATECC608B）仅为参考实现，不属于协议本身。

---

## 1. 范围与术语

### 1.1 本协议定义

- 设备序列号（SN）的编码规则
- 号码合法性校验算法
- 报文数字签名算法
- 密钥管理与备份/降级策略
- 报文格式（应用层 JSON）
- 本规范为 Orpah ID **身份与真实性层**的权威定义（与其它实现/文档冲突时，以本规范为准）

### 1.2 本协议不定义

- 链路层帧格式（Probe Request / Beacon / 数据帧等由承载链路定义）
- 射频参数、信道、带宽
- router 与 server 之间的具体传输协议（HTTP/MQTT/UDP 等由部署决定）
- 具体芯片/安全元件的型号与 Slot 划分（§6 为参考实现，非规范性）
- 承载链路适配示例（§7 仅为示例，非规范性）

### 1.3 术语

| 术语 | 含义 |
|------|------|
| SN | Serial Number，设备序列号，本协议的核心标识 |
| CC | Country Code，ISO 3166-1 alpha-2 国家码 |
| ORG | Organization Code，机构码 |
| UNIQUE | 唯一流水号 |
| CHECK | 校验码（可选） |
| SE | Secure Element，安全元件（如 ATECC608B） |
| JCS | JSON Canonicalization Scheme（RFC 8785） |
| client | 佩戴终端（寻人标签）＝链路层 **STA** |
| router | 接入点/转发器 ＝链路层 **AP** |
| server | 后端服务，负责验签与定位判定 |

---

## 2. SN 编码规则

### 2.1 格式

```
CC-ORG-UNIQUE[-CHECK]
```

| 字段 | 长度 | 字符集 | 说明 |
|------|------|--------|------|
| CC | 2 位 | A–Z（ISO 3166-1） | 国家/地区码（本规范样例统一用 CN）；**不套用 Crockford 限制**（允许含 I/L/O/U 的字母） |
| ORG | 2–6 位 | Crockford Base32 | 机构码，私有自分配或向注册机构申请 |
| UNIQUE | 8–16 位 | Crockford Base32 | 唯一流水，由 SE 硬件 RNG 或注册机构分配 |
| CHECK | 0/1/2 位 | Crockford Base32 | 校验码，可选：1 位（Damm32 / Luhn mod 32）或 2 位（Mod 97），见 §3 |

分隔符：连字符 `-`，仅出现在字段之间。

### 2.2 示例

```
CN-WH01-9AF3C1D28E44          （无校验码）
CN-WH01-9AF3C1D2-B            （1 位校验：Damm32，B 为校验字符）
CN-WH01-9AF3C1D2-21           （2 位校验：Mod 97，两位十进制数字）
```

> 本规范所有示例统一使用 CC=`CN`（中国）；校验位只由 `ORG-UNIQUE` 计算（不含 CC）。

### 2.3 规则

1. **全部大写**，存储和传输统一转为大写后处理
2. **型号不进 SN**：型号（如硬件版本、模组型号）作为独立属性存在 server 资产表 `sn → model/fw/owner`，SN 本身不含型号信息
3. **全 Unicode 名称不进 SN**：人员姓名、备注等只进业务 payload，SN 只用 ASCII 字符
4. **唯一性**：由 UNIQUE 字段保证（见 §2.4），校验码不贡献唯一性
5. **不可复用**：一个 SN 一旦分配给设备，即使设备报废也不得再分配给其他设备（建议软删除 + 保留期）

### 2.4 唯一性保证

| 方式 | 适用场景 | 说明 |
|------|----------|------|
| SE 硬件 RNG | 私有部署、不接入国际注册 | ATECC608B 内部 RNG 生成 16 字节随机数 → Crockford Base32 截断为 8–16 位；碰撞概率可忽略 |
| 注册机构分配 | 跨机构、合规部署 | 走 ISO/IEC 15459 发行机构码 + 厂商码，或 OID 企业弧 |
| 中心化计数器 | 小规模内部系统 | 数据库单调自增，导出为 Crockford Base32 |

### 2.5 字符集与长度约束

- **SN 总长度 ≤ 32 字符**（兼容 802.11 SSID 长度限制，便于承载链路使用 SSID 做发现）
- **Crockford Base32 字母表**：`0123456789ABCDEFGHJKMNPQRSTVWXYZ`（去除易混的 `I L O U`）
- 不允许：小写、空格、连字符以外的标点、Unicode 字符、控制字符
- `ORG`/`UNIQUE`/`CHECK` 用 Crockford Base32；`CC` 为 ISO 3166-1 alpha-2，**不套用 Crockford 限制**
- 正则（Crockford 字符类记作 `c`，见下）：

  ```regex
  ^ [A-Z]{2}        # CC：ISO 3166-1 alpha-2（2 位大写字母，含 I/L/O/U 亦可）
  - c{2,6}          # ORG：2–6 位 Crockford Base32
  - c{8,16}         # UNIQUE：8–16 位 Crockford Base32
  ( - c{1,2} )?     # CHECK：可选，1–2 位 Crockford Base32
  $
  ```

  其中 Crockford 字符类 `c = [0-9A-HJKMNP-TV-Z]`，即 `0-9` + `A-Z` 去掉 `I L O U`：

  | 范围 | 包含 | 说明 |
  |------|------|------|
  | `0-9` | 0 1 2 3 4 5 6 7 8 9 | 数字 |
  | `A-H` | A B C D E F G H | 到 H 为止（排除 I，易混 1） |
  | `J K` | J K | 跳过 I、L（易混 1） |
  | `M N` | M N | — |
  | `P-T` | P Q R S T | 跳过 O（易混 0） |
  | `V-Z` | V W X Y Z | 跳过 U（易混 V / 避免歧义） |

---

## 3. 号码校验算法

> 校验码（CHECK）只防**手误/扫码错误**，不防伪造。防伪造靠 §5 的数字签名。

### 3.1 不加校验码（默认，机器为主场景）

- SN 由设备自动生成、自动传输，不涉及人工录入
- 完整性靠传输层 CRC + 应用层签名验签
- CHECK 字段为空

### 3.2 加校验码（有人工录入场景）

当存在人工抄写、电话报号、工单录入等场景时，建议在 UNIQUE 后追加 1 位校验码。**校验位只由 `ORG-UNIQUE` 计算（不含 `CC`）**。

#### 算法：Damm（Crockford Base32 扩展）

Damm 算法能检测**所有单字错误**和**所有相邻双字换位**，实现只需一个小查找表。

`ORG`/`UNIQUE` 是 Crockford Base32（N=32），需将标准十进制 Damm 表扩展为 32×32 quasigroup。
**校验位就是同一字母表（Crockford Base32）中的 1 个字符**（可为数字或字母），取值由算法给定，不可强制为数字。

```
// 校验位只算 ORG-UNIQUE（不含 CC；CC=ISO 3166-1 alpha-2，不参与校验）。
// 32×32 quasigroup 构造已定稿，见附录 B.2（T[x][y] = 2·(x⊕y)，GF(2^5)、p(t)=t^5+t+1）。
// 参数 org_unique = "ORG-UNIQUE"（不含 CC，也不含连字符后的 CHECK）
char compute_check(const char *org_unique) {
    uint8_t state = 0;
    for (char *p = org_unique; *p; p++) {
        if (*p == '-') continue;            // 跳过分隔符
        uint8_t d = crockford_to_index(*p);  // Crockford Base32 → 0-31
        state = damm32_table[state][d];      // damm32_table 构造见附录 B.2
    }
    return index_to_crockford(state);        // 0-31 → Crockford 字符（0-9 A-Z，无 I L O U）
}
```

> **校验位字符集与长度**：Damm32 输出的校验字符属于 Crockford Base32（可能为字母），因此
> `CHECK` 的字符集是 Crockford Base32，而非“仅数字”（早期版本曾误写为 0–9）；`CHECK` 长度
> 可为 0（无校验）、1（Damm32 / Luhn mod 32）或 2（Mod 97）。
>
> **兜底方案（Phase 2 先用）**：若 32×32 Damm 表尚未就绪，可选：
> - **Mod 97**（字母数字，IBAN 思路）→ **2 位**校验（`CHECK` 长度 2）；输出固定为**两位十进制数字**（`02`–`98`，校验位不可能为 00/01），是 Crockford Base32 字符集的**子集**（例：`…-42`，不是字母）
> - **Luhn mod 32**（N=32，Crockford Base32）→ **1 位**校验（`CHECK` 长度 1）。
>
> 两者实现简单、验证充分；最终算法与 `CHECK` 长度在 Phase 2 定稿并固化（同一部署内保持一致）。
>
> **Mod 97 字母→数字映射**：采用 IBAN 规则，`A=10, B=11, …, Z=35`（字符序数值，
> **非** Crockford Base32 索引；二者对 J/K/M/N/P/Q/R/S/T/V/W/X/Y/Z 的取值不同）。
> 完整校验规则：`N` = 字母数字串（去 `-` 分隔符）按上述映射拼成的十进制数，末尾追加 `"00"`；
> `CHECK = 98 − (N mod 97)`，不足两位补零（输出范围 `02`–`98`）。

#### 校验时机

- **client 端**：生成 SN 时计算 CHECK，存入 SE 的只读 slot 或 CH32 Flash
- **router 端**：收到报文后先做 CHECK 快速过滤非法 SN（廉价，不消耗验签算力）
- **server 端**：CHECK 通过后再验签；CHECK 失败直接拒绝

### 3.3 校验码与签名的分工

| 能力 | CHECK（Damm/Mod97/Luhn） | 签名（ECDSA/HMAC） |
|------|--------------------------|---------------------|
| 防手敲错 | ✅ | ✅（间接） |
| 防扫码截断 | ✅ | ✅（间接） |
| 防伪造 | ❌ | ✅ |
| 防篡改 | ❌ | ✅ |
| 计算成本 | 极低（查表） | 较高（椭圆曲线） |
| 在哪验证 | router/server | server（权威） |

**原则**：CHECK 是"前置过滤器"，签名是"最终裁决"。即使 CHECK 通过，没有合法签名仍视为不可信。

---

## 4. Unicode 处理

> 虽然 SN 本身只用 ASCII，但 Orpah ID 的 payload 可能包含人员姓名、备注等 Unicode 字段。本节规定规范化规则。

### 4.1 规范化步骤

所有 Unicode 字符串在参与校验、哈希、签名前必须经过：

1. **NFKC 规范化**（兼容合成）：将视觉相同的字符统一为同一码位序列
   - 例：`é`（U+00E9）与 `e` + `́`（U+0065 + U+0301）→ 统一为 U+00E9
2. **大小写折叠**：按 Unicode Case Folding 转为小写（用于比较）；或按场景统一大写
3. **去零宽字符**：移除 ZWSP（U+200B）、ZWJ（U+200D）、ZWNJ（U+200C）、BOM（U+FEFF）
4. **去双向控制符**：移除 LRE/RLR/PDF 等（U+202A–U+202E）
5. **全角转半角**：全角数字/字母 → 半角（可选，按部署约定）
6. **最终编码**：UTF-8 字节序列，用于哈希/签名

### 4.2 影响范围

| 字段 | 是否规范化 | 说明 |
|------|-----------|------|
| SN | 不参与（纯 ASCII） | SN 生成时已限制为 Crockford Base32 |
| payload 中的 name/remark | ✅ NFKC + 去控制符 | 签名前规范化 |
| SSID（承载链路发现用） | 截断/派生，不用全量 Unicode | 见 §7 |
| JSON 序列化 | JCS（RFC 8785） | key 字典序、无多余空白 |

### 4.3 服务端一致性要求

**发送端与接收端必须使用相同的规范化函数**。建议：

- 将规范化函数作为协议的一部分，写入 SDK
- 服务端验签前，对接收到的 JSON 重新执行同样的 JCS + NFKC，再哈希验签
- 任一方使用不同规范化形式（如 NFD vs NFC）都会导致验签失败

---

## 5. 数字签名

### 5.1 签名对象

签名不是对"美化后的 JSON 字符串"直接签名，而是对**规范化后的字节序列**（**签名预像**，定义见下）签名：

```
preimage = UTF-8( JCS( { "hdr": <hdr>, "payload": <payload> } ) )
ES256: sig = ECDSA-P256-sign( privkey, SHA-256(preimage) )
HS256: sig = HMAC-SHA256( symkey, preimage )
```

- **顶层对象只含 `hdr` 与 `payload` 两个键**（键名固定；不含 `sig`，也不含任何传输元数据）
- 序列化严格按 **RFC 8785 JCS**（键按 UTF-16 码元字典序、无多余空白、数字最短表示），签名与验签两侧**必须字节一致**
- 发送与验签都用**报文中实际存在的** `hdr`/`payload` 对象本身（不得增删字段后再签/验）
- `ES256`：对 `SHA-256(preimage)` 签名；`HS256`：**直接对 `preimage` 做 HMAC**（不再先哈希）
- `alg=none`（L3，见 §5.6/§8）不产生签名，`sig` 字段省略

### 5.2 算法选择

| 级别 | 算法 | 密钥位置 | 适用场景 |
|------|------|----------|----------|
| **主用** | ECDSA P-256 + SHA-256 | ATECC608B Slot 0 | 生产环境 |
| 降级 L1 | HMAC-SHA256 | ATECC608B Slot 5 | Slot 0 异常时 |
| 降级 L2 | HMAC-SHA256 | CH32 软件（读保护区） | SE 完全不可用时 |
| 降级 L3 | 无签名 | — | SE 不可用且无对称密钥 |

### 5.3 ECDSA P-256 流程（ATECC608B）

```
CH32V203                          ATECC608B
   │                                  │
   │  1. 组 hdr + payload             │
   │  2. JCS 序列化 → UTF-8 字节      │
   │  3. atcab_sha(bytes) ──────────► │
   │  ◄──────────────── 32B digest   │
   │  4. atcab_sign(Slot0, digest) ─► │
   │  ◄─────────────── 64B R‖S       │
   │  5. base64url(sig) → JSON       │
   │  6. 通过承载链路发送              │
```

签名输出 64 字节（r: 32 字节 + s: 32 字节），JSON 中做 base64url 编码后约 86 字符。

### 5.4 报文格式

```json
{
  "hdr": {
    "typ": "orpah-id-report",
    "ver": 1,
    "alg": "ES256",
    "level": 0
  },
  "payload": {
    "sn": "CN-WH01-9AF3C1D28E44",
    "ts": 1757420000,
    "nonce": "3F9A8B2C1D4E5F6A7B8C9D0E1F2A3B4C",
    "seen_routers": [
      {"bssid": "AA:BB:CC:DD:EE:FF", "ssid": "ORPAHID_ZONE_A", "rssi": -42},
      {"bssid": "11:22:33:44:55:66", "ssid": "ORPAHID_ZONE_B", "rssi": -71}
    ],
    "battery_mv": 3700,
    "firmware": "1.0.3",
    "se_sn": "ATECC608B-72BIT-SERIAL"
  },
  "sig": "base64url(R‖S)"
}
```

#### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `hdr.typ` | ✅ | 固定 `orpah-id-report` |
| `hdr.ver` | ✅ | 协议版本，当前 1 |
| `hdr.alg` | ✅ | 签名算法：`ES256`（主用）/ `HS256`（降级 L1/L2）/ `none`（L3 无签名，仅覆盖用） |
| `hdr.level` | ✅ | 降级级别 0–3（`alg=none` 必须 `level=3`） |
| `payload.sn` | ✅ | 设备序列号（§2 格式） |
| `payload.ts` | ✅ | Unix 时间戳（秒），防重放窗口 ±300s |
| `payload.nonce` | ✅ | 16 字节随机数（ATECC608B RNG），防重放 |
| `payload.seen_routers` | ✅ | **client 观测**到的 router 列表（client 侧 RSSI），用于粗覆盖；**三角/粗定位用 router 侧观测**（见 §5.7） |
| `payload.battery_mv` | ⭕ | 电池电压，可选 |
| `payload.firmware` | ⭕ | 固件版本，可选 |
| `payload.se_sn` | ⭕ | SE 芯片序列号，用于 attestation |
| `sig` | ✅（`alg≠none`） | 签名值（base64url）；`alg=none` 时省略 |

### 5.5 防重放与时间

> **签名不依赖时间**：ECDSA/HMAC 的计算与绝对时间无关。时间只在**防重放**（`ts` 窗口）与
> **日志排序**时用到。因此**无 RTC 的终端也能正常签名**——只是 `ts` 可能不准。

- **时间戳窗口**：`|server_ts - payload.ts| ≤ W` 秒（默认 `W=300`；对无 RTC 设备可放宽，或用 `ts=0` 表示未知；`W` 属部署配置）
- **nonce 去重（防重放主手段）**：server 按 `sn` 缓存近期 nonce（建议 LRU，容量 1024/设备），重复 nonce 拒绝
- **可选：单调计数器**：无 RTC 设备可用 SE 单调计数器 / 递增序号替代时间，作为第二因子
- **校时**：终端首次关联时，服务器可经 router 下发当前时间，终端据此校正本地时钟
- **推荐组合**：`nonce`（必选）+ `ts` 或单调计数器（择一）

### 5.6 alg 白名单

server 验签时：

- **接受** `ES256`（主用）、`HS256`（降级 L1/L2）
- **`none` 仅在 `hdr.level == 3` 时接受**，且**一律视为不可信**（只作覆盖发现，见 §8.3）
- **拒绝** 其它任何未注册算法；`alg=none` 与 `level≠3` 的组合直接拒绝
- **不按客户端自称随意切换**：`payload.sn` 绑定的密钥类型决定允许使用的算法

### 5.7 定位数据源：client 观测 vs router 观测

粗定位需要**多个 router 各自测得的 client 信号强度（RSSI）**，与 client 自报的
`payload.seen_routers` 是**两回事**：

| 数据 | 观测方 | 内容 | 用途 | 是否在签名内 |
|------|--------|------|------|------|
| `payload.seen_routers` | **client** | client 听到的 AP 列表 + 其 RSSI | 粗覆盖、辅助 | ✅ |
| `xport`（传输元数据） | **router** | 转发者 BSSID/SSID + 该 router 测得的 RSSI + 接收时间 | **多 router 粗定位** | ❌ |

router 转发已签报文时**不得修改 `hdr`/`payload`/`sig`**，只能在其外附加自己的观测：

```json
{
  "hdr": { ... }, "payload": { ... }, "sig": "...",
  "xport": { "router_bssid": "AA:BB:CC:DD:EE:FF", "router_ssid": "ORPAHID_ZONE_A",
             "router_rssi": -58, "rx_ts": 1757420001 }
}
```

server 用**同一 `sn` 的多条 `xport`**（来自不同 router）做粗定位；`xport` 不参与验签，
但 server 应校验 `router_bssid` 是否属于受信 router 集合。

### 5.8 限频（防刷）

签名防伪造，但不防**洪水**。各环节须限频：

| 环节 | 措施 |
|------|------|
| router（未签名 probe / 发现阶段） | 按源 MAC 限速（如 ≤ 1 次/秒）；丢弃高频探测 |
| router（已签上报转发） | 按 SN 限速，超限丢弃或降采样后转发 |
| server（按 sn） | 最小间隔 + 令牌桶；超限丢弃并计数（可选告警） |
| server（按 router） | 限制单 router 上行速率，防单点刷 |

限频参数属**部署配置**，本协议不规定具体数值。

---

## 6. 密钥管理

> **非规范性说明**：本节出现的具体芯片与 Slot 划分（如 ATECC608B 的 Slot 0/5/8/9）**仅为参考实现**；协议本身**不绑定任何具体 SE 型号**。实际 Slot 用途、类型与锁定策略以**芯片数据手册**与**产线配置**为准（投产前须逐项与手册核对）。

### 6.1 密钥层级

```
┌─────────────────────────────────────────┐
│            ATECC608B (SE)               │
│  ┌───────────────────────────────────┐  │
│  │ Slot 0: ECDSA P-256 私钥（终身） │  │
│  │ Slot 5: HMAC-SHA256 密钥（L1）   │  │
│  │ Slot 8: IO Protection Key        │  │
│  │ Slot 9: Monotonic Counter        │  │
│  └───────────────────────────────────┘  │
│  Config Zone (Locked after provision)   │
└─────────────────────────────────────────┘
```

> **关于密钥轮换**：本系统**不实施密钥轮换**。Slot 0 的 ECDSA 私钥在产线烧录后终身使用，直至设备报废或密钥被吊销（见 §6.3）。因此 ATECC608B 不需要为轮换预留多个 ECDSA Slot，其余 Slot（1、2、3、4、6、7 等）可按部署需要用于其他用途（如设备 attestation、将来扩展），协议不做规定。

### 6.2 产线烧录流程

```
Step 1: 生成 SN
  - 从 ATECC608B RNG 取 16 字节 → Crockford Base32 → 截取 10–16 位
  - SN = "CC-ORG-" + UNIQUE
  - （可选）计算 CHECK → 追加到 SN

Step 2: 生成密钥对
  - ATECC608B Slot 0: genkey → 得到 P256 公钥（终身私钥，不轮换）
  - ATECC608B Slot 5: random → 生成 HMAC 密钥（降级用）

Step 3: 绑定
  - 读取 SE 72-bit 唯一序列号
  - 读取/导出 HMAC 密钥（Slot 5）—— server 验 HS256 需**同一密钥**，必须一并登记
  - 组装记录: {sn, pubkey, hmac_key, se_sn}
  - 上传 server 密钥库

Step 4: Lock
  - Lock Config Zone（锁定配置，不可再改）
  - Lock Data Zone / Slot Lock（锁定指定 slot，私钥不可读）
  - 设置 IO Protection Key（防止通过 I2C 篡改）

Step 5: CH32 烧录
  - 写入规范 SN（用于 JSON payload）
  - 写入 server 地址/router SSID 列表
  - 开启 Flash 读保护 + WRP

> 每个设备只注册**一对** ECDSA 密钥（一个 SN 对应一个公钥）。不生成备用密钥、不预留轮换密钥，简化产线与运维。公钥的检索键就是 SN 本身，无需独立的 Key ID。
```

### 6.3 密钥生命周期：不轮换，仅撤销

#### 6.3.1 不实施密钥轮换

本系统**不实施密钥轮换**。ECDSA 私钥（ATECC608B Slot 0）在产线烧录后**终身固定**，直到设备报废或密钥被吊销，期间不会更换。

理由：

1. **系统目标优先**：Orpah ID 的核心是人员定位与寻人，而非金融级防破解。攻击者要获取私钥，必须先物理接触终端并突破 ATECC608B 的硬件防护（主动屏蔽、反探针、密钥不可导出）——这类攻击在实际寻人场景中的风险远低于"轮换流程失败导致终端失联"的风险。
2. **简化设计与运维**：免除轮换协议、新旧密钥共存窗口、过渡期管理、Slot 预留等复杂度，产线烧录和后端密钥库都只需处理"一机一密钥"。
3. **硬件资源释放**：ATECC608B 的 Slot 数量有限（共 16 个，可用作 ECDSA 密钥对的更少），不预留轮换 Slot，可将其他 Slot 用于 attestation、将来扩展等用途。

> **若未来需求变化**（如确有必要引入轮换），可在后续版本中追加轮换协议。当前版本明确排除轮换。

#### 6.3.2 密钥撤销（唯一生命周期操作）

| 操作 | 触发条件 | 流程 |
|------|----------|------|
| 设备撤销 | 丢失 / 报废 / 被盗 / 疑似私钥泄露 | server 将该 `sn` 加入撤销列表，拒绝此后该 SN 的所有报文；撤销不可逆 |

撤销是**一锤子买卖**：一旦撤销，该设备的密钥即作废，无法恢复，只能重新烧录或更换 SE。这与"不轮换"一致——密钥要么一直有效，要么被撤销。

> **关于"疑似私钥泄露"**：即便私钥可能已被破解，本系统也不靠轮换来止血（因不轮换），而是通过立即**撤销**该设备来切断其上报可信度。这足以满足寻人场景：攻击者即便能伪造报文，运维侧可通过撤销快速隔离。

### 6.4 私钥保护

| 安全级别 | 实现 | 适用场景 |
|----------|------|----------|
| **高** | 私钥仅存 ATECC608B，永不出芯片；签名在 SE 内完成 | 生产环境（推荐） |
| 中 | CH32 Flash 读保护 + WRP，私钥加密存储（UID 派生 KEK） | 低成本场景 |
| 低 | CH32 软件 HMAC，密钥在 SRAM/Flash 明文 | 仅降级 L2 临时使用 |

---

## 7. 承载链路适配（示例：Wi-Fi HaLow）

> 本节为**参考实现**，展示 Orpah ID 协议如何承载于 802.11ah（Wi-Fi HaLow）。使用其他链路时，替换本节即可。

### 7.1 发现阶段（不签名）

> **实现前提（重要）**：发现阶段依赖 router（AP）能**捕获并上报** STA 的 Probe Request /
> 关联前探测信息。**标准 AP 固件通常不会把任意 probe 的 SSID 上报后端**，因此本阶段需要
> **定制 / 协作式 AP 固件**（本项目的 TH-RJ45 等为可定制载体）。若承载链路无法抓 probe，
> 则退化为「短关联 + 已签上报」（§7.2）一条路径。

- client（STA 模式）周期性发送 Probe Request
- SSID 字段：**仅放短码**，格式 `ORPAHID_<CC><ORG><UNIQUE前6位>`
  - 例：`ORPAHID_CNWH019AF3C1`（≤ 32 字符）
  - **短码为不透明前缀**：router/server **不从中解析 CC/ORG/UNIQUE 字段**（ORG 变长，解析会有歧义），只当整体字符串用
- **不放完整 SN、不放签名**（SSID 长度限制 + 管理帧不适合承载签名）
- router 收到后记录：`源 MAC + SSID短码 + RSSI + 时间戳`
- 用途：**粗覆盖判定**，不作为身份确证

### 7.2 上报阶段（签名）

- client 短暂关联 router（链路层加密，如 WPA2/3-PSK）
- 通过数据通道发送 §5.4 的完整已签 JSON
- 发完立即断开，进入深睡
- router 透传到 server（RJ45 / 蜂窝 / 其他）

### 7.3 两级信任模型

| 阶段 | 数据 | 信任级别 | 用途 |
|------|------|----------|------|
| 发现 | SSID 短码 + RSSI | 低（仅覆盖） | 触发上报、粗定位 |
| 上报 | 已签 JSON | 高（签名验证） | 人员确认、告警、定位结论 |

**核心原则**：任何人都可以伪造 SSID 喊话（低信任），但只有持有合法私钥的设备才能产出通过验签的报文（高信任）。

### 7.4 链路层参数与区域配置

本协议**不规定**任何射频参数（频段、信道、带宽、发射功率、占空比、LBT 等）。这些参数由部署方根据**目标市场的现行监管规则**与**所用模组的 region profile** 配置，与 Orpah ID 码号、签名逻辑完全解耦。

**设计原则**：

- **协议层无关**：§1.2 已声明本协议不定义射频参数、信道、带宽。无论终端工作在哪个国家、使用哪套频段，SN 编码、JCS 规范化、ECDSA 签名、降级策略均完全相同。
- **配置外置**：区域参数（国家码、频段、信道计划、功率上限、占空比/LBT 策略）存放在**资产表 / 模组 region profile** 中，通过部署配置或运维通道下发，**不写死在应用代码**，更不作为常量编译进固件。
- **SN 不含射频信息**：SN 只表达身份（CC-ORG-UNIQUE），不携带国家频段、信道号、频率等链路层信息；跨区域迁移只需更新配置，无需重发 SN。
- **SSID 短码不含频率**：发现阶段的 SSID 短码仅含身份前缀，不含任何频段/信道字段。

**配置责任划分**：

| 责任方 | 职责 |
|--------|------|
| **部署方 / 运营方** | 确认目标市场的现行无线电监管规则（免许可频段、功率上限、占空比、LBT 等）；选型已通过当地认证的模组/设备 |
| **模组厂商** | 在模组固件/region profile 中固化合规的信道计划与功率表，提供按国家切换的接口 |
| **终端固件（CH32 侧）** | 仅通过 AT 指令或 API 设置"区域/国家"参数，由模组自行映射为具体频段与信道；**禁止**手工计算或硬编码频率值 |
| **Orpah ID 协议** | 不涉及、不约束、不验证射频参数 |

**推荐做法**：

- 终端上电时从资产/配置读取 `region` 字段（如 `CN` / `US` / `EU` / `JP` …），传给模组 region 接口；应用层不关心该 region 对应什么频率。
- 同一硬件跨区部署：仅刷写对应 region profile + 重新认证，SN、密钥、签名流程不变。
- 国内（及其他尚未明确划分商用频段的市场）部署前，须以**当地监管最新公告 + 模组 SRRC/型号核准**为准，协议文档不做任何频段假设。

> **禁止事项**：本协议文档、示例代码、配置模板中均**不得**出现"某国 = 某频段"这类硬编码映射，避免把标准规划值、ISM 频段、型号核准频段混为一谈，也避免因监管规则变更产生误导。

---

## 8. 降级策略

### 8.1 四级降级

| 级别 | 条件 | 算法 | 报文标识 | 信任度 |
|------|------|------|----------|--------|
| **L0** | 正常 | ECDSA P-256 | `alg=ES256, level=0` | 高 |
| **L1** | Slot 0 签名失败 | HMAC-SHA256（Slot 5） | `alg=HS256, level=1` | 中 |
| **L2** | SE 完全不可用 | HMAC-SHA256（CH32） | `alg=HS256, level=2` | 低 |
| **L3** | 无可用密钥 | 裸上报（不签名） | `alg=none, level=3` | 极低 |

### 8.2 降级流程

```
CH32 唤醒
  │
  ├─ Step 1: 尝试 ATECC608B I2C 通信
  │   ├─ 失败 → 跳到 L2
  │   └─ 成功 ↓
  │
  ├─ Step 2: atcab_sign(Slot0, digest)
  │   ├─ 失败（签名错误，如 Slot 0 未配置/锁定异常）→ 跳到 L1
  │   └─ 成功 → L0（ECDSA，正常）
  │
  ├─ Step 3: 若 SE 不可用，检查 CH32 是否有 HMAC 密钥
  │   ├─ 有 → L2
  │   └─ 无 → L3
  │
  └─ Step 4: 组装报文，hdr.level 标注降级级别
```

### 8.3 server 处理

- **L0/L1**：正常处理，更新定位
- **L2**：记录告警（SE 异常），仍更新定位但标记 `degraded=true`
- **L3**：仅用于覆盖发现，**不用于人员确认/告警**；触发 server 侧"设备异常"通知运维

---

## 9. 后端接口（参考）

### 9.1 密钥注册

```
POST /orpah-id/v1/keys/register
{
  "sn": "CN-WH01-9AF3C1D28E44",
  "pubkey": "base64(DER)",
  "hmac_key": "base64(32B)",
  "se_sn": "ATECC608B-72BIT-SERIAL",
  "model": "CH32V203C8T6+T-Halow+ATECC608B",
  "firmware": "1.0.3",
  "issued_at": 1757420000
}
```

> **HMAC 密钥必须注册**：`HS256`（降级 L1/L2）是**对称验签**，server 必须持有与终端相同的
> `hmac_key`（L1 存于 SE Slot 5；L2 存于 CH32 保护区）。若产线**只登记 `pubkey`**，降级后
> server 无对称密钥可用 → 所有 HS256 上报会被拒。若不便于在注册接口携带密钥，可另提供
> `POST /orpah-id/v1/keys/hmac` 导入接口，或由产线工装经安全信道单独导入。

### 9.2 上报接收

```
POST /orpah-id/v1/report
{
  "hdr": { ... },
  "payload": { ... },
  "sig": "..."
}

Response:
{
  "accepted": true,
  "location": "ZONE_A",
  "confidence": "high",
  "ts": 1757420000
}
```

### 9.3 server 验签伪代码

```python
def verify_report(report):
    hdr, payload, sig = report["hdr"], report["payload"], report["sig"]

    # 1. 格式校验
    assert hdr["typ"] == "orpah-id-report"
    assert hdr["ver"] == 1
    assert hdr["alg"] in ("ES256", "HS256", "none")
    if hdr["alg"] == "none":
        # L3 无签名：仅作覆盖发现，不用于人员确认（§8.3）
        assert hdr["level"] == 3
        record_coverage_only(payload)
        return {"accepted": True, "trust": "none"}

    # 2. 时间窗口（无 RTC 设备 ts 可能不准，W 属部署配置，见 §5.5）
    #    ts=0 表示未知：跳过时间窗口检查，仅靠 nonce 去重防重放（§5.5）
    if payload["ts"] != 0 and abs(now() - payload["ts"]) > 300:
        reject("timestamp_out_of_window")

    # 2.5 限频（§5.8）
    if not rate_limit_ok(payload["sn"], client_ip):
        reject("rate_limited")

    # 3. nonce 去重
    if payload["nonce"] in used_nonces[payload["sn"]]:
        reject("replay_detected")
    used_nonces[payload["sn"]].add(payload["nonce"])

    # 4. SN 合法性（CHECK 校验，如果有的话）
    if has_check_digit(payload["sn"]):
        assert verify_damm32(payload["sn"])

    # 5. 撤销检查
    if payload["sn"] in revoked_list:
        reject("revoked")

    # 6. 查公钥（每设备仅一个活跃密钥，见 §6.3；以 sn 为检索键）
    key_record = keystore.get_by_sn(payload["sn"])
    if not key_record:
        reject("unknown_device")

    # 7. 验签（签名预像见 §5.1）
    preimage = jcs_canonicalize({"hdr": hdr, "payload": payload})  # RFC 8785, UTF-8

    if hdr["alg"] == "ES256":
        ok = ecdsa_verify(key_record.pubkey, sha256(preimage), base64url_decode(sig))
    else:  # HS256（直接对 preimage 做 HMAC）
        hk = keystore.get_hmac_key(payload["sn"])
        if not hk:
            reject("no_hmac_key")   # 降级需对称密钥；未注册则拒（见 §9.1）
        expected = hmac_sha256(hk, preimage)
        ok = constant_time_eq(expected, base64url_decode(sig))

    if not ok:
        reject("signature_invalid")

    # 8. 定位判定
    location = triangulate(payload["seen_routers"])
    return {"accepted": True, "location": location, "confidence": "high"}
```

---

## 10. 威胁模型

| 威胁 | 防御措施 | 有效性 |
|------|----------|--------|
| 伪造 SSID 喊话 | SSID 短码不采信身份，仅粗覆盖 | ✅ 发现阶段不依赖 |
| 伪造已签报文 | ECDSA 签名，私钥在 SE 不可导出 | ✅ 上报阶段强防护 |
| 报文篡改 | 签名覆盖完整 payload | ✅ |
| 重放攻击 | ts 窗口 + nonce 去重 | ✅ |
| SE 物理提取私钥 | ATECC608B 防侧信道防护 | ✅（硬件级） |
| CH32 Flash 读取 | 读保护 + WRP + UID 派生 KEK | ⚠️ 中等级 |
| HMAC 密钥批量泄露 | 每设备独立密钥 + 可远程吊销 | ⚠️ 降级场景有限 |
| SN CHECK 被猜 | CHECK 不是安全边界，靠签名 | ✅ 设计清晰 |
| Unicode 规范化不一致 | NFKC + JCS，SDK 固化 | ✅ 需测试覆盖 |
| 洪水 / DoS（高频上报、伪造 probe） | §5.8 各环节限频；签名过滤伪造 | ⚠️ 需部署限频参数 |

---

## 11. Phase 2 待验证项

> ⚠️ 以下项目需在真机上验证后定稿，当前为设计假设：

1. **Damm 32 扩展表**：**已完成**——Damm32 拟群构造定稿为 GF(2⁵) 代数式 `T[x][y] = 2·(x⊕y)`（`p(t)=t⁵+t+1`，见附录 B.1/B.2），黄金样本 `WH01-9AF3C1D2 → B` 已由 `damm32.py` / `c/damm32.c` / Web 工具页交叉验证；1 位校验仍可选 Luhn mod 32、2 位用 Mod 97
2. **ATECC608B Base32 RNG**：确认 `atcab_random` 输出范围足够覆盖 8–16 位 Crockford Base32（需 16 字节随机 → 取前 N 字节）
3. **承载链路未关联数据**：若使用 HaLow，需验证 STA 在未关联状态能否通过数据帧发送自定义 payload；若不可行，统一走"短关联 + 已签 JSON"
4. **JCS 实现一致性**：CH32（C）与 server（Python）的 JCS 输出必须字节一致（尤其是签名预像 `JCS({"hdr":…,"payload":…})`），需交叉测试

---

## 12. 附录

### 附录 A：ISO 3166-1 alpha-2 国家码

#### A.1 标准国家码（摘录）

| 码 | 国家/地区 |
|----|-----------|
| CN | 中国 |
| US | 美国 |
| JP | 日本 |
| KR | 韩国 |
| DE | 德国 |
| FR | 法国 |
| GB | 英国 |
| AU | 澳大利亚 |
| SG | 新加坡 |
| IN | 印度 |

完整列表见 ISO 3166-1 官方维护机构。

> **地外/外太空延伸**（天体码、地外地名、地月链路参考等）已移至单独文档
> 《[Orpah ID 地外篇](OrpahIDSpace.md)》，本规范不再收录。

### 附录 B：Damm 32（Crockford Base32）校验算法参考实现

#### B.1 算法原理

Damm 算法基于一个**弱全反对称拟群**（weak totally anti-symmetric quasigroup）运算。
对 Crockford Base32（0–9, A–Z 去除 I L O U，共 32 符号），取有限域 GF(2⁵) 上的拟群：

&nbsp;&nbsp;`x ⊙ y = 2 · (x ⊕ y)`　（`·` = GF(2⁵) 乘法，`⊕` = 域加法 = 按位异或，`2` = 域元素 t）

其中不可约多项式 `p(t) = t⁵ + t + 1`（系数 `0x23`）。该拟群满足 Damm 检出「所有单字符替换
+ 所有相邻换位」的充要条件（拉丁方、主对角线全 0、相邻换位条件），已在 `damm32.py` 与
Web 工具页穷举验证（长度 ≤3 全部 33824 串 0 漏检）。

**校验位只算 `ORG-UNIQUE`（不含 `CC`）**：`CC` 为 ISO 3166-1 alpha-2，不套 Crockford 限制、
不参与校验位计算（`CC` 可含 I/L/O/U，不影响 CHECK）。

#### B.2 C 语言参考实现（拟群由 GF(2⁵) 代数式直接计算，无需固化 32×32 表）

```c
#include <stdint.h>
#include <string.h>

// ---- Damm32 拟群：x ⊙ y = 2 · (x ⊕ y)，在 GF(2^5) 上 ----
// 不可约多项式 p(t) = t^5 + t + 1（系数 0x23）。该拟群是弱全反对称拟群，
// 满足 Damm 检出「所有单字符替换 + 所有相邻换位」的充要条件。

// GF(2^5) 乘法：无进位乘 + 模 p(t) 约简
static uint8_t gf_mul(uint8_t a, uint8_t b) {
    uint8_t r = 0;
    for (int i = 0; i < 5; i++) {
        if (b & 1) r ^= a;
        b >>= 1;
        a <<= 1;
        if (a & 0x20) a ^= 0x23;    // p(t) = t^5 + t + 1
    }
    return r & 0x1F;
}

// 拟群运算：x ⊙ y = 2 · (x ⊕ y)；2 = 域元素 t
static uint8_t quasigroup(uint8_t x, uint8_t y) {
    return gf_mul(2, x ^ y);
}

// 将 Crockford Base32 字符转换为索引（0-31）；非法字符（含 I L O U）返回 0xFF。
// 注意：字母表去掉了 I/L/O/U，字母索引不连续，不能用 c-'A'+10 直接换算，须查表/反查。
static uint8_t char_to_index(char c) {
    static const char *CA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
    if (c >= 'a' && c <= 'z') c -= 'a' - 'A';     // 小写 → 大写
    for (uint8_t i = 0; i < 32; i++)
        if (CA[i] == c) return i;
    return 0xFF; // 非法字符（含 I L O U）
}

// 将索引转换回 Crockford Base32 字符（0-31）
static char index_to_char(uint8_t idx) {
    static const char *CA = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
    return (idx < 32) ? CA[idx] : '\0';
}

// 计算 Damm 32 校验字符（输入 = ORG-UNIQUE，不含 CC，可含 '-' 分隔符）
char damm32_compute(const char *input) {
    uint8_t interim = 0;
    size_t len = strlen(input);
    
    for (size_t i = 0; i < len; i++) {
        if (input[i] == '-') continue;       // 跳过分隔符（与 sn_digits 一致）
        uint8_t idx = char_to_index(input[i]);
        if (idx == 0xFF) return '\0'; // 非法输入
        interim = quasigroup(interim, idx);
    }
    // 校验位 c 满足 quasigroup(interim, c) == 0；本构造下
    // 2·(interim⊕c) = 0 ⟺ interim⊕c = 0（2 可逆）⟺ c = interim
    return index_to_char(interim);
}

// 验证 Damm 32 校验（输入 = ORG-UNIQUE-CHECK，不含 CC）。
// 返回 0 同时涵盖「校验位不匹配」与「含非法字符（I/L/O/U 等）」两种情况，调用方无需区分。
int damm32_verify(const char *input) {
    uint8_t interim = 0;
    size_t len = strlen(input);
    
    for (size_t i = 0; i < len; i++) {
        if (input[i] == '-') continue;       // 跳过分隔符（与 sn_digits 一致）
        uint8_t idx = char_to_index(input[i]);
        if (idx == 0xFF) return 0;
        interim = quasigroup(interim, idx);
    }
    
    return (interim == 0);
}
```

> **注意**：拟群由 GF(2⁵) 代数式 `2·(x⊕y)`（`p(t)=t⁵+t+1`）直接计算，无需预置 32×32 表；
> 若真机需免去逐位 GF 乘法，可用 `damm32.py` 的 `build_table()` 生成 32×32 常量表内联（同一构造）。

> **参考实现算例（黄金样本）**：`ORG-UNIQUE` = `WH01-9AF3C1D2` → CHECK = `B`，整串
> `CN-WH01-9AF3C1D2-B` 校验通过（CC=CN，校验位只算 ORG-UNIQUE）。该算例由
> `halow-demo/simulator/orpah/damm32.py` 的自检产生（拟群 `T[x][y] = 2·(x⊕y)`，
> GF(2⁵)、`p(t)=t⁵+t+1`），可作跨实现对照基准。

> 900MHz 地球/月球链路距离参考已移至《[Orpah ID 地外篇](OrpahIDSpace.md)》。

---

### 附录 C：依赖库

| 组件 | 库 | 说明 |
|------|-----|------|
| CH32 I2C HAL | CryptoAuthLib (Microchip) | ATECC608B 驱动 |
| JCS 规范化 | tiny_jcs 或自实现 | RFC 8785 |
| ECDSA 验签 | cryptography (Python) / mbedTLS (C) | server / 调试 |
| HMAC | CH32 软件或 608B Slot 5 | 降级用 |
| Damm 32 表 | 自生成 + 固化 | Phase 2 定稿 |

### 附录 D：修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-09-10 | 初版：SN 编码、校验、签名、降级、报文格式 |
| 1.1 | 2026-09-10 | 新增附录 D（900MHz 地球/月球传输距离参考）；移除防拆相关条款（注：该 900MHz 参考后于 v1.7 移至《Orpah ID 地外篇》§3，本规范“附录 D”现为修订记录） |
| 1.2 | 2026-09-10 | 明确不实施密钥轮换：移除备用/轮换密钥（Slot 2、kid_backup）、kid 并行过渡；新增 §6.3 不轮换说明与撤销-only 生命周期；简化产线烧录、降级流程与注册接口 |
| 1.3 | 2026-09-11 | 移除 kid（Key ID）：公钥检索键改为 SN 本身；hdr 去掉 `kid` 字段，§9.1 注册接口去掉 `kid`/`hmac_kid`（改为 `hmac_key_id`），§9.3 验签改为 `get_by_sn` 并删除 kid-sn 一致性校验 |
| 1.4 | 2026-09-11 | 移除 `hmac_key_id`：HMAC 密钥同样按 SN 检索，每设备一个、终身固定，无需独立 ID；产线记录改为 `{sn, pubkey, se_sn}`（v1.8 起增补 `hmac_key` 为 `{sn, pubkey, hmac_key, se_sn}`），§9.1 注册接口删除 `hmac_key_id`，§9.3 验签改为 `keystore.get_hmac_key(sn)` |
| 1.5 | 2026-09-11 | 协议正式命名为 **Orpah ID**（*Orpah Identity*），文档标题改为《Orpah ID 协议规范》；同步更新线上取值：`hdr.typ` 由 `orpah-report` 改为 `orpah-id-report`，SSID 短码前缀由 `ORPAH_` 改为 `ORPAHID_`，API 路径前缀由 `/orpah/` 改为 `/orpah-id/`；内部代号与文档名统一，无功能变更 |
| 1.6 | 2026-09-11 | 版本号统一（标题与修订记录对齐至 1.6） |
| 1.7 | 2026-09-11 | 本轮修订：① CHECK 字符集改为 Crockford Base32、长度放宽为 0/1/2 位；② 字符集 Base36→**Crockford Base32**（Damm 32 / Luhn mod 32）；③ 精确化**签名预像**定义（`JCS({"hdr":…,"payload":…})`）与 HMAC 预像；④ L3 无签名改用 `alg=none`（仅 `level=3` 接受，视为不可信）；⑤ 新增 §5.7 定位数据源（client 观测 vs router 观测 `xport`）、§5.8 限频；⑥ §5.5 补充无 RTC 与校时；⑦ §6 标注参考实现（非规范性）；§7.1 补“需定制 AP 抓 probe”实现前提与短码不透明；⑧ 地外内容移至《Orpah ID 地外篇》 |
| 1.8 | 2026-09-11 | 审计修正：① **§9.1 注册接口补 `hmac_key`**（降级 HS256 需对称密钥，否则降级后全部拒报），§6.2 Step 3 记录含 hmac_key，§9.3 无密钥时 `reject(no_hmac_key)`；② §3.2 明确 Mod 97 输出为**两位十进制**（Crockford 子集）并修正示例；③ §2.5 正则拆行注释 + Crockford 字符类映射表；④ §1.3 补 STA/AP 别名、§7.1 去除重复括号；⑤ 地外篇版本对齐 v1.8 |
| 1.9 | 2026-09-11 | 二审修正：① 附录 B.2 `char_to_index` 改用 Crockford 字母表反查（原 `c-'A'+10` 忽略 I/L/O/U 致索引错位）；② 附录 B.2 标注“Phase 2 定稿前为示意骨架”；③ 地外篇天体码改用**三字母**（XAA/XBB/XCC），并更正 Apollo 11 为 `Tranquillitatis Statio` 俗名注记 |
| 1.10 | 2026-09-11 | 三审修正：① §3.2 `compute_check` 注释明确传入 `CC-ORG-UNIQUE`（不含 CHECK）；② §9.3 验签伪代码增加 `ts=0` 分支（跳过时间窗口、仅靠 nonce 防重放，呼应 §5.5）；③ 地外篇坐标基准注明 IAU 月心坐标系、月球示例改用嫦娥五号 `Statio Tianchuan` |
| 1.11 | 2026-09-11 | 四审修正：修订历史 v1.1/v1.4 补过期注记（900MHz 附录已移至地外篇 §3；产线记录字段 v1.8 起含 hmac_key）；地外篇经度统一 0–360°E、嫦娥五号补 USGS 引用 |
| 1.12 | 2026-09-11 | 同步地外篇 v1.12（§2.2 删除“俗名 Chang'e 5”矛盾表述，括注改为任务标识） |
| 1.13 | 2026-09-11 | 五审修正：附录 B.2 补**参考实现算例（黄金样本）** `CN-WH01-9AF3C1D2 → CHECK=H`，与 `damm32.py` 相互锚定 |
| 1.14 | 2026-09-11 | 六审修正：附录 B.2 去除占位 32×32 表，改为 GF(2⁵) 代数式 `T[x][y]=2·(x⊕y)` 直接计算（`gf_mul`+`quasigroup`），并补 `-` 分隔符跳过；B.1 补构造定义 |
| 1.15 | 2026-09-11 | 七审修正：① CHECK 只由 `ORG-UNIQUE` 计算（不含 CC；CC=ISO 3166-1 alpha-2 不套 Crockford 限制、不参与校验）；② 附录 B.2 黄金样本 + §2.2 示例校验值按新规则重算（Damm32→`B`、Mod97→`21`）；③ 所有样例统一用 CC=`CN`（删除 JP 示例） |
| 1.16 | 2026-09-11 | 八审修正：§3.2 Mod 97 输出范围更正为 `02`–`98`（校验位不可能为 00/01；原误写 00–96） |
| 1.17 | 2026-09-11 | 九审修正：① §3.2 补 Mod 97 字母→数字映射（IBAN 规则 A=10..Z=35，非 Crockford 索引）与完整校验式；② §11 待验证项 1 更新为「已完成」（Damm32 构造定稿 GF(2⁵)）；③ 附录 B.2 `damm32_verify` 注释说明返回 0 涵盖两种失败原因 |
