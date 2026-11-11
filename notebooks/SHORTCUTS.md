# OneLake shortcuts

Create these in each consuming lakehouse. Name = `<source domain>_<table>`. Read-only; the source domain owns the data.

| In lakehouse | Shortcut name | Points to |
|---|---|---|
| lh_sales | core_silver_customer | lh_core / silver_customer |
| lh_sales | core_silver_product | lh_core / silver_product |
| lh_sales | core_dim_product | lh_core / dim_product |
| lh_supply | sales_silver_sales_order | lh_sales / silver_sales_order |
| lh_delivery | sales_silver_sales_order | lh_sales / silver_sales_order |
| lh_delivery | supply_silver_battery_delivery | lh_supply / silver_battery_delivery |
| lh_delivery | supply_silver_supplier | lh_supply / silver_supplier |
| lh_assets | core_silver_customer | lh_core / silver_customer |
| lh_assets | core_silver_site | lh_core / silver_site |
| lh_assets | sales_silver_sales_order | lh_sales / silver_sales_order |
| lh_assets | core_dim_site | lh_core / dim_site |
| lh_assets | core_fact_weather_daily | lh_core / fact_weather_daily |
| lh_hseq | assets_silver_installation | lh_assets / silver_installation |
| lh_hseq | delivery_silver_job | lh_delivery / silver_job |
| lh_hseq | assets_dim_installation | lh_assets / dim_installation |
| lh_hseq | delivery_fact_job | lh_delivery / fact_job |
| lh_hseq | supply_fact_battery_delivery | lh_supply / fact_battery_delivery |
| lh_hseq | supply_dim_supplier | lh_supply / dim_supplier |
| lh_hseq | delivery_dim_crew | lh_delivery / dim_crew |
| lh_hseq | supply_fact_supplier_prequal | lh_supply / fact_supplier_prequal |
| lh_hseq | core_dim_site | lh_core / dim_site |
| lh_hseq | core_dim_customer | lh_core / dim_customer |
| lh_hseq | core_fact_weather_forecast | lh_core / fact_weather_forecast |
| lh_hseq | sales_fact_order_line | lh_sales / fact_order_line |
