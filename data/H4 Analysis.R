Dataset <- read.csv("data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)

# Required packages
library(clubSandwich)
library(marginaleffects)
library(openxlsx)

dir.create("results", showWarnings = FALSE)

# Reference categories
Dataset$target_gender <- factor(Dataset$target_gender, levels=c("All","Men","Women"))
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))

# Check reference levels
levels(Dataset$target_gender)
levels(Dataset$sector)

# H4 Sample: unrestricted gender targeting only
d4 <- droplevels(subset(Dataset, target_gender=="All" & !is.na(female_delivery_share)))

# H4 Descriptives
H4.desc <- aggregate(female_delivery_share ~ sector, d4, function(x) c(N=length(x), Mean=mean(x), SD=sd(x), Median=median(x), Min=min(x), Max=max(x)))
H4.desc <- do.call(data.frame, H4.desc)
H4.desc

# H4 Sample
H4.sample <- data.frame(N=nrow(d4), Retailers=length(unique(d4$search_brand)))
H4.sample

# H4 Retailer-level means
H4.retailer <- aggregate(female_delivery_share ~ search_brand + sector, d4, mean)
H4.retailer

# H4 Primary fractional-logit model
GLM.3 <- glm(female_delivery_share ~ sector, family=quasibinomial(logit), data=d4)
summary(GLM.3)

# H4 Convergence
H4.converged <- data.frame(Converged=GLM.3$converged)
H4.converged

# H4 Retailer-clustered CR2 inference
H4.cr2 <- coef_test(GLM.3, vcov="CR2", cluster=d4$search_brand, test="Satterthwaite")
H4.cr2

# H4 Joint sector test
H4.joint <- Wald_test(GLM.3, constraints=constrain_zero("sector", reg_ex=TRUE), vcov="CR2", cluster=d4$search_brand, test="HTZ")
H4.joint

# H4 Predicted female delivery shares
V3 <- vcovCR(GLM.3, cluster=d4$search_brand, type="CR2")

H4.pred <- avg_predictions(GLM.3, by="sector", vcov=V3, type="response")
H4.pred

# H4 Sector contrasts vs Grocery
H4.comp <- avg_comparisons(GLM.3, variables=list(sector="reference"), vcov=V3, type="response")
H4.comp

# H4 Brand-level test (sector varies between brands, so test the 20 brand means)
H4.brandtest <- kruskal.test(female_delivery_share ~ sector, data=H4.retailer)
H4.brandtest.df <- data.frame(Statistic=unname(H4.brandtest$statistic), Df=unname(H4.brandtest$parameter), P_value=H4.brandtest$p.value)
H4.brandtest.df

# H4 LOBO
LOBO <- do.call(rbind, lapply(unique(d4$search_brand), function(b){ m <- glm(female_delivery_share ~ sector, family=quasibinomial(logit), data=d4[d4$search_brand != b,]); x <- as.data.frame(avg_predictions(m, by="sector", type="response")); x$brand <- b; x }))

H4.lobo <- do.call(data.frame, aggregate(estimate ~ sector, LOBO, function(x) c(min=min(x), max=max(x))))
H4.lobo

# H4 Minimum reach >=1000
d <- droplevels(subset(d4, known_gender_reach >= 1000))

H4.reach1000.sample <- data.frame(N=nrow(d), Retailers=length(unique(d$search_brand)))
H4.reach1000.sample

m <- glm(female_delivery_share ~ sector, family=quasibinomial(logit), data=d)

H4.reach1000.joint <- Wald_test(m, constraints=constrain_zero("sector", reg_ex=TRUE), vcov="CR2", cluster=d$search_brand, test="HTZ")
H4.reach1000.joint

V <- vcovCR(m, cluster=d$search_brand, type="CR2")

H4.reach1000.pred <- avg_predictions(m, by="sector", vcov=V, type="response")
H4.reach1000.pred

H4.reach1000.comp <- avg_comparisons(m, variables=list(sector="reference"), vcov=V, type="response")
H4.reach1000.comp

# Remove unnecessary df and s.value columns before Excel export
for (x in c("H4.pred","H4.comp","H4.reach1000.pred","H4.reach1000.comp")) {
  z <- as.data.frame(get(x))
  if ("df" %in% names(z)) z$df <- NULL
  if ("s.value" %in% names(z)) z$s.value <- NULL
  assign(x, z)
}

# Export H4 results
file <- "results/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H4" %in% names(wb)) removeWorksheet(wb, "H4")
addWorksheet(wb, "H4")

r <- 1
put <- function(title, x, rowNames=FALSE){ writeData(wb, "H4", title, startRow=r); r <<- r+1; writeData(wb, "H4", as.data.frame(x), startRow=r, rowNames=rowNames); r <<- r+nrow(as.data.frame(x))+2 }

put("H4 Descriptives", H4.desc)
put("H4 Sample", H4.sample)
put("H4 Retailer-level means", H4.retailer)
put("H4 Convergence", H4.converged)
put("H4 CR2 inference", H4.cr2, rowNames=TRUE)
put("H4 Joint sector test", H4.joint)
put("H4 Predicted female shares", H4.pred)
put("H4 Sector contrasts vs Grocery", H4.comp)
put("H4 Brand-level Kruskal-Wallis", H4.brandtest.df)
put("H4 LOBO ranges", H4.lobo)
put("H4 Reach >=1000 sample", H4.reach1000.sample)
put("H4 Reach >=1000 joint sector test", H4.reach1000.joint)
put("H4 Reach >=1000 predicted shares", H4.reach1000.pred)
put("H4 Reach >=1000 contrasts", H4.reach1000.comp)

saveWorkbook(wb, file, overwrite=TRUE)


