Dataset <- read.csv("C:/Users/Rishu/Desktop/meta-retail-ads-collection2/data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)

library(clubSandwich)
library(marginaleffects)
library(lmtest)
library(RcmdrMisc)
library(openxlsx)

Dataset$target_gender <- factor(Dataset$target_gender, levels=c("All","Men","Women"))
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))
Dataset$platform_category <- factor(Dataset$platform_category, levels=c("Both","Facebook-only","Instagram-only","Other"))

levels(Dataset$target_gender)
levels(Dataset$sector)
levels(Dataset$platform_category)

d2 <- droplevels(subset(Dataset, !is.na(female_delivery_share)))

# H2 Descriptives
H2.desc <- numSummary(d2[,"female_delivery_share",drop=FALSE], groups=d2$target_gender, statistics=c("mean","sd","IQR","quantiles"), quantiles=c(0,.25,.5,.75,1))
H2.desc
H2.desc.df <- data.frame(group=rownames(H2.desc$table), H2.desc$table, row.names=NULL)

# H2 Exact 0s and 1s
H2.zeros <- as.data.frame(table(d2$target_gender, d2$female_delivery_share==0))
H2.zeros

H2.ones <- as.data.frame(table(d2$target_gender, d2$female_delivery_share==1))
H2.ones

# H2 Boundary mass by reach
d2$boundary <- ifelse(d2$female_delivery_share==0, "Zero", ifelse(d2$female_delivery_share==1, "One", "Interior"))
H2.boundary <- aggregate(known_gender_reach ~ target_gender + boundary, d2, median)
H2.boundary

# H2 Primary fractional-logit model
GLM.3 <- glm(female_delivery_share ~ target_gender + sector + platform_category, family=quasibinomial(logit), data=d2)
summary(GLM.3)

# H2 Convergence
H2.converged <- data.frame(Converged=GLM.3$converged)
H2.converged

# H2 Retailer-clustered CR2 inference
H2.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d2$search_brand, test="Satterthwaite")
H2.cr2

# H2 HTZ joint target-gender test
H2.joint.gender <- as.data.frame(Wald_test(GLM.3, constraints=constrain_zero("target_gender", reg_ex=TRUE), vcov="CR2", cluster=d2$search_brand, test="HTZ"))
H2.joint.gender

# H2 Predicted shares and targeting contrasts
V3 <- vcovCR(GLM.3, cluster=d2$search_brand, type="CR2")

H2.pred <- avg_predictions(GLM.3, variables="target_gender", vcov=V3, type="response")
H2.pred

H2.comp <- avg_comparisons(GLM.3, variables=list(target_gender="reference"), vcov=V3, type="response")
H2.comp

# H2 Specification / link test
d2$hat <- predict(GLM.3, type="link")
d2$hat2 <- d2$hat^2

m <- glm(female_delivery_share ~ hat + hat2, family=quasibinomial(logit), data=d2)
H2.link <- data.frame(Term=rownames(summary(m)$coefficients), summary(m)$coefficients, row.names=NULL)
H2.link

# H2 LOBO
brands <- unique(d2$search_brand)

LOBO <- do.call(rbind, lapply(brands, function(b){
  m <- glm(female_delivery_share ~ target_gender + sector + platform_category, family=quasibinomial(logit), data=d2[d2$search_brand != b,])
  x <- as.data.frame(avg_comparisons(m, variables=list(target_gender="reference"), type="response"))
  x$brand <- b
  x
}))

H2.lobo <- do.call(data.frame, aggregate(estimate ~ contrast, LOBO, function(x) c(min=min(x), max=max(x))))
H2.lobo

# H2 OLS robustness
m <- lm(female_delivery_share ~ target_gender + sector + platform_category, data=d2)

H2.ols.range <- data.frame(Min_fitted=min(fitted(m)), Max_fitted=max(fitted(m)), Outside_0_1=sum(fitted(m)<0 | fitted(m)>1))
H2.ols.range

H2.ols.bp <- bptest(m)
H2.ols.bp

H2.ols.cr2 <- coef_test(m, vcov="CR2", cluster=d2$search_brand, test="Satterthwaite")
H2.ols.cr2

# H2 Alternative gender denominator
d2$female_share_total <- with(d2, de_female/(de_male + de_female + de_unknown))

m <- glm(female_share_total ~ target_gender + sector + platform_category, family=quasibinomial(logit), data=d2)
V <- vcovCR(m, cluster=d2$search_brand, type="CR1S")

H2.altdenom <- avg_comparisons(m, variables=list(target_gender="reference"), vcov=V, type="response")
H2.altdenom

# H2 Minimum reach >=1000
d <- droplevels(subset(d2, known_gender_reach >= 1000))

m <- glm(female_delivery_share ~ target_gender + sector + platform_category, family=quasibinomial(logit), data=d)
V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H2.reach1000 <- avg_comparisons(m, variables=list(target_gender="reference"), vcov=V, type="response")
H2.reach1000

# H2 Reach-weighted model
m <- glm(female_delivery_share ~ target_gender + sector + platform_category, family=quasibinomial(logit), weights=known_gender_reach, data=d2)
V <- vcovCR(m, cluster=d2$search_brand, type="CR2")

H2.weighted <- avg_comparisons(m, variables=list(target_gender="reference"), vcov=V, type="response")
H2.weighted

# Clean output for Excel
clean <- function(x){
  x <- as.data.frame(x)
  if ("df" %in% names(x)) x$df <- NULL
  if ("s.value" %in% names(x)) x$s.value <- NULL
  x
}

# Export H2 results
file <- "C:/Users/Rishu/Desktop/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H2" %in% names(wb)) removeWorksheet(wb, "H2")
addWorksheet(wb, "H2")

r <- 1

put <- function(title, x, rowNames=FALSE){
  x <- clean(x)
  writeData(wb, "H2", title, startRow=r)
  r <<- r+1
  writeData(wb, "H2", x, startRow=r, rowNames=rowNames)
  r <<- r+nrow(x)+2
}

put("H2 Descriptives", H2.desc.df)
put("H2 Exact zeros", H2.zeros)
put("H2 Exact ones", H2.ones)
put("H2 Boundary reach medians", H2.boundary)
put("H2 Convergence", H2.converged)
put("H2 CR2 inference", H2.cr2, rowNames=TRUE)
put("H2 Joint target-gender HTZ test", H2.joint.gender)
put("H2 Predicted female shares", H2.pred)
put("H2 Targeting contrasts", H2.comp)
put("H2 Link test", H2.link)
put("H2 LOBO ranges", H2.lobo)
put("H2 OLS fitted-range check", H2.ols.range)
put("H2 OLS Breusch-Pagan", data.frame(Statistic=unname(H2.ols.bp$statistic), Df=unname(H2.ols.bp$parameter), P_value=H2.ols.bp$p.value))
put("H2 OLS CR2 inference", H2.ols.cr2, rowNames=TRUE)
put("H2 Alternative denominator", H2.altdenom)
put("H2 Reach >=1000", H2.reach1000)
put("H2 Reach-weighted", H2.weighted)

saveWorkbook(wb, file, overwrite=TRUE)

