# H7 specification check
# Platform x sector interaction model
# Supported sectors only: Grocery, Health/Beauty, Home

data_file <- "data/ads_primary_configuration_level.csv"
results_file <- "results/Thesis_Results.xlsx"
plot_file <- "results/H7_specification_check.png"

library(dplyr)
library(openxlsx)
library(ggplot2)

Dataset <- read.csv(
  data_file,
  stringsAsFactors = FALSE
)

# Supported H7 comparison sample
# Fashion excluded because there are no Facebook-only observations
d <- Dataset %>%
  filter(
    platform_category %in% c("Facebook-only", "Instagram-only"),
    sector %in% c("grocery", "health_beauty", "home"),
    !is.na(adult_18_34_share)
  ) %>%
  mutate(
    platform_category = factor(
      platform_category,
      levels = c("Facebook-only", "Instagram-only")
    ),
    sector = factor(
      sector,
      levels = c("grocery", "health_beauty", "home")
    )
  )

# H7 platform-by-sector interaction model
m <- glm(
  adult_18_34_share ~ platform_category * sector,
  family = quasibinomial("logit"),
  data = d
)

# Link / specification test
d$hat <- predict(m, type = "link")
d$hat2 <- d$hat^2

link <- glm(
  adult_18_34_share ~ hat + hat2,
  family = quasibinomial("logit"),
  data = d
)

link_out <- as.data.frame(summary(link)$coefficients)
link_out$Term <- rownames(link_out)
rownames(link_out) <- NULL
link_out <- link_out[, c("Term", setdiff(names(link_out), "Term"))]

# Observed versus predicted cell means
d$predicted <- predict(m, type = "response")

cell_out <- d %>%
  group_by(sector, platform_category) %>%
  summarise(
    N = n(),
    observed = mean(adult_18_34_share),
    predicted = mean(predicted),
    difference = observed - predicted,
    .groups = "drop"
  )

# Diagnostic plot
p <- ggplot(cell_out, aes(observed, predicted)) +
  geom_point(size = 3) +
  geom_abline(
    intercept = 0,
    slope = 1,
    linetype = "dashed"
  ) +
  labs(
    x = "Observed mean",
    y = "Predicted mean"
  ) +
  theme_minimal()

ggsave(
  plot_file,
  p,
  width = 6,
  height = 5,
  dpi = 300
)

# Export specification-check results
wb <- loadWorkbook(results_file)

if ("H7_Spec_Check" %in% names(wb)) {
  removeWorksheet(wb, "H7_Spec_Check")
}

addWorksheet(wb, "H7_Spec_Check")

writeData(
  wb,
  "H7_Spec_Check",
  data.frame(
    N = nrow(d),
    Retailers = n_distinct(d$search_brand)
  ),
  startRow = 1
)

writeData(
  wb,
  "H7_Spec_Check",
  "Link test",
  startRow = 4
)

writeData(
  wb,
  "H7_Spec_Check",
  link_out,
  startRow = 5
)

writeData(
  wb,
  "H7_Spec_Check",
  "Observed vs predicted means",
  startRow = 10
)

writeData(
  wb,
  "H7_Spec_Check",
  cell_out,
  startRow = 11
)

insertImage(
  wb,
  "H7_Spec_Check",
  plot_file,
  startRow = 20,
  startCol = 1,
  width = 6,
  height = 5
)

saveWorkbook(
  wb,
  results_file,
  overwrite = TRUE
)