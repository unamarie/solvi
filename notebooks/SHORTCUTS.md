# OneLake shortcuts

Create these in each consuming lakehouse. Name = source domain + table, like `coredimsite`. Read-only; the source domain owns the data.

| In lakehouse | Shortcut name | Points to |
|---|---|---|
| Sales | coresilvercustomer | Core / silvercustomer |
| Sales | coresilverproduct | Core / silverproduct |
| Sales | coredimproduct | Core / dimproduct |
| Supply | salessilversalesorder | Sales / silversalesorder |
| Delivery | salessilversalesorder | Sales / silversalesorder |
| Delivery | supplysilverbatterydelivery | Supply / silverbatterydelivery |
| Delivery | supplysilversupplier | Supply / silversupplier |
| Assets | coresilvercustomer | Core / silvercustomer |
| Assets | coresilversite | Core / silversite |
| Assets | salessilversalesorder | Sales / silversalesorder |
| Assets | coredimsite | Core / dimsite |
| Assets | corefactweatherdaily | Core / factweatherdaily |
| HSEQ | assetssilverinstallation | Assets / silverinstallation |
| HSEQ | deliverysilverjob | Delivery / silverjob |
| HSEQ | assetsdiminstallation | Assets / diminstallation |
| HSEQ | deliveryfactjob | Delivery / factjob |
| HSEQ | supplyfactbatterydelivery | Supply / factbatterydelivery |
| HSEQ | supplydimsupplier | Supply / dimsupplier |
| HSEQ | deliverydimcrew | Delivery / dimcrew |
| HSEQ | supplyfactsupplierprequal | Supply / factsupplierprequal |
| HSEQ | coredimsite | Core / dimsite |
| HSEQ | coredimcustomer | Core / dimcustomer |
| HSEQ | corefactweatherforecast | Core / factweatherforecast |
| HSEQ | salesfactorderline | Sales / factorderline |
