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

# H6 Adult-only 18-34 share

# H6 Full descriptive/support sample
d6 <- droplevels(subset(Dataset, platform_category %in% c("Facebook-only","Instagram-only") & !is.na(adult_18_34_share)))

# H6 Cell support
H6.cells <- as.data.frame.matrix(table(d6$sector, d6$platform_category))
H6.cells

# H6 Descriptives
H6.desc <- aggregate(adult_18_34_share ~ platform_category, d6, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x), Min=min(x), Max=max(x)))
H6.desc <- do.call(data.frame, H6.desc)
H6.desc

# H6 Descriptives by sector and platform
H6.desc.sector <- aggregate(adult_18_34_share ~ sector + platform_category, d6, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x)))
H6.desc.sector <- do.call(data.frame, H6.desc.sector)
H6.desc.sector

# H6 Supported comparison sample: exclude Fashion
d6s <- droplevels(subset(d6, sector!="fashion"))

H6.sample <- data.frame(N=nrow(d6s), Retailers=length(unique(d6s$search_brand)))
H6.sample

# H6 Primary pooled fractional-logit model
GLM.3 <- glm(adult_18_34_share ~ platform_category + sector, family=quasibinomial(logit), data=d6s)
summary(GLM.3)

# H6 Convergence
H6.converged <- data.frame(Converged=GLM.3$converged)
H6.converged

# H6 Specification / link test
d6s$hat <- predict(GLM.3, type="link")
d6s$hat2 <- d6s$hat^2

m <- glm(adult_18_34_share ~ hat + hat2, family=quasibinomial(logit), data=d6s)

H6.link <- data.frame(Term=rownames(summary(m)$coefficients), summary(m)$coefficients, row.names=NULL)
H6.link

# H6 Retailer-clustered CR2 inference
H6.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d6s$search_brand, test="Satterthwaite")
H6.cr2

# H6 Adjusted predicted shares and platform contrast
V3 <- vcovCR(GLM.3, cluster=d6s$search_brand, type="CR2")

H6.pred <- avg_predictions(GLM.3, variables="platform_category", vcov=V3, type="response")
H6.pred

H6.comp <- avg_comparisons(GLM.3, variables=list(platform_category="reference"), vcov=V3, type="response")
H6.comp

# H6 Platform-by-sector interaction on supported sectors
m <- glm(adult_18_34_share ~ platform_category * sector, family=quasibinomial(logit), data=d6s)

H6.interaction.converged <- data.frame(Converged=m$converged)
H6.interaction.converged

H6.interaction.cr2 <- coef_test(m, vcov="CR2", cluster=d6s$search_brand, test="Satterthwaite")
H6.interaction.cr2

H6.interaction.joint <- Wald_test(m, constraints=constrain_zero(":", reg_ex=TRUE), vcov="CR2", cluster=d6s$search_brand, test="HTZ")
H6.interaction.joint

V <- vcovCR(m, cluster=d6s$search_brand, type="CR2")

H6.interaction.pred <- avg_predictions(m, by=c("platform_category","sector"), vcov=V, type="response")
H6.interaction.pred

H6.interaction.comp <- avg_comparisons(m, variables=list(platform_category="reference"), by="sector", vcov=V, type="response")
H6.interaction.comp

# H6 LOBO
LOBO <- do.call(rbind, lapply(unique(d6s$search_brand), function(b){
  m <- glm(adult_18_34_share ~ platform_category + sector, family=quasibinomial(logit), data=d6s[d6s$search_brand != b,])
  x <- as.data.frame(avg_comparisons(m, variables=list(platform_category="reference"), type="response"))
  x$brand <- b
  x
}))

H6.lobo <- do.call(data.frame, aggregate(estimate ~ contrast, LOBO, function(x) c(min=min(x), max=max(x))))
H6.lobo

# H6 Minimum adult reach >=1000
d <- droplevels(subset(d6s, known_adult_reach >= 1000))

H6.reach1000.sample <- data.frame(N=nrow(d), Retailers=length(unique(d$search_brand)))
H6.reach1000.sample

m <- glm(adult_18_34_share ~ platform_category + sector, family=quasibinomial(logit), data=d)

H6.reach1000.cr2 <- coef_test(m, vcov="CR2", cluster=d$search_brand, test="Satterthwaite")
H6.reach1000.cr2

V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H6.reach1000.pred <- avg_predictions(m, variables="platform_category", vcov=V, type="response")
H6.reach1000.pred

H6.reach1000.comp <- avg_comparisons(m, variables=list(platform_category="reference"), vcov=V, type="response")
H6.reach1000.comp

# Remove unnecessary df and s.value columns before Excel export
for (x in c("H6.pred","H6.comp","H6.interaction.pred","H6.interaction.comp","H6.reach1000.pred","H6.reach1000.comp")) {
  z <- as.data.frame(get(x))
  if ("df" %in% names(z)) z$df <- NULL
  if ("s.value" %in% names(z)) z$s.value <- NULL
  assign(x, z)
}

# Export H6 results
file <- "results/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H6" %in% names(wb)) removeWorksheet(wb, "H6")
addWorksheet(wb, "H6")

r <- 1
put <- function(title, x, rowNames=FALSE){
  writeData(wb, "H6", title, startRow=r)
  r <<- r+1
  writeData(wb, "H6", as.data.frame(x), startRow=r, rowNames=rowNames)
  r <<- r+nrow(as.data.frame(x))+2
}

put("H6 Cell support", H6.cells, rowNames=TRUE)
put("H6 Descriptives", H6.desc)
put("H6 Descriptives by sector and platform", H6.desc.sector)
put("H6 Supported sample", H6.sample)
put("H6 Convergence", H6.converged)
put("H6 Link test", H6.link)
put("H6 CR2 inference", H6.cr2, rowNames=TRUE)
put("H6 Adjusted predicted adult 18-34 shares", H6.pred)
put("H6 Facebook vs Instagram contrast", H6.comp)

put("H6 Interaction convergence", H6.interaction.converged)
put("H6 Interaction CR2 inference", H6.interaction.cr2, rowNames=TRUE)
put("H6 Joint platform x sector interaction test", H6.interaction.joint)
put("H6 Predicted adult 18-34 shares by sector and platform", H6.interaction.pred)
put("H6 Platform contrasts by sector", H6.interaction.comp)

put("H6 LOBO range", H6.lobo)

put("H6 Reach >=1000 sample", H6.reach1000.sample)
put("H6 Reach >=1000 CR2 inference", H6.reach1000.cr2, rowNames=TRUE)
put("H6 Reach >=1000 predicted shares", H6.reach1000.pred)
put("H6 Reach >=1000 contrast", H6.reach1000.comp)

saveWorkbook(wb, file, overwrite=TRUE)



