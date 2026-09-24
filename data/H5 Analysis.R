Dataset <- read.csv("data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)

# Required packages
library(clubSandwich)
library(marginaleffects)
library(openxlsx)

dir.create("results", showWarnings = FALSE)

# Reference categories
Dataset$target_gender <- factor(Dataset$target_gender, levels=c("All","Men","Women"))
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))
Dataset$platform_category <- factor(Dataset$platform_category, levels=c("Facebook-only","Instagram-only","Both","Other"))

# Check reference levels
levels(Dataset$target_gender)
levels(Dataset$sector)
levels(Dataset$platform_category)

# H5 Sample: unrestricted ads, Facebook-only vs Instagram-only
d5 <- droplevels(subset(Dataset, target_gender=="All" & platform_category %in% c("Facebook-only","Instagram-only") & !is.na(female_delivery_share)))

# H5 Cell support
H5.cells <- as.data.frame.matrix(table(d5$sector, d5$platform_category))
H5.cells

# H5 Descriptives
H5.desc <- aggregate(female_delivery_share ~ platform_category, d5, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x), Min=min(x), Max=max(x)))
H5.desc <- do.call(data.frame, H5.desc)
H5.desc

# H5 Descriptives by sector and platform
H5.desc.sector <- aggregate(female_delivery_share ~ sector + platform_category, d5, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x)))
H5.desc.sector <- do.call(data.frame, H5.desc.sector)
H5.desc.sector

# H5 Sample
H5.sample <- data.frame(N=nrow(d5), Retailers=length(unique(d5$search_brand)))
H5.sample

# H5 Primary pooled fractional-logit model
GLM.3 <- glm(female_delivery_share ~ platform_category + sector, family=quasibinomial(logit), data=d5)
summary(GLM.3)

# H5 Convergence
H5.converged <- data.frame(Converged=GLM.3$converged)
H5.converged

# H5 Specification / link test
d5$hat <- predict(GLM.3, type="link")
d5$hat2 <- d5$hat^2

m <- glm(female_delivery_share ~ hat + hat2, family=quasibinomial(logit), data=d5)

H5.link <- data.frame(
  Term=rownames(summary(m)$coefficients),
  summary(m)$coefficients,
  row.names=NULL
)

H5.link

# H5 Retailer-clustered CR2 inference
H5.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d5$search_brand, test="Satterthwaite")
H5.cr2

# H5 Supported common-comparison sample
d5s <- droplevels(subset(d5, sector!="fashion"))

H5.supported.sample <- data.frame(N=nrow(d5s), Retailers=length(unique(d5s$search_brand)))
H5.supported.sample

# H5 Adjusted predicted shares and pooled contrast
V3 <- vcovCR(GLM.3, cluster=d5$search_brand, type="CR2")

H5.pred <- avg_predictions(GLM.3, variables="platform_category", newdata=d5s, vcov=V3, type="response")
H5.pred

H5.comp <- avg_comparisons(GLM.3, variables=list(platform_category="reference"), newdata=d5s, vcov=V3, type="response")
H5.comp

# H5 Platform-by-sector interaction on supported sectors only
m <- glm(female_delivery_share ~ platform_category * sector, family=quasibinomial(logit), data=d5s)

H5.interaction.converged <- data.frame(Converged=m$converged)
H5.interaction.converged

H5.interaction.cr2 <- coef_test(m, vcov="CR2", cluster=d5s$search_brand, test="Satterthwaite")
H5.interaction.cr2

H5.interaction.joint <- Wald_test(m, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d5s$search_brand, test="HTZ")
H5.interaction.joint

V <- vcovCR(m, cluster=d5s$search_brand, type="CR2")

H5.interaction.pred <- avg_predictions(m, by=c("platform_category","sector"), vcov=V, type="response")
H5.interaction.pred

H5.interaction.comp <- avg_comparisons(m, variables=list(platform_category="reference"), by="sector", vcov=V, type="response")
H5.interaction.comp

# H5 LOBO for pooled platform contrast
LOBO <- do.call(rbind, lapply(unique(d5$search_brand), function(b){
  m <- glm(female_delivery_share ~ platform_category + sector, family=quasibinomial(logit), data=d5[d5$search_brand != b,])
  x <- as.data.frame(avg_comparisons(m, variables=list(platform_category="reference"), newdata=droplevels(subset(d5[d5$search_brand != b,], sector!="fashion")), type="response"))
  x$brand <- b
  x
}))

H5.lobo <- do.call(data.frame, aggregate(estimate ~ contrast, LOBO, function(x) c(min=min(x), max=max(x))))
H5.lobo

# H5 Minimum reach >=1000
d <- droplevels(subset(d5, known_gender_reach >= 1000))

H5.reach1000.sample <- data.frame(N=nrow(d), Retailers=length(unique(d$search_brand)))
H5.reach1000.sample

m <- glm(female_delivery_share ~ platform_category + sector, family=quasibinomial(logit), data=d)

H5.reach1000.cr2 <- coef_test(m, vcov="CR2", cluster=d$search_brand, test="Satterthwaite")
H5.reach1000.cr2

ds <- droplevels(subset(d, sector!="fashion"))
V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H5.reach1000.pred <- avg_predictions(m, variables="platform_category", newdata=ds, vcov=V, type="response")
H5.reach1000.pred

H5.reach1000.comp <- avg_comparisons(m, variables=list(platform_category="reference"), newdata=ds, vcov=V, type="response")
H5.reach1000.comp

# Remove unnecessary df and s.value columns before Excel export
for (x in c("H5.pred","H5.comp","H5.interaction.pred","H5.interaction.comp","H5.reach1000.pred","H5.reach1000.comp")) {
  z <- as.data.frame(get(x))
  if ("df" %in% names(z)) z$df <- NULL
  if ("s.value" %in% names(z)) z$s.value <- NULL
  assign(x, z)
}

# Export H5 results
file <- "results/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H5" %in% names(wb)) removeWorksheet(wb, "H5")
addWorksheet(wb, "H5")

r <- 1
put <- function(title, x, rowNames=FALSE){
  writeData(wb, "H5", title, startRow=r)
  r <<- r+1
  writeData(wb, "H5", as.data.frame(x), startRow=r, rowNames=rowNames)
  r <<- r+nrow(as.data.frame(x))+2
}

put("H5 Cell support", H5.cells, rowNames=TRUE)
put("H5 Descriptives", H5.desc)
put("H5 Descriptives by sector and platform", H5.desc.sector)
put("H5 Sample", H5.sample)
put("H5 Convergence", H5.converged)
put("H5 Link test", H5.link)
put("H5 CR2 inference", H5.cr2, rowNames=TRUE)
put("H5 Supported comparison sample", H5.supported.sample)
put("H5 Adjusted predicted shares", H5.pred)
put("H5 Facebook vs Instagram contrast", H5.comp)

put("H5 Interaction convergence", H5.interaction.converged)
put("H5 Interaction CR2 inference", H5.interaction.cr2, rowNames=TRUE)
put("H5 Joint platform x sector interaction test", H5.interaction.joint)
put("H5 Predicted shares by sector and platform", H5.interaction.pred)
put("H5 Platform contrasts by sector", H5.interaction.comp)

put("H5 LOBO range", H5.lobo)

put("H5 Reach >=1000 sample", H5.reach1000.sample)
put("H5 Reach >=1000 CR2 inference", H5.reach1000.cr2, rowNames=TRUE)
put("H5 Reach >=1000 predicted shares", H5.reach1000.pred)
put("H5 Reach >=1000 contrast", H5.reach1000.comp)

saveWorkbook(wb, file, overwrite=TRUE)


