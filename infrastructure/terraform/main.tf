# Intentionally declares no resources and no provider.
#
# This file exists to hold the naming/tagging convention future infrastructure
# modules (Snowflake objects, Fabric capacity, CI service principals, etc.)
# are expected to follow, expressed as a local value so it can be referenced
# once real resources are added. `terraform plan`/`apply` against this
# configuration provisions nothing.

locals {
  resource_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    project     = var.project_name
    environment = var.environment
    owner       = var.owner
    managed_by  = "terraform"
  }
}
