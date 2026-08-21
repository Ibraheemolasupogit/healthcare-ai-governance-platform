output "resource_prefix" {
  description = "Naming prefix future infrastructure modules should use. No infrastructure is provisioned by this configuration."
  value       = local.resource_prefix
}

output "common_tags" {
  description = "Tag set future infrastructure modules should apply. No infrastructure is provisioned by this configuration."
  value       = local.common_tags
}
