# Placeholder variables describing the shape future infrastructure modules
# are expected to take. None of these are consumed by any resource yet —
# there are no resources in this configuration.

variable "project_name" {
  description = "Short name used to prefix/tag future infrastructure resources."
  type        = string
  default     = "healthcare-ai-governance-platform"
}

variable "environment" {
  description = "Deployment environment label for future resources (e.g. dev, sandbox). No environment is provisioned by this configuration today."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "sandbox", "staging"], var.environment)
    error_message = "environment must be one of: dev, sandbox, staging. Production is intentionally not a valid value for this portfolio project."
  }
}

variable "owner" {
  description = "Free-text owner/maintainer tag applied to future resources."
  type        = string
  default     = "portfolio-project"
}
