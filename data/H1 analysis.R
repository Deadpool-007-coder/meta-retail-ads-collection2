Dataset <- read.csv("C:/Users/Rishu/Desktop/meta-retail-ads-collection2/data/ads_primary_configuration_level.csv", stringsAsFactors=TRUE)

# Required packages
library(clubSandwich)
library(marginaleffects)
library(openxlsx)

# Reference categories
Dataset$target_gender <- factor(Dataset$target_gender, levels=c("All","Men","Women"))
Dataset$sector <- factor(Dataset$sector, levels=c("grocery","fashion","health_beauty","home"))
Dataset$age_scope <- factor(Dataset$age_scope, levels=c("Broad","Narrow"))

# Check reference levels
levels(Dataset$target_gender)
levels(Dataset$sector)
levels(Dataset$age_scope)

# H1a Gender-targeting distribution by sector
H1a.cells <- table(Dataset$sector, Dataset$target_gender)

H1a.props <- prop.table(H1a.cells, 1)
H1a.props

# H1a Pearson chi-square with Monte Carlo p-value
set.seed(20260916)
H1a.chi <- chisq.test(H1a.cells, simulate.p.value=TRUE, B=10000)
H1a.chi

# H1a Expected cell counts
H1a.expected <- chisq.test(H1a.cells, correct=FALSE)$expected
H1a.expected

H1a.expected.check <- data.frame(
  min_expected=min(H1a.expected),
  cells_expected_lt_5=sum(H1a.expected < 5),
  pct_cells_expected_lt_5=100*mean(H1a.expected < 5)
)
H1a.expected.check

# H1a Cramer's V
H1a.cramersv <- sqrt(as.numeric(chisq.test(H1a.cells, correct=FALSE)$statistic)/(sum(H1a.cells)*min(nrow(H1a.cells)-1,ncol(H1a.cells)-1)))
H1a.cramersv

# H1a Binary gender restriction
Dataset$gender_restricted <- ifelse(Dataset$target_gender=="All", 0, 1)

H1a.binary.cells <- table(Dataset$sector, Dataset$gender_restricted)
H1a.binary.cells

H1a.binary.props <- prop.table(H1a.binary.cells, 1)
H1a.binary.props

# H1a Retailer-level proportions
H1a.retailer <- aggregate(gender_restricted ~ search_brand + sector, Dataset, mean)
H1a.retailer

# H1a Primary logistic model
GLM.H1a <- glm(gender_restricted ~ sector, family=binomial(logit), data=Dataset)
summary(GLM.H1a)

# H1a Convergence
GLM.H1a$converged

# H1a Retailer-clustered CR2 inference
H1a.cr2 <- coef_test(GLM.H1a, vcov="CR2", cluster=Dataset$search_brand, test="Satterthwaite")
H1a.cr2

# H1a Odds ratios
H1a.OR <- data.frame(
  Contrast=c(
    "Fashion vs Grocery",
    "Drugstore/Beauty vs Grocery",
    "Home/DIY vs Grocery"
  ),
  beta=H1a.cr2$beta[2:4],
  OR=exp(H1a.cr2$beta[2:4]),
  SE=H1a.cr2$SE[2:4],
  df=H1a.cr2$df_Satt[2:4],
  p_value=H1a.cr2$p_Satt[2:4]
)

H1a.OR$CI_L <- exp(
  H1a.OR$beta -
    qt(0.975, H1a.OR$df)*H1a.OR$SE
)

H1a.OR$CI_U <- exp(
  H1a.OR$beta +
    qt(0.975, H1a.OR$df)*H1a.OR$SE
)

H1a.OR


# H1a Joint sector test
H1a.joint <- Wald_test(GLM.H1a, constraints=constrain_zero("sector", reg_ex=TRUE), vcov="CR2", cluster=Dataset$search_brand, test="HTZ")
H1a.joint

# H1a Predicted probability of gender restriction
H1a.prob.model <- glm(gender_restricted ~ 0 + sector, family=binomial(logit), data=Dataset)

H1a.prob.cr2 <- as.data.frame(
  coef_test(H1a.prob.model, vcov="CR2", cluster=Dataset$search_brand, test="Satterthwaite")
)

H1a.crit <- qt(0.975, df=H1a.prob.cr2$df_Satt)

H1a.pred <- data.frame(
  sector=levels(Dataset$sector),
  estimate=plogis(H1a.prob.cr2$beta),
  std.error=plogis(H1a.prob.cr2$beta)*(1-plogis(H1a.prob.cr2$beta))*H1a.prob.cr2$SE,
  df_Satt=H1a.prob.cr2$df_Satt,
  conf.low=plogis(H1a.prob.cr2$beta-H1a.crit*H1a.prob.cr2$SE),
  conf.high=plogis(H1a.prob.cr2$beta+H1a.crit*H1a.prob.cr2$SE)
)
H1a.pred

# H1a Pairwise sector comparisons
H1a.pairwise <- linear_contrast(
  H1a.prob.model,
  vcov="CR2",
  cluster=Dataset$search_brand,
  contrasts=constrain_pairwise("sector", reg_ex=TRUE),
  test="Satterthwaite",
  p_values=TRUE,
  adjustment_method="holm"
)
H1a.pairwise

# H1a Leave-one-brand-out sensitivity (point estimates)

H1a.brands <- unique(as.character(Dataset$search_brand))

H1a.lobo <- do.call(rbind, lapply(H1a.brands, function(b){
  temp <- Dataset[Dataset$search_brand != b, ]
  p <- tapply(temp$gender_restricted, temp$sector, mean)
  data.frame(
    omitted_brand=b,
    grocery=unname(p["grocery"]),
    fashion=unname(p["fashion"]),
    health_beauty=unname(p["health_beauty"]),
    home=unname(p["home"])
  )
}))
H1a.lobo

H1a.lobo.range <- data.frame(
  sector=c("Grocery","Fashion","Drugstore/Beauty","Home/DIY"),
  min=c(min(H1a.lobo$grocery), min(H1a.lobo$fashion), min(H1a.lobo$health_beauty), min(H1a.lobo$home)),
  max=c(max(H1a.lobo$grocery), max(H1a.lobo$fashion), max(H1a.lobo$health_beauty), max(H1a.lobo$home))
)
H1a.lobo.range

# H1b Age-targeting breadth by sector
H1b.cells <- table(Dataset$sector, Dataset$age_scope)
H1b.cells

H1b.props <- prop.table(H1b.cells, 1)
H1b.props

# H1b Pearson chi-square
H1b.chi <- chisq.test(H1b.cells)
H1b.chi

# H1b Expected cell counts
H1b.expected <- H1b.chi$expected
H1b.expected

H1b.expected.check <- data.frame(
  min_expected=min(H1b.expected),
  cells_expected_lt_5=sum(H1b.expected < 5),
  pct_cells_expected_lt_5=100*mean(H1b.expected < 5)
)
H1b.expected.check

# H1b Cramer's V
H1b.cramersv <- sqrt(as.numeric(chisq.test(H1b.cells, correct=FALSE)$statistic)/(sum(H1b.cells)*min(nrow(H1b.cells)-1,ncol(H1b.cells)-1)))
H1b.cramersv

# H1b Binary Narrow targeting
Dataset$age_narrow <- ifelse(Dataset$age_scope=="Narrow", 1, 0)

# H1b Retailer-level proportions
H1b.retailer <- aggregate(age_narrow ~ search_brand + sector, Dataset, mean)
H1b.retailer

# H1b Primary logistic model
GLM.H1b <- glm(age_narrow ~ sector, family=binomial(logit), data=Dataset)
summary(GLM.H1b)

# H1b Convergence
GLM.H1b$converged

# H1b Retailer-clustered CR2 inference
H1b.cr2 <- coef_test(GLM.H1b, vcov="CR2", cluster=Dataset$search_brand, test="Satterthwaite")
H1b.cr2

# H1b Odds ratios
H1b.OR <- data.frame(
  Contrast=c(
    "Fashion vs Grocery",
    "Drugstore/Beauty vs Grocery",
    "Home/DIY vs Grocery"
  ),
  beta=H1b.cr2$beta[2:4],
  OR=exp(H1b.cr2$beta[2:4]),
  SE=H1b.cr2$SE[2:4],
  df=H1b.cr2$df_Satt[2:4],
  p_value=H1b.cr2$p_Satt[2:4]
)

H1b.OR$CI_L <- exp(
  H1b.OR$beta -
    qt(0.975, H1b.OR$df)*H1b.OR$SE
)

H1b.OR$CI_U <- exp(
  H1b.OR$beta +
    qt(0.975, H1b.OR$df)*H1b.OR$SE
)

H1b.OR


# H1b Joint sector test
H1b.joint <- Wald_test(GLM.H1b, constraints=constrain_zero("sector", reg_ex=TRUE), vcov="CR2", cluster=Dataset$search_brand, test="HTZ")
H1b.joint

# H1b Predicted probability of Narrow targeting
H1b.prob.model <- glm(age_narrow ~ 0 + sector, family=binomial(logit), data=Dataset)

H1b.prob.cr2 <- as.data.frame(
  coef_test(H1b.prob.model, vcov="CR2", cluster=Dataset$search_brand, test="Satterthwaite")
)

H1b.crit <- qt(0.975, df=H1b.prob.cr2$df_Satt)

H1b.pred <- data.frame(
  sector=levels(Dataset$sector),
  estimate=plogis(H1b.prob.cr2$beta),
  std.error=plogis(H1b.prob.cr2$beta)*(1-plogis(H1b.prob.cr2$beta))*H1b.prob.cr2$SE,
  df_Satt=H1b.prob.cr2$df_Satt,
  conf.low=plogis(H1b.prob.cr2$beta-H1b.crit*H1b.prob.cr2$SE),
  conf.high=plogis(H1b.prob.cr2$beta+H1b.crit*H1b.prob.cr2$SE)
)
H1b.pred

# H1b Pairwise sector comparisons
H1b.pairwise <- linear_contrast(
  H1b.prob.model,
  vcov="CR2",
  cluster=Dataset$search_brand,
  contrasts=constrain_pairwise("sector", reg_ex=TRUE),
  test="Satterthwaite",
  p_values=TRUE,
  adjustment_method="holm"
)
H1b.pairwise

# H1b Leave-one-brand-out sensitivity (point estimates)

H1b.lobo <- do.call(rbind, lapply(H1a.brands, function(b){
  temp <- Dataset[Dataset$search_brand != b, ]
  p <- tapply(temp$age_narrow, temp$sector, mean)
  data.frame(
    omitted_brand=b,
    grocery=unname(p["grocery"]),
    fashion=unname(p["fashion"]),
    health_beauty=unname(p["health_beauty"]),
    home=unname(p["home"])
  )
}))
H1b.lobo

H1b.lobo.range <- data.frame(
  sector=c("Grocery","Fashion","Drugstore/Beauty","Home/DIY"),
  min=c(min(H1b.lobo$grocery), min(H1b.lobo$fashion), min(H1b.lobo$health_beauty), min(H1b.lobo$home)),
  max=c(max(H1b.lobo$grocery), max(H1b.lobo$fashion), max(H1b.lobo$health_beauty), max(H1b.lobo$home))
)
H1b.lobo.range

# Export H1 results to one Excel sheet
file <- "C:/Users/Rishu/Desktop/Thesis_Results.xlsx"
wb <- if (file.exists(file)) loadWorkbook(file) else createWorkbook()

if ("H1" %in% names(wb)) removeWorksheet(wb, "H1")
addWorksheet(wb, "H1")

r <- 1
writeData(wb, "H1", "H1a Gender-targeting distribution", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.cells), startRow=r); r <- r+nrow(as.data.frame(H1a.cells))+2

writeData(wb, "H1", "H1a Row proportions", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.props), startRow=r); r <- r+nrow(as.data.frame(H1a.props))+2

writeData(wb, "H1", "H1a Chi-square and Cramer's V", startRow=r); r <- r+1
writeData(wb, "H1", data.frame(Chi_square=unname(H1a.chi$statistic), P_value=H1a.chi$p.value, Cramers_V=H1a.cramersv), startRow=r); r <- r+3

writeData(wb, "H1", "H1a Expected-cell check", startRow=r); r <- r+1
writeData(wb, "H1", H1a.expected.check, startRow=r); r <- r+nrow(H1a.expected.check)+2

writeData(wb, "H1", "H1a Expected cell counts", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.expected), startRow=r); r <- r+nrow(as.data.frame(H1a.expected))+2

writeData(wb, "H1", "H1a Binary restriction proportions", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.binary.props), startRow=r); r <- r+nrow(as.data.frame(H1a.binary.props))+2

writeData(wb, "H1", "H1a Retailer-level proportions", startRow=r); r <- r+1
writeData(wb, "H1", H1a.retailer, startRow=r); r <- r+nrow(H1a.retailer)+2

writeData(wb, "H1", "H1a CR2 inference", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.cr2), startRow=r); r <- r+nrow(as.data.frame(H1a.cr2))+2

writeData(wb, "H1", "H1a Odds ratios", startRow=r); r <- r+1
writeData(wb, "H1", H1a.OR, startRow=r); r <- r+nrow(H1a.OR)+2

writeData(wb, "H1", "H1a Joint sector test", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.joint), startRow=r); r <- r+nrow(as.data.frame(H1a.joint))+2

writeData(wb, "H1", "H1a Predicted probabilities", startRow=r); r <- r+1
writeData(wb, "H1", H1a.pred, startRow=r); r <- r+nrow(H1a.pred)+2

writeData(wb, "H1", "H1a Pairwise sector comparisons", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1a.pairwise), startRow=r); r <- r+nrow(as.data.frame(H1a.pairwise))+2

writeData(wb, "H1", "H1a Leave-one-brand-out (predicted probability by sector)", startRow=r); r <- r+1
writeData(wb, "H1", H1a.lobo, startRow=r); r <- r+nrow(H1a.lobo)+2

writeData(wb, "H1", "H1a LOBO range by sector", startRow=r); r <- r+1
writeData(wb, "H1", H1a.lobo.range, startRow=r); r <- r+nrow(H1a.lobo.range)+3

writeData(wb, "H1", "H1b Age-targeting breadth", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1b.cells), startRow=r); r <- r+nrow(as.data.frame(H1b.cells))+2

writeData(wb, "H1", "H1b Row proportions", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1b.props), startRow=r); r <- r+nrow(as.data.frame(H1b.props))+2

writeData(wb, "H1", "H1b Chi-square and Cramer's V", startRow=r); r <- r+1
writeData(wb, "H1", data.frame(Chi_square=unname(H1b.chi$statistic), P_value=H1b.chi$p.value, Cramers_V=H1b.cramersv), startRow=r); r <- r+3

writeData(wb, "H1", "H1b Expected-cell check", startRow=r); r <- r+1
writeData(wb, "H1", H1b.expected.check, startRow=r); r <- r+nrow(H1b.expected.check)+2

writeData(wb, "H1", "H1b Expected cell counts", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1b.expected), startRow=r); r <- r+nrow(as.data.frame(H1b.expected))+2

writeData(wb, "H1", "H1b Retailer-level proportions", startRow=r); r <- r+1
writeData(wb, "H1", H1b.retailer, startRow=r); r <- r+nrow(H1b.retailer)+2

writeData(wb, "H1", "H1b CR2 inference", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1b.cr2), startRow=r); r <- r+nrow(as.data.frame(H1b.cr2))+2

writeData(wb, "H1", "H1b Odds ratios", startRow=r); r <- r+1
writeData(wb, "H1", H1b.OR, startRow=r); r <- r+nrow(H1b.OR)+2

writeData(wb, "H1", "H1b Joint sector test", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1b.joint), startRow=r); r <- r+nrow(as.data.frame(H1b.joint))+2

writeData(wb, "H1", "H1b Predicted probabilities", startRow=r); r <- r+1
writeData(wb, "H1", H1b.pred, startRow=r); r <- r+nrow(H1b.pred)+2

writeData(wb, "H1", "H1b Pairwise sector comparisons", startRow=r); r <- r+1
writeData(wb, "H1", as.data.frame(H1b.pairwise), startRow=r); r <- r+nrow(as.data.frame(H1b.pairwise))+2

writeData(wb, "H1", "H1b Leave-one-brand-out (predicted probability by sector)", startRow=r); r <- r+1
writeData(wb, "H1", H1b.lobo, startRow=r); r <- r+nrow(H1b.lobo)+2

writeData(wb, "H1", "H1b LOBO range by sector", startRow=r); r <- r+1
writeData(wb, "H1", H1b.lobo.range, startRow=r)

saveWorkbook(wb, file, overwrite=TRUE)

