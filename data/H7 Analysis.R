Dataset <- read.csv("data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)

# Required packages
library(clubSandwich)
library(marginaleffects)
library(openxlsx)

dir.create("results", showWarnings = FALSE)

# Reference categories
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))
Dataset$platform_category <- factor(Dataset$platform_category, levels=c("Facebook-only","Instagram-only","Both","Other"))

# Check reference levels
levels(Dataset$sector)
levels(Dataset$platform_category)

# H7 Adult-only 18-34 share

# H7 Full descriptive/support sample
d7 <- droplevels(subset(Dataset, platform_category %in% c("Facebook-only","Instagram-only") & !is.na(adult_18_34_share)))

# H7 Cell support
H7.cells <- as.data.frame.matrix(table(d7$sector, d7$platform_category))
H7.cells

# H7 Descriptives by sector and platform
H7.desc <- aggregate(adult_18_34_share ~ sector + platform_category, d7, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x), Min=min(x), Max=max(x)))
H7.desc <- do.call(data.frame, H7.desc)
H7.desc

# H7 Supported interaction sample: exclude Fashion
d7s <- droplevels(subset(d7, sector!="fashion"))

# H7 Sample
H7.sample <- data.frame(N=nrow(d7s), Retailers=length(unique(d7s$search_brand)))
H7.sample

# H7 Primary platform-by-sector interaction model
GLM.3 <- glm(adult_18_34_share ~ platform_category * sector, family=quasibinomial(logit), data=d7s)
summary(GLM.3)

# H7 Convergence
H7.converged <- data.frame(Converged=GLM.3$converged)
H7.converged

# H7 Specification / link test
d7s$hat <- predict(GLM.3, type="link")
d7s$hat2 <- d7s$hat^2

m <- glm(adult_18_34_share ~ hat + hat2, family=quasibinomial(logit), data=d7s)

H7.link <- data.frame(Term=rownames(summary(m)$coefficients), summary(m)$coefficients, row.names=NULL)
H7.link

# H7 Retailer-clustered CR2 inference
H7.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d7s$search_brand, test="Satterthwaite")
H7.cr2

# H7 Joint moderation test
H7.joint <- Wald_test(GLM.3, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d7s$search_brand, test="HTZ")
H7.joint

# H7 Predicted shares and sector-specific platform contrasts
V3 <- vcovCR(GLM.3, cluster=d7s$search_brand, type="CR2")

H7.pred <- avg_predictions(GLM.3, by=c("platform_category","sector"), vcov=V3, type="response")
H7.pred

H7.comp <- avg_comparisons(GLM.3, variables=list(platform_category="reference"), by="sector", vcov=V3, type="response")
H7.comp

# H7 LOBO
LOBO <- do.call(rbind, lapply(unique(d7s$search_brand), function(b){
  m <- glm(adult_18_34_share ~ platform_category * sector, family=quasibinomial(logit), data=d7s[d7s$search_brand != b,])
  x <- as.data.frame(avg_comparisons(m, variables=list(platform_category="reference"), by="sector", type="response"))
  x$brand <- b
  x
}))

H7.lobo <- do.call(data.frame, aggregate(estimate ~ contrast + sector, LOBO, function(x) c(min=min(x), max=max(x))))
H7.lobo

# H7 Minimum adult reach >=1000
d <- droplevels(subset(d7s, known_adult_reach >= 1000))

H7.reach1000.sample <- data.frame(N=nrow(d), Retailers=length(unique(d$search_brand)))
H7.reach1000.sample

m <- glm(adult_18_34_share ~ platform_category * sector, family=quasibinomial(logit), data=d)

H7.reach1000.cr2 <- coef_test(m, vcov="CR2", cluster=d$search_brand, test="Satterthwaite")
H7.reach1000.cr2

H7.reach1000.joint <- Wald_test(m, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d$search_brand, test="HTZ")
H7.reach1000.joint

V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H7.reach1000.pred <- avg_predictions(m, by=c("platform_category","sector"), vcov=V, type="response")
H7.reach1000.pred

H7.reach1000.comp <- avg_comparisons(m, variables=list(platform_category="reference"), by="sector", vcov=V, type="response")
H7.reach1000.comp

# Remove unnecessary df and s.value columns before Excel export
for (x in c("H7.pred","H7.comp","H7.reach1000.pred","H7.reach1000.comp")) {
  z <- as.data.frame(get(x))
  if ("df" %in% names(z)) z$df <- NULL
  if ("s.value" %in% names(z)) z$s.value <- NULL
  assign(x, z)
}

# Export H7 results
file <- "results/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H7" %in% names(wb)) removeWorksheet(wb, "H7")
addWorksheet(wb, "H7")

r <- 1
put <- function(title, x, rowNames=FALSE){
  writeData(wb, "H7", title, startRow=r)
  r <<- r+1
  writeData(wb, "H7", as.data.frame(x), startRow=r, rowNames=rowNames)
  r <<- r+nrow(as.data.frame(x))+2
}

put("H7 Cell support", H7.cells, rowNames=TRUE)
put("H7 Descriptives by sector and platform", H7.desc)
put("H7 Supported sample", H7.sample)
put("H7 Convergence", H7.converged)
put("H7 Link test", H7.link)
put("H7 CR2 inference", H7.cr2, rowNames=TRUE)
put("H7 Joint platform x sector interaction test", H7.joint)
put("H7 Predicted adult 18-34 shares by sector and platform", H7.pred)
put("H7 Platform contrasts by sector", H7.comp)
put("H7 LOBO ranges", H7.lobo)

put("H7 Reach >=1000 sample", H7.reach1000.sample)
put("H7 Reach >=1000 CR2 inference", H7.reach1000.cr2, rowNames=TRUE)
put("H7 Reach >=1000 joint interaction test", H7.reach1000.joint)
put("H7 Reach >=1000 predicted shares", H7.reach1000.pred)
put("H7 Reach >=1000 contrasts", H7.reach1000.comp)

saveWorkbook(wb, file, overwrite=TRUE)



