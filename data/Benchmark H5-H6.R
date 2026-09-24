Dataset <- read.csv("C:/Users/Rishu/Desktop/meta-retail-ads-collection2/data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)
Benchmark <- read.csv("C:/Users/Rishu/Desktop/github_benchmark_upload_final/benchmark/meta_audience_estimates_germany.csv", stringsAsFactors=FALSE)

library(openxlsx)

Dataset$target_gender <- factor(Dataset$target_gender, levels=c("All","Men","Women"))
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))
Dataset$platform_category <- factor(Dataset$platform_category, levels=c("Both","Facebook-only","Instagram-only","Other"))

# Benchmark bounds
Benchmark.gender <- Benchmark[Benchmark$age_band=="18-65+" & Benchmark$gender %in% c("male","female"),]

x <- Benchmark.gender[Benchmark.gender$platform_scope=="facebook_instagram",]
female <- x[x$gender=="female",]
male <- x[x$gender=="male",]
B1 <- data.frame(benchmark_scope="facebook_instagram",
                 benchmark_lower=female$estimate_mau_lower_bound/(female$estimate_mau_lower_bound + male$estimate_mau_upper_bound),
                 benchmark_upper=female$estimate_mau_upper_bound/(female$estimate_mau_upper_bound + male$estimate_mau_lower_bound))

x <- Benchmark.gender[Benchmark.gender$platform_scope=="facebook_only",]
female <- x[x$gender=="female",]
male <- x[x$gender=="male",]
B2 <- data.frame(benchmark_scope="facebook_only",
                 benchmark_lower=female$estimate_mau_lower_bound/(female$estimate_mau_lower_bound + male$estimate_mau_upper_bound),
                 benchmark_upper=female$estimate_mau_upper_bound/(female$estimate_mau_upper_bound + male$estimate_mau_lower_bound))

x <- Benchmark.gender[Benchmark.gender$platform_scope=="instagram_only",]
female <- x[x$gender=="female",]
male <- x[x$gender=="male",]
B3 <- data.frame(benchmark_scope="instagram_only",
                 benchmark_lower=female$estimate_mau_lower_bound/(female$estimate_mau_lower_bound + male$estimate_mau_upper_bound),
                 benchmark_upper=female$estimate_mau_upper_bound/(female$estimate_mau_upper_bound + male$estimate_mau_lower_bound))

Benchmark.shares <- rbind(B1,B2,B3)
Benchmark.shares

# H4 benchmark sample
H4.benchmark.data <- droplevels(subset(Dataset, target_gender=="All" & !is.na(female_delivery_share) & !is.na(platform_category) & !is.na(sector)))

H4.benchmark.data$benchmark_scope <- NA
H4.benchmark.data$benchmark_scope[H4.benchmark.data$platform_category=="Both"] <- "facebook_instagram"
H4.benchmark.data$benchmark_scope[H4.benchmark.data$platform_category=="Facebook-only"] <- "facebook_only"
H4.benchmark.data$benchmark_scope[H4.benchmark.data$platform_category=="Instagram-only"] <- "instagram_only"

table(H4.benchmark.data$platform_category, H4.benchmark.data$benchmark_scope, useNA="ifany")

H4.benchmark.data <- droplevels(H4.benchmark.data[!is.na(H4.benchmark.data$benchmark_scope),])
H4.benchmark.data <- merge(H4.benchmark.data, Benchmark.shares, by="benchmark_scope", all.x=TRUE)

H4.benchmark.data$signed_gap_lower <- H4.benchmark.data$female_delivery_share - H4.benchmark.data$benchmark_lower
H4.benchmark.data$signed_gap_upper <- H4.benchmark.data$female_delivery_share - H4.benchmark.data$benchmark_upper
H4.benchmark.data$absolute_gap_lower <- abs(H4.benchmark.data$signed_gap_lower)
H4.benchmark.data$absolute_gap_upper <- abs(H4.benchmark.data$signed_gap_upper)

H4.benchmark <- aggregate(cbind(female_delivery_share, signed_gap_lower, signed_gap_upper, absolute_gap_lower, absolute_gap_upper) ~ sector, H4.benchmark.data, mean)
H4.benchmark[,2:6] <- H4.benchmark[,2:6] * 100
names(H4.benchmark) <- c("Sector","Observed_female_share_percent","Signed_gap_lower_pp","Signed_gap_upper_pp","Absolute_gap_lower_pp","Absolute_gap_upper_pp")
H4.benchmark

H4.retailers <- length(unique(H4.benchmark.data$search_brand))
H4.retailers

# H5 benchmark sample
H5.benchmark.data <- droplevels(subset(Dataset, target_gender=="All" & platform_category %in% c("Facebook-only","Instagram-only") & sector!="fashion" & !is.na(female_delivery_share) & !is.na(sector)))

H5.benchmark.data$benchmark_scope <- NA
H5.benchmark.data$benchmark_scope[H5.benchmark.data$platform_category=="Facebook-only"] <- "facebook_only"
H5.benchmark.data$benchmark_scope[H5.benchmark.data$platform_category=="Instagram-only"] <- "instagram_only"

H5.benchmark.data <- merge(H5.benchmark.data, Benchmark.shares, by="benchmark_scope", all.x=TRUE)

H5.benchmark.data$signed_gap_lower <- H5.benchmark.data$female_delivery_share - H5.benchmark.data$benchmark_lower
H5.benchmark.data$signed_gap_upper <- H5.benchmark.data$female_delivery_share - H5.benchmark.data$benchmark_upper
H5.benchmark.data$absolute_gap_lower <- abs(H5.benchmark.data$signed_gap_lower)
H5.benchmark.data$absolute_gap_upper <- abs(H5.benchmark.data$signed_gap_upper)

H5.benchmark <- aggregate(cbind(female_delivery_share, signed_gap_lower, signed_gap_upper, absolute_gap_lower, absolute_gap_upper) ~ platform_category, H5.benchmark.data, mean)
H5.benchmark[,2:6] <- H5.benchmark[,2:6] * 100
names(H5.benchmark) <- c("Platform","Observed_female_share_percent","Signed_gap_lower_pp","Signed_gap_upper_pp","Absolute_gap_lower_pp","Absolute_gap_upper_pp")
H5.benchmark

H5.retailers <- length(unique(H5.benchmark.data$search_brand))
H5.retailers

# Export
file <- "C:/Users/Rishu/Desktop/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("Benchmark_H4_H5" %in% names(wb)) removeWorksheet(wb, "Benchmark_H4_H5")
addWorksheet(wb, "Benchmark_H4_H5")

r <- 1

writeData(wb, "Benchmark_H4_H5", "Meta benchmark female-share bounds", startRow=r)
r <- r+1
writeData(wb, "Benchmark_H4_H5", Benchmark.shares, startRow=r)
r <- r+nrow(Benchmark.shares)+2

writeData(wb, "Benchmark_H4_H5", "H4 benchmark gaps by sector (percentage points)", startRow=r)
r <- r+1
writeData(wb, "Benchmark_H4_H5", H4.benchmark, startRow=r)
r <- r+nrow(H4.benchmark)+2

writeData(wb, "Benchmark_H4_H5", "H4 retailer count", startRow=r)
r <- r+1
writeData(wb, "Benchmark_H4_H5", data.frame(Retailers=H4.retailers), startRow=r)
r <- r+3

writeData(wb, "Benchmark_H4_H5", "H5 benchmark gaps by platform (percentage points)", startRow=r)
r <- r+1
writeData(wb, "Benchmark_H4_H5", H5.benchmark, startRow=r)
r <- r+nrow(H5.benchmark)+2

writeData(wb, "Benchmark_H4_H5", "H5 retailer count", startRow=r)
r <- r+1
writeData(wb, "Benchmark_H4_H5", data.frame(Retailers=H5.retailers), startRow=r)

saveWorkbook(wb, file, overwrite=TRUE)

