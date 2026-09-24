Dataset <- read.csv("C:/Users/Rishu/Desktop/meta-retail-ads-collection2/data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)

# Required packages
library(clubSandwich)
library(marginaleffects)
library(openxlsx)

# Reference categories
Dataset$target_gender <- factor(Dataset$target_gender, levels=c("All","Men","Women"))
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))
Dataset$platform_category <- factor(Dataset$platform_category, levels=c("Both","Facebook-only","Instagram-only","Other"))

# Check reference levels
levels(Dataset$target_gender)
levels(Dataset$sector)
levels(Dataset$platform_category)

# H3 Cell support
H3.sector.cells <- as.data.frame.matrix(table(Dataset$target_gender, Dataset$sector))
H3.sector.cells

H3.platform.cells <- as.data.frame.matrix(table(Dataset$target_gender, Dataset$platform_category))
H3.platform.cells

# H3a Women vs All: Sector interaction
d_sec <- droplevels(subset(Dataset, target_gender %in% c("All","Women") & sector %in% c("fashion","health_beauty") & !is.na(female_delivery_share)))

# H3a Descriptives
H3a.desc <- aggregate(female_delivery_share ~ target_gender + sector, d_sec, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x)))
H3a.desc <- do.call(data.frame, H3a.desc)
H3a.desc

# H3a Sample
H3a.sample <- data.frame(N=nrow(d_sec), Retailers=length(unique(d_sec$search_brand)))
H3a.sample

# H3a Primary fractional-logit model
GLM.3 <- glm(female_delivery_share ~ target_gender * sector + platform_category, family=quasibinomial(logit), data=d_sec)
summary(GLM.3)

H3a.converged <- data.frame(Converged=GLM.3$converged)
H3a.converged

H3a.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d_sec$search_brand, test="Satterthwaite")
H3a.cr2

H3a.joint <- Wald_test(GLM.3, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d_sec$search_brand, test="HTZ")
H3a.joint

V3 <- vcovCR(GLM.3, cluster=d_sec$search_brand, type="CR2")

H3a.pred <- avg_predictions(GLM.3, by=c("target_gender","sector"), vcov=V3, type="response")
H3a.pred

H3a.comp <- avg_comparisons(GLM.3, variables=list(target_gender="reference"), by="sector", vcov=V3, type="response")
H3a.comp

# H3a LOBO
LOBO.sector <- do.call(rbind, lapply(unique(d_sec$search_brand), function(b){ m <- glm(female_delivery_share ~ target_gender * sector + platform_category, family=quasibinomial(logit), data=d_sec[d_sec$search_brand != b,]); x <- as.data.frame(avg_comparisons(m, variables=list(target_gender="reference"), by="sector", type="response")); x$brand <- b; x }))

H3a.lobo <- do.call(data.frame, aggregate(estimate ~ contrast + sector, LOBO.sector, function(x) c(min=min(x), max=max(x))))
H3a.lobo

# H3a Minimum reach >=1000
d <- droplevels(subset(d_sec, known_gender_reach >= 1000))

m <- glm(female_delivery_share ~ target_gender * sector + platform_category, family=quasibinomial(logit), data=d)

H3a.reach1000.joint <- Wald_test(m, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d$search_brand, test="HTZ")
H3a.reach1000.joint

V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H3a.reach1000.comp <- avg_comparisons(m, variables=list(target_gender="reference"), by="sector", vcov=V, type="response")
H3a.reach1000.comp

# H3b Women vs All: Platform interaction
d_plat <- droplevels(subset(Dataset, target_gender %in% c("All","Women") & platform_category %in% c("Both","Instagram-only","Other") & !is.na(female_delivery_share)))

# H3b Descriptives
H3b.desc <- aggregate(female_delivery_share ~ target_gender + platform_category, d_plat, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x)))
H3b.desc <- do.call(data.frame, H3b.desc)
H3b.desc

# H3b Sample
H3b.sample <- data.frame(N=nrow(d_plat), Retailers=length(unique(d_plat$search_brand)))
H3b.sample

# H3b Primary fractional-logit model
GLM.3 <- glm(female_delivery_share ~ target_gender * platform_category + sector, family=quasibinomial(logit), data=d_plat)
summary(GLM.3)

H3b.converged <- data.frame(Converged=GLM.3$converged)
H3b.converged

H3b.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d_plat$search_brand, test="Satterthwaite")
H3b.cr2

H3b.joint <- Wald_test(GLM.3, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d_plat$search_brand, test="HTZ")
H3b.joint

V3 <- vcovCR(GLM.3, cluster=d_plat$search_brand, type="CR2")

H3b.pred <- avg_predictions(GLM.3, by=c("target_gender","platform_category"), vcov=V3, type="response")
H3b.pred

H3b.comp <- avg_comparisons(GLM.3, variables=list(target_gender="reference"), by="platform_category", vcov=V3, type="response")
H3b.comp

# H3b LOBO
LOBO.platform <- do.call(rbind, lapply(unique(d_plat$search_brand), function(b){ m <- glm(female_delivery_share ~ target_gender * platform_category + sector, family=quasibinomial(logit), data=d_plat[d_plat$search_brand != b,]); x <- as.data.frame(avg_comparisons(m, variables=list(target_gender="reference"), by="platform_category", type="response")); x$brand <- b; x }))

H3b.lobo <- do.call(data.frame, aggregate(estimate ~ contrast + platform_category, LOBO.platform, function(x) c(min=min(x), max=max(x))))
H3b.lobo

# H3b Minimum reach >=1000
d <- droplevels(subset(d_plat, known_gender_reach >= 1000))

m <- glm(female_delivery_share ~ target_gender * platform_category + sector, family=quasibinomial(logit), data=d)

H3b.reach1000.joint <- Wald_test(m, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d$search_brand, test="HTZ")
H3b.reach1000.joint

V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H3b.reach1000.comp <- avg_comparisons(m, variables=list(target_gender="reference"), by="platform_category", vcov=V, type="response")
H3b.reach1000.comp

# Remove non-finite df and s.value columns before Excel export
for (x in c("H3a.pred","H3a.comp","H3a.reach1000.comp","H3b.pred","H3b.comp","H3b.reach1000.comp")) {
  z <- as.data.frame(get(x))
  if ("df" %in% names(z)) z$df <- NULL
  if ("s.value" %in% names(z)) z$s.value <- NULL
  assign(x, z)
}

# Export H3 results
file <- "C:/Users/Rishu/Desktop/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H3" %in% names(wb)) removeWorksheet(wb, "H3")
addWorksheet(wb, "H3")

r <- 1
put <- function(title, x, rowNames=FALSE){ writeData(wb, "H3", title, startRow=r); r <<- r+1; writeData(wb, "H3", as.data.frame(x), startRow=r, rowNames=rowNames); r <<- r+nrow(as.data.frame(x))+2 }

put("H3 Sector cell support", H3.sector.cells, rowNames=TRUE)
put("H3 Platform cell support", H3.platform.cells, rowNames=TRUE)

put("H3a Descriptives", H3a.desc)
put("H3a Sample", H3a.sample)
put("H3a Convergence", H3a.converged)
put("H3a CR2 inference", H3a.cr2, rowNames=TRUE)
put("H3a Joint interaction test", H3a.joint)
put("H3a Predicted female shares", H3a.pred)
put("H3a Women vs All contrasts by sector", H3a.comp)
put("H3a LOBO ranges", H3a.lobo)
put("H3a Reach >=1000 joint interaction test", H3a.reach1000.joint)
put("H3a Reach >=1000 contrasts", H3a.reach1000.comp)

put("H3b Descriptives", H3b.desc)
put("H3b Sample", H3b.sample)
put("H3b Convergence", H3b.converged)
put("H3b CR2 inference", H3b.cr2, rowNames=TRUE)
put("H3b Joint interaction test", H3b.joint)
put("H3b Predicted female shares", H3b.pred)
put("H3b Women vs All contrasts by platform", H3b.comp)
put("H3b LOBO ranges", H3b.lobo)
put("H3b Reach >=1000 joint interaction test", H3b.reach1000.joint)
put("H3b Reach >=1000 contrasts", H3b.reach1000.comp)

saveWorkbook(wb, file, overwrite=TRUE)

