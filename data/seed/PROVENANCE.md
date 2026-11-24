# 数据来源与口径

- 数据集：Amazon Reviews 2023（McAuley-Lab/Amazon-Reviews-2023），类别 All Beauty。
- 上游地址：https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
- 引用：Hou, Y., Li, J., He, Z., Yan, A., Chen, X., & McAuley, J. (2024). Bridging Language and Items for Retrieval and Recommendation. arXiv:2403.03952.
- 许可与用途：该数据集面向研究与非商业用途；本仓库只用于公开演示。
- 快照下载日期：2026-11-23（评论时间截至 2023 年）。
- 元数据文件 sha256：`1cfbdf6d2ccf9c3ac52a4508b15f31f8f340508a245b65c3e3b5f461e06e97ef`
- 评论文件 sha256：`36ca7c48440a8247b2dca0174d095238422b506a8a80c114dca722b7715f1c94`

## 哪些是真实数据

- 5 个主 SKU 的商品标题、五点、描述、价格、评分、评论数、原始评论正文和评论日期。
- 20 条历史 Listing 的标题、五点、描述、评分、评论数。
- 评论按 helpful_vote 取前 50 条后确定性打乱，仅保留 rating/title/text/date/verified_purchase。

## 哪些是模拟数据

- 广告：90 天 impressions / clicks / spend / sales、关键词出价与 30 天回测数据。
- 库存、成本、目标 ACOS、当前出价、关键词搜索量。
- 历史 Listing 的 conversion_rate（由评分与评论数估算，非真实转化率）。

## 匿名化与清洗

- 5 个主 SKU 的品牌名替换为 Brand A–E；评论中的 user_id、图片、helpful_vote 不落种子。
- 用于生成草稿的 title / bullets / description 会移除违规宣称（100%、guarantee、medical grade、made in USA 等）；
  `current_listing` 保留真实原文，用于演示合规扫描。

## 主 SKU 对照

| SKU | parent_asin | 评分 | 评论数 | 价格 |
|---|---|---|---|---|
| SKU-001 | B019GBG0IE | 4.1 | 5312 | 16.99 |
| SKU-002 | B07D1B499B | 3.7 | 2425 | 7.99 |
| SKU-003 | B074CQC2NG | 3.4 | 2945 | 16.95 |
| SKU-004 | B00692OA2M | 4.0 | 582 | 31.14 |
| SKU-005 | B0BMWQQR9W | 4.2 | 3892 | 6.97 |
